"""
test/webui/test_api.py — Unit tests for the Local Web UI FastAPI endpoints.
"""

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
from webui.server import create_app


class TestWebUIApi(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_healthz_endpoint(self):
        """Verify /healthz probe returns 200 OK."""
        resp = self.client.get("/healthz")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    @patch("webui.routers.system.get_comfy_manager")
    @patch("webui.routers.system.get_llama_manager")
    def test_system_status_endpoint(self, mock_get_lm, mock_get_cm):
        """Verify /api/system/status returns structured service info."""
        mock_cm = MagicMock()
        mock_cm.get_status.return_value = {"status": "ONLINE", "port": 8188}
        mock_get_cm.return_value = mock_cm

        mock_lm = MagicMock()
        mock_lm.get_status.return_value = {"status": "OFFLINE", "port": 8080}
        mock_get_lm.return_value = mock_lm

        resp = self.client.get("/api/system/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("comfy", data)
        self.assertIn("llm", data)
        self.assertEqual(data["comfy"]["status"], "ONLINE")
        self.assertEqual(data["llm"]["status"], "OFFLINE")

    def test_media_path_traversal_forbidden(self):
        """Verify /api/media rejects directory traversal attacks."""
        resp = self.client.get("/api/media?file=../windows/system32/cmd.exe")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("forbidden", resp.json().get("detail", "").lower())

    def test_media_nonexistent_returns_404(self):
        """Verify /api/media returns 404 for missing assets."""
        resp = self.client.get("/api/media/nonexistent_test_asset_12345.png")
        self.assertEqual(resp.status_code, 404)

    def test_root_serves_spa_html(self):
        """Verify GET / serves the compiled React Single Page Application."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers.get("content-type", ""))
        self.assertIn('<div id="root">', resp.text)

    @patch("webui.routers.scripts._get_state_manager")
    def test_list_scripts_endpoint(self, mock_get_sm):
        """Verify /api/scripts returns normalized summary array."""
        mock_sm = MagicMock()
        mock_sm.get_all_scripts.return_value = [
            {
                "id": "EE01",
                "content_metadata": {"language": "english", "video_type": "expression", "topic": "raining cats and dogs"},
                "status": {"script_generation": "done", "voice_generation": "pending"},
                "assets": {},
            }
        ]
        mock_get_sm.return_value = mock_sm

        resp = self.client.get("/api/scripts")
        self.assertEqual(resp.status_code, 200)
        scripts = resp.json()
        self.assertEqual(len(scripts), 1)
        self.assertEqual(scripts[0]["id"], "EE01")
        self.assertEqual(scripts[0]["language"], "english")
        self.assertEqual(scripts[0]["status"]["script_generation"], "done")
