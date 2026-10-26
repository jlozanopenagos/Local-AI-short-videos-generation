"""
test_layer/unit/test_voice_manager.py — Unit tests for VoiceManager language normalization and voice allocation.
"""
import unittest
import tempfile
from pathlib import Path

# Add main to sys.path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_DIR = PROJECT_ROOT / "main"
for p in [str(PROJECT_ROOT), str(MAIN_DIR), str(MAIN_DIR / "core")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.voice_manager import VoiceManager
# pyrefly: ignore[missing-import]
import config


class TestVoiceManager(unittest.TestCase):
    def setUp(self):
        self.vm = VoiceManager(config.OPEN_SWARA_DIR, config.COMFY_INPUT_DIR)

    def test_normalize_language_compound_labels(self):
        cases = [
            ("French | Culture | Fun Facts | Pronunciation", "french"),
            ("Spanish | Slang | Expressions", "spanish"),
            ("Italian | Food & Culture | Travel", "italian"),
            ("English | Idioms | Business", "english"),
            ("French | Français", "french"),
            ("Español | Slang", "spanish"),
            ("Italiano | Grammatica", "italian"),
            ("fr", "french"),
            ("es", "spanish"),
            ("it", "italian"),
            ("en", "english"),
            ("", "english"),
            (None, "english"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                result = VoiceManager.normalize_language(raw)
                self.assertEqual(result, expected)

    def test_assign_voices_for_french_script_with_compound_label(self):
        """Verifies that passing a compound French label assigns a French voice, NEVER English."""
        compound_label = "French | Culture | Fun Facts | Pronunciation"
        self.vm.assign_voices_for_script(["Narrator"], compound_label)
        gender, voice_path, seed = self.vm.get_speaker_voice("Narrator", compound_label)
        
        self.assertIsNotNone(voice_path, "Voice path should not be None")
        self.assertTrue(voice_path.exists(), f"Assigned voice file must exist: {voice_path}")
        self.assertTrue(
            voice_path.name.startswith("french_"),
            f"Assigned voice must be a French voice, but got: {voice_path.name}"
        )
        self.assertNotIn("english", voice_path.name.lower())

    def test_assign_voices_for_spanish_script(self):
        """Verifies that Spanish scripts receive Spanish reference voices."""
        compound_label = "Spanish | Slang | Street Talk"
        self.vm.assign_voices_for_script(["Narrator"], compound_label)
        gender, voice_path, seed = self.vm.get_speaker_voice("Narrator", compound_label)

        self.assertIsNotNone(voice_path)
        self.assertTrue(voice_path.exists())
        self.assertTrue(
            voice_path.name.startswith("spanish_"),
            f"Expected Spanish voice, got {voice_path.name}"
        )

    def test_assign_voices_for_italian_script(self):
        """Verifies that Italian scripts receive Italian reference voices."""
        compound_label = "Italian | Food & Idioms"
        self.vm.assign_voices_for_script(["Narrator"], compound_label)
        gender, voice_path, seed = self.vm.get_speaker_voice("Narrator", compound_label)

        self.assertIsNotNone(voice_path)
        self.assertTrue(voice_path.exists())
        self.assertTrue(
            voice_path.name.startswith("italian_"),
            f"Expected Italian voice, got {voice_path.name}"
        )

    def test_get_available_voices_for_language_and_gender(self):
        """Verifies that get_available_voices returns valid, existing paths for target language."""
        french_female = self.vm.get_available_voices("french", "female")
        self.assertGreater(len(french_female), 0)
        for p in french_female:
            self.assertTrue(p.exists())
            self.assertTrue(p.name.startswith("french_female_"))

    def test_manual_voice_paths_override(self):
        """Verifies that supplying manual_voice_paths overrides default pool selection."""
        french_pool = self.vm.get_available_voices("french", "male")
        if french_pool:
            chosen_manual = french_pool[0]
            self.vm.assign_voices_for_script(
                ["Narrator"],
                "french",
                manual_genders={"Narrator": "male"},
                manual_voice_paths={"Narrator": chosen_manual}
            )
            gender, voice_path, _ = self.vm.get_speaker_voice("Narrator", "french")
            self.assertEqual(gender, "male")
            self.assertEqual(voice_path, chosen_manual)


if __name__ == "__main__":
    unittest.main()
