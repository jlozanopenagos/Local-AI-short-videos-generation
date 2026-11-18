"""
test/unit/test_image_prompt_builder.py — Stage C characterization (golden snapshot) tests.

These tests lock the EXACT text sent to the LLM and the final sanitized prompts for the 16 golden
scripts (4 types x 4 languages) plus sanitizer / environment probes. They run fully offline
(fake LLM client). They guard the Phase 1-2 refactors of the image-prompt workflow: any
difference means behavior changed.

To intentionally accept a behavior change (Phase 3+ only), regenerate with:
    py test/tools/freeze_image_fixtures.py snapshot
"""
import json
import sys
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent.parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

import image_prompt_harness as H  # noqa: E402


def _load(name):
    return json.loads((H.SNAPSHOT_DIR / name).read_text(encoding="utf-8"))


class TestSanitizerSnapshots(unittest.TestCase):
    def test_sanitizer_probes_unchanged(self):
        expected = _load("_sanitizer.json")
        self.assertEqual(H.capture_sanitizer(), expected)

    # NOTE: the sanitizer is intentionally NOT asserted idempotent. Known quirk (plan Q11):
    # a 2nd pass turns "NOT a child" into "NOT a teenager". Production applies it twice, so both
    # the ONCE and TWICE outputs are locked in the snapshot above until Phase 3 decides the fix.


class TestEnvironmentSnapshots(unittest.TestCase):
    def test_environment_resolution_unchanged(self):
        self.assertEqual(H.capture_environment_cases(), _load("_environment.json"))


class TestVisualProfileRegistry(unittest.TestCase):
    def test_registry_resolves_names_codes_and_script_ids(self):
        from _C_image_generation.visual.types import get_visual_profile

        self.assertEqual(get_visual_profile("game").video_type, "game")
        self.assertEqual(get_visual_profile("G").video_type, "game")
        self.assertEqual(get_visual_profile("SG01").video_type, "game")
        self.assertEqual(get_visual_profile("fun_facts").video_type, "fun_facts")
        self.assertEqual(get_visual_profile("FUNFACTS").video_type, "fun_facts")
        self.assertEqual(get_visual_profile("EF01").video_type, "fun_facts")
        self.assertEqual(get_visual_profile("expression").video_type, "expression")
        self.assertEqual(get_visual_profile("FE01").video_type, "expression")
        self.assertEqual(get_visual_profile("roleplay").video_type, "roleplay")
        self.assertEqual(get_visual_profile("IR01").video_type, "roleplay")
        self.assertEqual(len(get_visual_profile("roleplay").get_comfy_scene_names()), 6)
        self.assertEqual(len(get_visual_profile("game").get_comfy_scene_names()), 3)

    def test_legacy_switch_disables_typed_profile(self):
        import os
        from unittest import mock
        from _C_image_generation.visual.types import get_visual_profile

        with mock.patch.dict(os.environ, {"IMAGE_PROMPT_ENGINE": "legacy"}):
            self.assertIsNone(get_visual_profile("game"))
            self.assertIsNone(get_visual_profile("roleplay"))
        with mock.patch.dict(os.environ, {"IMAGE_PROMPT_ENGINE": "legacy:roleplay"}):
            self.assertIsNone(get_visual_profile("ROLEPLAY"))
            self.assertIsNotNone(get_visual_profile("GAME"))


class TestGoldenScriptSnapshots(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.systems = _load("_system_prompts.json")

    def _check(self, script_id):
        expected = _load(f"{script_id}.json")
        got = H.condense(H.capture_script(H.load_state(script_id)), {})
        for key in ("calls", "calls_no_gp"):
            self.assertEqual(len(got[key]), len(expected[key]), f"{script_id} {key}: number of LLM calls changed")
            for i, (g, e) in enumerate(zip(got[key], expected[key])):
                self.assertEqual(g["kind"], e["kind"], f"{script_id} {key}[{i}] kind")
                self.assertEqual(g["system_sha"], e["system_sha"], f"{script_id} {key}[{i}] SYSTEM prompt changed")
                self.assertEqual(g["user"], e["user"], f"{script_id} {key}[{i}] USER prompt changed")
        self.assertEqual(got["outputs"], expected["outputs"], f"{script_id}: final prompts/anchors changed")
        self.assertEqual(got["outputs_no_gp"], expected["outputs_no_gp"], f"{script_id}: no-GP outputs changed")


def _make(script_id):
    def test(self):
        self._check(script_id)
    return test


for _sid in H.GOLDEN_IDS:
    setattr(TestGoldenScriptSnapshots, f"test_golden_{_sid}", _make(_sid))


if __name__ == "__main__":
    unittest.main()
