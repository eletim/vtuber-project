"""Speech delivery ownership, cancellation and provider failures."""
import asyncio
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
        return b'RIFF'+b'0000WAVE'+text.encode()

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
    async def test_cache_bounded(self):
        first=None
        for i in range(9):
            r=await self.client.post('/api/speech',json={'text':str(i)})
            event=await r.json()
            if first is None:first=event['url']
        self.assertEqual((await self.client.get(first)).status,404)

if __name__=='__main__': unittest.main()
