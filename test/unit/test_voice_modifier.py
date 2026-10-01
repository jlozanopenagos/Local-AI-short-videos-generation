import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# pyrefly: ignore [missing-import]
from video_creation._B_voice_generation.voice_modifier import (
    is_stress_pronunciation_vital,
    infer_dialogue_emotion,
    map_emotion_to_energy,
)


class TestVoiceModifier(unittest.TestCase):
    def test_is_stress_pronunciation_vital_with_cased_notation(self):
        script_data = {
            "metadata": {"LABEL": "english"},
            "prompt_params": {"SUBJECT": "Grammar"},
            "content_metadata": {},
        }
        # Noun capitalized notation
        self.assertTrue(is_stress_pronunciation_vital(script_data, "Say a PREsent now"))
        # Verb capitalized notation
        self.assertTrue(is_stress_pronunciation_vital(script_data, "You need to preSENT today"))
        # Plain text
        self.assertFalse(is_stress_pronunciation_vital(script_data, "Hello world, how are you?"))

    def test_is_stress_pronunciation_vital_from_metadata(self):
        script_data = {
            "metadata": {"LABEL": "english"},
            "prompt_params": {"SUBJECT": "Word stress and heteronyms"},
            "content_metadata": {"learning_objective": "Syllable stress contrast"},
        }
        self.assertTrue(is_stress_pronunciation_vital(script_data, "Normal sentence text"))

    def test_map_emotion_to_energy(self):
        self.assertEqual(map_emotion_to_energy("electrifying trivia host"), "very high")
        self.assertEqual(map_emotion_to_energy("whisper sad"), "medium")
        self.assertEqual(map_emotion_to_energy("warm confident"), "high")

    def test_infer_dialogue_emotion_narrator(self):
        emo = infer_dialogue_emotion("Narrator", "Check this secret out!", section="hook")
        self.assertIn("dramatic", emo)


if __name__ == "__main__":
    unittest.main()
