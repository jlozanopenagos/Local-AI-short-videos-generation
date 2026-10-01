"""
test_layer/unit/test_subtitle_builder.py — Unit tests for ASS dynamic animated subtitle generation.
"""
import unittest
import tempfile
from pathlib import Path

# pyrefly: ignore [missing-import]
from video_creation._G_video_assembly.core.subtitle_builder import SubtitleBuilder


class TestSubtitleBuilder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.builder = SubtitleBuilder()
        self.out_path = Path(self.temp_dir.name) / "test_subtitles.ass"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_ass_basic_structure(self):
        words = [
            {"word": "Hello", "start": 0.50, "end": 0.90},
            {"word": "world", "start": 0.95, "end": 1.40}
        ]
        created = self.builder.build_ass(words, self.out_path)
        self.assertTrue(created.exists())

        content = created.read_text(encoding="utf-8")
        self.assertIn("[Script Info]", content)
        self.assertIn("PlayResX: 576", content)
        self.assertIn("PlayResY: 1024", content)
        self.assertIn("&H0000FFFF", content)  # Hormozi Yellow primary color

        # Dialogue events
        self.assertIn("HELLO", content)
        self.assertIn("WORLD", content)

    def test_build_ass_suppression_windows(self):
        # Challenge window between 5.0 and 15.0 seconds
        words = [
            {"word": "Before", "start": 2.0, "end": 2.5},
            {"word": "HiddenInChallenge", "start": 7.0, "end": 8.0},
            {"word": "After", "start": 16.0, "end": 16.5}
        ]
        suppress = [(5.0, 15.0)]
        self.builder.build_ass(words, self.out_path, suppress_windows=suppress)

        content = self.out_path.read_text(encoding="utf-8")
        self.assertIn("BEFORE", content)
        self.assertNotIn("HIDDENINCHALLENGE", content)
        self.assertIn("AFTER", content)

    def test_timestamp_formatting_accuracy(self):
        words = [
            {"word": "MinuteOne", "start": 65.25, "end": 66.50}
        ]
        self.builder.build_ass(words, self.out_path)
        content = self.out_path.read_text(encoding="utf-8")
        # 65.25s -> 0:01:05.25, 66.50s -> 0:01:06.50
        self.assertIn("0:01:05.25", content)
        self.assertIn("0:01:06.50", content)

    def test_build_ass_preserves_heteronym_stress_casing(self):
        """Verify that educational heteronym words preserve their syllable stress casing."""
        words = [
            {"word": "Feel", "start": 0.0, "end": 0.2},
            {"word": "the", "start": 0.2, "end": 0.3},
            {"word": "noun", "start": 0.3, "end": 0.5},
            {"word": "a", "start": 0.5, "end": 0.6},
            {"word": "present", "start": 0.6, "end": 1.0},
            {"word": "versus", "start": 1.0, "end": 1.3},
            {"word": "the", "start": 1.3, "end": 1.4},
            {"word": "verb", "start": 1.4, "end": 1.6},
            {"word": "to", "start": 1.6, "end": 1.7},
            {"word": "present", "start": 1.7, "end": 2.2},
        ]
        script_data = {
            "script_text": "Feel the noun a PREsent versus the verb to preSENT."
        }
        self.builder.build_ass(words, self.out_path, script_data=script_data)
        content = self.out_path.read_text(encoding="utf-8")

        # Standard words are upper-cased for Hormozi short visual punch
        self.assertIn("FEEL", content)
        self.assertIn("NOUN", content)
        self.assertIn("VERB", content)

        # Crucial educational heteronyms preserve their exact syllable stress casing
        self.assertIn("PREsent", content)
        self.assertIn("preSENT", content)
        # Ensure they were not crushed into flat all-caps PRESENT
        dialogue_lines = [l for l in content.splitlines() if l.startswith("Dialogue:")]
        texts = [l.split(",")[-1] for l in dialogue_lines]
        self.assertEqual(texts[4], "PREsent")
        self.assertEqual(texts[9], "preSENT")


if __name__ == "__main__":
    unittest.main()
