"""
test_corrected_scripts.py — Unit Tests for Corrected Scripts Fetching (Feature 2).

Verifies:
1. Column D (SCRIPT_CHANGED) extraction and mapping to NEW_SCRIPT.
2. Scope filtering: all, range, specific IDs, and CSV file.
3. Output CSV generation in main/input/csv/script_to_change/ with schema ID,NEW_SCRIPT.
"""

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Setup path to prioritize main
TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
MAIN_DIR = REPO_ROOT / "main"
for p in [str(MAIN_DIR), str(REPO_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# pyrefly: ignore [missing-import]
from connectivity.corrected_scripts.fetcher import (
    extract_numeric_id,
    load_ids_from_csv,
    filter_corrected_records,
    save_corrected_scripts_csv,
    fetch_raw_corrected_records,
    fetch_and_save_corrected_scripts,
    TARGET_COLUMNS,
)


class TestCorrectedScriptsFetcher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_extract_numeric_id(self):
        """Verify numeric extraction from standard script IDs."""
        self.assertEqual(extract_numeric_id("EE01"), 1)
        self.assertEqual(extract_numeric_id("FE15"), 15)
        self.assertEqual(extract_numeric_id("SF119"), 119)
        self.assertIsNone(extract_numeric_id("INVALID"))

    def test_load_ids_from_csv(self):
        """Verify reading IDs from a CSV file."""
        sample_csv = self.test_output_dir / "test_ids.csv"
        sample_csv.write_text("ID\nEE01\nEE05\nFE10\n", encoding="utf-8")

        ids = load_ids_from_csv(sample_csv)
        self.assertEqual(ids, {"EE01", "EE05", "FE10"})

    def test_filter_corrected_records_all_non_empty(self):
        """Verify filtering for all non-empty changed scripts."""
        sample = [
            {"ID": "EE01", "NEW_SCRIPT": "New script for EE01"},
            {"ID": "EE02", "NEW_SCRIPT": ""},
            {"ID": "EE03", "NEW_SCRIPT": "   "},
            {"ID": "EE04", "NEW_SCRIPT": "New script for EE04"},
        ]
        filtered = filter_corrected_records(sample, scope="all", require_non_empty_script=True)
        self.assertEqual(len(filtered), 2)
        self.assertEqual([r["ID"] for r in filtered], ["EE01", "EE04"])

    def test_filter_corrected_records_by_range(self):
        """Verify filtering records by numeric ID range."""
        sample = [
            {"ID": "EE01", "NEW_SCRIPT": "Script 1"},
            {"ID": "EE02", "NEW_SCRIPT": "Script 2"},
            {"ID": "EE05", "NEW_SCRIPT": "Script 5"},
            {"ID": "EE10", "NEW_SCRIPT": "Script 10"},
        ]
        filtered = filter_corrected_records(
            sample,
            scope="range",
            start_num=2,
            end_num=5,
            require_non_empty_script=False
        )
        self.assertEqual(len(filtered), 2)
        self.assertEqual([r["ID"] for r in filtered], ["EE02", "EE05"])

    def test_filter_corrected_records_by_ids(self):
        """Verify filtering records by specific target ID list."""
        sample = [
            {"ID": "EE01", "NEW_SCRIPT": "Script 1"},
            {"ID": "EE02", "NEW_SCRIPT": "Script 2"},
            {"ID": "EE03", "NEW_SCRIPT": "Script 3"},
        ]
        filtered = filter_corrected_records(
            sample,
            scope="ids",
            target_ids=["EE01", "EE03"],
            require_non_empty_script=False
        )
        self.assertEqual(len(filtered), 2)
        self.assertEqual([r["ID"] for r in filtered], ["EE01", "EE03"])

    def test_save_corrected_scripts_csv(self):
        """Verify saving CSV writes schema ID, NEW_SCRIPT and correct file name."""
        records = [
            {"ID": "EE01", "NEW_SCRIPT": "Corrected script 1"},
            {"ID": "EE02", "NEW_SCRIPT": "Corrected script 2"},
        ]
        out_file = save_corrected_scripts_csv(
            records=records,
            language="english",
            video_type="expression",
            output_dir=self.test_output_dir,
        )

        self.assertTrue(out_file.exists())
        self.assertEqual(out_file.name, "english_expression_script_to_change.csv")

        with out_file.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, ["ID", "NEW_SCRIPT"])
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["ID"], "EE01")
            self.assertEqual(rows[0]["NEW_SCRIPT"], "Corrected script 1")

    def test_fetch_and_save_corrected_scripts_mock(self):
        """Verify end-to-end fetch and save using mock endpoint response."""
        mock_payload = {
            "status": "success",
            "count": 3,
            "data": [
                {
                    "ID": "FE01",
                    "expression": "Poser un lapin",
                    "script": "Old script",
                    "SCRIPT_CHANGED": "New edited script for FE01",
                },
                {
                    "ID": "FE02",
                    "expression": "Avoir le cafard",
                    "script": "Old script",
                    "SCRIPT_CHANGED": "",  # Empty
                },
                {
                    "ID": "FE03",
                    "expression": "Coup de foudre",
                    "script": "Old script",
                    "SCRIPT_CHANGED": "New edited script for FE03",
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            out_path, count = fetch_and_save_corrected_scripts(
                language="french",
                video_type="expression",
                scope="all",
                output_dir=self.test_output_dir,
                require_non_empty_script=True,
            )

        self.assertEqual(count, 2)
        self.assertTrue(out_path.exists())
        self.assertEqual(out_path.name, "french_expression_script_to_change.csv")


if __name__ == "__main__":
    unittest.main()
