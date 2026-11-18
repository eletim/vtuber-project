"""Cancellation remains authoritative while a speech broadcast is backpressured."""
import asyncio
import io
import sys
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import server


class OrderedPeers(set):
    """Choose a valid, deterministic peer traversal: overlay before owner."""
    def __init__(self):
        super().__init__()
        self.order = []

    def add(self, value):
        if value not in self:
            self.order.append(value)
        super().add(value)

    def discard(self, value):
        if value in self:
            self.order.remove(value)
        super().discard(value)

    def __iter__(self):
        return iter(self.order)


class Voice:
    credit = 'VOICEVOX:test'

    async def synthesize(self, text):
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(1)
            audio.setframerate(8000)
            audio.writeframes(b'\x80' * 8000)
        return buffer.getvalue()


class BroadcastCancellation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.gate_player = False
        original_socket = web.WebSocketResponse
        test = self

        class SlowSocket(original_socket):
            async def send_json(self, data, *args, **kwargs):
                should_gate = (data.get('type') == 'speech'
                               and data.get('play') == test.gate_player
                               and not test.entered.is_set())
                # A real send writes the frame before it can await transport
                # drain. Do not simulate reordering within a single socket.
                result = await super().send_json(data, *args, **kwargs)
                if should_gate:
                    test.entered.set()
                    await test.release.wait()
                return result

        self.socket_patch = patch.object(server.web, 'WebSocketResponse', SlowSocket)
        self.socket_patch.start()
        self.addCleanup(self.socket_patch.stop)
        with patch.object(server, 'set', OrderedPeers, create=True):
            app = server.create_app(Voice())
        self.client = TestClient(TestServer(app))
        await self.client.start_server()
        await self.client.post('/api/mode', json={'mode': 'ai'})
        self.overlay = await self.client.ws_connect('/ws?role=overlay')
        await self.overlay.receive_json()
        self.owner = await self.client.ws_connect('/ws?role=controller')
        await self.owner.receive_json()

    async def asyncTearDown(self):
        self.release.set()
        await self.client.close()

    async def start_blocked_speech(self, request_id='old'):
        task = asyncio.create_task(self.client.post('/api/speech', json={
            'text': 'A fresh utterance', 'request_id': request_id}))
        await asyncio.wait_for(self.entered.wait(), 1)
        return task

    async def owner_events(self):
        events = []
        while True:
            try:
                events.append(await self.owner.receive_json(timeout=.05))
            except asyncio.TimeoutError:
                return events

    async def test_stop_during_overlay_drain_never_reaches_unsent_owner(self):
        speech = await self.start_blocked_speech()
        stopped = await self.client.post('/api/speech/cancel', json={'request_id': 'old'})
        self.assertTrue((await stopped.json())['cancelled'])
        self.release.set()
        self.assertEqual((await speech).status, 409)
        events = await self.owner_events()
        self.assertTrue(any(event.get('reason') == 'stopped' for event in events))
        self.assertFalse(any(event['type'] == 'speech' for event in events))
        state = await (await self.client.get('/api/state')).json()
        self.assertEqual(state['speech']['phase'], 'idle')

    async def test_superseding_speech_cannot_be_followed_by_old_delivery(self):
        old = await self.start_blocked_speech()
        new = await self.client.post('/api/speech', json={
            'text': 'The replacement utterance', 'request_id': 'new'})
        self.assertEqual(new.status, 200)
        self.release.set()
        self.assertEqual((await old).status, 409)
        deliveries = [event['request_id'] for event in await self.owner_events()
                      if event['type'] == 'speech']
        self.assertEqual(deliveries, ['new'])
        state = await (await self.client.get('/api/state')).json()
        self.assertEqual(state['speech']['request_id'], 'new')

    async def test_unscoped_stop_identifies_external_request_for_client_tombstones(self):
        speech = await self.start_blocked_speech('external-client-request')
        await self.client.post('/api/speech/cancel', json={})
        self.release.set()
        self.assertEqual((await speech).status, 409)
        events = await self.owner_events()
        stopped = next(event for event in events if event.get('reason') == 'stopped')
        self.assertEqual(stopped['request_id'], 'external-client-request')
        self.assertFalse(any(event['type'] == 'speech' for event in events))

    async def test_stop_during_final_owner_drain_cannot_return_success(self):
        self.gate_player = True
        speech = await self.start_blocked_speech()
        await self.client.post('/api/speech/cancel', json={'request_id': 'old'})
        self.release.set()
        self.assertEqual((await speech).status, 409)
        events = await self.owner_events()
        delivered = next(i for i, event in enumerate(events) if event['type'] == 'speech')
        stopped = next(i for i, event in enumerate(events) if event.get('reason') == 'stopped')
        # The in-flight frame cannot be recalled, but the following stop wins.
        self.assertLess(delivered, stopped)
        self.assertFalse(any(event['type'] == 'speech' for event in events[stopped + 1:]))


if __name__ == '__main__':
    unittest.main()
