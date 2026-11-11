"""
test_script_engine_foundation.py — Unit tests for Phase 1 of the modular script workflow refactor.
Tests BaseScriptEngine contracts, spoken word counter, JSON parser, and ScriptEngineRegistry.
"""

from __future__ import annotations

import unittest
from typing import Any, Dict, List, Optional

# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.common.base_engine import (
    BaseScriptEngine,
    ScriptGenerationResult,
    ValidationResult,
)
# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.common.text_utils import (
    clean_narrator_prefix,
    count_spoken_words,
    extract_json_from_llm_response,
    extract_spoken_text,
    strip_speaker_tags,
    strip_stage_directions,
)
# pyrefly: ignore[missing-import]
from video_creation._A_video_scripts.registry import (
    ScriptEngineRegistry,
    register_script_engine,
)


class TestTextUtils(unittest.TestCase):
    """Verifies spoken word count calculations and text normalization."""

    def test_strip_speaker_tags(self):
        self.assertEqual(
            strip_speaker_tags("PERSON_ONE: Have you seen the car?"),
            "Have you seen the car?",
        )
        self.assertEqual(
            strip_speaker_tags("PERSON_TWO (Excited): Yes, it's amazing!"),
            "Yes, it's amazing!",
        )
        self.assertEqual(
            strip_speaker_tags("NARRATOR: Here is the truth."),
            "Here is the truth.",
        )

    def test_strip_stage_directions(self):
        text = "I cannot believe (whispering) what just happened [sighs] today!"
        cleaned = strip_stage_directions(text)
        self.assertNotIn("whispering", cleaned)
        self.assertNotIn("sighs", cleaned)
        self.assertIn("what just happened", cleaned)

    def test_extract_spoken_text(self):
        raw = "PERSON_ONE (Curious & energetic): Did you know that cats sleep all day?"
        spoken = extract_spoken_text(raw)
        self.assertEqual(spoken, "Did you know that cats sleep all day?")

    def test_count_spoken_words_eliminates_phantom_bloat(self):
        # Naive split count on this string is 12 words:
        # PERSON_ONE (Curious & energetic): Have you seen my blue keys?
        raw_dialogue = "PERSON_ONE (Curious & energetic): Have you seen my blue keys?"
        naive_count = len(raw_dialogue.split())
        self.assertEqual(naive_count, 10)  # Contains 4 phantom words: PERSON_ONE (Curious & energetic):

        spoken_count = count_spoken_words(raw_dialogue)
        # Spoken words: "Have you seen my blue keys?" = 6 words
        self.assertEqual(spoken_count, 6)

    def test_count_spoken_words_dict(self):
        script_dict = {
            "hook": "Narrator: What is the biggest secret in English?",
            "dialogue_part_1": "PERSON_ONE (Whispering): Do not say that aloud!\nPERSON_TWO (Laughing): Why not?",
            "chalkboard_exercise": "A) proJECT\nB) PROject",  # Should be ignored in spoken count
        }
        # Hook spoken: "What is the biggest secret in English?" (7 words)
        # Part 1 spoken: "Do not say that aloud! Why not?" (7 words: 5 + 2)
        # Total = 14 words
        total = count_spoken_words(script_dict)
        self.assertEqual(total, 14)

    def test_clean_narrator_prefix(self):
        self.assertEqual(
            clean_narrator_prefix("Narrator: Have you ever noticed this?"),
            "Have you ever noticed this?",
        )
        self.assertEqual(
            clean_narrator_prefix("NARRATOR (cheerful): Welcome back!"),
            "Welcome back!",
        )
        self.assertEqual(
            clean_narrator_prefix("Standard text without prefix."),
            "Standard text without prefix.",
        )

    def test_extract_json_markdown_fenced(self):
        raw = """Here is the generated script:
```json
{
  "hook": "Did you know?",
  "payoff": "Now you know!"
}
```
Hope you like it!"""
        data = extract_json_from_llm_response(raw)
        self.assertEqual(data["hook"], "Did you know?")
        self.assertEqual(data["payoff"], "Now you know!")

    def test_extract_json_raw_braces(self):
        raw = "Certainly! {\"test\": 123} is your answer."
        data = extract_json_from_llm_response(raw)
        self.assertEqual(data["test"], 123)

    def test_extract_json_invalid_raises_value_error(self):
        with self.assertRaises(ValueError):
            extract_json_from_llm_response("No JSON here at all.")


