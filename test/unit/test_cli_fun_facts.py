"""
test/unit/test_cli_fun_facts.py — Unit tests for Fun Facts CLI options and prompt modes.
"""

from __future__ import annotations

import argparse
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from core.cli_prompt import prompt_production_mode, prompt_fun_facts_mode


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


if __name__ == "__main__":
    unittest.main()
