"""
test/webui/test_jobs.py — Tests for Web UI Job Manager, Adapter execution, and REST endpoints.
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAIN_DIR = REPO_ROOT / "main"
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

from webui.jobs.manager import JobManager, get_job_manager
from webui.jobs.models import JobCreateRequest, JobResponse, JobStage, JobStatus
from webui.jobs.adapters.base import BaseStageAdapter
from webui.server import create_app


class MockAdapter(BaseStageAdapter):
    def run(self, script_ids, options, emit_log, emit_progress, check_cancelled):
        for idx, sid in enumerate(script_ids, start=1):
            if check_cancelled():
                emit_log(f"Cancelled before {sid}")
                break
            emit_log(f"Processing {sid}")
            emit_progress(idx, len(script_ids), sid)
        return {"success_count": len(script_ids), "failed_ids": []}


class TestWebUIJobs(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())
        self.jm = get_job_manager()
        # Register a quick mock adapter for scripts stage to test pipeline execution
        self.mock_adapter = MockAdapter()
        self.jm.register_adapter(JobStage.SCRIPTS, self.mock_adapter)

    def test_enqueue_job_rest(self):
        """Verify POST /api/jobs enqueues a job."""
        response = self.client.post(
            "/api/jobs",
            json={"stage": "scripts", "script_ids": ["TEST01", "TEST02"]},
        )
        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertIn("job_id", data)
        self.assertEqual(data["stage"], "scripts")
        self.assertEqual(data["script_ids"], ["TEST01", "TEST02"])

        # Fetch it back
        job_id = data["job_id"]
        get_res = self.client.get(f"/api/jobs/{job_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["job_id"], job_id)

    def test_enqueue_job_missing_scripts_400(self):
        """Verify POST /api/jobs fails when script_ids is empty."""
        response = self.client.post(
            "/api/jobs",
            json={"stage": "scripts", "script_ids": []},
        )
        self.assertEqual(response.status_code, 400)

    def test_list_jobs_rest(self):
        """Verify GET /api/jobs lists all jobs."""
        response = self.client.get("/api/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_get_nonexistent_job_404(self):
        """Verify GET /api/jobs/NONEXISTENT returns 404."""
        response = self.client.get("/api/jobs/NONEXISTENT999")
        self.assertEqual(response.status_code, 404)

    def test_cancel_job_rest(self):
        """Verify cancellation endpoint."""
        # Enqueue a job
        res = self.client.post(
            "/api/jobs",
            json={"stage": "scripts", "script_ids": ["CANCEL_ME"]},
        )
        job_id = res.json()["job_id"]
        # Cancel it
        cancel_res = self.client.post(f"/api/jobs/{job_id}/cancel")
        self.assertIn(cancel_res.status_code, [200, 400])


if __name__ == "__main__":
    unittest.main()

