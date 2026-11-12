"""
test/webui/test_jobs.py — Tests for Web UI Job Manager, Adapter execution, and REST endpoints.
"""

from __future__ import annotations

import sys
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
from webui.jobs.manager import JobManager, get_job_manager
# pyrefly: ignore[missing-import]
from webui.jobs.models import JobCreateRequest, JobResponse, JobStage, JobStatus
# pyrefly: ignore[missing-import]
from webui.jobs.adapters.base import BaseStageAdapter
# pyrefly: ignore[missing-import]
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
        # Register a quick mock adapter for scripts and assembly stages to test pipeline execution without real ffmpeg/llm
        self.mock_adapter = MockAdapter()
        self.jm.register_adapter(JobStage.SCRIPTS, self.mock_adapter)
        self.jm.register_adapter(JobStage.ASSEMBLY, self.mock_adapter)

    def tearDown(self):
        # pyrefly: ignore[missing-import]
        from webui.jobs.adapters.scripts import ScriptsAdapter
        from webui.jobs.adapters.assembly import AssemblyAdapter
        self.jm.register_adapter(JobStage.SCRIPTS, ScriptsAdapter())
        self.jm.register_adapter(JobStage.ASSEMBLY, AssemblyAdapter())

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

    def test_job_captures_stdout_and_logging(self):
        """Verify prints and logging in adapters are captured in job logs."""
        class VerboseAdapter(BaseStageAdapter):
            def run(self, script_ids, options, emit_log, emit_progress, check_cancelled):
                print("Captured print statement from worker module")
                import logging
                logging.getLogger("test").info("Captured logging info from worker module")
                return {"success_count": 1, "failed_ids": []}

        self.jm.register_adapter(JobStage.SCRIPTS, VerboseAdapter())
        res = self.client.post("/api/jobs", json={"stage": "scripts", "script_ids": ["PRINT_TEST"]})
        job_id = res.json()["job_id"]
        # Give worker a moment to execute
        for _ in range(50):
            time.sleep(0.1)
            job = self.jm.get_job(job_id)
            if job and job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                break
        self.assertIsNotNone(job)
        all_logs = " ".join(job.logs)
        self.assertIn("Captured print statement", all_logs)
        self.assertIn("Captured logging info", all_logs)

    def test_assembly_job_enqueue(self):
        """Verify POST /api/jobs enqueues an assembly stage job."""
        response = self.client.post(
            "/api/jobs",
            json={"stage": "assembly", "script_ids": ["IE07", "IG07"]},
        )
        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertEqual(data["stage"], "assembly")
        self.assertEqual(data["script_ids"], ["IE07", "IG07"])

    @patch("webui.jobs.adapters.assembly.StateManager")
    @patch("webui.jobs.adapters.assembly.process_script")
    def test_assembly_adapter_execution(self, mock_process, mock_sm_cls):
        """Verify AssemblyAdapter runs process_script and reports progress."""
        from webui.jobs.adapters.assembly import AssemblyAdapter

        mock_sm = MagicMock()
        mock_sm.script_exists.return_value = True
        mock_sm.get_script_state.return_value = {
            "id": "IE07",
            "status": {"voice_generation": "done", "image_generation": "done", "video_assembly": "pending"},
        }
        mock_sm_cls.return_value = mock_sm
        mock_process.return_value = True

        adapter = AssemblyAdapter()
        logs = []
        progress = []

        result = adapter.run(
            script_ids=["IE07"],
            options={"force": True},
            emit_log=lambda msg: logs.append(msg),
            emit_progress=lambda cur, tot, sid: progress.append((cur, tot, sid)),
            check_cancelled=lambda: False,
        )

        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failed_ids"], [])
        self.assertTrue(mock_process.called)
        self.assertTrue(any("✓ Video assembly completed" in l for l in logs))


if __name__ == "__main__":
    unittest.main()

