"""Checks Fun Facts card choices used by the assembly service."""

import unittest
from unittest.mock import patch

from config import resolve_opening_closure_paths
from core.cli_prompt import prompt_fun_facts_cards_variant


class TestFunFactsCards(unittest.TestCase):
    def test_prompt_fun_facts_cards_variant_filtering(self):
        """Verify prompt_fun_facts_cards_variant only triggers for English/Spanish Fun Facts."""
        # Other video types: Expression, Game, Roleplay -> None
        script_expression = {"id": "EE01", "content_metadata": {"video_type": "EXPRESSION", "language": "English"}}
        self.assertIsNone(prompt_fun_facts_cards_variant(script_expression))

        script_game = {"id": "SG01", "content_metadata": {"video_type": "GAME", "language": "Spanish"}}
        self.assertIsNone(prompt_fun_facts_cards_variant(script_game))

        # Other languages: French, Italian Fun Facts -> None
        script_french_ff = {"id": "FF01", "content_metadata": {"video_type": "FUN_FACTS", "language": "French"}}
        self.assertIsNone(prompt_fun_facts_cards_variant(script_french_ff))

        script_italian_ff = {"id": "IF01", "content_metadata": {"video_type": "FUN_FACTS", "language": "Italian"}}
        self.assertIsNone(prompt_fun_facts_cards_variant(script_italian_ff))

        # Auto mode returns standard defaults without prompting
        script_english_ff = {"id": "EF01", "content_metadata": {"video_type": "FUN_FACTS", "language": "English"}}
        self.assertEqual(prompt_fun_facts_cards_variant(script_english_ff, auto=True), "american")

        script_spanish_ff = {"id": "SF01", "content_metadata": {"video_type": "FUN_FACTS", "language": "Spanish"}}
        self.assertEqual(prompt_fun_facts_cards_variant(script_spanish_ff, auto=True), "latin_american")

    def test_prompt_fun_facts_cards_variant_interactive_and_batch_memory(self):
        """Verify interactive choices and batch 'apply-all' memory for English and Spanish."""
        script_english_ff = {"id": "EF01", "content_metadata": {"video_type": "FUN_FACTS", "language": "English"}}
        script_spanish_ff = {"id": "SF01", "content_metadata": {"video_type": "FUN_FACTS", "language": "Spanish"}}

        # English: choice '2' -> british
        with patch("builtins.input", return_value="2"), patch("sys.stdin.isatty", return_value=True):
            res = prompt_fun_facts_cards_variant(script_english_ff, auto=False)
            self.assertEqual(res, "british")

        # English: choice '1' -> american
        with patch("builtins.input", return_value="1"), patch("sys.stdin.isatty", return_value=True):
            res = prompt_fun_facts_cards_variant(script_english_ff, auto=False)
            self.assertEqual(res, "american")

        # Spanish: choice '2a' -> spain + remembered in batch
        batch_memory = {}
        with patch("builtins.input", return_value="2a"), patch("sys.stdin.isatty", return_value=True):
            res = prompt_fun_facts_cards_variant(script_spanish_ff, auto=False, remembered_dialects=batch_memory)
            self.assertEqual(res, "spain")
            self.assertEqual(batch_memory.get("spanish"), "spain")

        # Next Spanish script reuses batch memory without calling input()
        script_spanish_ff2 = {"id": "SF02", "content_metadata": {"video_type": "FUN_FACTS", "language": "Spanish"}}
        with patch("builtins.input", side_effect=AssertionError("Should not prompt")):
            res2 = prompt_fun_facts_cards_variant(script_spanish_ff2, auto=False, remembered_dialects=batch_memory)
            self.assertEqual(res2, "spain")

    def test_resolve_opening_closure_paths_fun_facts_variants(self):
        """Verify resolve_opening_closure_paths picks the correct image assets for English & Spanish Fun Facts."""
        script_ef = {"id": "EF01", "content_metadata": {"video_type": "FUN_FACTS", "language": "English"}}
        script_sf = {"id": "SF01", "content_metadata": {"video_type": "FUN_FACTS", "language": "Spanish"}}

        # English American vs British
        open_us, close_us = resolve_opening_closure_paths(script_ef, dialect="american")
        self.assertIn("american", open_us.name.lower())
        self.assertIn("american", close_us.name.lower())

        open_uk, close_uk = resolve_opening_closure_paths(script_ef, dialect="british")
        self.assertIn("british", open_uk.name.lower())
        self.assertIn("british", close_uk.name.lower())

        # Spanish Latin American vs Spain
        open_latam, close_latam = resolve_opening_closure_paths(script_sf, dialect="latin_american")
        self.assertIn("latin_american", open_latam.name.lower())
        self.assertIn("latin_american", close_latam.name.lower())

        open_spain, close_spain = resolve_opening_closure_paths(script_sf, dialect="spain")
        self.assertIn("spain", open_spain.name.lower())
        self.assertIn("spain", close_spain.name.lower())


if __name__ == "__main__":
    unittest.main()

