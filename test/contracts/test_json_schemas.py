"""
test_layer/contracts/test_json_schemas.py — Contract validation for runtime state JSON schemas.
"""
import unittest
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAIN_DIR = REPO_ROOT / "main"


class TestJSONSchemas(unittest.TestCase):
    def setUp(self):
        self.sample_state_path = MAIN_DIR / "state" / "script_state.sample.json"

    def test_sample_state_file_exists_and_is_valid_json(self):
        self.assertTrue(self.sample_state_path.exists())
        with self.sample_state_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)

    def test_sample_state_root_keys(self):
        with self.sample_state_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        required_keys = ["id", "status", "assets", "prompt_params", "script_text", "content_metadata", "metadata"]
        for key in required_keys:
            self.assertIn(key, data)

    def test_sample_state_status_stages(self):
        with self.sample_state_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        status = data.get("status", {})
        expected_stages = [
            "script_generation",
            "voice_generation",
            "image_generation",
            "thumbnail_generation",
            "video_assembly"
        ]
        for stage in expected_stages:
            self.assertIn(stage, status)
            self.assertIn(status[stage], ["done", "pending", "error"])

    def test_sample_state_metadata_keys(self):
        with self.sample_state_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        metadata = data.get("metadata", {})
        expected_meta = ["TITLE", "DESCRIPTION", "SHORT_DESCRIPTION", "TAGS", "HASHTAGS", "LABEL", "FILENAME"]
        for key in expected_meta:
            self.assertIn(key, metadata)


if __name__ == "__main__":
    unittest.main()
