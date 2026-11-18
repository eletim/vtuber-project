"""Expression API ownership, validation, expiry, and actual playback lifecycle."""
import asyncio
import io
import math
import sys
import time
import unittest
import wave
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
from server import create_app


EXPRESSIONS = (
    "neutral", "soft_smile", "big_smile", "worried", "surprised",
    "bashful", "displeased", "thinking",
)


class Voice:
    """A local four-second WAV provider with controllable synthesis timing."""

    credit = "VOICEVOX:雨晴はう"

    def __init__(self):
        self.gate = asyncio.Event()
        self.gate.set()
        self.started = asyncio.Event()
        self.calls = 0
        self.fail = False

    async def synthesize(self, text):
        self.calls += 1
        self.started.set()
        await self.gate.wait()
        if self.fail:
            raise ConnectionError("test voice provider is offline")
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(1)
            wav.setframerate(24000)
            wav.writeframes(b"\x80" * 96000)
        return buffer.getvalue()


class RuntimeCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.voice = Voice()
        self.pending = []
        self.client = TestClient(TestServer(create_app(self.voice)))
        await self.client.start_server()

    async def asyncTearDown(self):
        self.voice.gate.set()
        if self.pending:
            await asyncio.gather(*self.pending, return_exceptions=True)
        await self.client.close()

    async def post(self, path, data, status=200):
        if data is None:
            response = await self.client.post(
                path, data="null", headers={"Content-Type": "application/json"},
            )
        else:
            response = await self.client.post(path, json=data)
        body = await response.text()
        self.assertEqual(response.status, status, f"{path}: {body}")
        return response

    async def state(self):
        response = await self.client.get("/api/state")
        self.assertEqual(response.status, 200)
        return await response.json()

    async def expression(self, expression="soft_smile", duration=2, source="human"):
        await self.post("/api/expression", {
            "source": source, "expression": expression, "duration": duration,
        })
        return (await self.state())["expression"]

    async def wait_state(self, predicate, timeout=1.5):
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            state = await self.state()
            if predicate(state):
                return state
            if asyncio.get_running_loop().time() >= deadline:
                self.fail(f"State did not reach expected condition: {state}")
            await asyncio.sleep(0.01)

    def assert_idle(self, expression):
        self.assertEqual(expression["id"], "neutral")
        self.assertEqual(expression["owner"], "idle")
        self.assertEqual(expression["until"], 0)

    def assert_manual(self, expression, expected, source="human"):
        self.assertEqual(expression["id"], expected)
        self.assertEqual(expression["source"], source)
        self.assertEqual(expression["owner"], "manual")
        self.assertTrue(math.isfinite(expression["started_at"]))
        self.assertGreater(expression["until"], expression["started_at"])


