"""
test/unit/test_thumbnail_builder.py — Unit tests for Stage F thumbnail prompt construction.
"""
import unittest

# pyrefly: ignore [missing-import]
from video_creation._F_thumbnail_image_generation.core.thumbnail_prompt_builder import ThumbnailPromptBuilder


class TestThumbnailPromptBuilder(unittest.TestCase):
    def test_build_prompt_contains_uppercase_chalkboard_text(self):
        """Verify build_prompt places uppercase target text in quotes."""
        text = "break a leg"
        prompt = ThumbnailPromptBuilder.build_prompt(text, "English")
        self.assertIn('"BREAK A LEG"', prompt)
        self.assertIn("classroom chalkboard", prompt.lower())
        self.assertIn("reference image", prompt.lower())

    def test_build_prompt_with_special_characters(self):
        """Verify build_prompt handles accented and punctuation-heavy text cleanly."""
        text = "c'est pas la mer à boire!"
        prompt = ThumbnailPromptBuilder.build_prompt(text, "French")
        self.assertIn("\"C'EST PAS LA MER À BOIRE!\"", prompt)


if __name__ == "__main__":
    unittest.main()
