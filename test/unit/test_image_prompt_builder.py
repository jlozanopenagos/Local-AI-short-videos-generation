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

    def test_sanitizer_preserves_late_teen_ages_and_upgrades_younger_ages(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.core.prompt_builder import sanitize_and_style_prompt

        forbidden_negative_leaks = (
            "not a child",
            "no young children",
            "no elementary kids",
            "no childish proportions",
            "no bulging eyes",
            "no deadpan",
        )
        for age in ("16-year-old", "17-year-old", "18-year-old"):
            out = sanitize_and_style_prompt(f"A {age} high-school student boy in a bakery.")
            self.assertIn(age, out)
            self.assertIn("1:7", out)
            self.assertNotIn("NOT a teenager", out)
            out_lower = out.lower()
            for leaked in forbidden_negative_leaks:
                self.assertNotIn(leaked, out_lower)

        for young_age in ("10-year-old kid", "14-year-old", "15-year-old", "14-16-year-old", "fourteen-year-old", "14-16yo"):
            young_out = sanitize_and_style_prompt(f"A {young_age} at a bookshop counter.")
            self.assertNotIn(young_age, young_out)
            self.assertIn("17-year-old", young_out)
            self.assertIn("1:7", young_out)

    def test_sanitizer_upgrades_legacy_negative_tails_idempotently(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.core.prompt_builder import sanitize_and_style_prompt

        legacy_prompt = (
            "Single character solo shot. One 16-year-old high-school student girl with warm tan skin, "
            "mature teenage features (NOT a child). "
            "Clean modern 2D cartoon narrative illustration, stylized 2D animation art style, "
            "vibrant flat colors, bold outlines, expressive high-school student character design "
            "(approx. 14-16 years old, natural balanced teenage proportions, healthy youthful athletic build, mature teenage features, NOT a child). "
            "(high-school student protagonist, stylish venue wardrobe, NO young children, NO elementary kids, NO bulging eyes, NO deadpan blank face)."
        )
        once = sanitize_and_style_prompt(legacy_prompt)
        twice = sanitize_and_style_prompt(once)
        self.assertEqual(once, twice)
        self.assertIn("1:7", once)
        self.assertIn("17-year-old", once)
        self.assertIn("pure text-free visual illustration", once)
        once_lower = once.lower()
        for leaked in ("not a child", "no young children", "no elementary kids", "no bulging eyes", "no deadpan"):
            self.assertNotIn(leaked, once_lower)

    def test_sanitizer_replaces_shortened_tail_without_proportion_anchor(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.core.prompt_builder import sanitize_and_style_prompt

        se01_like = (
            "Vibrant 2D cartoon narrative illustration, 35mm angled waist-up shot. "
            "A 16-year-old high-school student girl in a boutique, bold outlines, vibrant flat colors, "
            "and expressive facial design, pure text-free visual illustration."
        )
        ie01_like = (
            "A wide-angle 35mm waist-up composition. A 16-year-old boy in an opera dressing room. "
            "Clean modern 2D cartoon narrative illustration, vibrant flat colors, bold outlines, "
            "expressive 16-year-old high-school student character design, pure text-free visual illustration."
        )
        for sample in (se01_like, ie01_like):
            once = sanitize_and_style_prompt(sample)
            twice = sanitize_and_style_prompt(once)
            self.assertEqual(once, twice)
            self.assertIn("1:7", once)
            self.assertIn("17-year-old", once)
            self.assertEqual(once.lower().count("pure text-free visual illustration"), 1)

    def test_sanitizer_preserves_reading_lamp_and_alcove(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.core.prompt_builder import sanitize_and_style_prompt

        out = sanitize_and_style_prompt(
            "Inside a Parisian comic bookshop with a vintage brass reading lamp beside a warm yellow reading alcove lamp."
        )
        self.assertIn("brass reading lamp", out)
        self.assertIn("reading alcove lamp", out)
        self.assertNotIn("speaking expressively", out)

    def test_strip_footwear_removes_wearable_shoes_preserves_venues(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.core.prompt_builder import sanitize_and_style_prompt, strip_footwear_clauses

        cropped = (
            "Waist-up 3/4-angled shot of a 17-year-old high-school senior boy wearing a mustard corduroy "
            "overshirt over a patterned shirt, dark straight jeans, and burgundy canvas high-tops."
        )
        out = sanitize_and_style_prompt(cropped, strip_footwear=True)
        self.assertNotIn("high-tops", out.lower())
        self.assertIn("dark straight jeans", out)

        venue = (
            "Inside a chic retro Italian designer sneaker boutique and luxury leather footwear workshop, "
            "three towering designer shoe boxes rest on the counter while a 17-year-old high-school senior girl "
            "wears an olive blazer, dark chinos, and white leather trainers."
        )
        stripped = strip_footwear_clauses(venue)
        self.assertIn("designer sneaker boutique", stripped)
        self.assertIn("luxury leather footwear workshop", stripped)
        self.assertIn("designer shoe boxes", stripped)
        self.assertNotIn("white leather trainers", stripped)

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

    def test_sanitizer_run3_polish_rules(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.core.prompt_builder import sanitize_and_style_prompt

        # 1. Strips echoed rubric headers & General Visual Prompt prefix
        header_out = sanitize_and_style_prompt("HOOK [THE INSIDER GUIDE]: Medium close-up 50mm shot.")
        self.assertFalse(header_out.startswith("HOOK"))
        self.assertIn("Medium close-up 50mm shot", header_out)

        gp_prefix_out = sanitize_and_style_prompt("General Visual Prompt: A vibrant 2D cartoon lounge.")
        self.assertFalse(gp_prefix_out.startswith("General Visual Prompt"))

        # 2. Repairs speaking expressivelyr mid-word truncation and respects word boundaries
        trunc_out = sanitize_and_style_prompt(
            "He is actively speaking expressivelyr, visually demonstrating the acoustic power."
        )
        self.assertNotIn("expressivelyr", trunc_out)
        self.assertIn("speaking expressively,", trunc_out)

        # 3. Scrubs floating word-cards, phonetic symbols, and giant letters
        floating_out = sanitize_and_style_prompt(
            "Oversized, stylized word-cards and phonetic symbols floating in the air alongside oversized, stylized letters (like a giant K and N) and glowing 21 individual letters."
        )
        self.assertNotIn("word-cards", floating_out.lower())
        self.assertNotIn("phonetic symbols", floating_out.lower())
        self.assertNotIn("giant k and n", floating_out.lower())
        self.assertNotIn("individual letters", floating_out.lower())

        # 4. Scrubs colored eyes (blue, emerald green, hazel, brown) into simple black cartoon eyes
        eyes_out = sanitize_and_style_prompt(
            "A 15-year-old girl with warm tan skin and bright emerald green cartoon eyes talks to a 15-year-old boy with fair peach skin and clear blue cartoon eyes."
        )
        self.assertNotIn("emerald green", eyes_out.lower())
        self.assertNotIn("clear blue cartoon eyes", eyes_out.lower())
        self.assertIn("simple black cartoon eyes", eyes_out.lower())


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

    def test_roleplay_solo_dialogue_uses_angled_waist_up_framing(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.types import get_visual_profile

        prof = get_visual_profile("roleplay")
        task = prof.build_storyboard_director_task("girl", "boy")
        grammar = prof.build_storyboard_system_grammar()

        for blob in (task, grammar):
            blob_low = blob.lower()
            self.assertNotIn("chest-up tight framing", blob_low)
            self.assertNotIn("85mm portrait lens", blob_low)
            self.assertIn("3/4", blob_low)
            self.assertIn("waist-up", blob_low)
            self.assertIn("off-camera", blob_low)

        for part in ("dialogue_part_1", "dialogue_part_2"):
            goal = prof.build_single_scene_goal(part, "girl", "boy")
            goal_low = goal.lower()
            self.assertNotIn("chest-up", goal_low)
            self.assertNotIn("85mm portrait lens", goal_low)
            self.assertIn("3/4", goal_low)
            self.assertIn("waist-up", goal_low)
            self.assertIn("off-camera", goal_low)
            self.assertIn("gesture", goal_low)

    def test_cropped_hook_prompts_for_game_expression_and_fun_facts(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.types import get_visual_profile

        forbidden = (
            "14-16yo",
            "14-16-year-old",
            "not a child",
            "never wide bug eyes",
            "never bulging eyes",
            "never staring rounded eyes",
        )
        for vtype in ("game", "expression", "fun_facts"):
            prof = get_visual_profile(vtype)
            blobs = (
                prof.build_storyboard_system_grammar(),
                prof.build_storyboard_director_task("girl", "boy"),
                prof.build_single_scene_goal("hook", "girl", "boy"),
            )
            for blob in blobs:
                low = blob.lower()
                self.assertTrue("waist-up" in low or "mid-thigh" in low, f"{vtype} hook missing cropped framing")
                self.assertIn("17-year-old", low)
                self.assertIn("1:7", low)
                for bad in forbidden:
                    self.assertNotIn(bad, low, f"{vtype} still contains '{bad}'")


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
        # pyrefly: ignore[missing-import]
        from core.gemini_auditor import get_video_type_directive
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.types import get_visual_profile

        for vtype in ("game", "fun_facts", "expression", "roleplay"):
            prof = get_visual_profile(vtype)
            self.assertEqual(get_video_type_directive(vtype), prof.build_general_prompt_archetype_directive())
            self.assertTrue(prof.general_prompt_camera_opener.endswith("."))


class TestStructuredCharacterCast(unittest.TestCase):
    def test_game_and_fun_facts_stay_solo_even_if_prompt_mentions_friend(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.common import build_character_cast

        gp = "Medium shot. A 15-year-old high-school student boy in a bakery thinking about a gift for his friend."
        cast_game = build_character_cast(gp, speakers_gender={"NARRATOR": "male"}, video_type="GAME")
        self.assertFalse(cast_game.has_two_characters)
        cast_ff = build_character_cast(gp, speakers_gender={"NARRATOR": "male"}, video_type="FUN_FACTS")
        self.assertFalse(cast_ff.has_two_characters)
        cast_rp = build_character_cast(gp, speakers_gender={}, video_type="ROLEPLAY")
        self.assertTrue(cast_rp.has_two_characters)

    def test_centralized_default_speakers_gender(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.common import resolve_default_speakers_gender

        rp_defaults = resolve_default_speakers_gender({}, video_type="ROLEPLAY")
        self.assertEqual(rp_defaults["PERSON_ONE"], "male")
        self.assertEqual(rp_defaults["PERSON_TWO"], "female")

        rp_f_first = resolve_default_speakers_gender({"PERSON_ONE": "female"}, video_type="ROLEPLAY")
        self.assertEqual(rp_f_first["PERSON_ONE"], "female")
        self.assertEqual(rp_f_first["PERSON_TWO"], "male")

    def test_persist_character_anchors_in_state(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.common import persist_character_anchors_in_state

        state = {"id": "EE01", "assets": {}, "content_metadata": {}}
        gp = "A 15-year-old high-school student girl with dark hair in a ponytail wearing an emerald blazer."
        anchors = persist_character_anchors_in_state(state, gp, {"NARRATOR": "female"}, "EXPRESSION")
        self.assertEqual(anchors["gender_word1"], "girl")
        self.assertEqual(state["assets"]["character_anchors"], anchors)
        self.assertEqual(state["content_metadata"]["character_anchors"], anchors)

    def test_shirt_with_sleeves_or_scarf_is_not_scrubbed_into_thematic_decor(self):
        # pyrefly: ignore[missing-import]
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
        # pyrefly: ignore[missing-import]
        from _C_image_generation.core.prompt_builder import sanitize_and_style_prompt

        s = sanitize_and_style_prompt("One high school student boy with dark hair in a sleek ponytail wearing a navy polo shirt.")
        self.assertNotIn("ponytail", s.lower())
        self.assertIn("short textured dark hair", s.lower())

    def test_character_cast_splits_beside_her_and_aligns_with_speakers_gender(self):
        # pyrefly: ignore[missing-import]
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

    def test_character_cast_ignores_characterized_and_two_characters_staging_sentences(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.common import build_character_cast

        gp_fr01 = (
            "A vibrant 2D cartoon illustration set in a Parisian bistro. "
            "A dynamic diagonal trajectory is established across the edge of the table, separating the two characters. "
            "On the left, a 14-16-year-old high-school girl with warm tan skin and dark wavy hair tied in an elegant ponytail wears a tailored linen shirt. "
            "On the right, a 14-16-year-old high-school boy with fair peach skin and short textured chestnut-brown hair with clean-cut sideburns stands facing left."
        )
        cast = build_character_cast(
            gp_fr01,
            speakers_gender={"PERSON_ONE": "female", "PERSON_TWO": "male"},
            video_type="ROLEPLAY",
        )
        self.assertTrue(cast.p1_is_female)
        self.assertFalse(cast.p2_is_female)
        self.assertEqual(cast.gender_word1, "girl")
        self.assertEqual(cast.gender_word2, "boy")
        self.assertIn("high-school girl", cast.char1_desc)
        self.assertIn("high-school boy", cast.char2_desc)
        self.assertNotIn("diagonal trajectory", cast.char1_desc)

        gp_sr01 = (
            "The setting is an opulent chic metropolitan haute-couture boutique, characterized by polished white marble flooring. "
            "On the left side of the frame stands a 15-year-old high-school student girl with warm tan skin. "
            "On the right side of the frame is a 15-year-old high-school student boy with fair peach skin."
        )
        cast_sr = build_character_cast(
            gp_sr01,
            speakers_gender={"PERSON_ONE": "female", "PERSON_TWO": "male"},
            video_type="ROLEPLAY",
        )
        self.assertNotIn("characterized by", cast_sr.char1_desc)
        self.assertIn("student girl", cast_sr.char1_desc)
        self.assertIn("student boy", cast_sr.char2_desc)


class TestCulturalWorldAtlas(unittest.TestCase):
    def test_all_languages_have_rich_text_free_cultural_worlds_and_global_diversity(self):
        import re
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.languages import ALL_LANGUAGE_PROFILES

        banned_cliches = ("creative studio", "study lounge", "design atelier", "workshop", "greenhouse", "conservatory")
        forbidden_leaks = ("85mm", "24mm", "fourth-wall", "roleplay", "dialogue_part", "chalkboard")

        for prof in ALL_LANGUAGE_PROFILES:
            worlds = prof.cultural_worlds
            self.assertGreaterEqual(len(worlds), 26, f"{prof.language} should have >=26 CulturalWorlds")
            ids = [w.id for w in worlds]
            self.assertEqual(len(ids), len(set(ids)), f"Duplicate CulturalWorld id in {prof.language}")
            monumental_count = sum(1 for w in worlds if "monumental" in w.staging_tags)
            self.assertGreaterEqual(monumental_count, 8, f"{prof.language} needs monumental worlds for FUN_FACTS")

            for w in worlds:
                blob = f"{w.title} {w.setting_prompt} {' '.join(w.focal_props)} {w.wardrobe_cue}".lower()
                for cliche in banned_cliches:
                    self.assertNotIn(cliche, blob, f"{w.id} contains cliché '{cliche}'")
                for leak in forbidden_leaks:
                    self.assertNotIn(leak, blob, f"{w.id} leaked camera/type token '{leak}'")
                self.assertFalse(re.search(r"\b(sign reading|text|words|menus|lettering|price tag)\b", blob), f"{w.id} mentions text surface")

        # Verify regional expansion requested for Spanish (Spain + LatAm) and English (global Anglophone)
        es_prof = next(p for p in ALL_LANGUAGE_PROFILES if p.language == "spanish")
        es_regions = " ".join(w.region for w in es_prof.cultural_worlds)
        for country in ("Spain", "Mexico", "Argentina", "Colombia", "Peru", "Chile", "Cuba", "Guatemala", "Uruguay"):
            self.assertIn(country, es_regions, f"Spanish Atlas missing {country}")

        en_prof = next(p for p in ALL_LANGUAGE_PROFILES if p.language == "english")
        en_regions = " ".join(w.region for w in en_prof.cultural_worlds)
        for nation in ("England", "Scotland", "Wales", "Ireland", "USA", "Canada", "Australia", "New Zealand", "Jamaica", "South Africa", "Singapore"):
            self.assertIn(nation, en_regions, f"English Atlas missing {nation}")

    def test_multilingual_explicit_matching_and_no_studio_fallback(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.common import resolve_anchor_environment, resolve_cultural_world

        fr_thrifter = resolve_cultural_world("Dans cette friperie du Marais...", topic="Acheter une veste", language="French", script_id="FE90")
        self.assertEqual(fr_thrifter.id, "fr_marais_friperie")

        it_gelato = resolve_cultural_world("Vorrei un cono al pistacchio in gelateria.", topic="Ordinare un gelato", language="Italian", script_id="IR90")
        self.assertEqual(it_gelato.id, "it_trastevere_gelateria")

        es_tapas = resolve_cultural_world("Vamos a una tapería en Sevilla.", topic="Pedir tapas", language="Spanish", script_id="SE90")
        self.assertEqual(es_tapas.id, "es_triana_taperia")

        abstract_it = resolve_anchor_environment(
            script_text="La differenza tra sapere e conoscere in italiano.",
            topic="Sapere vs Conoscere",
            lexical_field="Grammatica pratica",
            language="Italian",
            video_type="EXPRESSION",
            script_id="IE05",
        )
        self.assertNotIn("creative studio", abstract_it.lower())
        self.assertNotIn("study lounge", abstract_it.lower())

    def test_triplet_diversity_fun_facts_landmark_and_exclusion(self):
        # pyrefly: ignore[missing-import]
        from _C_image_generation.visual.common import resolve_cultural_world

        for lang_char, lang_name in (("E", "English"), ("F", "French"), ("I", "Italian"), ("S", "Spanish")):
            e_w = resolve_cultural_world("Grammar nuance lesson.", topic="Grammar check", lexical_field="Grammar", language=lang_name, video_type="EXPRESSION", script_id=f"{lang_char}E04")
            g_w = resolve_cultural_world("Grammar quiz challenge.", topic="Grammar check", lexical_field="Grammar", language=lang_name, video_type="GAME", script_id=f"{lang_char}G04")
            r_w = resolve_cultural_world("Two students talk.", topic="Grammar check", lexical_field="Grammar", language=lang_name, video_type="ROLEPLAY", script_id=f"{lang_char}R04")
            f_w = resolve_cultural_world("Wait till you hear why!", topic="Origin story", lexical_field="History", language=lang_name, video_type="FUN_FACTS", script_id=f"{lang_char}F04")
            self.assertEqual(len({e_w.id, g_w.id, r_w.id}), 3, f"Triplet collision in {lang_name}: {e_w.id}, {g_w.id}, {r_w.id}")
            self.assertIn("monumental", f_w.staging_tags, f"FUN_FACTS {lang_name} should use monumental world, got {f_w.id}")

            # Anti-repetition across 15 sequential scripts
            seq_ids = {
                resolve_cultural_world("Abstract practice.", topic=f"Topic {i}", lexical_field="Vocabulary", language=lang_name, video_type="EXPRESSION", script_id=f"{lang_char}E{i:02d}").id
                for i in range(1, 16)
            }
            self.assertGreaterEqual(len(seq_ids), 10, f"Low variety in sequential {lang_name} IDs: {len(seq_ids)}")

            # Exclusion switches venue cleanly
            rerolled = resolve_cultural_world("Grammar nuance lesson.", topic="Grammar check", lexical_field="Grammar", language=lang_name, video_type="EXPRESSION", script_id=f"{lang_char}E04", exclude_world_ids=[e_w.id])
            self.assertNotEqual(rerolled.id, e_w.id)


class TestScriptVisualContracts(unittest.TestCase):
    REFERENCE_IDS = {"EE01", "FG01", "IR01", "SF01"}

    def _check(self, script_id):
        expected = _load(f"{script_id}.json")
        got = H.condense(H.capture_script(H.load_state(script_id)), {})
        for branch in ("outputs", "outputs_no_gp"):
            self.assertTrue(got[branch]["general_prompt"].strip(), script_id)
            prompts = got[branch]["image_prompts"]
            self.assertEqual(set(prompts), set(expected[branch]["image_prompts"]), script_id)
            self.assertTrue(all(prompt.strip() for prompt in prompts.values()), script_id)
        self.assertEqual(
            got["outputs"]["anchor_environment"], got["outputs"]["general_prompt"],
            f"{script_id}: visual anchor lost between stages",
        )

        if script_id in self.REFERENCE_IDS:
            for key in ("calls", "calls_no_gp", "outputs", "outputs_no_gp"):
                self.assertEqual(got[key], expected[key], f"{script_id}: reviewed snapshot changed")


def _make(script_id):
    def test(self):
        self._check(script_id)
    return test


for _sid in H.GOLDEN_IDS:
    setattr(TestScriptVisualContracts, f"test_golden_{_sid}", _make(_sid))


if __name__ == "__main__":
    unittest.main()
