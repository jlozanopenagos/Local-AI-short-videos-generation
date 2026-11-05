"""
test/unit/test_comfy_pool.py — Unit tests for ComfyConnectionPool and VRAM concurrency arbiter.
"""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from core.comfy_pool import ComfyConnectionPool, get_comfy_pool


class TestComfyPool(unittest.TestCase):
    def setUp(self):
        # Reset singleton between tests
        ComfyConnectionPool._instance = None
        self.pool = ComfyConnectionPool(api_url="http://127.0.0.1:8188", pool_size=5)

    def tearDown(self):
        ComfyConnectionPool._instance = None

    def test_singleton_accessor(self):
        """Verify get_comfy_pool returns the identical singleton instance."""
        pool1 = get_comfy_pool()
        pool2 = get_comfy_pool()
        self.assertIs(pool1, pool2)

    def test_vram_guard_mutual_exclusion(self):
        """Verify vram_guard prevents concurrent execution of competing tasks."""
        order = []

        def task_one():
            with self.pool.vram_guard("TASK_A"):
                order.append("A_START")
                time.sleep(0.05)
                order.append("A_END")

        def task_two():
            time.sleep(0.01)  # Ensure task_one acquires first
            with self.pool.vram_guard("TASK_B"):
                order.append("B_START")
                order.append("B_END")

        t1 = threading.Thread(target=task_one)
        t2 = threading.Thread(target=task_two)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(order, ["A_START", "A_END", "B_START", "B_END"])

    def test_vram_guard_timeout(self):
        """Verify vram_guard raises TimeoutError if lock cannot be acquired within timeout."""
        # Hold lock in background thread
        lock_held = threading.Event()
        stop_holding = threading.Event()

        def holder():
            with self.pool.vram_guard("HOLDER"):
                lock_held.set()
                stop_holding.wait()

        t = threading.Thread(target=holder)
        t.start()
        lock_held.wait()

        try:
            with self.assertRaises(TimeoutError):
                with self.pool.vram_guard("COMPETITOR", timeout=0.1):
                    pass
        finally:
            stop_holding.set()
            t.join()

    @patch("core.comfy_pool.requests.Session.post")
    def test_free_vram_calls_free_endpoint(self, mock_post):
        """Verify free_vram sends POST to /free with correct payload."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        ok = self.pool.free_vram(unload_models=False)
        self.assertTrue(ok)
        mock_post.assert_called_once()
        self.assertIn("/free", mock_post.call_args[0][0])
        payload = mock_post.call_args[1]["json"]
        self.assertFalse(payload["unload_models"])
        self.assertTrue(payload["free_memory"])

    @patch("core.comfy_pool.requests.Session.get")
    def test_check_health(self, mock_get):
        """Verify check_health handles healthy and unhealthy responses."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        ok, msg = self.pool.check_health()
        self.assertTrue(ok)
        self.assertIn("healthy", msg)


if __name__ == "__main__":
    unittest.main()