class ExpressionAPI(RuntimeCase):
    async def test_initial_state_and_all_expression_ids(self):
        initial = (await self.state())["expression"]
        self.assertTrue({"id", "source", "owner", "started_at", "until"} <= initial.keys())
        self.assert_idle(initial)
        for expression in EXPRESSIONS:
            with self.subTest(expression=expression):
                result = await self.expression(expression, duration=2.5)
                self.assert_manual(result, expression)
                self.assertAlmostEqual(result["until"] - result["started_at"], 2.5, places=3)

    async def test_duration_boundaries_are_accepted(self):
        for duration in (0.1, 30):
            with self.subTest(duration=duration):
                result = await self.expression(duration=duration)
                self.assert_manual(result, "soft_smile")
                self.assertAlmostEqual(result["until"] - result["started_at"], duration, places=3)

    async def test_invalid_expression_requests_are_atomic(self):
        await self.expression("bashful", duration=30)
        baseline = await self.state()
        good = {"source": "human", "expression": "soft_smile", "duration": 2}
        invalid = [
            [], None, "soft_smile", {},
            {**good, "source": "idle"}, {**good, "source": None},
            {**good, "source": []},
            {**good, "expression": "unknown"}, {**good, "expression": None},
            {**good, "expression": []}, {**good, "expression": {}},
        ]
        invalid.extend({**good, "duration": duration} for duration in (
            -1, 0, 0.099, 30.001, True, "2", None, [], {},
            float("nan"), float("inf"), -float("inf"),
        ))
        for data in invalid:
            with self.subTest(data=data):
                await self.post("/api/expression", data, 400)
                self.assertEqual(await self.state(), baseline)
        for raw in ("", "{broken"):
            with self.subTest(raw=raw):
                malformed = await self.client.post(
                    "/api/expression", data=raw, headers={"Content-Type": "application/json"},
                )
                self.assertEqual(malformed.status, 400, await malformed.text())
                self.assertEqual(await self.state(), baseline)

    async def test_inactive_sources_and_mode_switch_reset(self):
        await self.expression("worried")
        baseline = await self.state()
        await self.post("/api/expression", {
            "source": "ai", "expression": "thinking", "duration": 2,
        }, 409)
        self.assertEqual(await self.state(), baseline)
        for source in ("ai", "human", "ai", "human"):
            await self.post("/api/mode", {"mode": source})
            self.assert_idle((await self.state())["expression"])
            await self.expression("big_smile", source=source)
            stale = "human" if source == "ai" else "ai"
            await self.post("/api/expression", {
                "source": stale, "expression": "displeased", "duration": 2,
            }, 409)
            self.assert_manual((await self.state())["expression"], "big_smile", source)

    async def test_control_expression_is_atomic_with_numeric_pose(self):
        await self.post("/api/control", {
            "source": "human", "parameters": {"ParamAngleX": 7}, "ttl_ms": 10000,
            "expression": "thinking", "expression_duration": 30,
        })
        baseline = await self.state()
        self.assertEqual(baseline["parameters"]["ParamAngleX"], 7)
        self.assert_manual(baseline["expression"], "thinking")
        self.assertAlmostEqual(
            baseline["expression"]["until"] - baseline["expression"]["started_at"], 30, places=3,
        )
        good = {
            "source": "human", "parameters": {"ParamAngleX": -9}, "ttl_ms": 10000,
            "expression": "surprised", "expression_duration": 3,
        }
        invalid = [
            {**good, "expression": "unknown"}, {**good, "expression": []},
            {**good, "expression": None},
            {**good, "parameters": {"unknown": 1}},
            {**good, "parameters": {"ParamAngleX": True}},
            {**good, "ttl_ms": "bad"}, {**good, "ttl_ms": float("nan")},
        ]
        invalid.extend({**good, "expression_duration": duration} for duration in (
            0, 0.099, 30.001, True, None, "2", [], {}, float("nan"), float("inf"),
        ))
        for data in invalid:
            with self.subTest(data=data):
                await self.post("/api/control", data, 400)
                self.assertEqual(await self.state(), baseline)
        await self.post("/api/control", {**good, "source": "ai"}, 409)
        self.assertEqual(await self.state(), baseline)

    async def test_pose_expiry_does_not_clear_independent_expression(self):
        chosen = await self.expression("bashful", duration=1.2)
        await self.post("/api/control", {
            "source": "human", "parameters": {"ParamAngleX": 8}, "ttl_ms": 100,
        })
        state = await self.wait_state(lambda state: state["parameters"]["ParamAngleX"] == 0)
        self.assertEqual(state["expression"], chosen)
        self.assert_manual(state["expression"], "bashful")

    async def test_expression_expiry_does_not_clear_independent_pose(self):
        await self.post("/api/control", {
            "source": "human", "parameters": {"ParamAngleX": 8}, "ttl_ms": 2000,
        })
        await self.expression("worried", duration=0.1)
        state = await self.wait_state(lambda state: state["expression"]["owner"] == "idle")
        self.assert_idle(state["expression"])
        self.assertEqual(state["parameters"]["ParamAngleX"], 8)

    async def test_old_expression_deadline_does_not_expire_new_selection(self):
        await self.expression("soft_smile", duration=0.1)
        chosen = await self.expression("thinking", duration=1)
        await asyncio.sleep(0.25)
        self.assertEqual((await self.state())["expression"], chosen)

    async def test_rapid_switching_preserves_latest_manual_selection(self):
        for _ in range(3):
            for expression in EXPRESSIONS:
                chosen = await self.expression(expression, duration=1)
                self.assert_manual(chosen, expression)
        self.assertEqual((await self.state())["expression"], chosen)
        await self.post("/api/mode", {"mode": "ai"})
        await self.expression("worried", duration=1, source="ai")
        await self.post("/api/mode", {"mode": "human"})
        self.assert_idle((await self.state())["expression"])

    async def test_expression_source_racing_mode_switch_cannot_leak(self):
        for _ in range(8):
            await self.post("/api/mode", {"mode": "human"})
            mode, expression = await asyncio.gather(
                self.client.post("/api/mode", json={"mode": "ai"}),
                self.client.post("/api/expression", json={
                    "source": "human", "expression": "displeased", "duration": 3,
                }),
            )
            self.assertEqual(mode.status, 200, await mode.text())
            self.assertIn(expression.status, (200, 409), await expression.text())
            state = await self.state()
            self.assertEqual(state["mode"], "ai")
            self.assert_idle(state["expression"])

    async def test_websocket_expression_controls_validate_and_ignore_stale_source(self):
        ws = await self.client.ws_connect("/ws")
        await ws.receive_json()
        await ws.send_json({
            "source": "human", "parameters": {"ParamAngleX": 5},
            "expression": "bashful", "expression_duration": 3,
        })
        event = await ws.receive_json(timeout=1)
        self.assertEqual(event["type"], "state")
        self.assert_manual(event["expression"], "bashful")
        baseline = await self.state()
        await ws.send_json({
            "source": "human", "parameters": {"ParamAngleX": -5},
            "expression": "not-an-expression", "expression_duration": 3,
        })
        self.assertEqual((await ws.receive_json(timeout=1))["type"], "error")
        self.assertEqual(await self.state(), baseline)
        await self.post("/api/mode", {"mode": "ai"})
        await ws.send_json({
            "source": "human", "expression": "big_smile", "expression_duration": 3,
        })
        # A subsequent HTTP request allows the queued stale frame to be processed.
        await asyncio.sleep(0.03)
        self.assert_idle((await self.state())["expression"])
        await ws.close()


