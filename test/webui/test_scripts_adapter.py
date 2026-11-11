"""
test/webui/test_scripts_adapter.py — Tests for WebUI ScriptsAdapter and /generate endpoint.
Verifies Stage A script creation via the WebUI background job runner (Phase 3).
"""

from __future__ import annotations

import sys
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
from webui.jobs.manager import get_job_manager
# pyrefly: ignore[missing-import]
from webui.jobs.models import JobCreateRequest, JobStage, JobStatus
# pyrefly: ignore[missing-import]
from webui.server import create_app


class TestScriptsAdapter(unittest.TestCase):
    """Verifies ScriptsAdapter execution and WebUI API integration."""

    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.jm = get_job_manager()
        self.adapter = ScriptsAdapter()
        self.jm.register_adapter(JobStage.SCRIPTS, self.adapter)

    def test_scripts_adapter_is_registered_in_job_manager(self):
        self.assertIn(JobStage.SCRIPTS, self.jm._adapters)
        self.assertIsInstance(self.jm._adapters[JobStage.SCRIPTS], ScriptsAdapter)

    @patch("webui.jobs.adapters.scripts.generate_script_for_payload")
    @patch("webui.jobs.adapters.scripts.get_llama_manager")
    def test_scripts_adapter_run_lifecycle_updates_state(self, mock_get_lm, mock_generate):
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

        adapter = ScriptsAdapter()
        logs = []
        progresses = []

        res = adapter.run(
            script_ids=["SG02"],
            options={"force": True},
            emit_log=lambda l: logs.append(l),
            emit_progress=lambda c, t, s: progresses.append((c, t, s)),
            check_cancelled=lambda: False,
        )

        self.assertEqual(res["success_count"], 1)
        self.assertEqual(len(res["failed_ids"]), 0)
        self.assertTrue(any("Successfully generated script" in log for log in logs))
        self.assertEqual(progresses[-1], (1, 1, "SG02"))

    def test_post_script_generate_endpoint_enqueues_job(self):
        resp = self.client.post("/api/scripts/SG02/generate", json={"force": True})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "enqueued")
        self.assertEqual(data["script_id"], "SG02")
        self.assertTrue(data.get("job_id"))

        # Verify job is registered in JobManager
        job = self.jm.get_job(data["job_id"])
        self.assertIsNotNone(job)
        self.assertEqual(job.stage, JobStage.SCRIPTS)
        self.assertEqual(job.script_ids, ["SG02"])


if __name__ == "__main__":
    unittest.main()
