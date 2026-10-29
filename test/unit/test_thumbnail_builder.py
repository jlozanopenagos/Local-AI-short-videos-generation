"""
test/unit/test_thumbnail_builder.py — Unit tests for Stage F chalkboard thumbnail rendering and prompt construction.
"""
import tempfile
import unittest
from pathlib import Path
# pyrefly: ignore[missing-import]
from PIL import Image

# pyrefly: ignore[missing-import]
from config import THUMBNAIL_MODELS_DIR
# pyrefly: ignore [missing-import]
from video_creation._F_thumbnail_image_generation.core.thumbnail_prompt_builder import ThumbnailPromptBuilder
# pyrefly: ignore [missing-import]
from video_creation._F_thumbnail_image_generation.core.thumbnail_renderer import (
    clean_thumbnail_title,
    detect_chalkboard_bounds,
    extract_thumbnail_title,
    render_thumbnail_chalkboard,
)


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


class TestThumbnailChalkboardRenderer(unittest.TestCase):
    def test_clean_thumbnail_title_preserves_stress_and_fixes_quotes(self):
        """Verify heteronym stress casing is preserved and trailing unmatched quotes are closed."""
        self.assertEqual(
            clean_thumbnail_title("REcord vs reCORD: The Native Secret"),
            "REcord vs reCORD: The Native Secret",
        )
        self.assertEqual(
            clean_thumbnail_title("The Secret to Saying 'Piece of Cake"),
            "The Secret to Saying 'Piece of Cake'",
        )

    def test_extract_thumbnail_title_prioritizes_script_title(self):
        """Verify extract_thumbnail_title uses content_metadata.script.title with fallback to target_expression."""
        state_with_title = {
            "content_metadata": {
                "target_expression": "Break a leg",
                "script": {"title": "The Secret Theater Phrase: Break a Leg"},
            }
        }
        self.assertEqual(
            extract_thumbnail_title(state_with_title),
            "The Secret Theater Phrase: Break a Leg",
        )

        state_fallback = {
            "content_metadata": {
                "target_expression": "Break a leg",
            }
        }
        self.assertEqual(extract_thumbnail_title(state_fallback), "Break a leg")

    def test_detect_chalkboard_bounds_on_models(self):
        """Verify chalkboard detection finds a valid green board region above Tito on language models."""
        for lang in ("english", "french", "spanish", "italian"):
            model_path = THUMBNAIL_MODELS_DIR / lang / f"{lang}_thumbnail_model.png"
            if not model_path.exists():
                continue
            with Image.open(model_path) as im:
                x1, y1, x2, y2 = detect_chalkboard_bounds(im)
                self.assertGreater(x2 - x1, 300)
                self.assertGreater(y2 - y1, 200)
                self.assertLess(y2, 820)  # Above Tito's head/ears

    def test_render_thumbnail_chalkboard_creates_576x1024_image(self):
        """Verify render_thumbnail_chalkboard renders 576x1024 PNGs for both colon and single-block titles."""
        model_path = THUMBNAIL_MODELS_DIR / "english" / "english_thumbnail_model.png"
        if not model_path.exists():
            self.skipTest("english_thumbnail_model.png not found")

        with tempfile.TemporaryDirectory() as tmp_dir:
            dest_colon = Path(tmp_dir) / "thumb_colon.png"
            out1 = render_thumbnail_chalkboard(
                model_path, "The Secret Theater Phrase: Break a Leg", dest_colon
            )
            self.assertTrue(out1.exists())
            with Image.open(out1) as im1:
                self.assertEqual(im1.size, (576, 1024))

            dest_single = Path(tmp_dir) / "thumb_single.png"
            out2 = render_thumbnail_chalkboard(
                model_path, "STOP Saying OBject vs obJECT Wrong!", dest_single
            )
            self.assertTrue(out2.exists())
            with Image.open(out2) as im2:
                self.assertEqual(im2.size, (576, 1024))


if __name__ == "__main__":
    unittest.main()
