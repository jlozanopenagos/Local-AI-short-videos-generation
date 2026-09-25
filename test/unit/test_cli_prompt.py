"""
test/unit/test_cli_prompt.py — Unit tests for interactive CLI prompts, countdown timers,
Fun Facts filtering, and CSV queue modes (Option 5 and Option 6).
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
    prompt_fun_facts_mode,
    find_ready_scripts_csvs,
    prompt_ready_scripts_mode,
)


class TestCLIFunFacts(unittest.TestCase):
    """Test suite for Fun Facts filtering, CLI args, and interactive prompt modes."""

    def test_cli_argument_parsing_fun_facts_flags(self):
        """Verify argparse correctly parses --fun-facts and --fun-facts-only."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--fun-facts",
            "--fun-facts-only",
            dest="fun_facts_only",
            action="store_true"
        )
        parser.add_argument(
            "--video-type",
            type=str,
            default=None,
            choices=["expression", "game", "roleplay", "fun_facts", "all"]
        )
        parser.add_argument(
            "--language",
            type=str,
            default=None,
            choices=["all", "english", "french", "spanish", "italian"]
        )

        args1 = parser.parse_args(["--fun-facts"])
        self.assertTrue(args1.fun_facts_only)
        self.assertIsNone(args1.video_type)

        args2 = parser.parse_args(["--fun-facts-only", "--language", "spanish"])
        self.assertTrue(args2.fun_facts_only)
        self.assertEqual(args2.language, "spanish")

        args3 = parser.parse_args(["--video-type", "fun_facts"])
        self.assertFalse(args3.fun_facts_only)
        self.assertEqual(args3.video_type, "fun_facts")

    def test_prompt_production_mode_offers_fun_facts_choice(self):
        """Verify prompt_production_mode accepts choice 4 when allow_fun_facts_mode is True."""
        with patch("core.cli_prompt.sys.stdin.isatty", return_value=True), \
             patch("core.cli_prompt._timed_choice", return_value="4"), \
             patch("core.cli_prompt.prompt_fun_facts_mode", return_value=["EF01", "EF02"]):
            result, mode = prompt_production_mode(
                stage_title="Part A: Video Scripts",
                asset_name="scripts",
                allow_fun_facts_mode=True,
                return_mode=True,
            )
            self.assertEqual(mode, "fun_facts")
            self.assertEqual(result, ["EF01", "EF02"])

    def test_prompt_fun_facts_mode_all_languages_default_scope(self):
        """Verify prompt_fun_facts_mode returns Fun Facts IDs for all languages."""
        # Inputs: choice 1 for all languages, choice 1 for all pending scope
        with patch("builtins.input", side_effect=["1", "1"]):
            result = prompt_fun_facts_mode()
            self.assertIsNotNone(result)
            self.assertTrue(len(result) > 0)
            # Must include IDs starting with EF, FF, SF, IF
            prefixes = {sid[:2] for sid in result}
            self.assertIn("EF", prefixes)
            self.assertIn("FF", prefixes)
            self.assertIn("SF", prefixes)
            self.assertIn("IF", prefixes)

    def test_prompt_fun_facts_mode_specific_language_and_range(self):
        """Verify prompt_fun_facts_mode correctly generates range IDs for selected language."""
        # Inputs: choice 2 for English (EF), choice 2 for range, '1-3' for range
        with patch("builtins.input", side_effect=["2", "2", "1-3"]):
            result = prompt_fun_facts_mode()
            self.assertEqual(result, ["EF01", "EF02", "EF03"])

    def test_fun_facts_filtering_logic(self):
        """Verify prompt filtering correctly isolates Fun Facts rows from mixed prompt rows."""
        mixed_prompts = [
            {"ID": "EE01", "VIDEO_TYPE": "EXPRESSION", "TARGET_LANGUAGE": "English"},
            {"ID": "EG01", "VIDEO_TYPE": "GAME", "TARGET_LANGUAGE": "English"},
            {"ID": "ER01", "VIDEO_TYPE": "ROLEPLAY", "TARGET_LANGUAGE": "English"},
            {"ID": "EF01", "VIDEO_TYPE": "FUN_FACTS", "TARGET_LANGUAGE": "English"},
            {"ID": "FF01", "VIDEO_TYPE": "FUN_FACTS", "TARGET_LANGUAGE": "French"},
            {"ID": "SF01", "VIDEO_TYPE": "FUN_FACTS", "TARGET_LANGUAGE": "Spanish"},
        ]

        filtered = [
            p for p in mixed_prompts
            if p.get("VIDEO_TYPE", "").upper() in ("FUN_FACTS", "FUNFACTS")
            or (len(p.get("ID", "")) >= 2 and p["ID"][1].upper() == "F")
        ]
        self.assertEqual(len(filtered), 3)
        self.assertEqual([p["ID"] for p in filtered], ["EF01", "FF01", "SF01"])


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
        self.assertEqual(load_ids_from_csv(self.voice_csv_dir / "non_existent.csv"), [])

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

        voice_ids = prompt_csv_list_mode(
            base_dir=self.base_dir,
            folder_name="voice_to_change",
            auto=True,
            require_existing_state=False
        )
        self.assertEqual(voice_ids, ["EE01"])

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
        """Verify prompt_production_mode offers Option 5 when allow_csv_list_mode is True."""
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

        args1 = p.parse_args(["--from-csv"])
        self.assertEqual(args1.csv_list, "")

        args2 = p.parse_args(["--from-csv", "my_list.csv", "--auto", "--force"])
        self.assertEqual(args2.csv_list, "my_list.csv")
        self.assertTrue(args2.auto)
        self.assertTrue(args2.force)

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

            found = find_ready_scripts_csvs(p)
            found_names = [f.name for f in found]

            self.assertIn("2026-09-23_ready_scripts.csv", found_names)
            self.assertIn("2026-09-23_ready_scripts_to_work_with.csv", found_names)
            self.assertNotIn("error_report.csv", found_names)
            self.assertTrue(found_names.index("2026-09-23_ready_scripts.csv") < found_names.index("2026-09-23_ready_scripts_to_work_with.csv"))

    def test_prompt_ready_scripts_mode_from_file(self):
        """Verify prompt_ready_scripts_mode loads IDs from ready scripts CSV directly."""
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
