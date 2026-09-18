"""
test_layer/contracts/test_system_prompts.py — Contract validation for external editor system prompts.
"""
import unittest
import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAIN_DIR = REPO_ROOT / "main"


class TestSystemPrompts(unittest.TestCase):
    def setUp(self):
        self.editor_csv = MAIN_DIR / "system_prompts_editor.csv"

    def test_editor_csv_exists(self):
        self.assertTrue(self.editor_csv.exists())

    def test_editor_csv_schema_and_rows(self):
        with self.editor_csv.open("r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        expected_cols = ["video_type", "target_duration", "word_count_range", "sections_structure", "system_prompt"]
        self.assertEqual(list(reader[0].keys()), expected_cols)

        types_found = {row["video_type"].upper(): row for row in reader}
        for expected_type in ["EXPRESSION", "ROLEPLAY", "GAME", "FUN_FACTS"]:
            self.assertIn(expected_type, types_found)
            row = types_found[expected_type]
            self.assertTrue(len(row["system_prompt"].strip()) > 100)
            self.assertTrue(len(row["target_duration"].strip()) > 0)
            self.assertTrue(len(row["word_count_range"].strip()) > 0)


if __name__ == "__main__":
    unittest.main()
