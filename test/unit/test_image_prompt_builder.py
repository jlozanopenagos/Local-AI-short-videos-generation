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

    def test_sanitizer_is_idempotent(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.core.prompt_builder import sanitize_and_style_prompt

        for probe in H.SANITIZER_PROBES:
            once = sanitize_and_style_prompt(probe)
            self.assertEqual(sanitize_and_style_prompt(once), once, probe)

    def test_sanitizer_preserves_14_to_16_teen_ages_and_upgrades_child_ages(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.core.prompt_builder import sanitize_and_style_prompt

        for age in ("14-year-old", "15-year-old", "16-year-old", "14-16-year-old"):
            out = sanitize_and_style_prompt(f"A {age} high-school student boy in a bakery.")
            self.assertIn(age, out)
            self.assertIn("NOT a child", out)
            self.assertNotIn("NOT a teenager", out)
        child_out = sanitize_and_style_prompt("A 10-year-old kid at a desk.")
        self.assertNotIn("10-year-old", child_out)
        self.assertIn("15-year-old", child_out)

    def test_gift_box_exception_only_for_present_heteronym(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.core.prompt_builder import sanitize_and_style_prompt, is_present_heteronym_topic

        raw = "A student reveals an ornate ribbon-wrapped gift box on the banquet table."
        scrubbed = sanitize_and_style_prompt(raw, allow_gift_box=False)
        preserved = sanitize_and_style_prompt(raw, allow_gift_box=True)
        self.assertNotIn("gift box", scrubbed.lower())
        self.assertIn("gift box", preserved.lower())
        self.assertTrue(is_present_heteronym_topic(topic="PREsent vs preSENT"))
        self.assertFalse(is_present_heteronym_topic(topic="break a leg"))


class TestEnvironmentSnapshots(unittest.TestCase):
    def test_environment_resolution_unchanged(self):
        self.assertEqual(H.capture_environment_cases(), _load("_environment.json"))


class TestVisualProfileRegistry(unittest.TestCase):
    def test_registry_resolves_names_codes_and_script_ids(self):
        # pyrefly: ignore[missing-import]
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
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.types import get_visual_profile

        with mock.patch.dict(os.environ, {"IMAGE_PROMPT_ENGINE": "legacy"}):
            self.assertIsNone(get_visual_profile("game"))
            self.assertIsNone(get_visual_profile("roleplay"))
        with mock.patch.dict(os.environ, {"IMAGE_PROMPT_ENGINE": "legacy:roleplay"}):
            self.assertIsNone(get_visual_profile("ROLEPLAY"))
            self.assertIsNotNone(get_visual_profile("GAME"))

    def test_type_pure_storyboard_system_prompt_has_no_cross_type_leakage(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.common import build_storyboard_system_prompt
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.types import get_visual_profile

        type_headers = {
            "game": "FOR GAME SHORTS",
            "fun_facts": "FOR FUN_FACTS SHORTS",
            "expression": "FOR EXPRESSION SHORTS",
            "roleplay": "FOR ROLEPLAY SHORTS",
        }
        for vtype, expected_header in type_headers.items():
            prof = get_visual_profile(vtype)
            sys_prompt = build_storyboard_system_prompt(prof.build_storyboard_system_grammar())
            self.assertIn(expected_header, sys_prompt)
            for other_type, other_header in type_headers.items():
                if other_type != vtype:
                    self.assertNotIn(
                        other_header,
                        sys_prompt,
                        f"{vtype} storyboard system prompt leaked {other_header}",
                    )
            self.assertNotIn("tall slender", sys_prompt.lower())

    def test_fun_facts_has_complete_5_scene_camera_grammar(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.types import get_visual_profile

        prof = get_visual_profile("fun_facts")
        task = prof.build_storyboard_director_task("girl", "boy")
        for beat in ("HOOK [THE SCALE OF WONDER]", "SETUP [THE CURIOUS CLUE]", "DISCOVERY [THE HIDDEN MECHANISM REVEAL]", "EXPLANATION [LIVING CULTURAL CONTEXT]", "PAYOFF [MIND-BLOWN MASTERY]"):
            self.assertIn(beat, task)
        for scene_name in ("hook", "setup", "discovery", "explanation", "payoff"):
            goal = prof.build_single_scene_goal(scene_name, "girl", "boy")
            self.assertIn(scene_name.upper(), goal)


class TestLanguageVisualLayer(unittest.TestCase):
    def test_language_registry_resolves_names_labels_and_script_ids(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.languages import get_language_profile

        self.assertEqual(get_language_profile("English").language, "english")
        self.assertEqual(get_language_profile("French | work | greetings").language, "french")
        self.assertEqual(get_language_profile("français").language, "french")
        self.assertEqual(get_language_profile("Spanish").language, "spanish")
        self.assertEqual(get_language_profile("español").language, "spanish")
        self.assertEqual(get_language_profile("Italian").language, "italian")
        self.assertEqual(get_language_profile("FE01").language, "french")
        self.assertEqual(get_language_profile("SR01").language, "spanish")
        self.assertEqual(get_language_profile("IG02").language, "italian")
        self.assertEqual(get_language_profile("EE01").language, "english")

    def test_language_profiles_do_not_contain_camera_angle_or_video_type_directives(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.languages import ALL_LANGUAGE_PROFILES

        forbidden = ("85mm", "24mm", "fourth-wall", "roleplay", "dialogue_part", "chalkboard")
        for prof in ALL_LANGUAGE_PROFILES:
            blob = f"{prof.palette_mood} {prof.cultural_cue}".lower()
            for term in forbidden:
                self.assertNotIn(term, blob, f"Language profile {prof.language} leaked type/camera term '{term}'")

    def test_both_general_prompt_producers_read_from_visual_profile(self):
        from core.gemini_auditor import get_video_type_directive
        from _C_image_generation.visual.types import get_visual_profile

        for vtype in ("game", "fun_facts", "expression", "roleplay"):
            prof = get_visual_profile(vtype)
            self.assertEqual(get_video_type_directive(vtype), prof.build_general_prompt_archetype_directive())
            self.assertTrue(prof.general_prompt_camera_opener.endswith("."))


class TestStructuredCharacterCast(unittest.TestCase):
    def test_game_and_fun_facts_stay_solo_even_if_prompt_mentions_friend(self):
        from _C_image_generation.visual.common import build_character_cast

        gp = "Medium shot. A 15-year-old high-school student boy in a bakery thinking about a gift for his friend."
        cast_game = build_character_cast(gp, speakers_gender={"NARRATOR": "male"}, video_type="GAME")
        self.assertFalse(cast_game.has_two_characters)
        cast_ff = build_character_cast(gp, speakers_gender={"NARRATOR": "male"}, video_type="FUN_FACTS")
        self.assertFalse(cast_ff.has_two_characters)
        cast_rp = build_character_cast(gp, speakers_gender={}, video_type="ROLEPLAY")
        self.assertTrue(cast_rp.has_two_characters)

    def test_centralized_default_speakers_gender(self):
        from _C_image_generation.visual.common import resolve_default_speakers_gender

        rp_defaults = resolve_default_speakers_gender({}, video_type="ROLEPLAY")
        self.assertEqual(rp_defaults["PERSON_ONE"], "male")
        self.assertEqual(rp_defaults["PERSON_TWO"], "female")

        rp_f_first = resolve_default_speakers_gender({"PERSON_ONE": "female"}, video_type="ROLEPLAY")
        self.assertEqual(rp_f_first["PERSON_ONE"], "female")
        self.assertEqual(rp_f_first["PERSON_TWO"], "male")

    def test_persist_character_anchors_in_state(self):
        from _C_image_generation.visual.common import persist_character_anchors_in_state

        state = {"id": "EE01", "assets": {}, "content_metadata": {}}
        gp = "A 15-year-old high-school student girl with dark hair in a ponytail wearing an emerald blazer."
        anchors = persist_character_anchors_in_state(state, gp, {"NARRATOR": "female"}, "EXPRESSION")
        self.assertEqual(anchors["gender_word1"], "girl")
        self.assertEqual(state["assets"]["character_anchors"], anchors)
        self.assertEqual(state["content_metadata"]["character_anchors"], anchors)

    def test_shirt_with_sleeves_or_scarf_is_not_scrubbed_into_thematic_decor(self):
        from _C_image_generation.core.prompt_builder import sanitize_and_style_prompt

        s1 = sanitize_and_style_prompt("A 15-year-old boy wearing a crisp light blue linen button-down shirt with rolled-up sleeves.")
        self.assertIn("shirt with rolled-up sleeves", s1)
        self.assertNotIn("thematic decor", s1)

        s2 = sanitize_and_style_prompt("A 15-year-old girl dressed in a cream-colored linen shirt with a vibrant olive green scarf.")
        self.assertIn("shirt with a vibrant olive green scarf", s2)
        self.assertNotIn("thematic decor", s2)

        s3 = sanitize_and_style_prompt("A 15-year-old boy wearing a t-shirt with the words hello world.")
        self.assertNotIn("hello world", s3)

    def test_male_with_dark_hair_in_a_sleek_ponytail_is_scrubbed(self):
        from _C_image_generation.core.prompt_builder import sanitize_and_style_prompt

        s = sanitize_and_style_prompt("One high school student boy with dark hair in a sleek ponytail wearing a navy polo shirt.")
        self.assertNotIn("ponytail", s.lower())
        self.assertIn("short textured dark hair", s.lower())

    def test_character_cast_splits_beside_her_and_aligns_with_speakers_gender(self):
        from _C_image_generation.visual.common import build_character_cast

        gp = (
            "Medium shot. Inside a theater dressing room, a tall teen boy with short textured dark hair wears an emerald doublet. "
            "Beside him near a rehearsal stage, a teen girl with long wavy auburn hair wears a sapphire Tudor gown."
        )
        # When Narrator/PERSON_ONE is female, c1 and c2 swap so Character 1 is the girl
        cast = build_character_cast(gp, speakers_gender={"Narrator": "female"}, video_type="EXPRESSION")
        self.assertTrue(cast.p1_is_female)
        self.assertIn("sapphire Tudor gown", cast.char1_desc)
        self.assertIn("emerald doublet", cast.char2_desc)


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
