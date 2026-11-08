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
        self.assertEqual(data["comfy"]["status"].lower(), "online")
        self.assertEqual(data["llm"]["status"].lower(), "offline")

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

    @patch("webui.routers.scripts._get_state_manager")
    def test_list_scripts_pagination(self, mock_get_sm):
        """Verify /api/scripts with ?page= returns paginated catalog envelope."""
        mock_sm = MagicMock()
        mock_sm.get_all_scripts.return_value = [
            {"id": f"TEST{i:02d}", "content_metadata": {"language": "french"}, "status": {}}
            for i in range(1, 15)
        ]
        mock_get_sm.return_value = mock_sm

        resp = self.client.get("/api/scripts?page=1&page_size=5")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)
        self.assertEqual(data["total"], 14)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 5)
        self.assertEqual(data["total_pages"], 3)
        self.assertEqual(len(data["items"]), 5)
        self.assertIn("facets", data)

    @patch("webui.routers.scripts._get_state_manager")
    def test_get_facets_endpoint(self, mock_get_sm):
        """Verify /api/scripts/facets returns language, type, and status aggregates."""
        mock_sm = MagicMock()
        mock_sm.get_all_scripts.return_value = [
            {"id": "ES01", "content_metadata": {"language": "spanish", "video_type": "expression"}, "status": {}},
            {"id": "FR01", "content_metadata": {"language": "french", "video_type": "roleplay"}, "status": {}},
        ]
        mock_get_sm.return_value = mock_sm

        resp = self.client.get("/api/scripts/facets")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 2)
        self.assertIn("languages", data)
        self.assertIn("types", data)
        self.assertIn("stage_counts", data)

    @patch("webui.routers.scripts._get_state_manager")
    def test_get_and_update_script_detail(self, mock_get_sm):
        """Verify GET returns chalkboard/script info and PUT saves updates to state store."""
        mock_sm = MagicMock()
        mock_sm.script_exists.return_value = True

        state_doc = {
            "id": "SG02",
            "content_metadata": {
                "language": "spanish",
                "video_type": "game",
                "topic": "Tomar el pelo",
                "chalkboard_exercise": "Original question?",
                "script": {"title": "Tomar el pelo", "hook": "Original Hook"},
            },
            "prompt_params": {"EXPRESSION": "Tomar el pelo"},
            "status": {},
            "assets": {},
        }
        mock_sm.get_script_state.return_value = state_doc
        mock_get_sm.return_value = mock_sm

        # 1. GET script
        resp = self.client.get("/api/scripts/SG02")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], "SG02")
        self.assertEqual(data["chalkboard_exercise"], "Original question?")
        self.assertEqual(data["chalkboard_title"], "Tomar el pelo")
        self.assertIn("hook", data["script_dict"])

        # 2. PUT script with updated chalkboard and dialogue
        update_payload = {
            "chalkboard_title": "Tomar el pelo (Updated)",
            "chalkboard_exercise": "¿Qué significa me estás tomando el pelo?\nA) Broma\nB) Verdad",
            "script_dict": {
                "title": "Tomar el pelo (Updated)",
                "hook": "New updated hook",
                "challenge": "¿Qué significa?",
            },
        }
        put_resp = self.client.put("/api/scripts/SG02", json=update_payload)
        self.assertEqual(put_resp.status_code, 200)
        self.assertTrue(mock_sm.save_script_state.called)
        saved_id, saved_data = mock_sm.save_script_state.call_args[0]
        self.assertEqual(saved_id, "SG02")
        self.assertEqual(
            saved_data["content_metadata"]["chalkboard_exercise"],
            "¿Qué significa me estás tomando el pelo?\nA) Broma\nB) Verdad",
        )
        self.assertEqual(saved_data["content_metadata"]["target_expression"], "Tomar el pelo (Updated)")
        self.assertEqual(saved_data["content_metadata"]["script"]["hook"], "New updated hook")

    @patch("webui.routers.scripts._get_state_manager")
    def test_update_general_prompt_sets_image_generation_pending(self, mock_get_sm):
        """Verify updating general_prompt sets image_generation to pending and resets image_prompts."""
        mock_sm = MagicMock()
        mock_sm.script_exists.return_value = True

        state_doc = {
            "id": "SR04",
            "content_metadata": {
                "language": "spanish",
                "video_type": "roleplay",
                "topic": "Pan comido",
                "anchor_environment": "Old living room environment",
            },
            "prompt_params": {"ROLEPLAY_SCENARIO": "Living room scenario"},
            "status": {
                "script_generation": "done",
                "voice_generation": "done",
                "image_generation": "done",
            },
            "assets": {
                "general_prompt": "Old living room general prompt",
                "image_prompts": {
                    "hook": "Old hook prompt",
                    "dialogue_part_1": "Old dialogue prompt",
                },
            },
        }
        mock_sm.get_script_state.return_value = state_doc
        mock_get_sm.return_value = mock_sm

        # Update general prompt with a new version
        new_prompt = "A vibrant modern workshop with tools and bright overhead LED lighting"
        put_resp = self.client.put("/api/scripts/SR04", json={"general_prompt": new_prompt})
        self.assertEqual(put_resp.status_code, 200)

        self.assertTrue(mock_sm.save_script_state.called)
        saved_id, saved_data = mock_sm.save_script_state.call_args[0]
        self.assertEqual(saved_id, "SR04")

        # Check that image_generation changed to pending
        self.assertEqual(saved_data["status"]["image_generation"], "pending")
        # Check that general_prompt was updated
        self.assertEqual(saved_data["assets"]["general_prompt"], new_prompt)
        self.assertEqual(saved_data["content_metadata"]["anchor_environment"], new_prompt)
        # Check that old specific scene prompts were cleared so LLM regenerates them
        self.assertEqual(saved_data["assets"]["image_prompts"], {})

        # Check response stages
        resp_data = put_resp.json()
        self.assertEqual(resp_data["stages"]["images"], "pending")
        self.assertFalse(resp_data["has_images"])
