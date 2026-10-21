"""Request identity, real cancellation, clean startup, and provider failure QA."""
import asyncio
import io
import sys
import time
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from server import create_app
from voice import Voicevox, VoiceError, validate_wav


def pcm():
    b=io.BytesIO()
    with wave.open(b,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b'\0'*192000)
    return b.getvalue()

class ControlledVoice:
    credit='VOICEVOX:雨晴はう'
    def __init__(self):
        self.started=asyncio.Event();self.cancelled=asyncio.Event();self.gate=asyncio.Event();self.gate.set()
        self.audio=pcm();self.calls=0
    async def synthesize(self,text):
        self.calls+=1;self.started.set()
        try: await self.gate.wait()
        except asyncio.CancelledError:
            self.cancelled.set();raise
        return self.audio
    async def status(self): return {'available':True,'provider':'VOICEVOX','version':'test'}

class Lifecycle(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.voice=ControlledVoice();self.client=TestClient(TestServer(create_app(self.voice)))
        await self.client.start_server();await self.client.post('/api/mode',json={'mode':'ai'})
    async def asyncTearDown(self): await self.client.close()
    async def say(self,identifier='one'):
        return await self.client.post('/api/speech',json={'text':'こんにちは','request_id':identifier})
    async def state(self): return await (await self.client.get('/api/state')).json()
    async def test_stop_really_cancels_provider_and_late_result(self):
        self.voice.gate.clear();pending=asyncio.create_task(self.say())
        await self.voice.started.wait()
        self.assertEqual((await self.state())['speech']['phase'],'synthesizing')
        r=await self.client.post('/api/speech/cancel',json={'request_id':'one'})
        self.assertTrue((await r.json())['cancelled'])
        await asyncio.wait_for(self.voice.cancelled.wait(),1)
        self.assertEqual((await pending).status,409)
        self.assertEqual((await self.state())['mode'],'ai')
        self.assertEqual((await self.state())['speech']['phase'],'idle')
    async def test_prearrival_cancel_tombstone(self):
        await self.client.post('/api/speech/cancel',json={'request_id':'one'})
        self.assertEqual((await self.say()).status,409);self.assertEqual(self.voice.calls,0)
    async def test_stale_stop_does_not_cancel_replacement(self):
        first=await (await self.say()).json();second=await (await self.say('two')).json()
        r=await self.client.post('/api/speech/cancel',json={'request_id':'one'})
        self.assertTrue((await r.json())['ignored'])
        self.assertEqual((await self.state())['speech']['clip_id'],second['clip_id'])
        self.assertEqual((await self.say('two')).status,409)
        self.assertNotEqual(first['clip_id'],second['clip_id'])
    async def test_supersession_cancels_old_pending_task(self):
        self.voice.gate.clear();first=asyncio.create_task(self.say())
        await self.voice.started.wait();second=asyncio.create_task(self.say('two'))
        await asyncio.wait_for(self.voice.cancelled.wait(),1);self.voice.gate.set()
        self.assertEqual((await first).status,409);self.assertEqual((await second).status,200)
    async def test_owner_disconnect_cancels_pending_task(self):
        ws=await self.client.ws_connect('/ws?role=controller');await ws.receive_json()
        self.voice.gate.clear();pending=asyncio.create_task(self.say())
        await self.voice.started.wait();await ws.close()
        await asyncio.wait_for(self.voice.cancelled.wait(),1)
        self.assertEqual((await pending).status,409)
    async def test_stop_active_clip_rejects_playback(self):
        event=await (await self.say()).json()
        await self.client.post('/api/speech/cancel',json={})
        r=await self.client.post('/api/playback',json={'clip_id':event['clip_id'],'state':'playing','position':0,'sequence':0})
        self.assertEqual(r.status,409)
        self.assertEqual((await self.state())['parameters']['ParamMouthOpenY'],0)
    async def test_invalid_audio_cannot_be_published(self):
        self.voice.audio=b'not wav'
        r=await self.say();self.assertEqual(r.status,503)
        self.assertIn('PCM WAV',await r.text())
        self.assertEqual((await self.state())['speech']['error'],'invalid_audio')
    async def test_health_and_validation(self):
        self.assertTrue((await (await self.client.get('/api/voice')).json())['available'])
        for rid in ('',4,'x'*129):
            self.assertEqual((await self.say(rid)).status,400)
        self.assertEqual((await self.client.post('/api/speech',data='{')).status,400)
        self.assertEqual((await self.client.post('/api/speech/cancel',json=[])).status,400)
    async def test_rate_and_seek_duration(self):
        event=await (await self.say()).json()
        p={'clip_id':event['clip_id'],'state':'playing','position':1,'sequence':0,'playback_rate':2}
        performance=await (await self.client.post('/api/playback',json=p)).json()
        self.assertAlmostEqual(performance['until']-performance['started_at'],2,places=2)
        self.assertAlmostEqual(performance['until']-time.time(),1.5,delta=.1)
        for rate in (0,True,8):
            self.assertEqual((await self.client.post('/api/playback',json={**p,'playback_rate':rate,'sequence':1})).status,400)
    async def test_clean_checkout_without_vendor(self):
        original = Path.is_dir
        with patch('pathlib.Path.is_dir',lambda path: False if path.name == 'vendor' else original(path)):
            app=create_app(self.voice)
        self.assertIsNotNone(app)

class Provider(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.speakers=[{'name':'雨晴はう','styles':[{'name':'ノーマル','id':10}]}]
        async def version(r): return web.json_response('test-engine')
        async def speakers(r): return web.json_response(self.speakers)
        async def query(r): return web.json_response({})
        async def synth(r): return web.Response(body=pcm(),content_type='audio/wav')
        app=web.Application();app.router.add_get('/version',version);app.router.add_get('/speakers',speakers)
        app.router.add_post('/audio_query',query);app.router.add_post('/synthesis',synth)
        self.server=TestServer(app);await self.server.start_server()
        self.voice=Voicevox();self.voice.url=str(self.server.make_url('')).rstrip('/')
    async def asyncTearDown(self): await self.server.close()
    async def test_provider_status_and_fresh_pcm(self):
        self.assertTrue((await self.voice.status())['available'])
        self.assertEqual(validate_wav(await self.voice.synthesize('新しい文章')),4)
    async def test_missing_speaker_clear_error(self):
        self.speakers=[]
        self.assertEqual((await self.voice.status())['error'],'speaker_missing')
        with self.assertRaises(VoiceError) as e: await self.voice.synthesize('声')
        self.assertEqual(e.exception.code,'speaker_missing')
    async def test_offline_health(self):
        await self.server.close()
        self.assertEqual((await self.voice.status())['error'],'engine_unavailable')
    async def test_truncated_wav_rejected(self):
        with self.assertRaises(VoiceError): validate_wav(pcm()[:-10])

if __name__=='__main__':unittest.main()
