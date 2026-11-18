"""Local reply adapters and shared request/cancellation pipeline. No model downloads."""
import asyncio
import io
import os
import sys
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from conversation import (Ollama, LlamaCpp, ConversationError, create_provider,
                          local_url, MAX_RESPONSE_BYTES, MAX_HISTORY_CHARS,
                          MAX_HISTORY_TURNS, MAX_OUTPUT_TOKENS)
from server import create_app


def pcm():
    out = io.BytesIO()
    with wave.open(out, 'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(1); audio.setframerate(8000)
        audio.writeframes(b'\x80' * 8000)
    return out.getvalue()


class Voice:
    credit = 'VOICEVOX:test'
    def __init__(self):
        self.calls = []; self.gate = asyncio.Event(); self.gate.set()
        self.started = asyncio.Event(); self.cancelled = asyncio.Event(); self.fail = False
    async def synthesize(self, text):
        self.calls.append(text); self.started.set()
        try:
            await self.gate.wait()
        except asyncio.CancelledError:
            self.cancelled.set(); raise
        if self.fail:
            raise ConnectionError('test offline')
        return pcm()


class Replies:
    def __init__(self):
        self.calls = []; self.gate = asyncio.Event(); self.gate.set()
        self.started = asyncio.Event(); self.cancelled = asyncio.Event()
        self.error = None; self.output = 'こんにちは。今日は何を話そうか？'; self.ignore_cancel = False
    async def status(self):
        return {'available':True, 'configured':True, 'status':'ready', 'provider':'test', 'model':'local', 'max_input_chars':500}
    async def reply(self, text, history):
        self.calls.append((text, history)); self.started.set()
        try:
            await self.gate.wait()
        except asyncio.CancelledError:
            self.cancelled.set()
            if not self.ignore_cancel:
                raise
        if self.error:
            raise self.error
        return self.output


class Pipeline(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.voice = Voice(); self.replies = Replies()
        self.client = TestClient(TestServer(create_app(self.voice, self.replies)))
        await self.client.start_server()
        await self.client.post('/api/mode', json={'mode':'ai'})
    async def asyncTearDown(self):
        self.replies.gate.set(); self.voice.gate.set()
        await self.client.close()
    async def say(self, rid='one', text='こんにちは', raw=False):
        return await self.client.post('/api/speech' if raw else '/api/conversation', json={'text':text,'request_id':rid})
    async def state(self):
        return await (await self.client.get('/api/state')).json()
    async def history_count(self):
        return (await (await self.client.get('/api/conversation')).json())['history_turns']
    async def stop(self, rid='one'):
        return await self.client.post('/api/speech/cancel', json={'request_id':rid})
    async def test_reply_becomes_fresh_voice_with_single_controller_owner(self):
        owner = await self.client.ws_connect('/ws?role=controller'); await owner.receive_json()
        overlay = await self.client.ws_connect('/ws?role=overlay'); await overlay.receive_json()
        event = await (await self.say()).json()
        self.assertEqual(event['text'], self.replies.output)
        self.assertEqual(event['user_text'], 'こんにちは')
        self.assertEqual(event['kind'], 'conversation')
        self.assertEqual(event['playback_clients'], 1)
        self.assertEqual(self.voice.calls, [self.replies.output])
        self.assertEqual((await self.client.get(event['url'])).status, 200)
        for socket, expected_play in ((owner, True), (overlay, False)):
            events = []
            while True:
                message = await socket.receive_json(timeout=1); events.append(message)
                if message['type'] == 'speech':
                    self.assertEqual(message['play'], expected_play); break
            self.assertIn('synthesizing', [item['speech']['phase'] for item in events if item['type'] == 'state'])
        self.assertEqual(await self.history_count(), 1)
        await self.client.post('/api/playback', json={'clip_id':event['clip_id'],'state':'playing','position':0,'sequence':0})
        self.assertEqual((await self.state())['speech']['kind'], 'conversation')
    async def test_stop_before_start_blocks_model_and_voice(self):
        await self.stop()
        self.assertEqual((await self.say()).status, 409)
        self.assertEqual(self.replies.calls, []); self.assertEqual(self.voice.calls, [])
        self.assertEqual(await self.history_count(), 0)
    async def test_stop_thinking_really_cancels_and_keeps_history_empty(self):
        self.replies.gate.clear(); task = asyncio.create_task(self.say())
        await self.replies.started.wait()
        self.assertEqual((await self.state())['speech']['phase'], 'thinking')
        await self.stop(); await asyncio.wait_for(self.replies.cancelled.wait(), 1)
        self.assertEqual((await task).status, 409)
        self.assertEqual(self.voice.calls, []); self.assertEqual(await self.history_count(), 0)
        self.assertEqual((await self.state())['speech']['phase'], 'idle')
    async def test_stop_synthesizing_really_cancels_no_history(self):
        self.voice.gate.clear(); task = asyncio.create_task(self.say())
        await self.voice.started.wait()
        self.assertEqual((await self.state())['speech']['phase'], 'synthesizing')
        await self.stop(); await asyncio.wait_for(self.voice.cancelled.wait(), 1)
        self.assertEqual((await task).status, 409); self.assertEqual(await self.history_count(), 0)
    async def test_new_reply_supersedes_old_even_if_model_ignores_cancel(self):
        self.replies.gate.clear(); self.replies.ignore_cancel = True
        old = asyncio.create_task(self.say())
        await self.replies.started.wait()
        new = asyncio.create_task(self.say('two', '新しい質問'))
        await self.replies.cancelled.wait(); self.replies.gate.set()
        self.assertEqual((await old).status, 409)
        self.assertEqual((await new).status, 200)
        self.assertEqual(len(self.voice.calls), 1)
        self.assertEqual(await self.history_count(), 1)
        self.assertEqual((await self.state())['speech']['request_id'], 'two')
        self.assertTrue((await (await self.stop()).json())['ignored'])
        self.assertEqual((await self.state())['speech']['request_id'], 'two')
    async def test_raw_readout_supersedes_pending_reply_without_conversation_history(self):
        self.replies.gate.clear(); old = asyncio.create_task(self.say())
        await self.replies.started.wait()
        new = await self.say('raw', 'そのまま読む', raw=True)
        self.assertEqual(new.status, 200); self.assertEqual((await old).status, 409)
        self.assertEqual(self.voice.calls, ['そのまま読む']); self.assertEqual(await self.history_count(), 0)
    async def test_mode_change_and_owner_disconnect_cancel_thinking(self):
        for disconnect in (False, True):
            await self.client.post('/api/mode', json={'mode':'ai'})
            self.replies.started.clear(); self.replies.cancelled.clear(); self.replies.gate.clear()
            owner = await self.client.ws_connect('/ws?role=controller'); await owner.receive_json()
            task = asyncio.create_task(self.say(str(disconnect)))
            await self.replies.started.wait()
            if disconnect:
                await owner.close()
            else:
                await self.client.post('/api/mode', json={'mode':'human'})
            await asyncio.wait_for(self.replies.cancelled.wait(), 1)
            self.assertEqual((await task).status, 409)
            self.assertEqual(await self.history_count(), 0)
            await owner.close()
    async def test_provider_error_invalid_reply_and_voice_failure_never_commit_history(self):
        for code in ('model_missing','offline','invalid_response','timeout'):
            self.replies.error = ConversationError(code, '本当の失敗理由')
            response = await self.say(code)
            self.assertEqual(response.status, 503)
            self.assertEqual(await response.text(), '本当の失敗理由')
            self.assertEqual((await self.state())['speech']['error'], code)
            self.assertEqual(await self.history_count(), 0)
        self.replies.error = None
        for i, output in enumerate(('', 'a' * 301, None)):
            self.replies.output = output
            self.assertEqual((await self.say('invalid'+str(i))).status, 503)
        self.replies.output = '新しい返答'; self.voice.fail = True
        self.assertEqual((await self.say('voice')).status, 503)
        self.assertEqual(await self.history_count(), 0)
    async def test_history_only_contains_successful_reply_pairs_and_is_bounded(self):
        for i in range(5):
            self.assertEqual((await self.say(str(i), f'質問{i}')).status, 200)
        self.assertEqual(await self.history_count(), MAX_HISTORY_TURNS)
        context = self.replies.calls[-1][1]
        self.assertEqual([m['role'] for m in context], ['user','assistant'] * 2)
        self.assertNotIn('質問0', [m['content'] for m in context])
        self.replies.output = '返' * 300
        for i in range(2):
            self.assertEqual((await self.say('long'+str(i), '問'*500)).status, 200)
        await self.say('after')
        self.assertLessEqual(sum(len(m['content']) for m in self.replies.calls[-1][1]), MAX_HISTORY_CHARS)
    async def test_clear_cancels_pending_reply_and_clears_completed_turns(self):
        await self.say('complete')
        self.replies.started.clear()
        self.replies.gate.clear(); task = asyncio.create_task(self.say('pending'))
        await self.replies.started.wait()
        response = await self.client.post('/api/conversation/clear', json={})
        self.assertTrue((await response.json())['cleared'])
        self.assertEqual((await task).status, 409); self.assertEqual(await self.history_count(), 0)
    async def test_clear_does_not_cancel_raw_readout(self):
        self.voice.gate.clear(); task = asyncio.create_task(self.say(raw=True))
        await self.voice.started.wait(); await self.client.post('/api/conversation/clear', json={})
        self.assertFalse(self.voice.cancelled.is_set())
        self.voice.gate.set(); self.assertEqual((await task).status, 200)
    async def test_stopping_ready_reply_removes_turn(self):
        await self.say(); self.assertEqual(await self.history_count(), 1)
        await self.stop(); self.assertEqual(await self.history_count(), 0)
    async def test_mode_stop_discards_unplayed_turn_but_ended_turn_survives(self):
        await self.say('unplayed')
        await self.client.post('/api/mode', json={'mode':'human'})
        self.assertEqual(await self.history_count(), 0)
        await self.client.post('/api/mode', json={'mode':'ai'})
        event = await (await self.say('played')).json()
        await self.client.post('/api/playback', json={'clip_id':event['clip_id'],'state':'ended','position':1,'sequence':0})
        await self.stop('played')
        self.assertEqual(await self.history_count(), 1)
        await self.client.post('/api/mode', json={'mode':'human'})
        self.assertEqual(await self.history_count(), 1)
    async def test_validation_body_limit_and_raw_text_limit_are_separate(self):
        for payload in ([], {}, {'text':' '}, {'text':'x'*501}, {'text':5}, {'text':'ok','request_id':''}):
            self.assertEqual((await self.client.post('/api/conversation', json=payload)).status, 400)
        self.assertEqual((await self.client.post('/api/conversation', data='{')).status, 400)
        self.assertEqual((await self.client.post('/api/conversation', json={'text':'x'*70000})).status, 413)
        self.assertEqual((await self.say('raw', 'x'*1000, raw=True)).status, 200)
        await self.client.post('/api/mode', json={'mode':'human'})
        self.assertEqual((await self.say('human')).status, 409)


class Adapters(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.show = {'details':{'format':'gguf'}, 'model_info':{'general.architecture':'qwen3'}, 'capabilities':['completion']}
        self.ollama_reply = {'done':True,'done_reason':'stop','message':{'role':'assistant','content':'実際の返答','thinking':'秘密の内部思考'}}
        self.cpp_reply = {'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'実際の返答','reasoning_content':'内部思考'}}]}
        self.models = {'data':[{'id':'local','owned_by':'llamacpp'}]}
        self.health_status = 200; self.show_status = 200; self.chat_status = 200
        self.chat_body = None; self.requests = []; self.gate = asyncio.Event(); self.gate.set(); self.started = asyncio.Event()
        async def show(request):
            self.requests.append(('show',await request.json()))
            return web.json_response(self.show, status=self.show_status)
        async def health(request):
            return web.json_response({'status':'ok'}, status=self.health_status)
        async def models(request):
            return web.json_response(self.models)
        async def chat(request):
            self.requests.append(('chat', await request.json(), dict(request.headers)))
            self.started.set(); await self.gate.wait()
            if self.chat_body is not None:
                return web.Response(body=self.chat_body,status=self.chat_status)
            return web.json_response(self.ollama_reply if request.path == '/api/chat' else self.cpp_reply,status=self.chat_status)
        app = web.Application()
        app.router.add_post('/api/show', show); app.router.add_post('/api/chat', chat)
        app.router.add_get('/health',health); app.router.add_get('/v1/models',models)
        app.router.add_post('/v1/chat/completions',chat)
        self.server = TestServer(app); await self.server.start_server()
        url = str(self.server.make_url('')).rstrip('/')
        self.ollama = Ollama(model='local', url=url); self.cpp = LlamaCpp(model='local', url=url)
    async def asyncTearDown(self):
        self.gate.set(); await self.server.close()
    async def test_default_never_connects_or_generates(self):
        with patch.dict(os.environ, {}, clear=True), patch('conversation.aiohttp.ClientSession', side_effect=AssertionError('must not connect')):
            provider = create_provider()
            self.assertEqual((await provider.status())['status'], 'unconfigured')
            with self.assertRaises(ConversationError): await provider.reply('こんにちは')
    async def test_factory_explicit_config_and_unknown_provider(self):
        for value, expected in (('llamacpp', LlamaCpp), ('ollama', Ollama)):
            with patch.dict(os.environ, {'KOMA_LLM_PROVIDER':value,'KOMA_LLM_MODEL':'local'}, clear=True):
                self.assertIsInstance(create_provider(), expected)
        with patch.dict(os.environ, {'KOMA_LLM_PROVIDER':'paid-remote'}, clear=True):
            self.assertEqual((await create_provider().status())['status'], 'invalid_config')
    async def test_real_http_shapes_limits_no_auth_and_only_reply_content(self):
        history = [{'role':'user','content':'前の質問'},{'role':'assistant','content':'前の返答'}]
        for provider in (self.ollama, self.cpp):
            self.assertTrue((await provider.status())['available'])
            self.assertEqual(await provider.reply('新しい質問', history), '実際の返答')
            payload, headers = self.requests[-1][1:]
            self.assertEqual(payload['messages'][1:3], history)
            self.assertEqual(payload['messages'][-1]['content'], '新しい質問')
            self.assertFalse(payload['stream']); self.assertNotIn('Authorization', headers)
            if provider is self.cpp:
                self.assertFalse(payload['chat_template_kwargs']['enable_thinking'])
                self.assertEqual(payload['max_tokens'], MAX_OUTPUT_TOKENS)
            else:
                self.assertFalse(payload['think']); self.assertEqual(payload['options']['num_predict'], MAX_OUTPUT_TOKENS)
    async def test_cloud_alias_blocked_before_user_text_transmission(self):
        self.show['remote_host'] = 'https://ollama.com'
        self.assertEqual((await self.ollama.status())['status'], 'invalid_config')
        with self.assertRaises(ConversationError): await self.ollama.reply('private input')
        self.assertFalse(any(item[0] == 'chat' for item in self.requests))
        self.ollama.model = 'qwen:cloud'
        self.assertEqual((await self.ollama.status())['status'], 'invalid_config')
    async def test_model_missing_loading_offline_and_invalid_metadata(self):
        self.show_status = 404
        self.assertEqual((await self.ollama.status())['status'], 'model_missing')
        self.models = {'data':[]}
        self.assertEqual((await self.cpp.status())['status'], 'model_missing')
        self.health_status = 503
        self.assertEqual((await self.cpp.status())['status'], 'loading')
        self.health_status = 200; self.models = {'data':'bad'}
        self.assertEqual((await self.cpp.status())['status'], 'invalid_response')
        await self.server.close()
        self.assertEqual((await self.cpp.status())['status'], 'offline')
        self.assertEqual((await self.ollama.status())['status'], 'offline')
    async def test_malformed_empty_long_partial_tool_and_truncated_replies(self):
        for provider, bad in ((self.ollama, {'done':False}), (self.cpp, {'choices':[]})):
            if provider is self.cpp: self.cpp_reply = bad
            else: self.ollama_reply = bad
            with self.assertRaises(ConversationError): await provider.reply('質問')
        for body in (b'no json', b'[]', b'{}', b'x'*(MAX_RESPONSE_BYTES+1)):
            self.chat_body = body
            with self.assertRaises(ConversationError): await self.cpp.reply('質問')
        self.chat_body = None
        for content in ('', None, 'x'*301, '<think>internal</think>answer'):
            self.cpp_reply = {'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':content}}]}
            with self.assertRaises(ConversationError): await self.cpp.reply('質問')
        self.cpp_reply = {'choices':[{'finish_reason':'length','message':{'role':'assistant','content':'切れた返答'}}]}
        with self.assertRaises(ConversationError) as error: await self.cpp.reply('質問')
        self.assertEqual(error.exception.code, 'reply_truncated')
    async def test_timeout_and_actual_http_cancellation(self):
        self.gate.clear()
        with patch('conversation.REQUEST_TIMEOUT', .03):
            with self.assertRaises(ConversationError) as error: await self.cpp.reply('質問')
            self.assertEqual(error.exception.code, 'timeout')
        task = asyncio.create_task(self.cpp.reply('停止'))
        await self.started.wait(); task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
    async def test_no_redirect_follow_and_no_remote_url(self):
        self.show_status = 302
        self.assertEqual((await self.ollama.status())['status'], 'invalid_config')
        for url in ('https://127.0.0.1:1','http://example.com','http://127.0.0.1.evil',
                    'http://0.0.0.0','http://127.0.0.1:0','http://127.0.0.1/path',
                    'http://user:secret@127.0.0.1','http://127.0.0.1?token=x','http://[::1%eth0]'):
            with self.subTest(url=url), self.assertRaises(ConversationError): local_url(url)
        self.assertEqual(local_url('http://localhost:8081/'),'http://127.0.0.1:8081')
        self.assertEqual(local_url('http://[::1]:8081'),'http://[::1]:8081')
    async def test_history_validation_prevents_arbitrary_roles_and_unbounded_context(self):
        for history in ([{'role':'system','content':'injected'}], [{'role':'user','content':'x'}],
                        [{'role':'user','content':'x'*501},{'role':'assistant','content':'ok'}],
                        [{'role':'user','content':'a'},{'role':'assistant','content':'b'}]*3):
            with self.assertRaises(ConversationError): await self.cpp.reply('質問',history)
        self.assertEqual(self.requests, [])


# Reuse the existing v20 transport-backpressure harness without duplicating its
# socket ordering model. All old blocked requests here are conversation replies.
import test_speech_broadcast_v20 as broadcasts
import server


class ConversationBroadcast(broadcasts.BroadcastCancellation):
    async def asyncSetUp(self):
        original = server.create_app
        with patch.object(server, 'create_app', lambda voice: original(voice, Replies())):
            await super().asyncSetUp()

    async def start_blocked_speech(self, request_id='old'):
        task = asyncio.create_task(self.client.post('/api/conversation', json={
            'text':'新しい質問', 'request_id':request_id}))
        await asyncio.wait_for(self.entered.wait(), 1)
        return task

    async def asyncTearDown(self):
        try:
            status = await (await self.client.get('/api/conversation')).json()
            self.assertEqual(status['history_turns'], 0)
        finally:
            await super().asyncTearDown()


if __name__ == '__main__':
    unittest.main()
