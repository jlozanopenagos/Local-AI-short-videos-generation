"""
test/webui/test_chalkboard_adapter.py — Tests for WebUI ChalkboardAdapter and /render-chalkboard endpoint.
Verifies Game Chalkboard rendering for G-series scripts.
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
from webui.jobs.adapters.chalkboard import ChalkboardAdapter
# pyrefly: ignore[missing-import]
from webui.jobs.manager import get_job_manager
# pyrefly: ignore[missing-import]
from webui.jobs.models import JobCreateRequest, JobStage, JobStatus
# pyrefly: ignore[missing-import]
from webui.server import create_app


class TestChalkboardAdapter(unittest.TestCase):
    """Verifies ChalkboardAdapter execution and /render-chalkboard endpoint."""

    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.jm = get_job_manager()
        self.adapter = ChalkboardAdapter()
        self.jm.register_adapter(JobStage.CHALKBOARD, self.adapter)

    def test_chalkboard_adapter_is_registered_in_job_manager(self):
        self.assertIn(JobStage.CHALKBOARD, self.jm._adapters)
        self.assertIsInstance(self.jm._adapters[JobStage.CHALKBOARD], ChalkboardAdapter)

    def test_render_chalkboard_endpoint_non_game_fails_400(self):
        """Non-game scripts (e.g. EE01) must return 400 Bad Request."""
        res = self.client.post("/api/scripts/EE01/render-chalkboard", json={})
        self.assertEqual(res.status_code, 400)
        self.assertIn("not a GAME video", res.json().get("detail", ""))

    def test_render_chalkboard_endpoint_nonexistent_fails_404(self):
        """Nonexistent script returns 404."""
        res = self.client.post("/api/scripts/NONEXISTENT99/render-chalkboard", json={})
        self.assertEqual(res.status_code, 404)

    @patch("video_creation._C_image_generation.core.chalkboard_renderer.render_chalkboard_image")
    def test_render_chalkboard_endpoint_game_succeeds(self, mock_render):
        """Game script (e.g. EG01) renders successfully and updates image state."""
        mock_render.return_value = Path("dummy_challenge.png")
        res = self.client.post(
            "/api/scripts/EG01/render-chalkboard",
            json={"chalkboard_exercise": "Test sentence with ___\\nA) Alpha\\nB) Beta"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("script_EG01_challenge.png", data.get("image_file", ""))
        mock_render.assert_called_once()

    @patch("webui.jobs.adapters.chalkboard.render_chalkboard_image")
    def test_chalkboard_adapter_run_skips_non_game_and_renders_game(self, mock_render):
        """Batch adapter processes game scripts and skips non-game scripts."""
        logs = []
        progress_calls = []

        result = self.adapter.run(
            script_ids=["EE01", "EG01"],
            options={"force": True},
            emit_log=lambda msg: logs.append(msg),
            emit_progress=lambda cur, tot, sid: progress_calls.append((cur, tot, sid)),
            check_cancelled=lambda: False,
        )

        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["skipped_count"], 1)
        self.assertEqual(result["total"], 2)
        mock_render.assert_called_once()
        self.assertTrue(any("SKIPPED: Script is not a GAME video" in l for l in logs))
        self.assertTrue(any("Chalkboard challenge image saved" in l for l in logs))


if __name__ == "__main__":
    unittest.main()
