"""
test_game_engine.py — Unit tests for the isolated GAME domain engine (Step 2.1).
Verifies chalkboard preservation, option A challenge audio sanitization, and registry lookup.
"""

from __future__ import annotations

import unittest

# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.registry import ScriptEngineRegistry
# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.types.game.engine import GameEngine
# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.types.game.validator import validate_game_script


class TestGameEngine(unittest.TestCase):
    """Verifies GameEngine behavior, validation, and chalkboard protection."""

    def test_registry_resolves_game_engine(self):
        engine_by_name = ScriptEngineRegistry.get_engine("game")
        self.assertIsNotNone(engine_by_name)
        self.assertIsInstance(engine_by_name, GameEngine)

        engine_by_code = ScriptEngineRegistry.get_engine("G")
        self.assertIs(engine_by_code, engine_by_name)

        # Canonical script IDs
        self.assertIs(ScriptEngineRegistry.get_engine("SG01"), engine_by_name)
        self.assertIs(ScriptEngineRegistry.get_engine("EG12"), engine_by_name)
        self.assertIs(ScriptEngineRegistry.get_engine("FG99"), engine_by_name)

    def test_chalkboard_exercise_preserved_and_not_overwritten(self):
        """
        Critical regression test: Ensures visual chalkboard_exercise is NOT clobbered
        by the continuous spoken challenge audio string.
        """
        engine = GameEngine()
        board_text = "The committee will ___ the proposal.\nA) proJECT\nB) PROject"
        spoken_challenge_with_blank = "The committee will ___ the proposal."

        raw_script = {
            "title": "Project vs Project",
            "script": {
                "title": "Project vs Project",
                "hook": "Narrator: Watch out for this tricky English stress!",
                "challenge": spoken_challenge_with_blank,
                "pressure": "Three seconds, which one is it?",
                "answer": "Narrator: It's A! In this sentence we need the verb proJECT.",
                "explanation": "Natives stress the second syllable for verbs and the first for nouns.",
            },
            "chalkboard_exercise": board_text,
        }

        sanitized = engine.sanitize(raw_script)

        # 1. Visual chalkboard exercise MUST preserve linebreaks, blank (___), and stress options
        self.assertEqual(sanitized["chalkboard_exercise"], board_text)
        self.assertIn("\nA) proJECT", sanitized["chalkboard_exercise"])
        self.assertIn("___", sanitized["chalkboard_exercise"])

        # 2. Spoken challenge audio MUST have option A substituted and options voiced without raw blanks
        spoken = sanitized["script"]["challenge"]
        self.assertNotIn("___", spoken)
        self.assertIn("proJECT", spoken)
        self.assertIn("A: proJECT", spoken)
        self.assertIn("B: PROject", spoken)

        # 3. Narrator prefixes must be stripped from audio
        self.assertFalse(sanitized["script"]["hook"].startswith("Narrator:"))
        self.assertFalse(sanitized["script"]["answer"].startswith("Narrator:"))

    def test_validate_game_script_flags_raw_blank_in_spoken_challenge(self):
        invalid_script = {
            "title": "Test Title",
            "script": {
                "title": "Test Title",
                "hook": "Listen closely to this challenge right now!",
                "challenge": "She broke the world ___ in swimming. A: a record. B: to record.",
                "pressure": "Time is ticking fast!",
                "answer": "It is Option A, a record!",
                "explanation": "Because record is a noun when stressed on the first syllable in English.",
            },
            "chalkboard_exercise": "She broke the world ___ in swimming.\nA) a record\nB) to record",
        }
        res = validate_game_script(invalid_script)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("raw blank" in err.lower() for err in res.errors))

    def test_validate_game_script_requires_multiline_chalkboard(self):
        single_line_board = {
            "title": "Test Title",
            "script": {
                "title": "Test Title",
                "hook": "Listen closely to this sentence right now and decide!",
                "challenge": "She broke the world record. A: a record. B: to record.",
                "pressure": "Time is ticking fast right now!",
                "answer": "It is Option A, a record!",
                "explanation": "Because record is a noun when stressed on the first syllable.",
            },
            "chalkboard_exercise": "Single line board without options",
        }
        res = validate_game_script(single_line_board)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("multiline" in err.lower() for err in res.errors))


if __name__ == "__main__":
    unittest.main()

