"""
test/webui/test_jobs.py — Tests for Web UI Job Manager, Adapter execution, and REST endpoints.
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
        # pyrefly: ignore[missing-import]
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

    @patch("webui.jobs.adapters.assembly.get_script_output_dir")
    @patch("webui.jobs.adapters.assembly.StateManager")
    @patch("webui.jobs.adapters.assembly.process_script")
    def test_assembly_adapter_execution(self, mock_process, mock_sm_cls, mock_out_dir):
        """Verify AssemblyAdapter runs process_script and reports progress."""
        # pyrefly: ignore[missing-import]
        from webui.jobs.adapters.assembly import AssemblyAdapter

        with tempfile.TemporaryDirectory() as tmp:
            mock_out_dir.return_value = Path(tmp) / "script_IE07"
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

    @patch("webui.jobs.adapters.assembly.get_script_output_dir")
    @patch("webui.jobs.adapters.assembly.StateManager")
    @patch("webui.jobs.adapters.assembly.process_script")
    def test_assembly_adapter_forces_done_script_deletes_existing_video_and_recreates(
        self, mock_process, mock_sm_cls, mock_out_dir
    ):
        """Verify mass assembly forces target IDs even with force=False, deleting existing .mp4 before recreating."""
        # pyrefly: ignore[missing-import]
        from webui.jobs.adapters.assembly import AssemblyAdapter

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "script_IE07"
            out_dir.mkdir(parents=True, exist_ok=True)
            existing_mp4 = out_dir / "script_IE07_final.mp4"
            existing_mp4.write_bytes(b"stale-video-bytes")
            mock_out_dir.return_value = out_dir

            state = {
                "id": "IE07",
                "metadata": {"LABEL": "Italian | daily | greetings"},
                "assets": {"final_video": str(existing_mp4)},
                "status": {"voice_generation": "done", "image_generation": "done", "video_assembly": "done"},
            }
            mock_sm = MagicMock()
            mock_sm.script_exists.return_value = True
            mock_sm.get_script_state.return_value = state
            mock_sm_cls.return_value = mock_sm

            existed_when_process_called = []

            def _fake_process(**kwargs):
                existed_when_process_called.append(existing_mp4.exists())
                existing_mp4.write_bytes(b"recreated-video-bytes")
                return True

            mock_process.side_effect = _fake_process

            adapter = AssemblyAdapter()
            logs = []
            result = adapter.run(
                script_ids=["IE07"],
                options={"force": False},
                emit_log=lambda msg: logs.append(msg),
                emit_progress=lambda *_a: None,
                check_cancelled=lambda: False,
            )

            self.assertEqual(result["success_count"], 1)
            self.assertEqual(result["failed_ids"], [])
            # Must have deleted stale file BEFORE process_script ran, then saved reset state
            self.assertEqual(existed_when_process_called, [False])
            mock_sm.save_script_state.assert_called_once_with("IE07", state)
            self.assertEqual(state["status"]["video_assembly"], "pending")
            self.assertNotIn("final_video", state["assets"])
            self.assertTrue(mock_process.call_args.kwargs["regenerate_subtitles"])
            self.assertTrue(existing_mp4.exists())
            self.assertEqual(existing_mp4.read_bytes(), b"recreated-video-bytes")
            self.assertTrue(any("Deleted existing final video" in l for l in logs))

    @patch("webui.jobs.adapters.assembly.get_script_output_dir")
    @patch("webui.jobs.adapters.assembly.StateManager")
    @patch("webui.jobs.adapters.assembly.process_script")
    def test_assembly_adapter_preserves_existing_video_when_prerequisites_missing(
        self, mock_process, mock_sm_cls, mock_out_dir
    ):
        """Verify existing .mp4 is NOT deleted when prerequisites (voice/images) are missing."""
        # pyrefly: ignore[missing-import]
        from webui.jobs.adapters.assembly import AssemblyAdapter

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "script_IE07"
            out_dir.mkdir(parents=True, exist_ok=True)
            existing_mp4 = out_dir / "script_IE07_final.mp4"
            existing_mp4.write_bytes(b"keep-me")
            mock_out_dir.return_value = out_dir

            state = {
                "id": "IE07",
                "assets": {"final_video": str(existing_mp4)},
                "status": {"voice_generation": "done", "image_generation": "pending", "video_assembly": "done"},
            }
            mock_sm = MagicMock()
            mock_sm.script_exists.return_value = True
            mock_sm.get_script_state.return_value = state
            mock_sm_cls.return_value = mock_sm

            adapter = AssemblyAdapter()
            logs = []
            result = adapter.run(
                script_ids=["IE07"],
                options={"force": True},
                emit_log=lambda msg: logs.append(msg),
                emit_progress=lambda *_a: None,
                check_cancelled=lambda: False,
            )

            self.assertEqual(result["success_count"], 0)
            self.assertEqual(result["failed_ids"], ["IE07"])
            mock_process.assert_not_called()
            mock_sm.save_script_state.assert_not_called()
            self.assertTrue(existing_mp4.exists())

    def test_ensure_image_prompts_preserves_general_prompt_when_requested(self):
        """Verify preserve_general_prompt=True keeps saved general_prompt while regenerating scene prompts."""
        # pyrefly: ignore[missing-import]
        from video_creation._C_image_generation.main import ensure_image_prompts_for_script

        saved_gp = (
            "A sunlit cobbled square in Lisbon with azure tile facades and warm golden-hour light. "
            "One 16-year-old high-school student girl with warm tan skin, simple black 2D cartoon eyes, "
            "soft dark wavy ponytail, olive overshirt, navy chinos, and canvas sneakers."
        )
        script_data = {
            "id": "EF01",
            "script_text": json.dumps({
                "title": "Silent Letters",
                "hook": "Hook text",
                "setup": "Setup text",
                "discovery": "Discovery text",
                "explanation": "Explanation text",
                "payoff": "Payoff text",
            }),
            "metadata": {"LABEL": "english", "VIDEO_TYPE": "FUN_FACTS"},
            "content_metadata": {
                "language": "English",
                "video_type": "FUN_FACTS",
                "speakers_gender": {"Narrator": "female"},
                "anchor_environment": saved_gp,
            },
            "assets": {
                "general_prompt": saved_gp,
                "anchor_world_id": "custom_world",
                "anchor_world_title": "Lisbon Square",
                "image_prompts": {"hook": "stale hook"},
            },
        }

        mock_sm = MagicMock()
        mock_pb = MagicMock()
        mock_pb.build_storyboard_prompts.return_value = {
            "hook": "New hook following saved GP",
            "setup": "New setup following saved GP",
            "discovery": "New discovery following saved GP",
            "explanation": "New explanation following saved GP",
            "payoff": "New payoff following saved GP",
        }

        with patch("video_creation._C_image_generation.main.ensure_llama_running"):
            ok = ensure_image_prompts_for_script(
                script_data=script_data,
                state_manager=mock_sm,
                prompt_builder=mock_pb,
                force=True,
                preserve_general_prompt=True,
            )

        self.assertTrue(ok)
        mock_pb.build_general_prompt.assert_not_called()
        self.assertEqual(script_data["assets"]["general_prompt"], saved_gp)
        self.assertEqual(script_data["content_metadata"]["anchor_environment"], saved_gp)
        self.assertEqual(script_data["assets"]["anchor_world_id"], "custom_world")
        self.assertEqual(script_data["assets"]["anchor_world_title"], "Lisbon Square")
        self.assertIn("character_anchors", script_data["assets"])
        mock_pb.build_storyboard_prompts.assert_called_once()
        sb_kwargs = mock_pb.build_storyboard_prompts.call_args.kwargs
        self.assertEqual(sb_kwargs["general_prompt"], saved_gp)
        self.assertEqual(sb_kwargs["anchor_environment"], saved_gp)
        self.assertEqual(script_data["assets"]["image_prompts"]["hook"], "New hook following saved GP")

    @patch("webui.jobs.adapters.images.ImageComfyClient")
    @patch("webui.jobs.adapters.images.process_script", return_value=True)
    @patch("webui.jobs.adapters.images.ensure_llama_stopped")
    @patch("webui.jobs.adapters.images.ensure_llama_running")
    @patch("webui.jobs.adapters.images.ensure_image_prompts_for_script")
    @patch("webui.jobs.adapters.images.StateManager")
    def test_images_adapter_forwards_preserve_general_prompt_option(
        self, mock_sm_cls, mock_ensure, _mock_start, _mock_stop, _mock_proc, _mock_comfy
    ):
        """Verify ImagesAdapter forwards preserve_general_prompt=True when set and defaults to False."""
        # pyrefly: ignore[missing-import]
        from webui.jobs.adapters.images import ImagesAdapter

        saved_gp = "Saved custom general prompt"
        state = {
            "id": "EF01",
            "status": {"image_generation": "pending"},
            "assets": {"general_prompt": saved_gp, "image_prompts": {}},
        }
        mock_sm = MagicMock()
        mock_sm.script_exists.return_value = True

        def fake_get_state(sid):
            return {
                **state,
                "assets": {"general_prompt": saved_gp, "image_prompts": {"hook": "new hook"}},
            }

        mock_sm.get_script_state.side_effect = [state, fake_get_state("EF01"), state]
        mock_sm_cls.return_value = mock_sm

        adapter = ImagesAdapter()
        logs = []
        adapter.run(
            script_ids=["EF01"],
            options={"force": True, "regenerate_prompts": True, "preserve_general_prompt": True},
            emit_log=logs.append,
            emit_progress=lambda *_a: None,
            check_cancelled=lambda: False,
        )
        self.assertTrue(mock_ensure.call_args.kwargs["preserve_general_prompt"])
        self.assertTrue(any("Preserving saved general prompt" in l for l in logs))

        # Default (mass creation): preserve_general_prompt should default to False
        mock_ensure.reset_mock()
        mock_sm.get_script_state.side_effect = [state, fake_get_state("EF01"), state]
        adapter.run(
            script_ids=["EF01"],
            options={"force": True, "regenerate_prompts": True},
            emit_log=lambda _m: None,
            emit_progress=lambda *_a: None,
            check_cancelled=lambda: False,
        )
        self.assertFalse(mock_ensure.call_args.kwargs["preserve_general_prompt"])


if __name__ == "__main__":
    unittest.main()

