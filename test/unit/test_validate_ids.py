"""
test/unit/test_validate_ids.py — Unit tests for the script ID validation endpoint.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

MAIN_DIR = Path(__file__).resolve().parent.parent.parent / "main"
sys.path = [p for p in sys.path if not p.rstrip("/\\").endswith("tools")]
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

# If tools/webui.py was imported as 'webui', clear it so package 'webui' is resolved
if "webui" in sys.modules and not hasattr(sys.modules["webui"], "__path__"):
    del sys.modules["webui"]

# pyrefly: ignore[missing-import]
from webui.routers.scripts import validate_script_ids, ValidateIdsRequest


class TestValidateIds(unittest.TestCase):
    @patch("webui.routers.scripts._get_state_manager")
    def test_validate_ids_mixed(self, mock_get_sm):
        """Verify validation properly separates existing scripts from missing scripts."""
        mock_sm = MagicMock()
        mock_get_sm.return_value = mock_sm

        # EE01 exists, NONEXISTENT does not
        mock_sm.script_exists.side_effect = lambda sid: sid == "EE01"
        mock_sm.get_script_state.return_value = {
            "prompt_params": {
                "TARGET_LANGUAGE": "English",
                "VIDEO_TYPE": "EXPRESSION",
            },
            "status": {
                "voice_generation": "done",
                "image_generation": "pending",
                "thumbnail_generation": "done",
            },
        }

        req = ValidateIdsRequest(script_ids=["ee01", "NONEXISTENT", "EE01"])
        resp = validate_script_ids(req)

        self.assertEqual(resp["total"], 2)  # De-duplicated
        self.assertEqual(resp["valid_count"], 1)
        self.assertEqual(resp["invalid_count"], 1)

        valid_item = next(i for i in resp["items"] if i["id"] == "EE01")
        self.assertTrue(valid_item["exists"])
        self.assertEqual(valid_item["language"], "english")
        self.assertEqual(valid_item["type"], "expression")
        self.assertEqual(valid_item["stages"]["voice"], "done")
        self.assertEqual(valid_item["stages"]["images"], "pending")

        invalid_item = next(i for i in resp["items"] if i["id"] == "NONEXISTENT")
        self.assertFalse(invalid_item["exists"])
        self.assertIsNone(invalid_item["language"])


if __name__ == "__main__":
    unittest.main()
