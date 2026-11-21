"""
test/unit/test_thumbnail_builder.py — Unit tests for Stage F chalkboard thumbnail rendering and prompt construction.
"""
import tempfile
import unittest
from pathlib import Path
# pyrefly: ignore[missing-import]
from PIL import Image, ImageDraw

# pyrefly: ignore [missing-import]
from video_creation._F_thumbnail_image_generation.core.thumbnail_renderer import (
    clean_thumbnail_title,
    detect_chalkboard_bounds,
    extract_thumbnail_title,
    render_thumbnail_chalkboard,
    sanitize_thumbnail_title,
)


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

    def test_detect_chalkboard_bounds_in_synthetic_thumbnail(self):
        with Image.new("RGB", (576, 1024), "#af8761") as image:
            ImageDraw.Draw(image).rectangle((65, 100, 515, 550), fill="#285640")
            x1, y1, x2, y2 = detect_chalkboard_bounds(image)
            self.assertGreater(x2 - x1, 300)
            self.assertGreater(y2 - y1, 200)
            self.assertLess(y2, 820)

    def test_render_thumbnail_chalkboard_creates_576x1024_image(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "model.png"
            Image.new("RGB", (576, 1024), "#285640").save(model_path)
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


    def test_sanitize_thumbnail_title_latin_languages(self):
        """Verify English clichés and leakage are stripped or replaced with clean target expression."""
        # Italian: strip English suffix cliché
        self.assertEqual(
            sanitize_thumbnail_title("In bocca al lupo: The Native Secret", "italian", "In bocca al lupo"),
            "In bocca al lupo",
        )
        # Spanish: strip English suffix cliché
        self.assertEqual(
            sanitize_thumbnail_title("Costar un ojo de la cara: The Native Secret", "spanish", "Costar un ojo de la cara"),
            "Costar un ojo de la cara",
        )
        # French: strip English suffix cliché
        self.assertEqual(
            sanitize_thumbnail_title("Poser un lapin: The Native Secret", "french", "Poser un lapin"),
            "Poser un lapin",
        )
        # Italian: 100% English title replaced with clean target expression title
        self.assertEqual(
            sanitize_thumbnail_title("The Secret Italian Phrase for Good Luck", "italian", "In bocca al lupo"),
            "In bocca al lupo",
        )
        # Already native titles preserved untouched
        self.assertEqual(
            sanitize_thumbnail_title("Poser un Lapin : L'expression des natifs", "french", "Poser un lapin"),
            "Poser un Lapin : L'expression des natifs",
        )
        self.assertEqual(
            sanitize_thumbnail_title("Solo 21 Lettere: Il Segreto dell'Alfabeto Italiano", "italian", "L'alfabeto italiano"),
            "Solo 21 Lettere: Il Segreto dell'Alfabeto Italiano",
        )
        # English scripts remain untouched
        self.assertEqual(
            sanitize_thumbnail_title("Break a leg: The Native Secret", "english", "Break a leg"),
            "Break a leg: The Native Secret",
        )


if __name__ == "__main__":
    unittest.main()
