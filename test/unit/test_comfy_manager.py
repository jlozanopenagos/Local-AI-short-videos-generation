"""
test/unit/test_comfy_manager.py — Unit tests for Headless ComfyUI Process Supervisor.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# pyrefly: ignore[missing-import]
from core.comfy_manager import ComfyManager


class TestComfyManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp_dir.name)
        self.comfy_dir = self.base_dir / "ComfyUI_windows_portable"
        self.comfy_dir.mkdir(parents=True)
        (self.comfy_dir / "python_embeded").mkdir()
        (self.comfy_dir / "ComfyUI").mkdir()
        (self.comfy_dir / "ComfyUI" / "main.py").write_text("# mock main", encoding="utf-8")
        (self.comfy_dir / "python_embeded" / "pythonw.exe").write_text("", encoding="utf-8")

        self.log_dir = self.base_dir / "logs" / "comfyui"
        self.mgr = ComfyManager(
            comfy_dir=self.comfy_dir,
            api_url="http://127.0.0.1:8188",
            log_dir=self.log_dir,
        )

    def tearDown(self):
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_resolve_python_prefers_pythonw(self):
        """Verify _resolve_python selects pythonw.exe for windowless execution."""
        py_bin = self.mgr._resolve_python()
        self.assertEqual(py_bin.name.lower(), "pythonw.exe")

    def test_pid_lifecycle(self):
        """Verify writing, reading, and clearing process PID file."""
        self.assertIsNone(self.mgr._read_pid())
        self.mgr._write_pid(9999)
        self.assertEqual(self.mgr._read_pid(), 9999)
        self.mgr._clear_pid()
        self.assertIsNone(self.mgr._read_pid())

    @patch("core.comfy_manager.requests.get")
    def test_is_reachable_true_and_false(self, mock_get):
        """Verify is_reachable returns True on 200 OK and False on connection failure."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        self.assertTrue(self.mgr.is_reachable())

        mock_get.side_effect = Exception("Connection refused")
        self.assertFalse(self.mgr.is_reachable())

    @patch.object(ComfyManager, "is_reachable", return_value=True)
    def test_start_already_running(self, mock_reach):
        """Verify start() does not spawn a new process if ComfyUI is already active."""
        with patch("core.comfy_manager.subprocess.Popen") as mock_popen:
            ok = self.mgr.start(timeout=5, wait=False)
            self.assertTrue(ok)
            mock_popen.assert_not_called()

    @patch.object(ComfyManager, "is_running", return_value=(False, None))
    @patch.object(ComfyManager, "is_reachable", side_effect=[False, True])
    @patch("core.comfy_manager.subprocess.Popen")
    def test_start_spawns_process_with_correct_flags(self, mock_popen, mock_reach, mock_is_run):
        """Verify start() launches process with CREATE_NO_WINDOW / DETACHED_PROCESS and waits for readiness."""
        fake_proc = MagicMock()
        fake_proc.pid = 4321
        mock_popen.return_value = fake_proc

        with patch("core.comfy_manager.time.sleep"):
            ok = self.mgr.start(timeout=5, wait=True)

        self.assertTrue(ok)
        mock_popen.assert_called_once()
        call_kwargs = mock_popen.call_args.kwargs
        if os.name == "nt":
            self.assertTrue(call_kwargs["creationflags"] & 0x08000000)  # CREATE_NO_WINDOW
            self.assertTrue(call_kwargs["creationflags"] & 0x00000008)  # DETACHED_PROCESS
        self.assertEqual(self.mgr._read_pid(), 4321)

    @patch.object(ComfyManager, "is_running", return_value=(True, 4321))
    @patch.object(ComfyManager, "is_reachable", side_effect=[True, False])
    @patch("core.comfy_manager.subprocess.run")
    def test_stop_terminates_process_and_cleans_pid(self, mock_sub_run, mock_reach, mock_is_run):
        """Verify stop() executes taskkill /F /T and removes PID file upon port release."""
        self.mgr._write_pid(4321)
        with patch("core.comfy_manager.time.sleep"):
            ok = self.mgr.stop(timeout=5)

        self.assertTrue(ok)
        if os.name == "nt":
            mock_sub_run.assert_called_once()
            self.assertIn("taskkill", mock_sub_run.call_args[0][0])
        self.assertIsNone(self.mgr._read_pid())

    @patch.object(ComfyManager, "is_running", return_value=(True, 5555))
    @patch("core.comfy_manager.requests.get")
    def test_get_status_online_with_metrics(self, mock_get, mock_is_run):
        """Verify get_status returns parsed system_stats and queue counts."""
        sys_resp = MagicMock()
        sys_resp.status_code = 200
        sys_resp.json.return_value = {
            "devices": [{"name": "RTX 2060", "vram_total": 6442450944, "vram_free": 2147483648}]
        }

        queue_resp = MagicMock()
        queue_resp.status_code = 200
        queue_resp.json.return_value = {
            "queue_running": [["task-1"]],
            "queue_pending": [["task-2"], ["task-3"]],
        }

        mock_get.side_effect = [sys_resp, queue_resp]

        status = self.mgr.get_status()
        self.assertTrue(status["online"])
        self.assertEqual(status["pid"], 5555)
        self.assertEqual(status["queue_stats"]["running"], 1)
        self.assertEqual(status["queue_stats"]["pending"], 2)


if __name__ == "__main__":
    unittest.main()
