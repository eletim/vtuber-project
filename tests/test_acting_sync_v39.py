import sys, unittest
from pathlib import Path
from aiohttp.test_utils import TestClient, TestServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from server import create_app

class ActingSync(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client=TestClient(TestServer(create_app()));await self.client.start_server()
    async def asyncTearDown(self):await self.client.close()
    async def test_shared_epoch_repeat_join_stop_and_mode(self):
        c=await self.client.ws_connect('/ws');await c.receive_json()
        await c.send_json({'acting':'start'});first=(await c.receive_json())['acting']
        await c.send_json({'acting':'start'});self.assertEqual((await c.receive_json())['acting'],first)
        o=await self.client.ws_connect('/ws?role=overlay');self.assertEqual((await o.receive_json())['acting'],first)
        await o.send_json({'acting':'stop'});self.assertEqual((await o.receive_json())['type'],'error')
        await c.send_json({'acting':'stop'});stop=(await c.receive_json())['acting'];self.assertGreater(stop['stopped_at'],0)
        self.assertEqual((await o.receive_json())['acting'],stop)
        await c.send_json({'acting':'start'});self.assertEqual((await c.receive_json())['acting'],stop)
        await c.close();await o.close()
    async def test_mouth_expression_preserved_manual_pose_and_mode_release(self):
        c=await self.client.ws_connect('/ws');await c.receive_json();await c.send_json({'acting':'start'});await c.receive_json()
        r=await self.client.post('/api/control',json={'source':'human','parameters':{'ParamMouthOpenY':.7},'expression':'worried'})
        s=await r.json();self.assertEqual(s['acting']['stopped_at'],0);self.assertEqual(s['parameters']['ParamMouthOpenY'],.7)
        r=await self.client.post('/api/mode',json={'mode':'ai'});self.assertGreater((await r.json())['acting']['stopped_at'],0)
        await c.close()

    async def test_variant_is_shared_and_cannot_change_mid_epoch(self):
        c=await self.client.ws_connect('/ws');await c.receive_json()
        await c.send_json({'acting':'start','variant':'unknown'})
        self.assertEqual((await c.receive_json())['type'],'error')
        await c.send_json({'acting':'start','variant':'curious'})
        first=(await c.receive_json())['acting'];self.assertEqual(first['variant'],'curious')
        await c.send_json({'acting':'start','variant':'joyful'})
        self.assertEqual((await c.receive_json())['acting'],first)
        o=await self.client.ws_connect('/ws?role=overlay')
        self.assertEqual((await o.receive_json())['acting'],first)
        await c.close();await o.close()

if __name__=='__main__':unittest.main()
