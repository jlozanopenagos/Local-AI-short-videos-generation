"""
test_layer/unit/test_subtitle_builder.py — Unit tests for ASS dynamic animated subtitle generation.
"""
import unittest
import tempfile
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
