"""
test/integration/test_schema_contracts.py — Schema contract verification for:
1. CSV prompt templates and database models in input/csv/sample_templates/ and database/.
2. Runtime script state JSON contracts in state/script_state.sample.json.
"""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAIN_DIR = REPO_ROOT / "main"


class TestCSVSchemas(unittest.TestCase):
    """Verify input CSV templates and database sample formats adhere to strict schema contracts."""

    def setUp(self):
        self.templates_dir = MAIN_DIR / "input" / "csv" / "sample_templates"
        self.db_sample = MAIN_DIR / "database" / "expressions.sample.csv"

    def test_sample_templates_directory_exists(self):
        self.assertTrue(self.templates_dir.exists(), f"Templates directory not found: {self.templates_dir}")

    def test_expression_sample_csv_schema(self):
        csv_path = self.templates_dir / "READY_PROMPTS_EXPRESSION.sample.csv"
        self.assertTrue(csv_path.exists())
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            expected = ["ID", "EXPRESSION", "SUBJECT", "CONTEXT", "ANGLE", "LEXICAL_FIELD", "EMOTIONAL_TRIGGER"]
            self.assertEqual(header, expected)
            rows = list(reader)
            self.assertGreaterEqual(len(rows), 1)

    def test_game_sample_csv_schema(self):
        csv_path = self.templates_dir / "READY_PROMPTS_GAME.sample.csv"
        self.assertTrue(csv_path.exists())
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            expected = ["ID", "EXPRESSION", "CONTEXT", "SUBJECT", "LEXICAL_FIELD"]
            self.assertEqual(header, expected)
            rows = list(reader)
            self.assertGreaterEqual(len(rows), 1)

    def test_roleplay_sample_csv_schema(self):
        csv_path = self.templates_dir / "READY_PROMPTS_ROLEPLAY.sample.csv"
        self.assertTrue(csv_path.exists())
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            expected = ["ID", "ROLEPLAY_SCENARIO", "SUBJECT", "LEXICAL_FIELD", "EMOTIONAL_TRIGGER", "SPECIAL_TREATMENT"]
            self.assertEqual(header, expected)
            rows = list(reader)
            self.assertGreaterEqual(len(rows), 1)

    def test_fun_facts_sample_csv_schema(self):
        csv_path = self.templates_dir / "READY_PROMPTS_FUN_FACTS.sample.csv"
        self.assertTrue(csv_path.exists())
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            expected = ["ID", "TOPIC", "PILLAR", "FORMAT", "FACT_DETAILS", "HOOK_ANGLE", "EMOTIONAL_TRIGGER"]
            self.assertEqual(header, expected)
            rows = list(reader)
            self.assertGreaterEqual(len(rows), 1)

    def test_call_to_actions_sample_csv_schema(self):
        csv_path = self.templates_dir / "CALL_TO_ACTIONS.sample.csv"
        self.assertTrue(csv_path.exists())
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            expected = ["CALL_TO_ACTION"]
            self.assertEqual(header, expected)
            rows = list(reader)
            self.assertGreaterEqual(len(rows), 1)

    def test_database_expressions_sample_csv_schema(self):
        self.assertTrue(self.db_sample.exists())
        with self.db_sample.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            expected = ["ID", "EXPRESSION", "CONTEXT", "VIDEO_TYPE", "STATUS"]
            self.assertEqual(header, expected)
            rows = list(reader)
            self.assertGreaterEqual(len(rows), 1)


class TestJSONSchemas(unittest.TestCase):
    """Verify runtime state JSON schema structure and essential properties."""

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
