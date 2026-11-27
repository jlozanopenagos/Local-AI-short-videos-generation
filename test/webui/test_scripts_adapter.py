"""
test/webui/test_scripts_adapter.py — Tests for WebUI ScriptsAdapter and /generate endpoint.
Verifies Stage A script creation via the WebUI background job runner (Phase 3).
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

MAIN_DIR = Path(__file__).resolve().parent.parent.parent / "main"
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

# pyrefly: ignore[missing-import]
from fastapi.testclient import TestClient
# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.common.base_engine import ScriptGenerationResult
# pyrefly: ignore[missing-import]
from webui.jobs.adapters.scripts import ScriptsAdapter
# pyrefly: ignore[missing-import]
# pyrefly: ignore[missing-import]
from core.state_manager import DOWNSTREAM_STAGES, StateManager
from webui.jobs.models import JobStage
# pyrefly: ignore[missing-import]
from webui.server import create_app


class TestScriptsAdapter(unittest.TestCase):
    """Verifies ScriptsAdapter execution and WebUI API integration."""

    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.base_dir = Path(workspace.name)
        self.state_manager = StateManager(self.base_dir)
        fixture = Path(__file__).resolve().parents[1] / "fixtures/image_prompts/states/script_SG01.json"
        state = json.loads(fixture.read_text(encoding="utf-8"))
        state["id"] = "SG02"
        state["status"] = {"script_generation": "pending", **dict.fromkeys(DOWNSTREAM_STAGES, "done")}
        self.state_manager.save_script_state("SG02", state)
        self.app = create_app(self.base_dir)
        self.client = TestClient(self.app)
        self.jm = self.app.state.job_manager
        self.addCleanup(self.jm.close)

    def test_scripts_adapter_is_registered_in_job_manager(self):
        self.assertIn(JobStage.SCRIPTS, self.jm._adapters)
        self.assertIsInstance(self.jm._adapters[JobStage.SCRIPTS], ScriptsAdapter)

    @patch("webui.jobs.adapters.scripts.generate_script_for_payload")
    @patch("webui.jobs.adapters.scripts.get_llama_manager")
    def test_generate_endpoint_runs_real_adapter_and_persists_result(self, mock_get_lm, mock_generate):
        mock_lm = MagicMock()
        mock_lm.is_reachable.return_value = True
        mock_get_lm.return_value = mock_lm

        mock_generate.return_value = ScriptGenerationResult(
            script_id="SG02",
            script_type="game",
            script={
                "title": "Mock Game Title",
                "script": {
                    "title": "Mock Game Title",
                    "hook": "Listen up!",
                    "challenge": "The test. A: Opt A. B: Opt B.",
                    "pressure": "3 seconds!",
                    "answer": "It is A!",
                    "explanation": "Here is why.",
                },
                "chalkboard_exercise": "The test.\nA) Opt A\nB) Opt B",
            },
            spoken_words=100,
            is_valid=True,
        )

        resp = self.client.post("/api/scripts/SG02/generate", json={"force": True})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "enqueued")
        self.assertEqual(data["script_id"], "SG02")
        self.assertTrue(data.get("job_id"))

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            job = self.client.get(f"/api/jobs/{data['job_id']}").json()
            if job["status"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.01)
        self.assertEqual(job["status"], "completed", job)
        self.assertEqual(job["stage"], "scripts")
        self.assertEqual(job["script_ids"], ["SG02"])
        self.assertEqual(job["progress"]["current"], 1)
        updated = self.state_manager.get_script_state("SG02")
        self.assertEqual(updated["status"]["script_generation"], "done")
        for stage in DOWNSTREAM_STAGES:
            self.assertEqual(updated["status"][stage], "pending")
        self.assertEqual(updated["content_metadata"]["script"]["title"], "Mock Game Title")


if __name__ == "__main__":
    unittest.main()