class SpeechExpressions(RuntimeCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.post("/api/mode", {"mode": "ai"})

    async def synthesize(self, **data):
        response = await self.post("/api/speech", {"text": "test speech", **data})
        return await response.json()

    async def playback(self, clip, phase="playing", position=0, sequence=0, status=200):
        return await self.post("/api/playback", {
            "clip_id": clip["clip_id"], "state": phase,
            "position": position, "sequence": sequence,
        }, status)

    async def begin_gated_speech(self, **data):
        self.voice.started.clear()
        self.voice.gate.clear()
        task = asyncio.create_task(self.client.post("/api/speech", json={"text": "gated", **data}))
        self.pending.append(task)
        await asyncio.wait_for(self.voice.started.wait(), timeout=1)
        return task

    async def test_emotion_mapping_starts_only_at_actual_playback(self):
        mapping = {
            "happy": "soft_smile", "thoughtful": "thinking",
            "surprised": "surprised", "neutral": "neutral",
        }
        for emotion, expected in mapping.items():
            with self.subTest(emotion=emotion):
                clip = await self.synthesize(emotion=emotion)
                self.assertEqual(clip["duration"], 4)
                self.assert_idle((await self.state())["expression"])
                await self.playback(clip)
                expression = (await self.state())["expression"]
                self.assertEqual(expression["id"], expected)
                self.assertEqual(expression["source"], "ai")
                self.assertEqual(expression["owner"], "speech")
                self.assertAlmostEqual(expression["until"] - expression["started_at"], 4, places=3)
                await self.playback(clip, "ended", 4, 1)
                self.assert_idle((await self.state())["expression"])

    async def test_explicit_speech_expression_overrides_emotion_mapping(self):
        for expected in EXPRESSIONS:
            with self.subTest(expression=expected):
                clip = await self.synthesize(emotion="happy", expression=expected)
                self.assert_idle((await self.state())["expression"])
                await self.playback(clip)
                expression = (await self.state())["expression"]
                self.assertEqual(expression["id"], expected)
                self.assertEqual(expression["owner"], "speech")
                await self.playback(clip, "ended", 4, 1)

    async def test_invalid_speech_expression_does_not_cancel_active_clip(self):
        clip = await self.synthesize(expression="big_smile")
        await self.playback(clip)
        baseline = await self.state()
        calls = self.voice.calls
        for expression in ("unknown", None, [], {}, True):
            with self.subTest(expression=expression):
                await self.post("/api/speech", {"text": "bad request", "expression": expression}, 400)
                self.assertEqual(await self.state(), baseline)
                self.assertEqual(self.voice.calls, calls)
        await self.playback(clip, "paused", 1, 1)
        self.assert_idle((await self.state())["expression"])

    async def test_pause_resume_ended_and_delayed_status(self):
        clip = await self.synthesize(expression="worried")
        await self.playback(clip)
        await self.playback(clip, "paused", 1, 1)
        self.assert_idle((await self.state())["expression"])
        await self.playback(clip, "playing", 1, 2)
        expression = (await self.state())["expression"]
        self.assertEqual(expression["id"], "worried")
        self.assertEqual(expression["owner"], "speech")
        self.assertAlmostEqual(expression["until"] - time.time(), 3, delta=0.15)
        delayed = await self.playback(clip, "paused", 1, 1)
        self.assertTrue((await delayed.json())["ignored"])
        self.assertEqual((await self.state())["expression"], expression)
        await self.playback(clip, "ended", 4, 3)
        self.assert_idle((await self.state())["expression"])

    async def test_speech_expression_expires_at_remaining_audio_deadline(self):
        clip = await self.synthesize(expression="surprised")
        await self.playback(clip, position=3.85)
        self.assertEqual((await self.state())["expression"]["owner"], "speech")
        state = await self.wait_state(lambda state: state["expression"]["owner"] == "idle")
        self.assert_idle(state["expression"])

    async def test_manual_selection_before_playback_survives_all_statuses(self):
        clip = await self.synthesize(expression="big_smile")
        chosen = await self.expression("bashful", duration=30, source="ai")
        for sequence, (phase, position) in enumerate((
            ("playing", 0), ("paused", 1), ("playing", 1), ("ended", 4),
        )):
            await self.playback(clip, phase, position, sequence)
            self.assertEqual((await self.state())["expression"], chosen)

    async def test_manual_selection_during_playback_survives_delayed_reports(self):
        clip = await self.synthesize(expression="soft_smile")
        await self.playback(clip)
        chosen = await self.expression("displeased", duration=30, source="ai")
        for phase, position, sequence in (
            ("paused", 0.5, 1), ("playing", 0.5, 2),
            ("paused", 0.5, 1), ("ended", 4, 3),
        ):
            await self.playback(clip, phase, position, sequence)
            self.assertEqual((await self.state())["expression"], chosen)

    async def test_explicit_neutral_manual_reset_survives_old_clip_resume(self):
        clip = await self.synthesize(expression="big_smile")
        await self.playback(clip)
        chosen = await self.expression("neutral", duration=30, source="ai")
        self.assert_manual(chosen, "neutral", "ai")
        await self.playback(clip, "paused", 1, 1)
        await self.playback(clip, "playing", 1, 2)
        self.assertEqual((await self.state())["expression"], chosen)
        await self.playback(clip, "ended", 4, 3)
        self.assertEqual((await self.state())["expression"], chosen)

    async def test_manual_selection_during_synthesis_survives_playback(self):
        pending = await self.begin_gated_speech(expression="big_smile")
        chosen = await self.expression("thinking", duration=30, source="ai")
        self.voice.gate.set()
        response = await pending
        self.assertEqual(response.status, 200, await response.text())
        clip = await response.json()
        self.assertEqual((await self.state())["expression"], chosen)
        await self.playback(clip)
        self.assertEqual((await self.state())["expression"], chosen)

    async def test_control_selected_expression_also_overrides_pending_speech(self):
        clip = await self.synthesize(expression="big_smile")
        await self.post("/api/control", {
            "source": "ai", "parameters": {"ParamAngleX": 3},
            "expression": "worried", "expression_duration": 30,
        })
        chosen = (await self.state())["expression"]
        self.assert_manual(chosen, "worried", "ai")
        await self.playback(clip)
        self.assertEqual((await self.state())["expression"], chosen)
        await self.playback(clip, "ended", 4, 1)
        self.assertEqual((await self.state())["expression"], chosen)

    async def test_manual_and_playback_race_always_leaves_manual_owner(self):
        for _ in range(8):
            await self.post("/api/mode", {"mode": "ai"})
            clip = await self.synthesize(expression="big_smile")
            manual, playback = await asyncio.gather(
                self.client.post("/api/expression", json={
                    "source": "ai", "expression": "thinking", "duration": 30,
                }),
                self.client.post("/api/playback", json={
                    "clip_id": clip["clip_id"], "state": "playing",
                    "position": 0, "sequence": 0,
                }),
            )
            self.assertEqual(manual.status, 200, await manual.text())
            self.assertEqual(playback.status, 200, await playback.text())
            self.assert_manual((await self.state())["expression"], "thinking", "ai")

    async def test_newer_synthesis_supersedes_older_inflight_clip(self):
        first = await self.begin_gated_speech(expression="big_smile")
        second = await self.begin_gated_speech(expression="worried")
        chosen = await self.expression("bashful", duration=30, source="ai")
        self.voice.gate.set()
        first_response, second_response = await asyncio.gather(first, second)
        self.assertEqual(first_response.status, 409, await first_response.text())
        self.assertEqual(second_response.status, 200, await second_response.text())
        clip = await second_response.json()
        await self.playback(clip)
        self.assertEqual((await self.state())["expression"], chosen)

    async def test_new_speech_cancels_previous_expression_and_old_reports(self):
        first = await self.synthesize(expression="soft_smile")
        await self.playback(first)
        pending = await self.begin_gated_speech(expression="worried")
        self.assert_idle((await self.state())["expression"])
        await self.playback(first, sequence=1, status=409)
        self.voice.gate.set()
        response = await pending
        self.assertEqual(response.status, 200, await response.text())
        second = await response.json()
        self.assert_idle((await self.state())["expression"])
        await self.playback(second)
        self.assertEqual((await self.state())["expression"]["id"], "worried")
        await self.playback(first, "ended", 4, 2, status=409)
        self.assertEqual((await self.state())["expression"]["id"], "worried")

    async def test_replacement_synthesis_failure_leaves_old_speech_neutral(self):
        first = await self.synthesize(expression="soft_smile")
        await self.playback(first)
        self.voice.fail = True
        await self.post("/api/speech", {"text": "provider unavailable", "expression": "worried"}, 503)
        self.assert_idle((await self.state())["expression"])
        await self.playback(first, sequence=1, status=409)
        self.assert_idle((await self.state())["expression"])

    async def test_new_synthesis_and_failure_preserve_manual_selection(self):
        first = await self.synthesize(expression="soft_smile")
        await self.playback(first)
        chosen = await self.expression("bashful", duration=30, source="ai")
        pending = await self.begin_gated_speech(expression="worried")
        self.assertEqual((await self.state())["expression"], chosen)
        self.voice.fail = True
        self.voice.gate.set()
        response = await pending
        self.assertEqual(response.status, 503, await response.text())
        self.assertEqual((await self.state())["expression"], chosen)
        await self.playback(first, sequence=1, status=409)
        self.assertEqual((await self.state())["expression"], chosen)

    async def test_mode_switch_during_synthesis_invalidates_pending_speech(self):
        pending = await self.begin_gated_speech(expression="big_smile")
        await self.post("/api/mode", {"mode": "human"})
        chosen = await self.expression("displeased", duration=30)
        await self.post("/api/mode", {"mode": "ai"})
        self.voice.gate.set()
        response = await pending
        self.assertEqual(response.status, 409, await response.text())
        self.assert_idle((await self.state())["expression"])
        self.assertNotEqual((await self.state())["expression"], chosen)

    async def test_owner_disconnect_clears_speech_expression(self):
        owner = await self.client.ws_connect("/ws?role=controller")
        await owner.receive_json()
        clip = await self.synthesize(expression="big_smile")
        await self.playback(clip)
        await owner.close()
        state = await self.wait_state(lambda state: state["expression"]["owner"] == "idle")
        self.assert_idle(state["expression"])
        await self.playback(clip, sequence=1, status=409)

    async def test_owner_disconnect_does_not_clear_newer_manual_expression(self):
        owner = await self.client.ws_connect("/ws?role=controller")
        await owner.receive_json()
        clip = await self.synthesize(expression="big_smile")
        await self.playback(clip)
        chosen = await self.expression("thinking", duration=30, source="ai")
        await owner.close()
        await asyncio.sleep(0.03)
        self.assertEqual((await self.state())["expression"], chosen)
        await self.playback(clip, sequence=1, status=409)

    async def test_overlay_disconnect_does_not_clear_owner_speech(self):
        owner = await self.client.ws_connect("/ws?role=controller")
        overlay = await self.client.ws_connect("/ws?role=overlay")
        await owner.receive_json()
        await overlay.receive_json()
        clip = await self.synthesize(expression="surprised")
        await self.playback(clip)
        expression = (await self.state())["expression"]
        await overlay.close()
        await asyncio.sleep(0.03)
        self.assertEqual((await self.state())["expression"], expression)
        await owner.close()


if __name__ == "__main__":
    unittest.main()
