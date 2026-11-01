"""Test suite for the Coding Agent Server-Sent Events (SSE) streaming.

Tests:
  - Event buffering and sequential IDs in InteractiveBuildSession
  - GET /api/coding/build/<session_id>/stream endpoint
  - Event streaming for full build lifecycle: planning -> plan approval -> stepping -> diffs -> done
  - Reconnection using Last-Event-ID header and ?last_event_id query param
  - Pending confirmation event with diffs
  - Abort event streaming
  - Non-existent session handling
  - Streaming via GET /api/coding/build/<session_id> with Accept: text/event-stream
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from app import app
from coding_agent import guarded, interactive


def parse_sse_chunks(raw_text: str):
    """Parse raw SSE text into list of (id, event, data_dict) tuples."""
    events = []
    current_id = None
    current_event = "message"
    current_data = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            if current_data:
                data_str = "\n".join(current_data)
                try:
                    payload = json.loads(data_str)
                except Exception:
                    payload = data_str
                events.append({
                    "id": current_id,
                    "event": current_event,
                    "data": payload,
                })
                current_id = None
                current_event = "message"
                current_data = []
            continue

        if line.startswith("id:"):
            current_id = line[3:].strip()
        elif line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            current_data.append(line[5:].strip())

    if current_data:
        data_str = "\n".join(current_data)
        try:
            payload = json.loads(data_str)
        except Exception:
            payload = data_str
        events.append({
            "id": current_id,
            "event": current_event,
            "data": payload,
        })

    return events


class CodingAgentSseTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.tmp_dir = tempfile.mkdtemp(prefix="chhoti_test_sse_")
        guarded.revoke_workspace()

    def tearDown(self):
        guarded.revoke_workspace()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_session_event_buffering_and_replay(self):
        session = interactive.InteractiveBuildSession("test_buf_1", "test buffering")
        session.emit("session_start", {"task": "test buffering"})
        session.emit("planning", {"step": 0})
        session.emit("plan", {"plan": [{"tool": "fs_list_dir"}]})
        session.emit("done", {"status": "success"})
        session.state = "done"

        self.assertEqual(len(session.events), 4)
        self.assertEqual(session.events[0]["id"], 1)
        self.assertEqual(session.events[0]["event"], "session_start")
        self.assertEqual(session.events[1]["id"], 2)
        self.assertEqual(session.events[2]["id"], 3)
        self.assertEqual(session.events[3]["id"], 4)

        # Replay from last_event_id=1 -> should only get events 2, 3, 4
        stream_chunks = list(session.stream_events(last_event_id=1, heartbeat_interval=0.1))
        joined = "".join(stream_chunks)
        events = parse_sse_chunks(joined)

        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["data"]["id"], 2)
        self.assertEqual(events[0]["event"], "planning")
        self.assertEqual(events[1]["data"]["id"], 3)
        self.assertEqual(events[1]["event"], "plan")
        self.assertEqual(events[2]["data"]["id"], 4)
        self.assertEqual(events[2]["event"], "done")

    def test_sse_endpoint_nonexistent_session(self):
        res = self.client.get("/api/coding/build/non_existent_session_123/stream")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data["marker"], "SESSION_NOT_FOUND")

    def test_sse_stream_full_build_flow(self):
        guarded.grant_workspace(self.tmp_dir)

        responses = [
            # 1. Plan response
            json.dumps([
                {"tool": "fs_create_file", "args": {"path": "stream_test.txt", "content": "stream content\n"}, "note": "make file"}
            ]),
            # 2. Step 1: create file
            json.dumps({"tool": "fs_create_file", "args": {"path": "stream_test.txt", "content": "stream content\n"}}),
            # 3. Step 2: finish
            json.dumps({"finish": "created stream_test.txt successfully"}),
        ]
        resp_idx = {"val": 0}

        def mock_think(prompt):
            idx = resp_idx["val"]
            resp_idx["val"] += 1
            if idx < len(responses):
                return responses[idx]
            return json.dumps({"finish": "done"})

        with patch("app._coding_think_fn", return_value=mock_think):
            # Start build with wait=2.0
            res = self.client.post("/api/coding/build", json={
                "task": "build stream_test.txt",
                "wait": 2.0,
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            session_id = data["session_id"]
            self.assertEqual(data["status"], "pending_plan")

            # Approve the plan
            resp_res = self.client.post(f"/api/coding/build/{session_id}/respond", json={
                "approve": True,
                "wait": 5.0,
            })
            self.assertEqual(resp_res.status_code, 200)
            resp_data = resp_res.get_json()
            if resp_data.get("status") not in ("done", "success"):
                poll_res = self.client.get(f"/api/coding/build/{session_id}?wait=5.0")
                resp_data = poll_res.get_json()
            self.assertEqual(resp_data.get("status"), "done")

            # Now stream from the beginning
            stream_res = self.client.get(f"/api/coding/build/{session_id}/stream")
            self.assertEqual(stream_res.status_code, 200)
            self.assertIn("text/event-stream", stream_res.content_type)

            raw = stream_res.get_data(as_text=True)
            events = parse_sse_chunks(raw)
            event_names = [e["event"] for e in events]

            # Verify key events occurred in sequence
            self.assertIn("session_start", event_names)
            self.assertIn("planning", event_names)
            self.assertIn("plan", event_names)
            self.assertIn("pending_plan", event_names)
            self.assertIn("plan_response", event_names)
            self.assertIn("plan_approved", event_names)
            self.assertIn("step_start", event_names)
            self.assertIn("action_start", event_names)
            self.assertIn("action_complete", event_names)
            self.assertIn("diff", event_names)
            self.assertIn("finish", event_names)
            self.assertIn("done", event_names)

            # Find diff event and verify content
            diff_events = [e for e in events if e["event"] == "diff"]
            self.assertTrue(len(diff_events) >= 1)
            diff_payload = diff_events[0]["data"]
            self.assertEqual(diff_payload["path"], "stream_test.txt")
            self.assertIn("stream content", diff_payload["diff"])

            # Verify file created on disk
            target = os.path.join(self.tmp_dir, "stream_test.txt")
            self.assertTrue(os.path.exists(target))
            with open(target, "r", encoding="utf-8") as f:
                self.assertIn("stream content", f.read())

    def test_sse_stream_reconnection_last_event_id(self):
        session = interactive.InteractiveBuildSession("test_recon", "test reconnect")
        interactive._sessions["test_recon"] = session
        session.emit("session_start", {"task": "recon"})
        session.emit("step_start", {"step": 1})
        session.emit("diff", {"path": "a.py", "diff": "+a"})
        session.emit("done", {"status": "success"})
        session.state = "done"

        # Request with Last-Event-ID: 2 -> should only get events 3 and 4
        res = self.client.get(
            "/api/coding/build/test_recon/stream",
            headers={"Last-Event-ID": "2"}
        )
        self.assertEqual(res.status_code, 200)
        events = parse_sse_chunks(res.get_data(as_text=True))
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event"], "diff")
        self.assertEqual(events[1]["event"], "done")

        # Also test with ?last_event_id=3 query param
        res2 = self.client.get("/api/coding/build/test_recon/stream?last_event_id=3")
        self.assertEqual(res2.status_code, 200)
        events2 = parse_sse_chunks(res2.get_data(as_text=True))
        self.assertEqual(len(events2), 1)
        self.assertEqual(events2[0]["event"], "done")

    def test_sse_stream_abort(self):
        guarded.grant_workspace(self.tmp_dir)

        def mock_think(prompt):
            # Propose plan that waits
            return json.dumps([{"tool": "fs_create_file", "args": {"path": "abort.txt", "content": "x"}}])

        with patch("app._coding_think_fn", return_value=mock_think):
            res = self.client.post("/api/coding/build", json={"task": "abort stream test", "wait": 0.5})
            session_id = res.get_json()["session_id"]

            # Abort session
            abort_res = self.client.post(f"/api/coding/build/{session_id}/abort")
            self.assertEqual(abort_res.status_code, 200)

            # Stream events
            stream_res = self.client.get(f"/api/coding/build/{session_id}/stream")
            self.assertEqual(stream_res.status_code, 200)
            events = parse_sse_chunks(stream_res.get_data(as_text=True))
            event_names = [e["event"] for e in events]
            self.assertIn("aborted", event_names)

    def test_sse_accept_header_on_build_status(self):
        session = interactive.InteractiveBuildSession("test_accept", "test accept header")
        interactive._sessions["test_accept"] = session
        session.emit("session_start", {"task": "accept"})
        session.emit("done", {"status": "success"})
        session.state = "done"

        # GET /api/coding/build/<id> with Accept: text/event-stream
        res = self.client.get(
            "/api/coding/build/test_accept",
            headers={"Accept": "text/event-stream"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/event-stream", res.content_type)
        events = parse_sse_chunks(res.get_data(as_text=True))
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event"], "session_start")
        self.assertEqual(events[1]["event"], "done")

    def test_concurrent_subscribers(self):
        session = interactive.InteractiveBuildSession("test_concurrent", "test concurrent")
        q1 = session.subscribe()
        q2 = session.subscribe()

        session.emit("session_start", {"task": "concurrent"})
        session.emit("step_start", {"step": 1})
        session.emit("diff", {"path": "test.txt", "diff": "+test"})

        self.assertFalse(q1.empty())
        self.assertFalse(q2.empty())

        ev1 = q1.get_nowait()
        ev2 = q2.get_nowait()
        self.assertEqual(ev1["id"], 1)
        self.assertEqual(ev2["id"], 1)
        self.assertEqual(ev1["event"], "session_start")
        self.assertEqual(ev2["event"], "session_start")

        session.unsubscribe(q1)
        session.unsubscribe(q2)

    def test_pending_confirmation_stream(self):
        guarded.grant_workspace(self.tmp_dir)

        # Create a file so deleting it triggers a HIGH confirmation
        del_file = os.path.join(self.tmp_dir, "to_delete.txt")
        with open(del_file, "w", encoding="utf-8") as f:
            f.write("delete me\n")

        responses = [
            # 1. Plan response with delete
            json.dumps([
                {"tool": "fs_delete_file", "args": {"path": "to_delete.txt"}, "note": "delete file"}
            ]),
            # 2. Step 1: delete file (triggers HITL proposal confirmation)
            json.dumps({"tool": "fs_delete_file", "args": {"path": "to_delete.txt"}}),
            # 3. Step 2: finish
            json.dumps({"finish": "deleted successfully"}),
        ]
        resp_idx = {"val": 0}

        def mock_think(prompt):
            idx = resp_idx["val"]
            resp_idx["val"] += 1
            if idx < len(responses):
                return responses[idx]
            return json.dumps({"finish": "done"})

        with patch("app._coding_think_fn", return_value=mock_think):
            res = self.client.post("/api/coding/build", json={
                "task": "delete to_delete.txt",
                "wait": 2.0,
            })
            session_id = res.get_json()["session_id"]

            # Approve plan
            resp1 = self.client.post(f"/api/coding/build/{session_id}/respond", json={
                "approve": True,
                "wait": 2.0,
            })
            resp1_data = resp1.get_json()
            self.assertEqual(resp1_data["status"], "pending_confirmation")
            self.assertIn("diff", resp1_data["proposal"])

            # Approve the delete action
            resp2 = self.client.post(f"/api/coding/build/{session_id}/respond", json={
                "approve": True,
                "wait": 5.0,
            })
            resp2_data = resp2.get_json()
            if resp2_data.get("status") not in ("done", "success"):
                poll_res = self.client.get(f"/api/coding/build/{session_id}?wait=5.0")
                resp2_data = poll_res.get_json()
            self.assertEqual(resp2_data["status"], "done")

            # Verify events streamed
            stream_res = self.client.get(f"/api/coding/build/{session_id}/stream")
            events = parse_sse_chunks(stream_res.get_data(as_text=True))
            event_names = [e["event"] for e in events]
            self.assertIn("pending_confirmation", event_names)
            self.assertIn("confirmation_response", event_names)


if __name__ == "__main__":
    unittest.main()
