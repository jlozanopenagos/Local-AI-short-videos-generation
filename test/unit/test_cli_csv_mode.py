"""
test/unit/test_cli_csv_mode.py — Unit tests for CSV List production mode and folder isolation.
"""

from __future__ import annotations

import argparse
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# pyrefly: ignore [missing-import]
from core.cli_prompt import (
    load_ids_from_csv,
    prompt_csv_list_mode,
    prompt_production_mode,
)


class TestCLICSVMode(unittest.TestCase):
    """Test suite for CSV list mode, folder isolation, and parser routines."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

        # Setup standard folder structures
        self.csv_root = self.base_dir / "input" / "csv"
        self.voice_csv_dir = self.csv_root / "voice_to_change"
        self.image_csv_dir = self.csv_root / "image_to_change"
        self.script_csv_dir = self.csv_root / "script_to_change"

        self.voice_csv_dir.mkdir(parents=True, exist_ok=True)
        self.image_csv_dir.mkdir(parents=True, exist_ok=True)
        self.script_csv_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_ids_from_csv_standard_header(self):
        """Verify load_ids_from_csv extracts IDs with standard ID column."""
        csv_file = self.voice_csv_dir / "test_voice.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "NOTES"])
            writer.writerow(["EE01", "Regenerate female voice"])
            writer.writerow(["FG02", "Fix cadence"])
            writer.writerow(["", "empty line"])
            writer.writerow(["SR03 ", "trim whitespace"])

        ids = load_ids_from_csv(csv_file)
        self.assertEqual(ids, ["EE01", "FG02", "SR03"])

    def test_load_ids_from_csv_alternative_headers(self):
        """Verify load_ids_from_csv handles 'script_id' and lowercase 'id' headers."""
        csv_file1 = self.image_csv_dir / "test_image.csv"
        with open(csv_file1, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["script_id", "prompt"])
            writer.writerow(["EF01", "funny cat"])

        self.assertEqual(load_ids_from_csv(csv_file1), ["EF01"])

        csv_file2 = self.image_csv_dir / "test_image2.csv"
        with open(csv_file2, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "status"])
            writer.writerow(["IF05", "pending"])

        self.assertEqual(load_ids_from_csv(csv_file2), ["IF05"])

    def test_load_ids_from_csv_missing_file_or_column(self):
        """Verify load_ids_from_csv gracefully returns empty list on invalid input."""
        # Non-existent file
        self.assertEqual(load_ids_from_csv(self.voice_csv_dir / "non_existent.csv"), [])

        # File without ID column
        bad_csv = self.voice_csv_dir / "bad.csv"
        with open(bad_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["FOO", "BAR"])
            writer.writerow(["1", "2"])
        self.assertEqual(load_ids_from_csv(bad_csv), [])

    def test_folder_isolation_voice_and_image(self):
        """Verify voice_to_change and image_to_change discover only their own CSVs."""
        voice_csv = self.voice_csv_dir / "voice_batch.csv"
        with open(voice_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID"])
            writer.writerow(["EE01"])

        image_csv = self.image_csv_dir / "image_batch.csv"
        with open(image_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID"])
            writer.writerow(["FG01"])

        # Auto select in voice folder
        voice_ids = prompt_csv_list_mode(
            base_dir=self.base_dir,
            folder_name="voice_to_change",
            auto=True,
            require_existing_state=False
        )
        self.assertEqual(voice_ids, ["EE01"])

        # Auto select in image folder
        image_ids = prompt_csv_list_mode(
            base_dir=self.base_dir,
            folder_name="image_to_change",
            auto=True,
            require_existing_state=False
        )
        self.assertEqual(image_ids, ["FG01"])

    def test_prompt_csv_list_mode_with_explicit_path_arg(self):
        """Verify prompt_csv_list_mode loads directly from csv_path_arg if provided."""
        custom_csv = self.base_dir / "custom_queue.csv"
        with open(custom_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID"])
            writer.writerow(["SF01"])
            writer.writerow(["SF02"])

        ids = prompt_csv_list_mode(
            base_dir=self.base_dir,
            folder_name="voice_to_change",
            csv_path_arg=str(custom_csv),
            require_existing_state=False
        )
        self.assertEqual(ids, ["SF01", "SF02"])

    def test_prompt_production_mode_choice_5_csv_list(self):
        """Verify prompt_production_mode offers Option 5 when allow_fun_facts_mode and allow_csv_list_mode are True."""
        with patch("core.cli_prompt.sys.stdin.isatty", return_value=True), \
             patch("core.cli_prompt._timed_choice", return_value="5"), \
             patch("core.cli_prompt.prompt_csv_list_mode", return_value=["EE10", "EE11"]):
            result, mode = prompt_production_mode(
                stage_title="Part B: Voice Generation",
                asset_name="voices",
                allow_fun_facts_mode=True,
                allow_csv_list_mode=True,
                csv_folder_name="voice_to_change",
                return_mode=True,
            )
            self.assertEqual(mode, "csv_list")
            self.assertEqual(result, ["EE10", "EE11"])

    def test_cli_flags_parsing_voice_and_image(self):
        """Verify both voice and image argument parsers support all new flags."""
        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument("--script-id", type=str, default=None)
            parser.add_argument("--force", action="store_true")
            parser.add_argument("--seed", type=int, default=None)
            parser.add_argument("--auto", action="store_true")
            parser.add_argument("--fun-facts", "--fun-facts-only", dest="fun_facts_only", action="store_true")
            parser.add_argument("--video-type", type=str, default=None)
            parser.add_argument("--language", type=str, default=None)
            parser.add_argument("--from-csv", "--csv-list", dest="csv_list", nargs="?", const="", default=None)
            return parser

        p = make_parser()

        # Flag alone (const="")
        args1 = p.parse_args(["--from-csv"])
        self.assertEqual(args1.csv_list, "")

        # Flag with file path
        args2 = p.parse_args(["--from-csv", "my_list.csv", "--auto", "--force"])
        self.assertEqual(args2.csv_list, "my_list.csv")
        self.assertTrue(args2.auto)
        self.assertTrue(args2.force)

        # Flag --csv-list alias
        args3 = p.parse_args(["--csv-list", "input/csv/voice_to_change/batch.csv"])
        self.assertEqual(args3.csv_list, "input/csv/voice_to_change/batch.csv")

    def test_find_ready_scripts_csvs(self):
        """Verify find_ready_scripts_csvs finds files and prioritizes standard ready_scripts."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir)
            f1 = p / "2026-09-23_ready_scripts.csv"
            f1.write_text("ID,expression\nEE01,Test\n", encoding="utf-8")
            f2 = p / "2026-09-23_ready_scripts_to_work_with.csv"
            f2.write_text("ID,SCRIPT_CHANGE\nEE01,Test\n", encoding="utf-8")
            err_f = p / "error_report.csv"
            err_f.write_text("ID,error\n", encoding="utf-8")

            # pyrefly: ignore [missing-import]
            from core.cli_prompt import find_ready_scripts_csvs
            found = find_ready_scripts_csvs(p)
            found_names = [f.name for f in found]

            self.assertIn("2026-09-23_ready_scripts.csv", found_names)
            self.assertIn("2026-09-23_ready_scripts_to_work_with.csv", found_names)
            self.assertNotIn("error_report.csv", found_names)
            # Standard ready_scripts file must come before to_work_with
            self.assertTrue(found_names.index("2026-09-23_ready_scripts.csv") < found_names.index("2026-09-23_ready_scripts_to_work_with.csv"))

    def test_prompt_ready_scripts_mode_from_file(self):
        """Verify prompt_ready_scripts_mode loads IDs from ready scripts CSV directly."""
        # pyrefly: ignore [missing-import]
        from core.cli_prompt import prompt_ready_scripts_mode
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "2026-09-23_ready_scripts.csv"
            csv_path.write_text("ID,expression\nEE01,Phrase one\nEE02,Phrase two\n", encoding="utf-8")

            ids = prompt_ready_scripts_mode(
                search_dir=Path(tmp_dir),
                csv_path_arg=str(csv_path),
                require_existing_state=False
            )
            self.assertEqual(ids, ["EE01", "EE02"])

    def test_prompt_production_mode_choice_6_ready_scripts(self):
        """Verify prompt_production_mode offers Option 6 when allow_ready_scripts_mode is True."""
        with patch("core.cli_prompt.sys.stdin.isatty", return_value=True), \
             patch("core.cli_prompt._timed_choice", return_value="6"), \
             patch("core.cli_prompt.prompt_ready_scripts_mode", return_value=["EE01", "EE02", "EE03"]):
            result, mode = prompt_production_mode(
                stage_title="Part B: Voice Generation",
                asset_name="voices",
                allow_fun_facts_mode=True,
                allow_csv_list_mode=True,
                allow_ready_scripts_mode=True,
                return_mode=True,
            )
            self.assertEqual(mode, "ready_scripts")
            self.assertEqual(result, ["EE01", "EE02", "EE03"])

    def test_cli_flags_parsing_ready_scripts(self):
        """Verify argument parser parses --from-ready-scripts and --ready-scripts flags."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--from-ready-scripts",
            "--ready-scripts",
            dest="ready_scripts_csv",
            nargs="?",
            const="",
            default=None,
        )

        args1 = parser.parse_args(["--from-ready-scripts"])
        self.assertEqual(args1.ready_scripts_csv, "")

        args2 = parser.parse_args(["--ready-scripts", "D:/AI/output/connectivity/ready_scripts/2026-09-23_ready_scripts.csv"])
        self.assertEqual(args2.ready_scripts_csv, "D:/AI/output/connectivity/ready_scripts/2026-09-23_ready_scripts.csv")


if __name__ == "__main__":
    unittest.main()
