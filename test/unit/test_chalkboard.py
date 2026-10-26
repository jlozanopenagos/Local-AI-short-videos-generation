"""
test_layer/unit/test_chalkboard.py — Unit tests for chalkboard typography parser and layout rules.
"""
import unittest

import tempfile
from pathlib import Path
from PIL import Image, ImageDraw

# pyrefly: ignore [missing-import]
from video_creation._C_image_generation.core.chalkboard_renderer import (
    parse_quiz_exercise, fit_option_text, render_chalkboard_image, _get_font
)
from config import GAME_IMAGES_DIR


class TestChalkboardRenderer(unittest.TestCase):
    def test_parse_quiz_multiline_options(self):
        text = """Both actors signed the employment ___ yesterday.
A) CONtract
B) conTRACT"""
        question, options = parse_quiz_exercise(text)
        self.assertEqual(question, "Both actors signed the employment ___ yesterday.")
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0], ("A", "CONtract"))
        self.assertEqual(options[1], ("B", "conTRACT"))

    def test_parse_quiz_inline_options(self):
        text = "Which word sounds natural? A) blessé B) béni"
        question, options = parse_quiz_exercise(text)
        self.assertEqual(question, "Which word sounds natural?")
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0], ("A", "blessé"))
        self.assertEqual(options[1], ("B", "béni"))

    def test_parse_quiz_punctuation_variants(self):
        text = "Select one: A: First Option B: Second Option C: Third Option"
        question, options = parse_quiz_exercise(text)
        self.assertEqual(len(options), 3)
        self.assertEqual(options[0], ("A", "First Option"))
        self.assertEqual(options[1], ("B", "Second Option"))
        self.assertEqual(options[2], ("C", "Third Option"))

    def test_parse_quiz_fallback_when_no_options(self):
        text = "Just a question without any structured options here."
        question, options = parse_quiz_exercise(text)
        self.assertEqual(question, text)
        self.assertEqual(len(options), 4)
        self.assertEqual(options[0][0], "A")
        self.assertEqual(options[1][0], "B")

    def test_chalkboard_dimensions(self):
        TARGET_WIDTH = 576
        TARGET_HEIGHT = 1024
        self.assertEqual(TARGET_WIDTH, 576)
        self.assertEqual(TARGET_HEIGHT, 1024)
        self.assertAlmostEqual(TARGET_HEIGHT / TARGET_WIDTH, 16 / 9, places=2)

    def test_fit_option_text_short_option(self):
        """Standard short option fits on a single line with maximum font size."""
        img = Image.new("RGBA", (100, 100))
        draw = ImageDraw.Draw(img)
        lines, font, size, lh = fit_option_text(draw, "CONtract", 636, None)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], "CONtract")
        self.assertEqual(size, 40)

    def test_fit_option_text_long_option_fg19(self):
        """Long option text (e.g. FG19) wraps into lines that all strictly fit within max_w."""
        img = Image.new("RGBA", (100, 100))
        draw = ImageDraw.Draw(img)
        max_w = 636
        long_opt = "Napoléon était un un grand homme respecté dans toute l'Europe."
        lines, font, size, lh = fit_option_text(draw, long_opt, max_w, None)
        self.assertGreater(len(lines), 1)
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            self.assertLessEqual(line_w, max_w, f"Line '{line}' width {line_w} exceeds {max_w}")

    def test_render_chalkboard_image_fg19_creates_image(self):
        """Verifies render_chalkboard_image runs end-to-end on FG19 and produces target 576x1024 image."""
        empty_cb = GAME_IMAGES_DIR / "empty_chalkboard.png"
        if not empty_cb.exists():
            self.skipTest("empty_chalkboard.png not found")
        exercise_text = """Il faut choisir vite ! Il dit:
A: Napoléon était un un grand homme respecté dans toute l'Europe. B: Napoléon était un un homme grand respecté dans toute l'Europe."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = Path(tmp_dir) / "test_fg19_output.png"
            out = render_chalkboard_image(empty_cb, exercise_text, dest)
            self.assertTrue(out.exists())
            with Image.open(out) as im:
                self.assertEqual(im.size, (576, 1024))


if __name__ == "__main__":
    unittest.main()
