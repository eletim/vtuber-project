import sys
import unittest
from pathlib import Path
from aiohttp.test_utils import TestClient,TestServer
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from server import create_app, LIMITS


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

    async def test_skirt_parameter_is_independent_clamped_and_reset(self):
        self.assertEqual(LIMITS['ParamSkirtSway'], (-1, 1, 0))
        response = await self.client.post('/api/control', json={
            'source': 'human', 'parameters': {'ParamSkirtSway': 20}})
        payload = await response.json()
        self.assertEqual(response.status, 200)
        self.assertEqual(payload['parameters']['ParamSkirtSway'], 1)
        for key in ('ParamArmLOpen', 'ParamArmROpen', 'ParamBodyAngleX', 'ParamShoulderY'):
            self.assertEqual(payload['parameters'][key], 0)
        response = await self.client.post('/api/mode', json={'mode': 'ai'})
        self.assertEqual((await response.json())['parameters']['ParamSkirtSway'], 0)
        for value in ('bad', True, None):
            response = await self.client.post('/api/control', json={
                'source': 'ai', 'parameters': {'ParamSkirtSway': value}})
            self.assertEqual(response.status, 400)
        ws = await self.client.ws_connect('/ws')
        await ws.receive_json()
        await ws.send_json({'source': 'ai', 'parameters': {'ParamSkirtSway': -.8}, 'ttl_ms': 100})
        self.assertEqual((await ws.receive_json())['parameters']['ParamSkirtSway'], -.8)
        self.assertEqual((await ws.receive_json(timeout=1))['parameters']['ParamSkirtSway'], 0)
        await ws.close()

    async def test_arm_body_parameters_clamp_reset_and_expire(self):
        keys = ('ParamArmLOpen', 'ParamArmROpen', 'ParamShoulderY', 'ParamBodyShiftX')
        self.assertTrue(all(LIMITS[key] == (-1, 1, 0) for key in keys))
        for source in ('human', 'ai'):
            await self.client.post('/api/mode', json={'mode': source})
            response = await self.client.post('/api/control', json={
                'source': source, 'parameters': dict(zip(keys, (5, -5, 1, -1)))})
            self.assertEqual(response.status, 200)
            payload = await response.json()
            self.assertEqual({key: payload['parameters'][key] for key in keys},
                             dict(zip(keys, (1, -1, 1, -1))))
        response = await self.client.post('/api/mode', json={'mode': 'human'})
        payload = await response.json()
        self.assertTrue(all(payload['parameters'][key] == 0 for key in keys))
        for invalid in ('bad', True, None):
            response = await self.client.post('/api/control', json={
                'source': 'human', 'parameters': {'ParamArmLOpen': invalid}})
            self.assertEqual(response.status, 400)
        ws = await self.client.ws_connect('/ws')
        await ws.receive_json()
        await ws.send_json({'source': 'human', 'parameters': dict.fromkeys(keys, .8), 'ttl_ms': 100})
        event = await ws.receive_json()
        self.assertTrue(all(event['parameters'][key] == .8 for key in keys))
        event = await ws.receive_json(timeout=1)
        self.assertTrue(all(event['parameters'][key] == 0 for key in keys))
        await ws.close()


if __name__=='__main__':unittest.main()
