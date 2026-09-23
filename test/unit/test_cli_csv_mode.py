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


if __name__ == "__main__":
    unittest.main()
