"""
test_layer/unit/test_script_parser.py — Unit tests for dialogue normalization, emotion extraction, and script parsing.
"""
import unittest

# pyrefly: ignore [missing-import]
from video_creation._B_voice_generation.core.script_parser import (
    extract_parenthetical,
    normalize_spoken_dialogue,
    clean_text_and_extract_emotions,
    parse_sections,
)


class TestScriptParser(unittest.TestCase):
    def test_extract_parenthetical(self):
        text1, emotion1 = extract_parenthetical("Agent (Stressé)")
        self.assertEqual(text1, "Agent")
        self.assertEqual(emotion1, "Stressé")

        text2, emotion2 = extract_parenthetical("Narrator")
        self.assertEqual(text2, "Narrator")
        self.assertIsNone(emotion2)

    def test_normalize_spoken_dialogue_laughs_and_sound_effects(self):
        # Removes laugh sounds
        raw1 = "Haha, that was really funny!"
        cleaned1 = normalize_spoken_dialogue(raw1)
        self.assertNotIn("Haha", cleaned1)
        self.assertEqual(cleaned1, "that was really funny!")

        # Removes sound effect asterisks
        raw2 = "Wait *sigh* let me think about that *gasp* now."
        cleaned2 = normalize_spoken_dialogue(raw2)
        self.assertEqual(cleaned2, "Wait let me think about that now.")

    def test_normalize_spoken_dialogue_leading_oh_no(self):
        raw = "Oh no, we are going to miss the train!"
        cleaned = normalize_spoken_dialogue(raw)
        self.assertEqual(cleaned, "No, we are going to miss the train!")

    def test_normalize_spoken_dialogue_multiple_dots(self):
        raw = "Break a... what did you say?"
        cleaned = normalize_spoken_dialogue(raw)
        self.assertEqual(cleaned, "Break a, what did you say?")

    def test_normalize_spoken_dialogue_smart_quotes_and_dashes(self):
        raw = "It’s a “classic” minimal pair—watch out."
        cleaned = normalize_spoken_dialogue(raw)
        self.assertEqual(cleaned, "It's a \"classic\" minimal pair, watch out.")

    def test_clean_text_and_extract_emotions(self):
        raw = "PERSON_ONE (Panicked): We only have four minutes left!"
        cleaned, emotion = clean_text_and_extract_emotions(raw)
        self.assertEqual(cleaned, "PERSON_ONE : We only have four minutes left!")
        self.assertEqual(emotion, "Panicked")

    def test_parse_sections_from_json(self):
        raw = """{
            "title": "Test Title",
            "hook": "Opening hook",
            "payoff": "Closing payoff"
        }"""
        sections = parse_sections(raw)
        self.assertIn("title", sections)
        self.assertEqual(sections["title"], "Test Title")
        self.assertEqual(sections["hook"], "Opening hook")
        self.assertEqual(sections["payoff"], "Closing payoff")

    def test_parse_sections_from_text_headers(self):
        raw = """Title: French Idiom
Hook: Did you hear that?
Payoff: That's how locals say it."""
        sections = parse_sections(raw)
        self.assertEqual(sections.get("title"), "French Idiom")
        self.assertEqual(sections.get("hook"), "Did you hear that?")
        self.assertEqual(sections.get("payoff"), "That's how locals say it.")


if __name__ == "__main__":
    unittest.main()