class DummyTestEngine(BaseScriptEngine):
    script_type = "dummy_game"
    type_codes = ["DG"]

    def build_prompt(self, input_data: Dict[str, Any]) -> str:
        return f"Build dummy game for {input_data.get('SCRIPT_ID')}"

    def validate(self, script_dict: Dict[str, Any], input_data: Optional[Dict[str, Any]] = None) -> ValidationResult:
        res = ValidationResult()
        if "challenge" not in script_dict:
            res.add_error("Missing 'challenge' key")
        return res

    def sanitize(self, script_dict: Dict[str, Any], input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cleaned = dict(script_dict)
        if "hook" in cleaned:
            cleaned["hook"] = clean_narrator_prefix(cleaned["hook"])
        return cleaned


class TestScriptEngineRegistryAndLifecycle(unittest.TestCase):
    """Verifies engine registration, canonical ID dispatch, and base lifecycle."""

    def setUp(self):
        ScriptEngineRegistry.clear()

    def tearDown(self):
        ScriptEngineRegistry.clear()

    def test_register_and_lookup_by_type_and_code(self):
        ScriptEngineRegistry.register(DummyTestEngine)

        # Lookup by exact name
        engine = ScriptEngineRegistry.get_engine("dummy_game")
        self.assertIsNotNone(engine)
        self.assertIsInstance(engine, DummyTestEngine)

        # Lookup by code
        engine_code = ScriptEngineRegistry.get_engine("DG")
        self.assertIs(engine_code, engine)

        # List supported types
        self.assertIn("dummy_game", ScriptEngineRegistry.list_supported_types())

    def test_dispatch_from_canonical_script_id(self):
        # Register an engine with code 'G'
        class MockGameEngine(BaseScriptEngine):
            script_type = "game"
            type_codes = ["G"]
            def build_prompt(self, input_data): return ""
            def validate(self, script_dict, input_data=None): return ValidationResult()

        ScriptEngineRegistry.register(MockGameEngine)

        # Script ID "SG05" has Language 'S' and Type 'G'
        engine = ScriptEngineRegistry.get_engine("SG05")
        self.assertIsNotNone(engine)
        self.assertEqual(engine.script_type, "game")

        # Script ID "EG12" has Language 'E' and Type 'G'
        engine_en = ScriptEngineRegistry.get_engine("EG12")
        self.assertIsNotNone(engine_en)
        self.assertEqual(engine_en.script_type, "game")

    def test_base_engine_generate_lifecycle_success(self):
        mock_response = '{"challenge": "The test", "hook": "Narrator: Listen up!"}'
        engine = DummyTestEngine(llm_callable=lambda prompt: mock_response)

        result = engine.generate({"SCRIPT_ID": "DG01"})
        self.assertTrue(result.is_valid)
        self.assertEqual(result.script["challenge"], "The test")
        # Ensure sanitize stripped "Narrator:"
        self.assertEqual(result.script["hook"], "Listen up!")
        self.assertEqual(result.retry_count, 0)
        self.assertGreater(result.spoken_words, 0)

    def test_base_engine_generate_lifecycle_retry_on_validation_failure(self):
        responses = [
            '{"invalid_field": "Missing challenge"}',  # 1st attempt: fails validation
            '{"challenge": "Valid on attempt 2"}',     # 2nd attempt: succeeds
        ]
        call_idx = {"idx": 0}

        def mock_llm(prompt: str) -> str:
            res = responses[call_idx["idx"]]
            call_idx["idx"] += 1
            return res

        engine = DummyTestEngine(llm_callable=mock_llm)
        result = engine.generate({"SCRIPT_ID": "DG02"}, max_retries=2)

        self.assertTrue(result.is_valid)
        self.assertEqual(result.script["challenge"], "Valid on attempt 2")
        self.assertEqual(result.retry_count, 1)


if __name__ == "__main__":
    unittest.main()
