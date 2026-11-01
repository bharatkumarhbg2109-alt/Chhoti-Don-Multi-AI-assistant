"""Test suite for the Coding Agent Flask API bridge and interactive HITL endpoints.

Tests all new endpoints added to app.py:
  - GET  /api/workspace
  - POST /api/workspace/grant
  - POST /api/workspace/revoke
  - GET  /api/workspace/files
  - GET  /api/workspace/file
  - GET  /api/workspace/servers
  - POST /api/workspace/servers/stop
  - POST /api/coding/build
  - GET  /api/coding/build/<session_id>
  - POST /api/coding/build/<session_id>/respond
  - POST /api/coding/build/<session_id>/abort
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
from coding_agent import guarded, interactive, server


class CodingAgentApiTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.tmp_dir = tempfile.mkdtemp(prefix="chhoti_test_api_")
        guarded.revoke_workspace()

    def tearDown(self):
        guarded.revoke_workspace()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_workspace_status_empty(self):
        res = self.client.get("/api/workspace")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertFalse(data["active"])
        self.assertIsNone(data["root"])

    def test_workspace_grant_invalid(self):
        res = self.client.post("/api/workspace/grant", json={"path": ""})
        self.assertEqual(res.status_code, 400)

        res2 = self.client.post("/api/workspace/grant", json={"path": "Z:\\non_existent_folder_xyz_123"})
        self.assertEqual(res2.status_code, 400)
        data2 = res2.get_json()
        self.assertEqual(data2["status"], "error")

    def test_workspace_grant_and_files(self):
        # Create a sample file in temp dir
        test_file = os.path.join(self.tmp_dir, "test.py")
        with open(test_file, "w", newline="\n", encoding="utf-8") as f:
            f.write("print('hello world')\n")

        # Grant workspace
        res = self.client.post("/api/workspace/grant", json={"path": self.tmp_dir})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("root", data)

        # Check status
        status_res = self.client.get("/api/workspace")
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.get_json()
        self.assertTrue(status_data["active"])
        self.assertEqual(os.path.normcase(status_data["root"]), os.path.normcase(self.tmp_dir))

        # List files
        files_res = self.client.get("/api/workspace/files")
        self.assertEqual(files_res.status_code, 200)
        files_data = files_res.get_json()
        self.assertEqual(files_data["status"], "success")
        items = files_data.get("entries", files_data.get("items", []))
        paths = [item["path"] for item in items]
        self.assertIn("test.py", paths)

        # Read file
        read_res = self.client.get("/api/workspace/file?path=test.py")
        self.assertEqual(read_res.status_code, 200)
        read_data = read_res.get_json()
        self.assertEqual(read_data["status"], "success")
        self.assertEqual(read_data["content"].replace("\r\n", "\n"), "print('hello world')\n")

    def test_workspace_revoke(self):
        guarded.grant_workspace(self.tmp_dir)
        self.assertTrue(guarded.active_workspace() is not None)

        res = self.client.post("/api/workspace/revoke")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["active"])
        self.assertIsNone(guarded.active_workspace())

        # Further file operations should fail
        fail_res = self.client.get("/api/workspace/files")
        self.assertEqual(fail_res.status_code, 400)

    def test_coding_build_no_workspace(self):
        res = self.client.post("/api/coding/build", json={"task": "create a file"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("No active workspace", res.get_json()["message"])

    def test_coding_build_interactive_plan_rejection(self):
        guarded.grant_workspace(self.tmp_dir)

        # Mock think function that emits a plan
        def mock_think(prompt):
            return json.dumps([
                {"tool": "fs_create_file", "args": {"path": "rejected.txt", "content": "foo"}, "note": "create"}
            ])

        with patch("app._coding_think_fn", return_value=mock_think):
            res = self.client.post("/api/coding/build", json={
                "task": "create rejected.txt",
                "wait": 2.0,
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            session_id = data["session_id"]
            self.assertEqual(data["status"], "pending_plan")
            self.assertIn("plan", data)

            # Reject the plan
            resp_res = self.client.post(f"/api/coding/build/{session_id}/respond", json={
                "approve": False,
                "wait": 2.0,
            })
            self.assertEqual(resp_res.status_code, 200)
            resp_data = resp_res.get_json()
            self.assertFalse(resp_data["approved"])
            self.assertIn(resp_data["status"], ("done", "rejected"))
            # File should not have been created
            self.assertFalse(os.path.exists(os.path.join(self.tmp_dir, "rejected.txt")))

    def test_coding_build_interactive_plan_approval(self):
        guarded.grant_workspace(self.tmp_dir)

        responses = [
            # 1. Plan response
            json.dumps([
                {"tool": "fs_create_file", "args": {"path": "approved.txt", "content": "built successfully\n"}, "note": "make file"}
            ]),
            # 2. Step 1: create file
            json.dumps({"tool": "fs_create_file", "args": {"path": "approved.txt", "content": "built successfully\n"}}),
            # 3. Step 2: finish
            json.dumps({"finish": "created approved.txt successfully"}),
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
                "task": "create approved.txt",
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
            self.assertTrue(resp_data["approved"])
            # Give background thread a moment if still finalizing
            if resp_data["status"] not in ("done", "success"):
                poll_res = self.client.get(f"/api/coding/build/{session_id}?wait=5.0")
                resp_data = poll_res.get_json()

            self.assertEqual(resp_data["status"], "done")
            # File must exist on disk!
            target = os.path.join(self.tmp_dir, "approved.txt")
            self.assertTrue(os.path.exists(target))
            with open(target, "r", encoding="utf-8") as f:
                self.assertIn("built successfully", f.read())

    def test_coding_build_abort(self):
        guarded.grant_workspace(self.tmp_dir)

        def mock_think(prompt):
            # Slow think or pending
            return json.dumps([{"tool": "fs_create_file", "args": {"path": "abort.txt", "content": "x"}}])

        with patch("app._coding_think_fn", return_value=mock_think):
            res = self.client.post("/api/coding/build", json={"task": "abort test", "wait": 1.0})
            session_id = res.get_json()["session_id"]

            abort_res = self.client.post(f"/api/coding/build/{session_id}/abort")
            self.assertEqual(abort_res.status_code, 200)
            self.assertEqual(abort_res.get_json()["state"], "aborted")

    def test_workspace_servers_api(self):
        res = self.client.get("/api/workspace/servers")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIsInstance(data["servers"], list)

        # Stop invalid server
        stop_res = self.client.post("/api/workspace/servers/stop", json={"id": "non_existent"})
        self.assertEqual(stop_res.status_code, 200)
        self.assertEqual(stop_res.get_json()["status"], "error")


if __name__ == "__main__":
    unittest.main()
