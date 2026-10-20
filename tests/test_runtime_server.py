import sys
import unittest
from pathlib import Path
from aiohttp.test_utils import TestClient,TestServer
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from server import create_app


class Controls(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client=TestClient(TestServer(create_app()))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_source_ownership_and_switch_reset(self):
        r=await self.client.post('/api/control',json={'source':'ai','parameters':{'ParamAngleX':8}})
        self.assertEqual(r.status,409)
        await self.client.post('/api/mode',json={'mode':'ai'})
        r=await self.client.post('/api/control',json={'source':'ai','parameters':{'ParamAngleX':80}})
        self.assertEqual((await r.json())['parameters']['ParamAngleX'],15)
        r=await self.client.post('/api/control',json={'source':'human','parameters':{}})
        self.assertEqual(r.status,409)
        r=await self.client.post('/api/mode',json={'mode':'human'})
        self.assertEqual((await r.json())['parameters']['ParamAngleX'],0)

    async def test_bad_commands_and_expiry(self):
        for payload in [[],{'source':'human','parameters':{'unknown':0}},
            {'source':'human','parameters':{'ParamAngleX':'bad'}},
            {'source':'human','parameters':{},'ttl_ms':'bad'}]:
            r=await self.client.post('/api/control',json=payload)
            self.assertEqual(r.status,400)
        ws=await self.client.ws_connect('/ws');await ws.receive_json()
        await ws.send_json({'source':'human','parameters':{'ParamMouthOpenY':1},'ttl_ms':100})
        self.assertEqual((await ws.receive_json())['parameters']['ParamMouthOpenY'],1)
        event=await ws.receive_json(timeout=1)
        self.assertEqual(event['source'],'idle')
        self.assertEqual(event['parameters']['ParamMouthOpenY'],0)
        await ws.close()


if __name__=='__main__':unittest.main()
