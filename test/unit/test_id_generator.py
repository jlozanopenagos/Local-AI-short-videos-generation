"""
test_layer/unit/test_id_generator.py — Unit tests for canonical ID generation, parsing, and allocation.
"""
import unittest

from video_creation._A_video_scripts.id_generator import (
    get_language_code,
    get_type_code,
    generate_script_id,
    parse_script_id,
)


class TestIdGenerator(unittest.TestCase):
    def test_get_language_code(self):
        cases = [
            ("english", "E"),
            ("English", "E"),
            ("french", "F"),
            ("French | Français", "F"),
            ("spanish", "S"),
            ("Spanish | Español", "S"),
            ("italian", "I"),
            ("Italian | Italiano", "I"),
        ]
        for lang, expected in cases:
            with self.subTest(lang=lang):
                self.assertEqual(get_language_code(lang), expected)

    def test_get_type_code(self):
        cases = [
            ("EXPRESSION", "E"),
            ("GAME", "G"),
            ("ROLEPLAY", "R"),
            ("FUN_FACTS", "F"),
            ("FUNFACTS", "F"),
            ("FACTS", "F"),
        ]
        for vtype, expected in cases:
            with self.subTest(vtype=vtype):
                self.assertEqual(get_type_code(vtype), expected)

    def test_generate_script_id(self):
        self.assertEqual(generate_script_id("french", "expression", 1), "FE01")
        self.assertEqual(generate_script_id("english", "game", 12), "EG12")
        self.assertEqual(generate_script_id("spanish", "roleplay", 5), "SR05")
        self.assertEqual(generate_script_id("italian", "fun_facts", 9), "IF09")
        self.assertEqual(generate_script_id("english", "expression", 105), "EE105")

    def test_parse_script_id(self):
        cases = [
            ("EE01", ("english", "EXPRESSION", 1)),
            ("FG05", ("french", "GAME", 5)),
            ("SR10", ("spanish", "ROLEPLAY", 10)),
            ("IF15", ("italian", "FUN_FACTS", 15)),
        ]
        for sid, (exp_lang, exp_type, exp_idx) in cases:
            with self.subTest(script_id=sid):
                res = parse_script_id(sid)
                self.assertIsNotNone(res)
                self.assertEqual(res["language"], exp_lang)
                self.assertEqual(res["video_type"], exp_type)
                self.assertEqual(res["index"], exp_idx)

    def test_parse_script_id_invalid(self):
        self.assertIsNone(parse_script_id("INVALID"))
        self.assertIsNone(parse_script_id("1234"))
        self.assertIsNone(parse_script_id(""))


if __name__ == "__main__":
    unittest.main()
