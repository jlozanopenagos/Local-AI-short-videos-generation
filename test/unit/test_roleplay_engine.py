"""
test_roleplay_engine.py — Unit tests for the isolated ROLEPLAY domain engine (Step 2.2).
Verifies character alternation enforcement, narrator isolation, spoken word metric, and registry lookup.
"""

from __future__ import annotations

import unittest

# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.registry import ScriptEngineRegistry
# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.types.roleplay.engine import RoleplayEngine
# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.types.roleplay.validator import validate_roleplay_script


class TestRoleplayEngine(unittest.TestCase):
    """Verifies RoleplayEngine behavior, validation gates, and sanitization."""

    def test_registry_resolves_roleplay_engine(self):
        engine_by_name = ScriptEngineRegistry.get_engine("roleplay")
        self.assertIsNotNone(engine_by_name)
        self.assertIsInstance(engine_by_name, RoleplayEngine)

        engine_by_code = ScriptEngineRegistry.get_engine("R")
        self.assertIs(engine_by_code, engine_by_name)

        # Canonical script IDs
        self.assertIs(ScriptEngineRegistry.get_engine("SR01"), engine_by_name)
        self.assertIs(ScriptEngineRegistry.get_engine("ER04"), engine_by_name)
        self.assertIs(ScriptEngineRegistry.get_engine("FR10"), engine_by_name)

    def test_detects_single_speaker_degeneration_bug(self):
        """
        Critical regression test: Ensures that dialogue parts containing only a single
        speaker (the bug present in 133 existing scripts) are strictly rejected!
        """
        malformed_script = {
            "title": "The Flight Gate Mix-Up",
            "script": {
                "title": "The Flight Gate Mix-Up",
                "hook": "Ever notice how airport nerves turn simple English into pure comedy?",
                "DIALOGUE_PART_1": "PERSON_ONE (Nervous): We need a special permit to board this flight!\nPERSON_TWO (Deadpan): She asked if they permitted backpacks.",
                "DIALOGUE_PART_2": "PERSON_ONE (Baffled): Wait, so nobody is canceling our boarding passes right now?",  # Missing PERSON_TWO!
                "DIALOGUE_PART_3": "PERSON_ONE (Relieved): So permit is the paper and permit is the action?\nPERSON_TWO (Smirking): Exactly right.",
                "DIALOGUE_PART_4": "PERSON_ONE (Grinning): Got it, no more panicking at international gates!\nPERSON_TWO (Laughing): Great, now grab the bags.",
                "PAYOFF": "One misplaced syllable and you are sweating at the gate. Own the conversation and drop your travel story below!",
            },
        }

        res = validate_roleplay_script(malformed_script)
        self.assertFalse(res.is_valid)
        self.assertTrue(
            any("DIALOGUE_PART_2" in err and "PERSON_TWO" in err for err in res.errors),
            f"Expected error about DIALOGUE_PART_2 missing PERSON_TWO, got: {res.errors}",
        )

    def test_rejects_narrator_in_dialogue_parts(self):
        script_with_narrator_in_part = {
            "title": "The Flight Gate Mix-Up",
            "script": {
                "title": "The Flight Gate Mix-Up",
                "hook": "Ever notice how airport nerves turn simple English into pure comedy?",
                "DIALOGUE_PART_1": "PERSON_ONE (Nervous): We need a permit!\nPERSON_TWO (Deadpan): She asked if they permitted bags.",
                "DIALOGUE_PART_2": "NARRATOR: Meanwhile, at the boarding counter...\nPERSON_TWO (Laughing): Why are you running?",
                "DIALOGUE_PART_3": "PERSON_ONE (Relieved): So permit is the paper?\nPERSON_TWO (Smirking): Exactly.",
                "DIALOGUE_PART_4": "PERSON_ONE (Grinning): Got it!\nPERSON_TWO (Laughing): Great, grab the bags.",
                "PAYOFF": "One misplaced syllable and you sweat at the gate. Drop your travel story below!",
            },
        }

        res = validate_roleplay_script(script_with_narrator_in_part)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("NARRATOR" in err for err in res.errors))

    def test_sanitize_inserts_missing_newlines_and_strips_narrator_prefix(self):
        engine = RoleplayEngine()
        raw_script = {
            "title": "Test Title",
            "script": {
                "title": "Test Title",
                "hook": "Narrator: Have you ever wondered about this?",
                "DIALOGUE_PART_1": "PERSON_ONE (Curious): What is this? PERSON_TWO (Energetic): It is a new tool!",
                "DIALOGUE_PART_2": "PERSON_ONE (Shocked): Really? PERSON_TWO (Chuckling): Yes indeed!",
                "DIALOGUE_PART_3": "PERSON_ONE (Relieved): Wow.\nPERSON_TWO (Smiling): Pretty cool.",
                "DIALOGUE_PART_4": "PERSON_ONE (Happy): Awesome.\nPERSON_TWO (Laughing): Let us go.",
                "PAYOFF": "Narrator: That is how you use it in real life. Follow for more tips!",
            },
        }

        sanitized = engine.sanitize(raw_script)

        # 1. Narrator prefix stripped
        self.assertFalse(sanitized["script"]["hook"].startswith("Narrator:"))
        self.assertFalse(sanitized["script"]["PAYOFF"].startswith("Narrator:"))

        # 2. Newline inserted before PERSON_TWO in Part 1 and Part 2
        self.assertIn("\nPERSON_TWO", sanitized["script"]["DIALOGUE_PART_1"])
        self.assertIn("\nPERSON_TWO", sanitized["script"]["DIALOGUE_PART_2"])


if __name__ == "__main__":
    unittest.main()

