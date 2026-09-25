"""
test_ready_scripts.py — Unit Tests for Ready Scripts Scanner (Feature 5).

Verifies:
1. Checkbox truthy parsing (is_checkbox_checked).
2. Date normalization across ISO, slash, and dash formats (normalize_date_str).
3. Filtering logic:
   - script_ready=True and video_ready=False -> INCLUDED
   - video_ready=True -> EXCLUDED (already done)
   - script_ready=False -> EXCLUDED (not ready)
4. Fallback grouping to 'undated' for missing dates.
5. Saving daily CSVs (<YYYY-MM-DD>_ready_scripts.csv & undated_ready_scripts.csv) with schema ID,expression.
6. Deduplication on multiple runs (merges by ID).
7. Mocked scan_sheet_ready_scripts and scan_all_sheets_ready_scripts.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure main project is at index 0 of sys.path
TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
MAIN_DIR = REPO_ROOT / "main"
if str(MAIN_DIR) in sys.path:
    sys.path.remove(str(MAIN_DIR))
sys.path.insert(0, str(MAIN_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

try:
    # pyrefly: ignore [missing-import]
    from connectivity.ready_scripts.scanner import (
        DEFAULT_READY_SCRIPTS_DIR,
        filter_ready_scripts,
        is_checkbox_checked,
        normalize_date_str,
        resolve_ready_scripts_output_dir,
        save_ready_scripts_by_date,
        save_ready_scripts_to_work_with_by_date,
        scan_all_sheets_ready_scripts,
        scan_sheet_ready_scripts,
    )
except (ImportError, ModuleNotFoundError):
    from main.connectivity.ready_scripts.scanner import (
        DEFAULT_READY_SCRIPTS_DIR,
        filter_ready_scripts,
        is_checkbox_checked,
        normalize_date_str,
        resolve_ready_scripts_output_dir,
        save_ready_scripts_by_date,
        save_ready_scripts_to_work_with_by_date,
        scan_all_sheets_ready_scripts,
        scan_sheet_ready_scripts,
    )


class TestReadyScriptsScanner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_is_checkbox_checked_truthy(self):
        """Verify is_checkbox_checked recognizes various truthy representations."""
        for val in [True, 1, 1.0, "true", "TRUE", "True", "1", "yes", "YES", "checked", "x", "X"]:
            self.assertTrue(is_checkbox_checked(val), f"Expected {val!r} to be True")

    def test_is_checkbox_checked_falsy(self):
        """Verify is_checkbox_checked recognizes various falsy representations."""
        for val in [False, 0, 0.0, None, "", "false", "FALSE", "0", "no", "NO", "unchecked"]:
            self.assertFalse(is_checkbox_checked(val), f"Expected {val!r} to be False")

    def test_normalize_date_str_iso_and_timestamps(self):
        """Verify ISO dates and datetime strings normalize to YYYY-MM-DD."""
        self.assertEqual(normalize_date_str("2026-09-23"), "2026-09-23")
        self.assertEqual(normalize_date_str("2026-09-23T15:30:00.000Z"), "2026-09-23")
        self.assertEqual(normalize_date_str("2026-09-23 10:00:00"), "2026-09-23")
        self.assertEqual(normalize_date_str("2026/09/23"), "2026-09-23")

    def test_normalize_date_str_slash_and_dash(self):
        """Verify DD/MM/YYYY and other common date representations."""
        self.assertEqual(normalize_date_str("23/09/2026"), "2026-09-23")
        self.assertEqual(normalize_date_str("23-09-2026"), "2026-09-23")
        self.assertEqual(normalize_date_str("05/10/2026"), "2026-10-05")

    def test_normalize_date_str_two_digit_years(self):
        """Verify 2-digit year representations (e.g. 23/09/26, 23-09-26, 23.09.26)."""
        self.assertEqual(normalize_date_str("23/09/26"), "2026-09-23")
        self.assertEqual(normalize_date_str("23-09-26"), "2026-09-23")
        self.assertEqual(normalize_date_str("23.09.26"), "2026-09-23")
        self.assertEqual(normalize_date_str("23/9/26"), "2026-09-23")
        self.assertEqual(normalize_date_str("05/10/26"), "2026-10-05")
        self.assertEqual(normalize_date_str("9/23/26"), "2026-09-23")
        # DD-MM-YY parses with day first
        self.assertEqual(normalize_date_str("26-09-23"), "2023-09-26")

    def test_normalize_date_str_empty_or_invalid(self):
        """Verify empty or invalid date strings return empty string."""
        self.assertEqual(normalize_date_str(""), "")
        self.assertEqual(normalize_date_str(None), "")
        self.assertEqual(normalize_date_str("not_a_date"), "")

    def test_filter_ready_scripts_core_logic(self):
        """
        Verify:
        - script_ready=True and video_ready=False -> INCLUDED
        - video_ready=True -> EXCLUDED (video done)
        - script_ready=False -> EXCLUDED (not ready)
        """
        raw_rows = [
            # 1. Ready script (included)
            {
                "ID": "FE01",
                "expression": "avoir le cafard",
                "script": "Script 1",
                "script_ready": True,
                "script_date": "2026-09-23",
                "video_ready": False,
                "video_date": "",
            },
            # 2. Video already completed (excluded even if script_ready is True)
            {
                "ID": "FE02",
                "expression": "poser un lapin",
                "script": "Script 2",
                "script_ready": True,
                "script_date": "2026-09-23",
                "video_ready": True,
                "video_date": "2026-09-24",
            },
            # 3. Not script ready (excluded)
            {
                "ID": "FE03",
                "expression": "coup de foudre",
                "script": "Script 3",
                "script_ready": False,
                "script_date": "",
                "video_ready": False,
                "video_date": "",
            },
            # 4. Ready but with missing date -> included under 'undated'
            {
                "ID": "FE04",
                "expression": "tomber dans les pommes",
                "script": "Script 4",
                "script_ready": "TRUE",
                "script_date": "",
                "video_ready": "FALSE",
                "video_date": "",
            },
            # 5. Row with uppercase keys
            {
                "ID": "FE05",
                "EXPRESSION": "coute les yeux de la tete",
                "SCRIPT": "Script 5",
                "SCRIPT_READY": "1",
                "SCRIPT_DATE": "2026-09-22",
                "VIDEO_READY": "0",
            },
        ]

        result = filter_ready_scripts(raw_rows)
        ready_records = result["ready_records"]

        self.assertEqual(result["total_evaluated"], 5)
        self.assertEqual(result["video_ready_excluded_count"], 1)  # FE02
        self.assertEqual(result["not_script_ready_count"], 1)     # FE03
        self.assertEqual(len(ready_records), 3)                   # FE01, FE04, FE05

        ids = [r["ID"] for r in ready_records]
        self.assertIn("FE01", ids)
        self.assertIn("FE04", ids)
        self.assertIn("FE05", ids)
        self.assertNotIn("FE02", ids)
        self.assertNotIn("FE03", ids)

        # Check date keys
        fe01_rec = next(r for r in ready_records if r["ID"] == "FE01")
        self.assertEqual(fe01_rec["script_date"], "2026-09-23")

        fe04_rec = next(r for r in ready_records if r["ID"] == "FE04")
        self.assertEqual(fe04_rec["script_date"], "undated")

        fe05_rec = next(r for r in ready_records if r["ID"] == "FE05")
        self.assertEqual(fe05_rec["script_date"], "2026-09-22")

    def test_save_ready_scripts_by_date_and_schema(self):
        """Verify save_ready_scripts_by_date writes clean CSVs with schema ID,expression."""
        date_groups = {
            "2026-09-23": [
                {"ID": "FE01", "expression": "avoir le cafard"},
                {"ID": "SG02", "expression": "embarazada"},
            ],
            "undated": [
                {"ID": "ER03", "expression": "break a leg"},
            ],
        }

        save_res = save_ready_scripts_by_date(date_groups, output_dir=self.output_dir)
        self.assertEqual(save_res["total_files"], 2)

        # Check dated file
        dated_file = self.output_dir / "2026-09-23_ready_scripts.csv"
        self.assertTrue(dated_file.exists())
        with dated_file.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, ["ID", "expression"])
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["ID"], "FE01")
            self.assertEqual(rows[0]["expression"], "avoir le cafard")
            self.assertEqual(rows[1]["ID"], "SG02")
            self.assertEqual(rows[1]["expression"], "embarazada")

        # Check undated file
        undated_file = self.output_dir / "undated_ready_scripts.csv"
        self.assertTrue(undated_file.exists())
        with undated_file.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, ["ID", "expression"])
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["ID"], "ER03")

    def test_save_ready_scripts_deduplication_on_merge(self):
        """Verify multiple runs on the same date merge records without duplicating IDs."""
        batch_1 = {
            "2026-09-23": [
                {"ID": "FE01", "expression": "avoir le cafard"},
                {"ID": "FE02", "expression": "poser un lapin"},
            ]
        }
        save_ready_scripts_by_date(batch_1, output_dir=self.output_dir)

        # Second run: FE01 updated, FE03 added, FE02 unchanged
        batch_2 = {
            "2026-09-23": [
                {"ID": "FE01", "expression": "avoir le cafard (revised)"},
                {"ID": "FE03", "expression": "coup de foudre"},
            ]
        }
        save_ready_scripts_by_date(batch_2, output_dir=self.output_dir)

        dated_file = self.output_dir / "2026-09-23_ready_scripts.csv"
        with dated_file.open("r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 3)
            ids = [r["ID"] for r in rows]
            self.assertEqual(ids, ["FE01", "FE02", "FE03"])
            # Updated in-place
            fe01_row = next(r for r in rows if r["ID"] == "FE01")
            self.assertEqual(fe01_row["expression"], "avoir le cafard (revised)")

    def test_save_ready_scripts_pruning_undated_when_dated(self):
        """Verify that when an undated item is subsequently given a date, it is pruned from undated_ready_scripts.csv."""
        # Run 1: FE01 is undated
        batch_1 = {
            "undated": [
                {"ID": "FE01", "expression": "avoir le cafard"},
                {"ID": "FE02", "expression": "poser un lapin"},
            ]
        }
        save_ready_scripts_by_date(batch_1, output_dir=self.output_dir)
        undated_file = self.output_dir / "undated_ready_scripts.csv"
        self.assertTrue(undated_file.exists())
        with undated_file.open("r", encoding="utf-8-sig") as f:
            self.assertEqual(len(list(csv.DictReader(f))), 2)

        # Run 2: FE01 is now dated (2026-09-23), FE02 is still undated
        batch_2 = {
            "2026-09-23": [
                {"ID": "FE01", "expression": "avoir le cafard"},
            ],
            "undated": [
                {"ID": "FE02", "expression": "poser un lapin"},
            ],
        }
        save_ready_scripts_by_date(batch_2, output_dir=self.output_dir)

        # Dated file should have FE01
        dated_file = self.output_dir / "2026-09-23_ready_scripts.csv"
        self.assertTrue(dated_file.exists())
        with dated_file.open("r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["ID"], "FE01")

        # Undated file should now only have FE02
        with undated_file.open("r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["ID"], "FE02")

        # Run 3: FE02 is now also dated (2026-09-23)
        batch_3 = {
            "2026-09-23": [
                {"ID": "FE01", "expression": "avoir le cafard"},
                {"ID": "FE02", "expression": "poser un lapin"},
            ],
        }
        save_ready_scripts_by_date(batch_3, output_dir=self.output_dir)

        # Undated file should now be removed since all undated items were resolved
        self.assertFalse(undated_file.exists())

    def test_scan_sheet_ready_scripts_mocked(self):
        """Verify scan_sheet_ready_scripts fetches from endpoint and filters accurately."""
        mock_payload = {
            "status": "success",
            "data": [
                {
                    "ID": "FE01",
                    "expression": "avoir le cafard",
                    "script_ready": True,
                    "script_date": "2026-09-23",
                    "video_ready": False,
                },
                {
                    "ID": "FE02",
                    "expression": "poser un lapin",
                    "script_ready": True,
                    "script_date": "2026-09-23",
                    "video_ready": True,  # should be excluded
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            res = scan_sheet_ready_scripts("french", "expression")

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["language"], "french")
        self.assertEqual(res["video_type"], "expression")
        self.assertEqual(res["ready_count"], 1)
        self.assertEqual(res["video_ready_excluded_count"], 1)
        self.assertEqual(res["ready_records"][0]["ID"], "FE01")

    def test_scan_all_sheets_ready_scripts_mocked(self):
        """Verify scan_all_sheets_ready_scripts aggregates records and groups by date."""
        def fake_scan_sheet(lang, vtype, **kwargs):
            if lang == "french" and vtype == "expression":
                return {
                    "status": "success",
                    "language": lang,
                    "video_type": vtype,
                    "total_evaluated": 10,
                    "ready_count": 1,
                    "video_ready_excluded_count": 2,
                    "ready_records": [
                        {"ID": "FE01", "expression": "avoir le cafard", "script_date": "2026-09-23"}
                    ]
                }
            elif lang == "spanish" and vtype == "game":
                return {
                    "status": "success",
                    "language": lang,
                    "video_type": vtype,
                    "total_evaluated": 10,
                    "ready_count": 1,
                    "video_ready_excluded_count": 0,
                    "ready_records": [
                        {"ID": "SG05", "expression": "embarazada", "script_date": "2026-09-23"}
                    ]
                }
            else:
                return {
                    "status": "success",
                    "language": lang,
                    "video_type": vtype,
                    "total_evaluated": 5,
                    "ready_count": 0,
                    "video_ready_excluded_count": 0,
                    "ready_records": []
                }

        with patch("connectivity.ready_scripts.scanner.scan_sheet_ready_scripts", side_effect=fake_scan_sheet):
            summary = scan_all_sheets_ready_scripts()

        self.assertEqual(summary["status"], "success")
        self.assertEqual(summary["total_ready"], 2)
        self.assertIn("2026-09-23", summary["date_groups"])
        grouped_ids = [r["ID"] for r in summary["date_groups"]["2026-09-23"]]
        self.assertEqual(grouped_ids, ["FE01", "SG05"])

    def test_save_ready_scripts_to_work_with_by_date_and_schema(self):
        """Verify save_ready_scripts_to_work_with_by_date writes clean CSV with ID,SCRIPT_CHANGE."""
        date_groups = {
            "2026-09-23": [
                {"ID": "FE01", "script_change": "Voici une nouvelle explication..."},
                {"ID": "SG02", "script_change": "Un autre script..."},
            ],
            "undated": [
                {"ID": "ER03", "script_change": "Undated change..."},
            ],
        }

        save_res = save_ready_scripts_to_work_with_by_date(date_groups, output_dir=self.output_dir)
        self.assertEqual(save_res["total_files"], 2)
        self.assertEqual(save_res["errors_count"], 0)

        dated_file = self.output_dir / "2026-09-23_ready_scripts_to_work_with.csv"
        self.assertTrue(dated_file.exists())
        with dated_file.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, ["ID", "SCRIPT_CHANGE"])
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["ID"], "FE01")
            self.assertEqual(rows[0]["SCRIPT_CHANGE"], "Voici une nouvelle explication...")

        undated_file = self.output_dir / "undated_ready_scripts_to_work_with.csv"
        self.assertTrue(undated_file.exists())
        with undated_file.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, ["ID", "SCRIPT_CHANGE"])
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["ID"], "ER03")

    def test_save_ready_scripts_to_work_with_error_report_and_recovery(self):
        """Verify missing SCRIPT_CHANGE goes to error_report.csv and is pruned when resolved."""
        # Batch 1: FE01 is valid, FE02 is missing SCRIPT_CHANGE
        batch_1 = {
            "2026-09-23": [
                {"ID": "FE01", "script_change": "Valid script"},
                {"ID": "FE02", "script_change": ""},  # missing!
            ]
        }
        res_1 = save_ready_scripts_to_work_with_by_date(batch_1, output_dir=self.output_dir)
        self.assertEqual(res_1["errors_count"], 1)

        # Dated file should ONLY contain FE01
        dated_file = self.output_dir / "2026-09-23_ready_scripts_to_work_with.csv"
        self.assertTrue(dated_file.exists())
        with dated_file.open("r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["ID"], "FE01")

        # error_report.csv should exist and contain FE02
        error_file = self.output_dir / "error_report.csv"
        self.assertTrue(error_file.exists())
        with error_file.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, ["ID", "problem"])
            err_rows = list(reader)
            self.assertEqual(len(err_rows), 1)
            self.assertEqual(err_rows[0]["ID"], "FE02")

        # Batch 2: User fixes FE02 in Google Sheets, now running again
        batch_2 = {
            "2026-09-23": [
                {"ID": "FE01", "script_change": "Valid script"},
                {"ID": "FE02", "script_change": "Fixed now!"},
            ]
        }
        res_2 = save_ready_scripts_to_work_with_by_date(batch_2, output_dir=self.output_dir)
        self.assertEqual(res_2["errors_count"], 0)

        # Dated file should now contain both FE01 and FE02
        with dated_file.open("r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            ids = [r["ID"] for r in rows]
            self.assertIn("FE01", ids)
            self.assertIn("FE02", ids)

        # error_report.csv should be removed because all errors are resolved
        self.assertFalse(error_file.exists())

    def test_save_ready_scripts_to_work_with_pruning_undated(self):
        """Verify undated_ready_scripts_to_work_with.csv prunes items when dated."""
        batch_1 = {
            "undated": [
                {"ID": "FE01", "script_change": "Undated script 1"},
                {"ID": "FE02", "script_change": "Undated script 2"},
            ]
        }
        save_ready_scripts_to_work_with_by_date(batch_1, output_dir=self.output_dir)
        undated_file = self.output_dir / "undated_ready_scripts_to_work_with.csv"
        self.assertTrue(undated_file.exists())

        # Batch 2: Both now dated
        batch_2 = {
            "2026-09-23": [
                {"ID": "FE01", "script_change": "Dated script 1"},
                {"ID": "FE02", "script_change": "Dated script 2"},
            ]
        }
        save_ready_scripts_to_work_with_by_date(batch_2, output_dir=self.output_dir)
        # Undated file should be removed
        self.assertFalse(undated_file.exists())

    def test_prompt_export_work_with_scripts_not_atty(self):
        """Verify prompt returns False when sys.stdin is not a tty."""
        try:
            # pyrefly: ignore [missing-import]
            from connectivity.scan_ready_scripts import prompt_export_work_with_scripts
        except ImportError:
            from main.connectivity.scan_ready_scripts import prompt_export_work_with_scripts
        with patch("sys.stdin.isatty", return_value=False):
            self.assertFalse(prompt_export_work_with_scripts())

    def test_prompt_export_work_with_scripts_tty_yes(self):
        """Verify prompt returns True when user types 'y'."""
        try:
            # pyrefly: ignore [missing-import]
            from connectivity.scan_ready_scripts import prompt_export_work_with_scripts
        except ImportError:
            from main.connectivity.scan_ready_scripts import prompt_export_work_with_scripts
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="y"):
            self.assertTrue(prompt_export_work_with_scripts())

    def test_prompt_export_work_with_scripts_tty_no(self):
        """Verify prompt returns False when user types 'n'."""
        try:
            # pyrefly: ignore [missing-import]
            from connectivity.scan_ready_scripts import prompt_export_work_with_scripts
        except ImportError:
            from main.connectivity.scan_ready_scripts import prompt_export_work_with_scripts
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="n"):
            self.assertFalse(prompt_export_work_with_scripts())


if __name__ == "__main__":
    unittest.main()
