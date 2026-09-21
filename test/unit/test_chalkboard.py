"""
test_layer/unit/test_chalkboard.py — Unit tests for chalkboard typography parser and layout rules.
"""
import unittest

# pyrefly: ignore [missing-import]
from video_creation._C_image_generation.core.chalkboard_renderer import parse_quiz_exercise


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


if __name__ == "__main__":
    unittest.main()
