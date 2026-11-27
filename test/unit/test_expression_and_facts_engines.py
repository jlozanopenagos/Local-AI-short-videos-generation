"""
test_expression_and_facts_engines.py — Unit tests for isolated EXPRESSION and FUN_FACTS engines (Step 2.3).
Verifies complete 4-type registry coverage, validation rules, and narrator cleaning.
"""

from __future__ import annotations

import unittest

# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.registry import ScriptEngineRegistry
# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.types.expression.engine import ExpressionEngine
# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.types.expression.validator import validate_expression_script
# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.types.fun_facts.engine import FunFactsEngine
# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.types.fun_facts.validator import validate_fun_facts_script


class TestExpressionAndFactsEngines(unittest.TestCase):
    """Verifies ExpressionEngine and FunFactsEngine behaviors and registry dispatch."""

    def test_registry_resolves_all_four_script_types(self):
        # Expression
        e_engine = ScriptEngineRegistry.get_engine("expression")
        self.assertIsInstance(e_engine, ExpressionEngine)
        self.assertIs(ScriptEngineRegistry.get_engine("E"), e_engine)
        self.assertIs(ScriptEngineRegistry.get_engine("SE01"), e_engine)
        self.assertIs(ScriptEngineRegistry.get_engine("EE10"), e_engine)

        # Fun Facts
        f_engine = ScriptEngineRegistry.get_engine("fun_facts")
        self.assertIsInstance(f_engine, FunFactsEngine)
        self.assertIs(ScriptEngineRegistry.get_engine("funfacts"), f_engine)
        self.assertIs(ScriptEngineRegistry.get_engine("F"), f_engine)
        self.assertIs(ScriptEngineRegistry.get_engine("SF01"), f_engine)
        self.assertIs(ScriptEngineRegistry.get_engine("EF02"), f_engine)

        # All four types in registry
        types = ScriptEngineRegistry.list_supported_types()
        self.assertIn("expression", types)
        self.assertIn("fun_facts", types)
        self.assertIn("game", types)
        self.assertIn("roleplay", types)

    def test_validate_expression_script_success_and_failure(self):
        valid = {
            "title": "Hear the Beat Flip",
            "script": {
                "title": "Hear the Beat Flip",
                "hook": "Ever notice how your vocal pitch changes the moment you hit the record button?",
                "setup": "Drop your voice heavily onto the front beat: a record. That solid punch holds the album in your hands.",
                "discovery": "Now let the rhythm climb: to record. The energy surges forward because you are creating music right now.",
                "example": "For example in the studio: Quiet everyone, we are ready to record the final album track now.",
                "payoff": "Heavy front punch for the object, rising climb for the action. Hear the music in your words! Drop your favorite track below!",
            },
        }
        res_valid = validate_expression_script(valid)
        self.assertTrue(res_valid.is_valid)
        self.assertGreaterEqual(res_valid.spoken_words, 80)
        self.assertLessEqual(res_valid.spoken_words, 120)

        # Missing example
        invalid = {
            "title": "Short",
            "script": {
                "title": "Short",
                "hook": "Hook line.",
                "setup": "Setup line.",
                "discovery": "Discovery line.",
                "payoff": "Payoff line.",
            },
        }
        res_invalid = validate_expression_script(invalid)
        self.assertFalse(res_invalid.is_valid)
        self.assertTrue(any("example" in err for err in res_invalid.errors))

    def test_validate_fun_facts_script_success_and_failure(self):
        valid = {
            "title": "The Ghost Word Trap",
            "script": {
                "title": "The Ghost Word Trap",
                "hook": "Did you know that dictionaries once printed a completely fake word for five entire years without anyone noticing?",
                "setup": "In nineteen thirty-four, an editor noticed a small slip of paper marked D or d for chemical density in laboratory work.",
                "discovery": "The typesetter accidentally glued the letters together and printed dord as a real English noun meaning density.",
                "explanation": "Nobody noticed the ghost word until an alert senior editor checked the dictionary years later and gasped in shock.",
                "payoff": "Even the most serious lexicons can birth phantom words by accident. What is your favorite weird language mystery? Tell me down in the comments below!",
            },
        }
        res_valid = validate_fun_facts_script(valid)
        self.assertTrue(res_valid.is_valid, f"Validation failed with errors: {res_valid.errors}")
        self.assertGreaterEqual(res_valid.spoken_words, 90)

        # Illegal invented keys
        invalid = {
            "title": "Test",
            "script": {
                "title": "Test",
                "hook": "Hook line.",
                "payoff": "Payoff line.",
                "invented_random_key": "Illegal payload.",
            },
        }
        res_invalid = validate_fun_facts_script(invalid)
        self.assertFalse(res_invalid.is_valid)
        self.assertTrue(any("invented_random_key" in err for err in res_invalid.errors))

    def test_sanitize_strips_narrator_in_expression_and_facts(self):
        e_engine = ExpressionEngine()
        raw_e = {
            "title": "Test",
            "script": {
                "title": "Test",
                "hook": "Narrator: Did you know?",
                "payoff": "NARRATOR: Now you know!",
            },
        }
        sanitized_e = e_engine.sanitize(raw_e)
        self.assertEqual(sanitized_e["script"]["hook"], "Did you know?")
        self.assertEqual(sanitized_e["script"]["payoff"], "Now you know!")

        f_engine = FunFactsEngine()
        sanitized_f = f_engine.sanitize(raw_e)
        self.assertEqual(sanitized_f["script"]["hook"], "Did you know?")
        self.assertEqual(sanitized_f["script"]["payoff"], "Now you know!")


if __name__ == "__main__":
    unittest.main()
