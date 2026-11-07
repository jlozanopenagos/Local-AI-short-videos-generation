"""
test_layer/unit/test_state_manager.py — Unit tests for StateManager and canonical ID resolution.
"""
import json
import unittest
import tempfile
from pathlib import Path

# pyrefly: ignore [missing-import]
from core.state_manager import StateManager, resolve_lang_and_type, LANG_MAP, TYPE_MAP
# pyrefly: ignore [missing-import]
from video_creation._A_video_scripts.id_generator import (
    get_language_code,
    get_type_code,
    generate_script_id,
    parse_script_id,
)


class TestStateManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.mgr = StateManager(self.base_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_resolve_lang_and_type_from_canonical_id(self):
        cases = [
            ("EE01", ("english", "expression")),
            ("EG15", ("english", "game")),
            ("ER02", ("english", "roleplay")),
            ("EF05", ("english", "fun_facts")),
            ("FE01", ("french", "expression")),
            ("FG10", ("french", "game")),
            ("FR03", ("french", "roleplay")),
            ("FF01", ("french", "fun_facts")),
            ("SE01", ("spanish", "expression")),
            ("SG02", ("spanish", "game")),
            ("SR04", ("spanish", "roleplay")),
            ("SF08", ("spanish", "fun_facts")),
            ("IE01", ("italian", "expression")),
            ("IG02", ("italian", "game")),
            ("IR09", ("italian", "roleplay")),
            ("IF12", ("italian", "fun_facts")),
        ]
        for sid, expected in cases:
            with self.subTest(script_id=sid):
                result = resolve_lang_and_type(sid)
                self.assertEqual(result, expected)

    def test_resolve_lang_and_type_from_state_fallback(self):
        state = {
            "prompt_params": {
                "TARGET_LANGUAGE": "French | Français",
                "VIDEO_TYPE": "ROLEPLAY"
            }
        }
        lang, vtype = resolve_lang_and_type("CUSTOM_ID", state)
        self.assertEqual(lang, "french")
        self.assertEqual(vtype, "roleplay")

    def test_get_script_state_default_when_missing(self):
        state = self.mgr.get_script_state("EE99")
        self.assertEqual(state["id"], "EE99")
        self.assertIn("status", state)
        for stage in [
            "script_generation",
            "voice_generation",
            "image_generation",
            "thumbnail_generation",
            "video_assembly"
        ]:
            self.assertEqual(state["status"][stage], "pending")

    def test_save_and_retrieve_script_state(self):
        script_id = "EE01"
        data = {
            "id": script_id,
            "status": {
                "script_generation": "done",
                "voice_generation": "pending",
                "image_generation": "pending",
                "thumbnail_generation": "pending",
                "video_assembly": "pending"
            },
            "script_text": "Sample script content",
            "content_metadata": {
                "title": "Test Title"
            }
        }
        self.mgr.save_script_state(script_id, data)
        self.assertTrue(self.mgr.script_exists(script_id))

        retrieved = self.mgr.get_script_state(script_id)
        self.assertEqual(retrieved["id"], script_id)
        self.assertEqual(retrieved["status"]["script_generation"], "done")
        self.assertEqual(retrieved["script_text"], "Sample script content")

        # Verify correct directory partitioning: state/english/expression/script_EE01.json
        expected_path = self.base_dir / "state" / "english" / "expression" / "script_EE01.json"
        self.assertTrue(expected_path.exists())

    def test_get_all_scripts_deduplication(self):
        # Save two distinct scripts
        self.mgr.save_script_state("EE01", {"id": "EE01", "status": {}})
        self.mgr.save_script_state("FE01", {"id": "FE01", "status": {}})

        scripts = self.mgr.get_all_scripts()
        ids = [s.get("id") for s in scripts]
        self.assertIn("EE01", ids)
        self.assertIn("FE01", ids)
        self.assertEqual(len(scripts), 2)


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
