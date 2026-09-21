"""
test_layer/contracts/test_csv_schemas.py — Contract validation for all sample CSV templates and database models.
"""
import unittest
import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAIN_DIR = REPO_ROOT / "main"


class TestCSVSchemas(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
