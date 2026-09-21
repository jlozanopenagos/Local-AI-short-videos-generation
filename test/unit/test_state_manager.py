"""
test_layer/unit/test_state_manager.py — Unit tests for StateManager and canonical ID resolution.
"""
import json
import unittest
import tempfile
from pathlib import Path

# pyrefly: ignore [missing-import]
from core.state_manager import StateManager, resolve_lang_and_type, LANG_MAP, TYPE_MAP


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


if __name__ == "__main__":
    unittest.main()
