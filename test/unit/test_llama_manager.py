"""
test/unit/test_llama_manager.py — Unit tests for Headless llama.cpp Process Supervisor.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# pyrefly: ignore[missing-import]
from core.llama_manager import (
    LlamaManager,
    active_llama_session,
    ensure_llama_running,
    ensure_llama_stopped,
)


class TestLlamaManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp_dir.name)
        self.llm_dir = self.base_dir / "llama.ccp"
        self.llm_dir.mkdir(parents=True)
        (self.llm_dir / "llama-server.exe").write_text("", encoding="utf-8")
        (self.llm_dir / "_Gemma4-E2B.bat").write_text(
            'llama-server.exe -m "Gemma4 E2B"\\model.gguf -ngl 999 -c 32768 --port 8080',
            encoding="utf-8",
        )

        self.log_dir = self.base_dir / "logs" / "llamacpp"
        self.mgr = LlamaManager(
            llm_dir=self.llm_dir,
            api_url="http://127.0.0.1:8080/v1",
            log_dir=self.log_dir,
        )

    def tearDown(self):
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_pid_lifecycle(self):
        """Verify writing, reading, and clearing process PID file."""
        self.assertIsNone(self.mgr._read_pid())
        self.mgr._write_pid(12345)
        self.assertEqual(self.mgr._read_pid(), 12345)
        self.mgr._clear_pid()
        self.assertIsNone(self.mgr._read_pid())

    def test_parse_bat_args(self):
        """Verify _parse_bat_args cleans carets and normalizes mid-token quotes."""
        args = self.mgr._parse_bat_args()
        self.assertIn("-m", args)
        self.assertIn("Gemma4 E2B\\model.gguf", args)
        self.assertIn("-ngl", args)
        self.assertIn("999", args)

    @patch("core.llama_manager.requests.get")
    def test_is_reachable_true_and_false(self, mock_get):
        """Verify is_reachable returns True on 200 OK and False on connection failure."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        self.assertTrue(self.mgr.is_reachable())

        mock_get.side_effect = Exception("Connection refused")
        self.assertFalse(self.mgr.is_reachable())

    @patch.object(LlamaManager, "is_running", return_value=(True, 1234))
    @patch.object(LlamaManager, "is_reachable", return_value=True)
    def test_start_already_running(self, mock_reach, mock_is_running):
        """Verify start() returns True immediately without spawning if reachable."""
        with patch("core.llama_manager.subprocess.Popen") as mock_popen:
            ok = self.mgr.start(timeout=5, wait=False)
            self.assertTrue(ok)
            mock_popen.assert_not_called()

    @patch.object(LlamaManager, "is_running", return_value=(False, None))
    @patch.object(LlamaManager, "is_reachable", side_effect=[False, True])
    @patch("core.llama_manager.subprocess.Popen")
    def test_start_spawns_process_with_correct_flags(self, mock_popen, mock_reach, mock_is_run):
        """Verify start() launches process with CREATE_NO_WINDOW / DETACHED_PROCESS."""
        fake_proc = MagicMock()
        fake_proc.pid = 9876
        mock_popen.return_value = fake_proc

        ok = self.mgr.start(timeout=5, wait=True)
        self.assertTrue(ok)
        mock_popen.assert_called_once()
        self.assertEqual(self.mgr._read_pid(), 9876)

    @patch.object(LlamaManager, "is_running", return_value=(True, 9876))
    @patch.object(LlamaManager, "is_reachable", side_effect=[True, False])
    @patch("core.llama_manager.subprocess.run")
    def test_stop_terminates_process_and_cleans_pid(self, mock_run, mock_reach, mock_is_run):
        """Verify stop() executes taskkill /F /T on Windows and removes PID file."""
        self.mgr._write_pid(9876)
        ok = self.mgr.stop(timeout=5)
        self.assertTrue(ok)
        self.assertIsNone(self.mgr._read_pid())

    @patch("core.llama_manager.get_llama_manager")
    def test_active_llama_session_lifecycle(self, mock_get_mgr):
        """Verify active_llama_session context manager starts and stops on demand."""
        mock_instance = MagicMock()
        mock_instance.is_reachable.return_value = False
        mock_instance.start.return_value = True
        mock_get_mgr.return_value = mock_instance

        with active_llama_session(auto_stop=True) as mgr:
            self.assertEqual(mgr, mock_instance)
            mock_instance.start.assert_called_once()

        mock_instance.stop.assert_called_once()
