"""
test/webui/test_jobs.py — Tests for Web UI Job Manager, Adapter execution, and REST endpoints.
"""

from __future__ import annotations

import json
import sys
import tempfile
from threading import Event
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
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.app = create_app(Path(workspace.name))
        self.client = TestClient(self.app)
        self.jm = self.app.state.job_manager
        transcriber = patch("webui.jobs.adapters.assembly.Transcriber")
        transcriber.start()
        self.addCleanup(transcriber.stop)
        self.addCleanup(self.jm.close)
        # Register a quick mock adapter for scripts and assembly stages to test pipeline execution without real ffmpeg/llm
        self.mock_adapter = MockAdapter()
        self.jm.register_adapter(JobStage.SCRIPTS, self.mock_adapter)
        self.jm.register_adapter(JobStage.ASSEMBLY, self.mock_adapter)

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

    def test_cancel_running_and_queued_jobs_without_stopping_worker(self):
        started = Event()
        release = Event()
        observed_cancellation = Event()

        class BlockingAdapter(BaseStageAdapter):
            def run(self, script_ids, options, emit_log, emit_progress, check_cancelled):
                started.set()
                if not release.wait(timeout=10):
                    raise TimeoutError("Test did not release the worker")
                if check_cancelled():
                    observed_cancellation.set()
                    raise InterruptedError("Cancellation observed")
                raise AssertionError("Adapter continued after cancellation")

        self.jm.register_adapter(JobStage.SCRIPTS, BlockingAdapter())
        def enqueue(stage):
            response = self.client.post("/api/jobs", json={"stage": stage, "script_ids": ["EG01"]})
            self.assertEqual(response.status_code, 202, response.text)
            return f"/api/jobs/{response.json()['job_id']}"

        try:
            running = enqueue("scripts")
            self.assertTrue(started.wait(timeout=5))
            self.assertEqual(self.client.get(running).json()["status"], "running")
            queued = enqueue("scripts")
            self.assertEqual(self.client.post(f"{queued}/cancel").status_code, 200)
            self.assertEqual(self.client.post(f"{running}/cancel").status_code, 200)
        finally:
            release.set()
        self.assertTrue(observed_cancellation.wait(timeout=5))
        self.assertEqual(self.client.get(running).json()["status"], "cancelled")
        self.assertEqual(self.client.get(queued).json()["status"], "cancelled")

        next_job = enqueue("assembly")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = self.client.get(next_job).json()
            if result["status"] == "completed":
                break
            time.sleep(0.01)
        self.assertEqual(result["status"], "completed", result)

    def test_job_captures_stdout_and_logging(self):
        """Verify prints and logging in adapters are captured in job logs."""
        class VerboseAdapter(BaseStageAdapter):
            def run(self, script_ids, options, emit_log, emit_progress, check_cancelled):
                print("Captured print statement from worker module")
                import logging
                logging.getLogger("test").warning("Captured worker warning")
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
        self.assertIn("Captured worker warning", all_logs)

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
        # pyrefly: ignore[missing-import]
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

    @patch("webui.jobs.adapters.assembly.StateManager")
    @patch("webui.jobs.adapters.assembly.process_script")
    def test_assembly_adapter_forces_done_script_and_preserves_previous_video(
        self, mock_process, mock_sm_cls
    ):
        """Verify mass assembly keeps the previous MP4 while delegating a forced render."""
        # pyrefly: ignore[missing-import]
        from webui.jobs.adapters.assembly import AssemblyAdapter

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "script_IE07"
            out_dir.mkdir(parents=True, exist_ok=True)
            existing_mp4 = out_dir / "script_IE07_final.mp4"
            existing_mp4.write_bytes(b"stale-video-bytes")

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
                return False

            mock_process.side_effect = _fake_process

            adapter = AssemblyAdapter()
            logs = []
            result = adapter.run(
                script_ids=["IE07"],
                options={"force": False, "max_attempts": 1},
                emit_log=lambda msg: logs.append(msg),
                emit_progress=lambda *_a: None,
                check_cancelled=lambda: False,
            )

            self.assertEqual(result["success_count"], 0)
            self.assertEqual(result["failed_ids"], ["IE07"])
            self.assertEqual(existed_when_process_called, [True])
            mock_sm.save_script_state.assert_not_called()
            self.assertEqual(state["status"]["video_assembly"], "done")
            self.assertEqual(state["assets"]["final_video"], str(existing_mp4))
            self.assertTrue(mock_process.call_args.kwargs["regenerate_subtitles"])
            self.assertEqual(existing_mp4.read_bytes(), b"stale-video-bytes")

    @patch("webui.jobs.adapters.assembly.StateManager")
    @patch("webui.jobs.adapters.assembly.process_script")
    def test_assembly_adapter_preserves_existing_video_when_prerequisites_missing(
        self, mock_process, mock_sm_cls
    ):
        """Verify existing .mp4 is NOT deleted when prerequisites (voice/images) are missing."""
        # pyrefly: ignore[missing-import]
        from webui.jobs.adapters.assembly import AssemblyAdapter

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "script_IE07"
            out_dir.mkdir(parents=True, exist_ok=True)
            existing_mp4 = out_dir / "script_IE07_final.mp4"
            existing_mp4.write_bytes(b"keep-me")

            state = {
                "id": "IE07",
                "assets": {"final_video": str(existing_mp4)},
                "status": {"voice_generation": "done", "image_generation": "pending", "video_assembly": "done"},
            }
            mock_sm = MagicMock()
            mock_sm.script_exists.return_value = True
            mock_sm.get_script_state.return_value = state
            mock_sm_cls.return_value = mock_sm

            adapter = AssemblyAdapter(base_dir=Path(tmp))
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
        from video_creation._C_image_generation.service import ensure_image_prompts_for_script

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

        with patch("video_creation._C_image_generation.service.ensure_llama_running"):
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

    @patch("webui.jobs.adapters.assembly.SubtitleBuilder")
    @patch("webui.jobs.adapters.assembly.VideoAssembler")
    @patch("webui.jobs.adapters.assembly.Transcriber")
    @patch("webui.jobs.adapters.assembly.StateManager")
    @patch("webui.jobs.adapters.assembly.process_script")
    def test_assembly_adapter_mass_parallel_pool_and_preflight_skip(
        self,
        mock_process,
        mock_sm_cls,
        mock_transcriber_cls,
        mock_assembler_cls,
        mock_builder_cls,
    ):
        """Verify mass AssemblyAdapter runs workers in parallel, skips missing prereqs upfront, and tracks exact counts."""
        import threading
        # pyrefly: ignore[missing-import]
        from webui.jobs.adapters.assembly import AssemblyAdapter

        states = {
            "MISSING": {
                "id": "MISSING",
                "status": {"voice_generation": "done", "image_generation": "pending", "video_assembly": "pending"},
            },
            "EF01": {
                "id": "EF01",
                "status": {"voice_generation": "done", "image_generation": "done", "video_assembly": "pending"},
            },
            "EE01": {
                "id": "EE01",
                "status": {"voice_generation": "done", "image_generation": "done", "video_assembly": "pending"},
            },
            "ER01": {
                "id": "ER01",
                "status": {"voice_generation": "done", "image_generation": "done", "video_assembly": "pending"},
            },
        }
        mock_sm = MagicMock()
        mock_sm.script_exists.side_effect = lambda sid: sid in states
        mock_sm.get_script_state.side_effect = lambda sid: states[sid]
        mock_sm_cls.return_value = mock_sm

        barrier = threading.Barrier(2, timeout=3.0)
        barrier_lock = threading.Lock()
        barrier_used = {"count": 0}
        conc_lock = threading.Lock()
        active = {"cur": 0, "max": 0}

        def _fake_process(**kwargs):
            sid = kwargs["script_data"]["id"]
            with conc_lock:
                active["cur"] += 1
                active["max"] = max(active["max"], active["cur"])
            try:
                should_wait = False
                with barrier_lock:
                    if barrier_used["count"] < 2:
                        barrier_used["count"] += 1
                        should_wait = True
                if should_wait:
                    barrier.wait()
                return sid != "MISSING"
            finally:
                with conc_lock:
                    active["cur"] -= 1

        mock_process.side_effect = _fake_process

        adapter = AssemblyAdapter()
        logs = []
        progress = []
        result = adapter.run(
            script_ids=["MISSING", "EF01", "EE01", "ER01"],
            options={"force": True, "workers": 3, "auto_keep_subtitles": False},
            emit_log=logs.append,
            emit_progress=lambda cur, tot, sid: progress.append((cur, tot, sid)),
            check_cancelled=lambda: False,
        )

        self.assertEqual(result["success_count"], 3)
        self.assertEqual(result["failed_ids"], ["MISSING"])
        self.assertEqual(result["total"], 4)
        self.assertGreaterEqual(active["max"], 2)
        self.assertEqual(mock_transcriber_cls.call_count, 1)
        self.assertEqual(mock_process.call_count, 3)
        self.assertTrue(any("3 parallel worker(s)" in l for l in logs))
        self.assertEqual(progress[-1], (4, 4, None))

    @patch("webui.jobs.adapters.assembly.SubtitleBuilder")
    @patch("webui.jobs.adapters.assembly.VideoAssembler")
    @patch("webui.jobs.adapters.assembly.Transcriber")
    @patch("webui.jobs.adapters.assembly.StateManager")
    @patch("webui.jobs.adapters.assembly.process_script")
    def test_assembly_adapter_auto_reuses_fresh_subtitles_and_skips_whisper_boot(
        self,
        mock_process,
        mock_sm_cls,
        mock_transcriber_cls,
        mock_assembler_cls,
        mock_builder_cls,
    ):
        """Verify Option A skips Whisper when `.ass` is newer than `.wav` and re-enables Whisper if `.wav` updates."""
        import os
        import time
        # pyrefly: ignore[missing-import]
        from config import get_script_output_dir
        # pyrefly: ignore[missing-import]
        from webui.jobs.adapters.assembly import AssemblyAdapter

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            states = {}
            wav_paths = {}
            for sid in ("EF01", "EF02"):
                out_dir = get_script_output_dir(sid, "english", tmp_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                wav_p = out_dir / f"script_{sid}_master.wav"
                ass_p = out_dir / f"script_{sid}_subtitles.ass"
                wav_p.write_bytes(b"RIFFdummy")
                ass_p.write_text("[Script Info]\nTitle: Test\n", encoding="utf-8")
                now = time.time()
                os.utime(wav_p, (now - 20, now - 20))
                os.utime(ass_p, (now - 5, now - 5))
                wav_paths[sid] = wav_p
                states[sid] = {
                    "id": sid,
                    "metadata": {"LABEL": "english"},
                    "status": {"voice_generation": "done", "image_generation": "done", "video_assembly": "done"},
                }

            mock_sm = MagicMock()
            mock_sm.script_exists.return_value = True
            mock_sm.get_script_state.side_effect = lambda sid: states[sid]
            mock_sm_cls.return_value = mock_sm

            regen_seen = {}

            def _record_process(**kwargs):
                regen_seen[kwargs["script_data"]["id"]] = kwargs["regenerate_subtitles"]
                return True

            mock_process.side_effect = _record_process
            adapter = AssemblyAdapter(base_dir=tmp_dir)
            logs = []
            res_fresh = adapter.run(
                script_ids=["EF01", "EF02"],
                options={"workers": 2},
                emit_log=logs.append,
                emit_progress=lambda *_a: None,
                check_cancelled=lambda: False,
            )

            self.assertEqual(res_fresh["success_count"], 2)
            self.assertEqual(mock_transcriber_cls.call_count, 0)
            self.assertEqual(regen_seen, {"EF01": False, "EF02": False})
            self.assertTrue(any("skipping Whisper model load" in l for l in logs))

            # Regenerate voice on EF02 -> newer WAV triggers Whisper only for EF02
            future = time.time() + 20
            os.utime(wav_paths["EF02"], (future, future))
            regen_seen.clear()
            res_mixed = adapter.run(
                script_ids=["EF01", "EF02"],
                options={"workers": 2},
                emit_log=logs.append,
                emit_progress=lambda *_a: None,
                check_cancelled=lambda: False,
            )

            self.assertEqual(res_mixed["success_count"], 2)
            self.assertEqual(mock_transcriber_cls.call_count, 1)
            self.assertEqual(regen_seen, {"EF01": False, "EF02": True})

    def test_job_log_capture_is_thread_safe(self):
        """Verify _JobLogCapture preserves every complete line cleanly across concurrent worker threads."""
        import threading
        import time
        # pyrefly: ignore[missing-import]
        from webui.jobs.manager import _JobLogCapture

        captured = []
        cap = _JobLogCapture(captured.append, original_stream=None)

        def _writer(tid: int):
            for idx in range(50):
                line = f"worker-{tid}-line-{idx}"
                cap.write(line[:8])
                time.sleep(0)
                cap.write(line[8:] + "\n")

        threads = [threading.Thread(target=_writer, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        cap.flush()

        expected = {f"worker-{t}-line-{idx}" for t in range(4) for idx in range(50)}
        self.assertEqual(len(captured), 200)
        self.assertEqual(set(captured), expected)

    @patch("webui.jobs.adapters.assembly.SubtitleBuilder")
    @patch("webui.jobs.adapters.assembly.VideoAssembler")
    @patch("webui.jobs.adapters.assembly.Transcriber")
    @patch("webui.jobs.adapters.assembly.StateManager")
    @patch("webui.jobs.adapters.assembly.process_script")
    def test_assembly_adapter_proceeds_when_status_pending_but_disk_assets_exist(
        self,
        mock_process,
        mock_sm_cls,
        mock_transcriber_cls,
        mock_assembler_cls,
        mock_builder_cls,
    ):
        """Verify mass assembly proceeds when image_generation/voice_generation is 'pending' but real assets exist on disk."""
        # pyrefly: ignore[missing-import]
        from config import get_script_output_dir
        # pyrefly: ignore[missing-import]
        from webui.jobs.adapters.assembly import AssemblyAdapter

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            out_dir = get_script_output_dir("EG01", "English", tmp_dir)
            img_dir = out_dir / "images"
            img_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "script_EG01_master.wav").write_bytes(b"RIFFdummy")
            (out_dir / "timings.json").write_text('{"hook":{"start":0.0,"end":1.0}}', encoding="utf-8")
            (img_dir / "script_EG01_hook.png").write_bytes(b"PNGdummy")

            state = {
                "id": "EG01",
                "metadata": {"LABEL": "English"},
                "status": {"voice_generation": "done", "image_generation": "pending", "video_assembly": "pending"},
                "assets": {},
            }
            mock_sm = MagicMock()
            mock_sm.script_exists.return_value = True
            mock_sm.get_script_state.return_value = state
            mock_sm_cls.return_value = mock_sm
            mock_process.return_value = True

            adapter = AssemblyAdapter(base_dir=tmp_dir)
            logs = []
            res = adapter.run(
                script_ids=["EG01"],
                options={"force": True},
                emit_log=logs.append,
                emit_progress=lambda *_a: None,
                check_cancelled=lambda: False,
            )

            self.assertEqual(res["success_count"], 1)
            self.assertEqual(res["failed_ids"], [])
            mock_process.assert_called_once()
            self.assertTrue(any("scene images exist on disk" in l for l in logs))


if __name__ == "__main__":
    unittest.main()

