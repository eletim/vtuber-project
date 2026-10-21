"""Speech delivery ownership, cancellation and provider failures."""
import asyncio
import io
import wave
import sys
import unittest
from pathlib import Path
from aiohttp.test_utils import TestClient, TestServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from server import create_app

class Voice:
    credit='VOICEVOX:雨晴はう'
    def __init__(self): self.gate=asyncio.Event(); self.gate.set(); self.fail=False
    async def synthesize(self,text):
        await self.gate.wait()
        if self.fail: raise ConnectionError('offline')
        buffer=io.BytesIO()
        with wave.open(buffer,'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(1);wav.setframerate(24000);wav.writeframes(b'\x80' * 96000)
        return buffer.getvalue()

class Speech(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.voice=Voice();self.client=TestClient(TestServer(create_app(self.voice)))
        await self.client.start_server()
        await self.client.post('/api/mode',json={'mode':'ai'})
    async def asyncTearDown(self): await self.client.close()
    async def test_single_player_overlay_and_download(self):
        a=await self.client.ws_connect('/ws?role=controller');await a.receive_json()
        b=await self.client.ws_connect('/ws?role=overlay');await b.receive_json()
        r=await self.client.post('/api/speech',json={'text':'こんにちは'})
        event=await r.json();self.assertEqual(event['playback_clients'],1)
        self.assertEqual((await a.receive_json())['type'],'cancel_speech')
        self.assertEqual((await b.receive_json())['type'],'cancel_speech')
        self.assertEqual((await a.receive_json())['type'],'state');self.assertEqual((await b.receive_json())['type'],'state')
        self.assertTrue((await a.receive_json())['play']);self.assertFalse((await b.receive_json())['play'])
        wav=await self.client.get(event['url']);self.assertTrue((await wav.read()).startswith(b'RIFF'))
        await a.close();await b.close()
    async def test_inflight_cancel_and_error(self):
        self.voice.gate.clear()
        task=asyncio.create_task(self.client.post('/api/speech',json={'text':'遅い音声'}))
        await asyncio.sleep(.03)
        await self.client.post('/api/mode',json={'mode':'human'})
        self.voice.gate.set();self.assertEqual((await task).status,409)
        await self.client.post('/api/mode',json={'mode':'ai'})
        self.voice.fail=True
        self.assertEqual((await self.client.post('/api/speech',json={'text':'接続失敗'})).status,503)
    async def test_performance_validation_and_mode_reset(self):
        for data in ({'emotion':'invalid'},{'enabled':'yes'},{'duration':-1}):
            self.assertEqual((await self.client.post('/api/performance',json=data)).status,400)
        r=await self.client.post('/api/performance',json={'emotion':'thoughtful','duration':4})
        self.assertEqual((await r.json())['emotion'],'thoughtful')
        await self.client.post('/api/mode',json={'mode':'human'})
        state=await (await self.client.get('/api/state')).json()
        self.assertEqual(state['performance']['emotion'],'neutral')

    async def test_playback_drives_emotion_and_pause_resume(self):
        event=await (await self.client.post('/api/speech',json={'text':'こんにちは','emotion':'happy'})).json()
        state=await (await self.client.get('/api/state')).json()
        self.assertEqual(state['performance']['emotion'],'neutral')
        self.assertEqual(event['emotion'],'happy')
        self.assertEqual(event['duration'],4)
        async def update(phase, position, sequence):
            return await self.client.post('/api/playback',json={'clip_id':event['clip_id'], 'state':phase,
                                                               'position':position,'sequence':sequence})
        response=await update('playing',0,0)
        self.assertEqual(response.status,200)
        self.assertEqual((await response.json())['emotion'],'happy')
        self.assertEqual((await (await update('paused',1,1)).json())['emotion'],'neutral')
        resumed=await (await update('playing',1,2)).json()
        self.assertEqual(resumed['emotion'],'happy')
        self.assertAlmostEqual(resumed['until']-resumed['started_at'],4,places=3)
        # A delayed pause must not overwrite a newer resume.
        self.assertTrue((await (await update('paused',1,1)).json())['ignored'])
        self.assertEqual((await (await update('ended',4,3)).json())['emotion'],'neutral')

    async def test_playback_controller_disconnect_resets_emotion(self):
        owner=await self.client.ws_connect('/ws?role=controller');await owner.receive_json()
        event=await (await self.client.post('/api/speech',json={'text':'こんにちは','emotion':'happy'})).json()
        payload={'clip_id':event['clip_id'],'state':'playing','position':0,'sequence':0}
        await self.client.post('/api/playback',json=payload)
        await owner.close()
        await asyncio.sleep(.01)
        state=await (await self.client.get('/api/state')).json()
        self.assertEqual(state['performance']['emotion'],'neutral')
        self.assertEqual((await self.client.post('/api/playback',json={**payload,'sequence':1})).status,409)

    async def test_playback_stale_clip_failure_and_validation(self):
        first=await (await self.client.post('/api/speech',json={'text':'こんにちは','emotion':'happy'})).json()
        payload={'clip_id':first['clip_id'],'state':'playing','position':0,'sequence':0}
        self.assertEqual((await self.client.post('/api/playback',json=payload)).status,200)
        for extra in ({'state':'invalid'},{'position':-1},{'position':True},{'position':10},
                      {'sequence':True},{'sequence':-1}):
            self.assertEqual((await self.client.post('/api/playback',json={**payload,'sequence':1,**extra})).status,400)
        self.voice.fail=True
        self.assertEqual((await self.client.post('/api/speech',json={'text':'置き換え失敗'})).status,503)
        state=await (await self.client.get('/api/state')).json()
        self.assertEqual(state['performance']['emotion'],'neutral')
        self.assertEqual((await self.client.post('/api/playback',json={**payload,'sequence':2})).status,409)
        self.voice.fail=False
        second=await (await self.client.post('/api/speech',json={'text':'新しい声'})).json()
        self.assertEqual((await self.client.post('/api/playback',json={**payload,'sequence':3})).status,409)
        await self.client.post('/api/mode',json={'mode':'human'})
        self.assertEqual((await self.client.post('/api/playback',json={**payload,'clip_id':second['clip_id']})).status,409)

    async def test_cache_bounded(self):
        first=None
        for i in range(9):
            r=await self.client.post('/api/speech',json={'text':str(i)})
            event=await r.json()
            if first is None:first=event['url']
        self.assertEqual((await self.client.get(first)).status,404)

if __name__=='__main__': unittest.main()
