import unittest
from aiohttp.test_utils import TestClient,TestServer
from server import create_app
class EmotionalSync(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client=TestClient(TestServer(create_app()));await self.client.start_server()
    async def asyncTearDown(self):await self.client.close()
    async def test_switch_new_epoch_repeats_and_late_join(self):
        c=await self.client.ws_connect('/ws');await c.receive_json()
        await c.send_json({'acting':'start','variant':'joyful'});first=(await c.receive_json())['acting']
        await c.send_json({'acting':'switch','variant':'joyful'});self.assertEqual((await c.receive_json())['acting'],first)
        await c.send_json({'acting':'switch','variant':'thinking'});second=(await c.receive_json())['acting'];self.assertNotEqual(second['id'],first['id'])
        o=await self.client.ws_connect('/ws?role=overlay');self.assertEqual((await o.receive_json())['acting'],second)
        await o.send_json({'acting':'switch','variant':'surprised'});self.assertEqual((await o.receive_json())['type'],'error')
        await c.send_json({'acting':'switch','variant':'surprised'});third=(await c.receive_json())['acting'];self.assertEqual(third['variant'],'surprised')
        await c.close();await o.close()
