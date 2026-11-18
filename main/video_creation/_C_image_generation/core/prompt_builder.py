"""
prompt_builder.py — Generates Z-Image-Turbo visual prompts from script data.

The local LLM acts as the visual director:
  1. We supply the full visual-director system prompt (sourced from the workflow's
     positive prompt node) plus the script metadata as user context.
  2. The LLM outputs a single, coherent visual description ready for Z-Image-Turbo.

The visual prompt is written in English (for best model performance) but
must accurately represent the target language's educational context.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional, Dict, Any, Tuple

# pyrefly: ignore [missing-import]
import httpx
# pyrefly: ignore [missing-import]
from openai import OpenAI

logger = logging.getLogger(__name__)


# ── Re-exported common layer (Phase 1 facade) ────────────────────────────────
from ..visual.common import (
    _VISUAL_DIRECTOR_SYSTEM_PROMPT,
    _STORYBOARD_DIRECTOR_SYSTEM_PROMPT,
    build_storyboard_system_prompt,
    _get_language_palette,
    _parse_label,
    HETERONYM_DOMAINS,
    EXPLICIT_SCENARIO_DOMAINS,
    is_figurative_idiom,
    resolve_anchor_environment,
    FEMALE_HAIRSTYLE_TERMS,
    MALE_HAIRSTYLE_TERMS,
    get_speaker_gender_safe,
    sanitize_character_hair,
    _split_sentences_safe,
    _clean_character_clause,
    extract_or_build_character_anchors,
    sanitize_and_style_prompt,
    is_present_heteronym_topic,
    _extract_json_payload,
)
from ..visual.types import get_visual_profile


def _extract_shared_story_context(
    script_text: str,
    language: str,
    label: str,
    speakers_gender: dict = None,
    video_type: str = "EXPRESSION",
    character_personalities: dict = None,
    topic: str = "",
    scenario: str = "",
    lexical_field: str = "",
    anchor_environment: str = "",
    general_prompt: str = "",
    character_anchors: dict = None,
) -> dict[str, Any]:
    """
    Extracts and standardizes shared narrative context across single-scene and multi-scene storyboard builders:
    - Resolves anchor environment
    - Voiceover isolation notice
    - Character personalities
    - Mandatory speaker genders (authoritatively anchored to General Prompt / character anchors)
    - Target language brand palette
    - Metadata topic/scenario/lexical context lines
    - Figurative idiom directive
    """
    video_type_upper = video_type.upper()
    if not anchor_environment:
        anchor_environment = general_prompt or resolve_anchor_environment(
            script_text=script_text,
            topic=topic,
            scenario=scenario,
            lexical_field=lexical_field,
            label=label,
            video_type=video_type,
        )

    voiceover_notice = ""
    personality_context = ""
    if video_type_upper == "ROLEPLAY":
        if character_personalities:
            pers_lines = [f"- {spk}: {pers}" for spk, pers in character_personalities.items() if spk != "Narrator"]
            if pers_lines:
                personality_context = "ACTING CHARACTERS IN SCENE:\n" + "\n".join(pers_lines) + "\n\n"
    else:
        voiceover_notice = (
            "VOICEOVER ISOLATION (MANDATORY):\n"
            "The Narrator is strictly an OFF-SCREEN AUDIO VOICEOVER. Do NOT illustrate a narrator, "
            "host, teacher, mentor, presenter, creator, or lecturer talking to the camera! "
            "Instead, the visual scene MUST depict real everyday human characters actively living out "
            "the authentic real-world situation described in the scene.\n\n"
        )
        if character_personalities:
            acting_chars = [f"- {spk}: {pers}" for spk, pers in character_personalities.items() if spk != "Narrator"]
            if acting_chars:
                personality_context = "ACTING CHARACTERS IN SCENE:\n" + "\n".join(acting_chars) + "\n\n"

    # Authoritative character anchors resolution (General Prompt is single source of truth)
    char_anchors = extract_or_build_character_anchors(
        general_prompt=general_prompt or anchor_environment,
        speakers_gender=speakers_gender,
        video_type=video_type,
        character_anchors=character_anchors,
    )
    p1_is_female = char_anchors.get("p1_is_female", False)
    p2_is_female = char_anchors.get("p2_is_female", not p1_is_female)
    p1_word = char_anchors.get("gender_word1") or ("girl" if p1_is_female else "boy")
    p2_word = char_anchors.get("gender_word2") or ("girl" if p2_is_female else "boy")
    has_two = char_anchors.get("has_two_characters") in (True, "True") or video_type_upper == "ROLEPLAY"

    if has_two:
        p1_desc = f"high school student {p1_word} (approx. 14-16 years old, natural balanced teenage proportions, healthy youthful athletic build, stylish thematic attire)"
        p2_desc = f"high school student {p2_word} (approx. 14-16 years old, natural balanced teenage proportions, healthy youthful athletic build, stylish thematic attire)"
        gender_context = (
            f"MANDATORY CHARACTER GENDERS & DEMOGRAPHIC (HIGH SCHOOL PROTAGONISTS — 14-16 YEARS OLD):\n"
            f"- PERSON_ONE: {p1_word.upper()} (MUST visually appear as a {p1_desc})\n"
            f"- PERSON_TWO: {p2_word.upper()} (MUST visually appear as a {p2_desc})\n"
            f"CRITICAL MULTI-CHARACTER RULE: If MORE THAN ONE character appears in the image, the sex/gender of EACH character MUST be explicitly specified! "
            f"NEVER use generic words like 'the two students', 'two friends', or 'the characters' without stating their individual sex (e.g. 'one high school student {p1_word} and one high school student {p2_word}').\n"
            f"CRITICAL RULE: Characters are 14-16 year old high school students (natural balanced teenage proportions, NOT childish proportions) dressed appropriately for this specific setting. Strictly ban generic plain t-shirts/hoodies, and strictly ban middle-aged/mature adult wrinkles!\n\n"
        )
    else:
        gender_word = p1_word
        gender_desc = f"high school student {gender_word}"
        gender_context = (
            f"MANDATORY CHARACTER DEMOGRAPHIC & THEMATIC WARDROBE (14-16 YEARS OLD):\n"
            f"- PROTAGONIST: MUST visually appear as an expressive high school student {gender_word.upper()} (approx. 14-16 years old {gender_desc}, natural balanced teenage proportions, healthy youthful athletic build, NOT a child).\n"
            f"- WARDROBE: The {gender_word} MUST wear an authentic costume or attire explicitly matching the thematic setting (e.g. theater stage costume/vest, chef uniform, studio apron, lab coat). Strictly ban generic casual clothes (plain t-shirts/hoodies)!\n"
            f"CRITICAL MULTI-CHARACTER RULE: If MORE THAN ONE character appears in the image, the sex/gender of EACH character MUST be explicitly specified! NEVER use generic words like 'two students' or 'friends'!\n"
            f"CRITICAL RULE: Character MUST be a {gender_word.upper()} ({gender_desc}). Strictly ban mature adult faces, wrinkles, childish proportions, and generic t-shirts!\n\n"
        )

    palette_context = _get_language_palette(language)

    context_lines = []
    if topic:
        context_lines.append(f"TOPIC / TARGET PHRASE: {topic}")
    if scenario:
        context_lines.append(f"SCENARIO / REAL-WORLD SETTING: {scenario}")
    if lexical_field:
        context_lines.append(f"LEXICAL FIELD: {lexical_field}")
    context_extra = "\n".join(context_lines) + "\n\n" if context_lines else ""

    idiom_rule = ""
    if is_figurative_idiom(topic, lexical_field, scenario, script_text):
        idiom_rule = (
            "CREATIVE VISUAL METAPHOR & GRAPHIC WORDPLAY DIRECTIVE:\n"
            f"This Short is about an idiom / figurative phrase ('{topic}').\n"
            "- Play with the graphic, visual sense of the expression across the scenes! Use the literal or visual imagery playfully to make the scenes entertaining and magnetic (e.g. giant towering multi-tiered cakes, dramatic theatrical props, colorful spilled jars, vintage travel luggage, hourglass timers, botanical planters).\n"
            "- AVOID BORING IMAGES: Never just show someone staring at a desk or paper looking stressed. Make the visual world lively, imaginative, and fun!\n"
            "- STRICT PROP RELEVANCE (ANTI-GIFT-BOX BAN): Ground props strictly in the environment and actual subject. NEVER use generic gift boxes, ribbon-wrapped packages, or mystery boxes as fallback props!\n\n"
        )

    return {
        "anchor_environment": anchor_environment,
        "voiceover_notice": voiceover_notice,
        "personality_context": personality_context,
        "gender_context": gender_context,
        "palette_context": palette_context,
        "context_extra": context_extra,
        "idiom_rule": idiom_rule,
        "char_anchors": char_anchors,
    }


def _build_user_context(
    script_text: str,
    language: str,
    subject: str,
    situation: str,
    label: str,
    scene_name: str,
    scene_text: str,
    speakers_gender: dict = None,
    video_type: str = "EXPRESSION",
    character_personalities: dict = None,
    topic: str = "",
    scenario: str = "",
    lexical_field: str = "",
    anchor_environment: str = "",
    existing_scene_prompts: dict = None,
    general_prompt: str = "",
) -> str:
    """Build the user-facing context block sent alongside the system prompt."""
    scene_lower = scene_name.lower().strip()
    video_type_upper = video_type.upper()

    ctx = _extract_shared_story_context(
        script_text=script_text,
        language=language,
        label=label,
        speakers_gender=speakers_gender,
        video_type=video_type,
        character_personalities=character_personalities,
        topic=topic,
        scenario=scenario,
        lexical_field=lexical_field,
        anchor_environment=anchor_environment,
        general_prompt=general_prompt,
    )
    anchor_environment = ctx["anchor_environment"]
    char_anchors = ctx.get("char_anchors", {})
    p1_word = char_anchors.get("gender_word1") or ("girl" if char_anchors.get("p1_is_female") else "boy")
    p2_word = char_anchors.get("gender_word2") or ("girl" if char_anchors.get("p2_is_female") else "boy")
    p1_g = p1_word.upper()
    p2_g = p2_word.upper()

    # ── Video-Type Specific Situational Directions ───────────────────────────
    profile = get_visual_profile(video_type_upper)
    if profile is not None:
        text_rule = profile.build_single_scene_goal(scene_lower, p1_word, p2_word)
    elif video_type_upper == "GAME":
        if scene_lower == "hook":
            text_rule = (
                "SCENE GOAL — HOOK (THE FRONTAL DILEMMA):\n"
                "1. CAMERA & STAGING: Front-facing, centered medium eye-level shot under an intense overhead spotlight beam with clean vertical symmetry. Solo 16yo student protagonist has a natural healthy athletic build and is centered, weighing two choices with engaging personality (solo character, no companion in hook).\n"
                "2. FOURTH-WALL GAZE: 100% DIRECT FOURTH-WALL EYE CONTACT WITH THE CAMERA LENS! The protagonist looks straight into the camera at the viewer, breaking the fourth wall to confront the audience with the quiz dilemma!\n"
                "3. EXPRESSIVE ACTING: Lively animated dilemma face with an amused raised eyebrow, slight thinking dilemma smirk, head tilted inquisitively, and warm expressive cartoon eyes full of life and spark (NEVER wide bug eyes, NEVER unexpressive deadpan stare).\n"
                "4. Relatable, lively real-life environment matching the locked anchor setting. Do NOT place them in a school, classroom, or generic cafe.\n"
                "5. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict chalkboards, whiteboards, screens, tablets, smartphones showing text/options, quiz cards, buzzers, podiums, or countdown timers. Focus 100% on the human character dilemma and authentic setting."
            )
        elif scene_lower == "answer":
            text_rule = (
                "SCENE GOAL — ANSWER (THE ASYMMETRICAL BREAKTHROUGH):\n"
                "1. CAMERA & STAGING: Dynamic 3/4 asymmetrical medium action shot with forward kinetic momentum. The character breaks free from the dilemma with radiant eureka relief, joyful smile, and forward momentum in the authentic setting!\n"
                "2. The character visibly displays confident triumph, a joyful smile, or a thumbs-up gesture, joyfully holding or gesturing toward the correct choice.\n"
                "3. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict success screens, monitors, scoreboards, chalkboards, or digital displays. Focus 100% on the human emotional celebration."
            )
        elif scene_lower == "explanation":
            text_rule = (
                "SCENE GOAL — EXPLANATION (REAL-WORLD APPLICATION):\n"
                "1. CAMERA & STAGING: Real-world narrative medium-wide shot (35mm wide lens) showing native speakers naturally and smoothly using the target expression in the authentic real-world setting.\n"
                "2. FOURTH-WALL GAZE: STRICTLY 0% EYE CONTACT WITH THE CAMERA! 100% in-scene narrative immersion (looking at the environment, peers, or task).\n"
                "3. Natural body language, warm communicative atmosphere, and engaging social interaction demonstrating practical usage.\n"
                "4. ZERO-TOLERANCE TEXT & SCREEN BAN: NO text, NO chalkboards, NO screens, NO tablets, NO signs anywhere in the image."
            )
        else:
            text_rule = (
                "SCENE GOAL — 2D CARTOON SCENE:\n"
                "1. Illustrate the real-life situation cleanly and expressively in modern 2D cartoon animation style.\n"
                "2. ZERO-TOLERANCE TEXT & SCREEN BAN: NO text, NO chalkboards, NO screens, NO UI. Focus 100% on characters, environment, and visual storytelling."
            )

    elif video_type_upper in ["FUN_FACTS", "FUNFACTS", "FUNFACT"]:
        text_rule = (
            "SCENE GOAL — FUN_FACTS (THE SCALE OF WONDER):\n"
            "1. CAMERA & STAGING: Dramatic low-angle heroic 24mm wide shot looking up from low elevation. The 15yo student protagonist is framed in the lower third, tilting their head upward in jaw-dropped awe at an imposing, towering cultural anomaly, ancient clockwork, or historic marvel.\n"
            "2. FOURTH-WALL GAZE: The character does NOT look at the camera; their eyes are locked upward on the central wonder/artifact in fascination.\n"
            "3. LIGHTING: Volumetric lighting shafts or golden hour beams cutting through atmospheric haze, creating monumental scale contrast.\n"
            "4. Visually depict the authentic historical era, cultural setting, or physical origin of the phrase or fact.\n"
            "5. TEXT IS STRICTLY BANNED: NO words, letters, signs, chalkboards, or whiteboards."
        )

    elif video_type_upper == "ROLEPLAY":
        shot_direction = ""
        if scene_lower == "hook":
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — SCENARIO THRESHOLD TWO-SHOT (35mm LENS): "
                f"Dynamic 3/4 over-the-shoulder (OTS) diagonal shot crossing a physical threshold (archway, curtain edge, counter, or doorway). "
                f"Both characters are visible in frame with explicit genders (PERSON_ONE as {p1_g}, PERSON_TWO as {p2_g}). "
                f"STRICTLY ZERO FOURTH-WALL EYE CONTACT: Characters lock eyes exclusively with each other in pre-performance tension. "
                f"Directional side-key lighting, dramatic chiaroscuro shadows across the authentic setting."
            )
        elif scene_lower in ["dialogue_part_1", "part_1"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — SOLO MEDIUM CLOSE-UP ON PERSON_ONE (85mm PORTRAIT LENS): "
                f"Single-character solo medium close-up shot focused ENTIRELY on PERSON_ONE ({p1_g}). "
                f"Dramatic key lighting, shallow depth of field with softly blurred background. "
                f"Highlighting their intense facial acting, nervous or questioning body language, and opening dilemma. "
                f"PERSON_TWO is strictly off-camera / NOT visible in this frame."
            )
        elif scene_lower in ["dialogue_part_2", "part_2"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — SOLO 180° REVERSE-ANGLE ON PERSON_TWO (85mm PORTRAIT LENS): "
                f"Dramatic 180° reverse-angle camera switch! Single-character solo medium close-up focused ENTIRELY on PERSON_TWO ({p2_g}). "
                f"Warm fill light, shallow depth of field. Highlighting their calm, confident, reassuring facial expression, "
                f"smirking or gesturing smoothly as they mentor and articulate the explanation. "
                f"PERSON_ONE is strictly off-camera / NOT visible in this frame."
            )
        elif scene_lower in ["dialogue_part_3", "part_3"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — 90° SIDE PROFILE / TOP-DOWN TWO-SHOT PROP INTERACTION (50mm LENS): "
                f"Camera shifts 90° to a dynamic side profile or high-angle table overview! "
                f"Both characters (one {p1_g} and one {p2_g}) are visible actively examining or interacting with an authentic physical prop "
                f"(pointing to details, examining an item, interacting with objects on table/counter). "
                f"This breaks the solo close-up sequence with collaborative environmental interaction."
            )
        elif scene_lower in ["dialogue_part_4", "part_4"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — SOLO WAIST-UP DYNAMIC ACTION ON PERSON_ONE (28mm/50mm LENS): "
                f"Single-character solo waist-up dynamic action shot focused ENTIRELY on PERSON_ONE ({p1_g}). "
                f"Completely different camera distance, body posture, and scale from the tight close-up in Part 1! "
                f"Medium-wide framing capturing PERSON_ONE standing or gesturing with clarity and newfound confidence! "
                f"PERSON_TWO is strictly off-camera / NOT visible in this frame."
            )
        elif scene_lower in ["payoff", "resolution"]:
            shot_direction = (
                f"\n6. CINEMATIC SHOT VARIATION — CELEBRATORY TRIUMPH TWO-SHOT (28mm WIDE CINEMATIC LENS): "
                f"Dynamic celebratory two-shot in motion! Both characters (one {p1_g} and one {p2_g}) "
                f"celebrate success with dynamic movement and dramatic stage backlighting (high-five, walking triumphantly into the event/stage together)."
            )

        text_rule = (
            "SCENE GOAL — ROLEPLAY CONVERSATIONAL SCENARIO:\n"
            "1. Visually represent the EXACT REAL-WORLD SCENARIO described in the script (e.g. bakery counter, airport baggage claim, taxi cab, restaurant table, train station, doctor's office). Do NOT place characters in a classroom or school UNLESS the scenario is explicitly a school setting.\n"
            f"2. GENDER MATCHING & MULTI-CHARACTER RULE (CRITICAL): This is a two-person roleplay. You MUST explicitly describe the physical characters in the scene using the EXACT genders provided: PERSON_ONE is {p1_g} and PERSON_TWO is {p2_g}. If both characters appear in the image, NEVER use generic words like 'two teens' or 'the characters' without specifying their individual sex!\n"
            "3. EMOTIONAL ACTING & FACIAL EXPRESSIONS (CRITICAL): Characters MUST visibly display the emotions of this scene in their facial expressions and body language (e.g. nervous anxiety, friendly open gesture, amused smile, shock). Characters must look emotionally alive!\n"
            "4. TEXT IS STRICTLY BANNED: NO words, letters, signs, chalkboards, or screens."
            + shot_direction
        )

    else:
        # Default / EXPRESSION (and Idioms, Vocabulary, Pronunciation)
        base_rule = (
            "SCENE GOAL — REAL-WORLD SITUATIONAL STORYTELLING:\n"
            "1. AUTHENTIC SITUATION ONLY: Visually represent the ACTUAL REAL-WORLD SITUATION described in the script. Do NOT place characters in a classroom, school, or presentation studio.\n"
            "2. REAL HUMAN CHARACTERS: Depict everyday characters experiencing the situation with genuine emotions, expressive faces, and natural body language.\n"
            "3. TEXT IS STRICTLY BANNED: NO written text, letters, words, captions, logos, chalkboards, whiteboards, or screens anywhere in the image. Focus 100% on characters and environmental storytelling."
        )

        if scene_lower == "hook":
            scene_specific = (
                "\n4. HOOK (THE INSIDER GUIDE — LAYERED DEPTH):\n"
                "CAMERA & COMPOSITION: Angled foreground-and-background depth composition with a 35mm cinematic lens (Rule of Thirds). "
                "In the foreground left or right occupying 35-40% of the frame, the 15yo student protagonist turns 3/4 toward the viewer with an engaging, playful knowing smile and natural relaxed cartoon eyes, sharing an insider secret with friendly confidence (subtle amused smirk, lively spark in the eyes, NEVER bulging or wide bug eyes) breaking the fourth wall. "
                "In the luminous midground and deep background (60%), the authentic story setting extends in rich perspective, showcasing the oversized thematic visual metaphor in atmospheric ambient lighting. "
                "Zero text, zero speech bubbles, zero signs with words."
            )
        elif scene_lower == "setup":
            scene_specific = (
                "\n4. SETUP (SOCIAL CONTEXT & CONTRAST):\n"
                "Depict the social friction, contrasting expectations, or conversational exchange between characters in a collaborative micro-zone. Two-shot or over-the-shoulder shot with expressive body language highlighting the misunderstanding, contrast, or tricky distinction."
            )
        elif scene_lower == "discovery":
            scene_specific = (
                "\n4. DISCOVERY (THE BREAKTHROUGH / TURNING POINT MOMENT):\n"
                "Show the breakthrough moment of realization happening naturally at a demonstration workbench or discovery station! Medium action shot: a companion or friend introduces the key insight or native touch, sparking a radiant smile of sudden clarity, relief, or confident realization on the character's face."
            )
        elif scene_lower == "example":
            scene_specific = (
                "\n4. EXAMPLE (REAL-WORLD USAGE MOMENT IN FULL ACTION):\n"
                "This scene visually captures the real-world example phrase in active motion! Dynamic wide or active motion shot showing the characters actively living out the specific example sentence in the story environment with believable, dynamic body language. Illustrate the specific physical verb/action from the narration!"
            )
        elif scene_lower == "payoff":
            scene_specific = (
                "\n4. PAYOFF (CONFIDENT REAL-WORLD RESOLUTION):\n"
                "Show triumphant mastery, confident relief, or warm shared celebration in the celebration lounge or exit area. Medium close-up or celebratory shot: characters radiate success, comfort, and natural confidence."
            )
        else:
            scene_specific = (
                "\n4. VIBRANT NARRATIVE MOMENT: Illustrate the specific real-life action and emotion described in the scene text cleanly and expressively within the story setting."
            )

        text_rule = base_rule + scene_specific

    anti_rep_context = ""
    if existing_scene_prompts:
        other_scenes = [
            f"- {k.upper()}: \"{v}\""
            for k, v in existing_scene_prompts.items()
            if k.lower() != scene_lower and v
        ]
        if other_scenes:
            anti_rep_context = (
                "ANTI-REPETITION CONSTRAINT (CRITICAL):\n"
                "The other scenes in this Short already depict:\n"
                + "\n".join(other_scenes) + "\n\n"
                "- STRICT PROHIBITION: DO NOT repeat any of the focal props, character poses, micro-locations, or actions used in the scenes above!\n"
                "- Ensure this scene has a completely unique focal object, distinct physical action, and fresh camera perspective!\n\n"
            )

    if general_prompt:
        anchor_block = (
            "MASTER STORY WORLD, PHYSICAL SETTING & CHARACTER ANCHOR (FROM GENERAL PROMPT):\n"
            f">> {general_prompt} <<\n\n"
            "CRITICAL CONTINUITY DIRECTIVE (ABSOLUTE PRECEDENCE):\n"
            "All scenes MUST take place in this exact physical story world and setting! Inherit the exact characters (ages, genders, hair colors, hairstyles, specific thematic wardrobes), and atmosphere established in this General Prompt!\n\n"
        )
    else:
        anchor_block = (
            "THEMATIC STORY WORLD & SCENARIO CONTINUITY (MANDATORY):\n"
            f"The overarching real-world thematic setting is:\n>> {anchor_environment} <<\n"
            "- MICRO-ZONE ROTATION: Each scene MUST occur in a different micro-zone (desk -> discussion lounge -> workbench -> action stage -> victory area)!\n"
            "- PROP ROTATION: NEVER repeat the same focal prop across scenes!\n"
            "- POSE DIVERSITY: Strictly ban repeating generic poses (no duplicate 'pointing' or 'gesturing at models')!\n"
            "- ANTI-CAFETERIA RULE: Do NOT place characters in a generic cafe, cafeteria, or coffee shop unless the setting explicitly specifies one.\n"
            f"- MANDATORY THEMATIC WARDROBE: The character MUST wear clothing/costume that directly belongs to this setting ({anchor_environment}).\n\n"
        )

    if profile is not None:
        progression_block = profile.build_single_scene_progression_summary()
    else:
        progression_block = (
            "DISTINCT SCENE PROGRESSION (CRITICAL — PREVENT IDENTICAL DUPLICATES):\n"
            "While all scenes share the story world above, EACH scene must depict a UNIQUE narrative beat, distinct physical action, and varied camera shot:\n"
            "- HOOK: Medium shot. Opening dilemma or curiosity with an intrigued or questioning expression.\n"
            "- SETUP: Two-shot or over-the-shoulder shot. Conversational exchange or physical contrast.\n"
            "- DISCOVERY: Medium action shot. Sudden breakthrough realization and physical gesture.\n"
            "- EXAMPLE: Dynamic wide or active motion shot. Character actively demonstrating the specific phrase in motion.\n"
            "- PAYOFF: Medium close-up or celebratory shot. Triumphant mastery, confident relief, warm accomplishment."
        )

    return (
        f"INPUT\n\n"
        f"LANGUAGE: {language}\n\n"
        f"{ctx['gender_context']}"
        f"{ctx['personality_context']}"
        f"{ctx['voiceover_notice']}"
        f"SUBJECT: {subject}\n\n"
        f"CONTEXT: {situation}\n\n"
        f"{ctx['context_extra']}"
        f"LABEL: {label}\n\n"
        f"{ctx['palette_context']}\n\n"
        f"ANGLE: visual storytelling / authentic situation\n\n"
        f"STYLE: polished modern 2D cartoon narrative illustration, clean, expressive high-school student protagonist (approx. 14-16 years old, natural balanced teenage proportions, healthy youthful athletic build, stylish situation-appropriate attire, NO mature adults, NOT a child), vibrant but balanced colors, rich cinematic atmosphere\n\n"
        f"FULL SCRIPT TEXT FOR CONTEXT (THE STORY):\n{script_text}\n\n"
        f"---\n\n"
        f"{anchor_block}"
        f"{anti_rep_context}"
        f"{ctx['idiom_rule']}"
        f"---\n\n"
        f"YOUR SPECIFIC TASK FOR THIS SCENE:\n"
        f"Illustrate this specific moment: SCENE [{scene_name.upper()}]:\n"
        f"SCENE TEXT: \"{scene_text}\"\n\n"
        f"{progression_block}\n\n"
        f"{text_rule}\n\n"
        f"CONCISENESS: Keep the final visual prompt strictly under 75 words. Focus only on the most important visual elements (character, facial expression, physical action, authentic setting, cinematic lighting). Do not overcomplicate.\n\n"
        f"Generate the Z-Image-Turbo visual prompt for this scene now. Ensure visual style, environment, and character remain 100% consistent with the story while showing this distinct scene action."
    )


def _build_storyboard_context(
    script_text: str,
    sections: dict[str, str],
    language: str,
    subject: str,
    situation: str,
    label: str,
    speakers_gender: dict = None,
    video_type: str = "EXPRESSION",
    character_personalities: dict = None,
    topic: str = "",
    scenario: str = "",
    lexical_field: str = "",
    anchor_environment: str = "",
    general_prompt: str = "",
    character_anchors: dict = None,
) -> str:
    """Build the prompt for generating a complete, non-repetitive visual storyboard in JSON."""
    ctx = _extract_shared_story_context(
        script_text=script_text,
        language=language,
        label=label,
        speakers_gender=speakers_gender,
        video_type=video_type,
        character_personalities=character_personalities,
        topic=topic,
        scenario=scenario,
        lexical_field=lexical_field,
        anchor_environment=anchor_environment,
        general_prompt=general_prompt,
    )
    anchor_environment = ctx["anchor_environment"]
    char_anchors = ctx.get("char_anchors", {})
    p1_word = char_anchors.get("gender_word1") or ("girl" if char_anchors.get("p1_is_female") else "boy")
    p2_word = char_anchors.get("gender_word2") or ("girl" if char_anchors.get("p2_is_female") else "boy")
    p1_g = p1_word.upper()
    p2_g = p2_word.upper()

    char_anchors = extract_or_build_character_anchors(
        general_prompt=general_prompt,
        speakers_gender=speakers_gender,
        video_type=video_type,
        character_anchors=character_anchors,
    )

    general_prompt_block = ""
    if general_prompt:
        general_prompt_block = (
            "MASTER STORY WORLD, PHYSICAL SETTING & CHARACTER ANCHOR (FROM GENERAL PROMPT):\n"
            f">> {general_prompt} <<\n\n"
            "CRITICAL STORY WORLD, SETTING & CHARACTER CONTINUITY DIRECTIVE (ABSOLUTE PRECEDENCE):\n"
            "1. MANDATORY PHYSICAL SETTING: All scenes below MUST strictly take place inside the exact physical setting "
            "established in this General Prompt! Micro-zones, props, architecture, and lighting must belong to this specific story world. "
            "NEVER relocate scenes to a different or unrelated location (e.g. if General Prompt establishes a sunny vintage park skate plaza, "
            "every scene MUST take place in that skate plaza or adjacent park area; NEVER switch the environment to a kitchen, restaurant, or classroom).\n"
            "2. MANDATORY CHARACTER CONTINUITY:\n"
            f"   - Character 1 (Protagonist): {char_anchors['char1_desc']}\n"
            f"   - Character 2 (Counterpart): {char_anchors['char2_desc']}\n"
            "Diffusion models generate EACH scene image independently with zero memory of other scenes! "
            "Therefore, in EVERY single scene prompt below, you MUST explicitly repeat the featured character's exact demographic (14-16yo high-school student, natural balanced teenage proportions, NOT a child), "
            "exact hair color, exact hairstyle, and exact wardrobe specified above. "
            "NEVER invent different clothing or different hairstyles across scenes!\n\n"
        )

    formatted_scenes = []
    for sec_name, sec_text in sections.items():
        if sec_text.strip():
            formatted_scenes.append(f"[{sec_name.upper()}]: \"{sec_text.strip()}\"")
    scenes_block = "\n".join(formatted_scenes)

    video_type_upper = video_type.strip().upper()
    profile = get_visual_profile(video_type_upper)
    if profile is not None:
        director_task = profile.build_storyboard_director_task(p1_word, p2_word)
    elif video_type_upper == "ROLEPLAY":
        p1_word = char_anchors.get("gender_word1") or ("girl" if char_anchors.get("p1_is_female") else "boy")
        p2_word = char_anchors.get("gender_word2") or ("girl" if char_anchors.get("p2_is_female") else "boy")
        p1 = p1_word.upper()
        p2 = p2_word.upper()
        director_task = (
            f"DIRECTOR'S ROLEPLAY STORYBOARD TASK (6-BEAT CINEMATIC PROGRESSION):\n"
            f"Transform this two-character roleplay dialogue into a dynamic, 6-scene visual storyboard between PERSON_ONE ({p1}) and PERSON_TWO ({p2}).\n\n"
            f"CRITICAL DIRECTIVES FOR CINEMATIC COVERAGE & ZERO REPETITION (MANDATORY):\n"
            f"To guarantee that no two images ever look like copies of each other, you MUST strictly follow this shot-by-shot coverage and camera matrix:\n\n"
            f"1. SCENE-BY-SCENE SUBJECT & CAMERA MATRIX (STRICTLY ENFORCED):\n"
            f"   - HOOK [ESTABLISHING TWO-SHOT (35mm LENS)]: Both characters in frame. Medium-wide 35mm establishing shot setting up the opening dilemma, spatial relationship, and environment. Both {p1_word} and {p2_word} are visible engaged in dialogue across the table, counter, or threshold. STRICTLY ZERO FOURTH-WALL EYE CONTACT.\n"
            f"   - DIALOGUE_PART_1 [SOLO TIGHT CLOSE-UP ON PERSON_ONE (85mm LENS)]: ONLY PERSON_ONE ({p1_word}) is in frame. 85mm portrait lens, shallow depth of field, dramatic key lighting, chest-up tight framing. Expressive facial acting showing opening questioning or dilemma. PERSON_TWO is strictly off-camera!\n"
            f"   - DIALOGUE_PART_2 [SOLO 180° REVERSE-ANGLE CLOSE-UP ON PERSON_TWO (85mm LENS)]: ONLY PERSON_TWO ({p2_word}) is in frame. 180° reverse-angle 85mm portrait lens, chest-up medium close-up, warm fill light. Focus entirely on PERSON_TWO's calm, reassuring expression as they mentor and explain. PERSON_ONE is strictly off-camera!\n"
            f"   - DIALOGUE_PART_3 [90° SIDE PROFILE / TOP-DOWN TWO-SHOT PROP INTERACTION (50mm LENS)]: Both characters in frame! Camera shifts 90° to a dynamic side profile or high-angle table overview. Both {p1_word} and {p2_word} are visible actively examining or manipulating an authentic physical prop (menu, map, book, tool, coffee cup, document with cartoon doodles). NOT another solo close-up!\n"
            f"   - DIALOGUE_PART_4 [SOLO WAIST-UP DYNAMIC ACTION ON PERSON_ONE (28mm/50mm LENS)]: ONLY PERSON_ONE ({p1_word}) is in frame. Completely different camera distance and physical stance from Part 1: waist-up medium-wide framing showing {p1_word} standing or gesturing dynamically with clarity and confidence. PERSON_TWO is strictly off-camera!\n"
            f"   - PAYOFF [CELEBRATORY ACTION TWO-SHOT (28mm LENS)]: Both characters in dynamic motion. 28mm wide cinematic lens, dramatic backlighting, shared celebratory mastery.\n\n"
            f"2. ZERO-AMBIGUITY CHARACTER DESCRIPTION & CONTINUITY:\n"
            f"   - For solo shots (dialogue_part_1, dialogue_part_2, dialogue_part_4): Explicitly describe ONLY the single featured character with their locked traits. State: 'Single character solo shot. The other character is off-camera.'\n"
            f"   - For two-shots (hook, dialogue_part_3, payoff): Explicitly specify the sex of EACH character (e.g. 'one 15-year-old teen {p1_word}' and 'one 15-year-old teen {p2_word}'). Strictly ban generic words like 'the characters'!\n\n"
            f"3. LENGTH: Around 70-110 words per scene prompt.\n\n"
            f"Return ONLY a valid JSON object mapping all 6 scene names in lowercase (hook, dialogue_part_1, dialogue_part_2, dialogue_part_3, dialogue_part_4, payoff) to their final prompt string."
        )
    elif video_type_upper == "GAME":
        director_task = (
            f"DIRECTOR'S GAME STORYBOARD TASK (FRONTAL DILEMMA TO ASYMMETRICAL TRIUMPH PROGRESSION):\n"
            f"Transform this game quiz into a cohesive storyboard where each scene faithfully depicts the specific question, answer, and explanation with exact camera geometry:\n"
            f"1. ARCHETYPE VISUAL GRAMMAR & SCENE MATRIX (MANDATORY):\n"
            f"   - HOOK [THE FRONTAL DILEMMA]: Front-facing, centered medium eye-level shot under an intense overhead spotlight beam with clean vertical symmetry. Solo 16yo student protagonist {p1_word} has a natural healthy athletic build and is centered, weighing two choices with engaging personality. FOURTH-WALL GAZE: 100% direct fourth-wall eye contact with the camera lens, confronting the viewer with the quiz dilemma! EXPRESSIVE ACTING: Lively animated dilemma face with an amused raised eyebrow, slight thinking dilemma smirk, head tilted inquisitively, and warm animated cartoon eyes (NEVER wide bug eyes, NEVER staring, NEVER unexpressive deadpan stare). Solo {p1_word} only (no companion in hook)!\n"
            f"   - ANSWER [THE ASYMMETRICAL BREAKTHROUGH]: Dynamic 3/4 asymmetrical medium action shot with forward kinetic momentum! Protagonist {p1_word} breaks free from the dilemma with radiant relief, a triumphant eureka smile, and forward kinetic energy, joyfully celebrating the winning choice in the setting.\n"
            f"   - EXPLANATION [REAL-WORLD IMMERSION]: Real-world narrative medium-wide shot (35mm wide lens) with deep spatial environment. Protagonist {p1_word} actively engages in the authentic cultural practice, ritual, or real-life application. FOURTH-WALL GAZE: STRICTLY 0% EYE CONTACT WITH THE CAMERA (100% in-scene narrative immersion).\n"
            f"2. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict chalkboards, whiteboards, screens, tablets, smartphones showing text/options, quiz cards, buzzers, podiums, or countdown timers. Completely ban all written words, letters, phrases, and quotes. If documents or papers appear, describe them strictly as containing abstract wavy cartoon doodle lines, 0% legible text. Focus 100% on the human character dilemma and authentic setting.\n"
            f"3. ZERO-AMBIGUITY GENDER RULE: Explicitly specify the sex of every character depicted. Character 1 protagonist MUST be a {p1_word.upper()}. Strictly ban generic words like 'two teens'.\n"
            f"4. MANDATORY CHARACTER CONTINUITY: In EVERY scene prompt, repeat the exact 16-year-old high-school student {p1_word} demographic (tall slender proportions, mature teenage features, NOT a child), skin tone, eye color, hair color, hairstyle, and wardrobe established in the General Prompt.\n"
            f"5. LENGTH: Around 70-110 words per scene prompt.\n\n"
            f"Return ONLY a valid JSON object mapping each scene name in lowercase (hook, answer, explanation) to its final prompt string."
        )
    elif video_type_upper in ["FUN_FACTS", "FUNFACTS", "FUNFACT"]:
        director_task = (
            f"DIRECTOR'S FUN FACTS STORYBOARD TASK (SCALE OF WONDER & DISCOVERY PROGRESSION):\n"
            f"Transform this curiosity script into a visually stunning, narrative-faithful storyboard:\n"
            f"1. ARCHETYPE VISUAL GRAMMAR & SCENE MATRIX (MANDATORY):\n"
            f"   - HOOK [THE SCALE OF WONDER]: Dramatic low-angle heroic 24mm wide shot looking up from floor level. Protagonist {p1_word} in lower third looking upward in jaw-dropped awe at an imposing, towering cultural anomaly or historic marvel. Upward gaze, volumetric lighting shafts, monumental scale contrast.\n"
            f"   - SETUP / DISCOVERY / FACTS: Collaborative inspection and dynamic reveal of the fascinating historical discovery in motion.\n"
            f"   - PAYOFF: Mind-blown celebratory outro celebrating trivia mastery.\n"
            f"2. ZERO-TOLERANCE TEXT BAN: Do NOT include words, quotes, letters, phrases, vocabulary words, or complete sentences in the visual prompt! If scrolls, books, parchment, signs, or artifacts are depicted, describe them strictly as containing 'abstract wavy cartoon scribble lines, graphic doodle curves, or decorative geometric diagrams representing text, completely devoid of legible alphabet letters, words, or typography'.\n"
            f"3. ZERO-AMBIGUITY GENDER RULE: Explicitly specify the sex of every character depicted. Character 1 protagonist MUST be a {p1_word.upper()}. Strictly ban generic words like 'two teens'.\n"
            f"4. MANDATORY CHARACTER CONTINUITY: In EVERY scene prompt, repeat the exact 16-year-old high-school student {p1_word} demographic (tall slender proportions, mature teenage features, NOT a child), skin tone, eye color, hair color, hairstyle, and wardrobe established in the General Prompt.\n"
            f"5. LENGTH: Around 70-110 words per scene prompt.\n\n"
            f"Return ONLY a valid JSON object mapping each scene name in lowercase to its final prompt string."
        )
    else:
        director_task = (
            f"DIRECTOR'S EXPRESSION STORYBOARD TASK (LAYERED DEPTH CHRONOLOGICAL 5-BEAT PROGRESSION):\n"
            f"Create a cohesive 5-scene visual storyboard where EVERY scene faithfully visualizes the specific narrative beat and spoken script text of that scene in CHRONOLOGICAL ORDER:\n"
            f"1. ARCHETYPE VISUAL GRAMMAR & SCENE MATRIX (MANDATORY):\n"
            f"   - HOOK [THE INSIDER GUIDE]: 35mm angled foreground-and-background depth composition (Rule of Thirds). The 15yo student protagonist {p1_word} occupies the foreground left or right (35-40%), turned 3/4 toward the viewer with an engaging, playful knowing smile and warm animated cartoon eyes, sharing an insider secret with natural relaxed facial acting (subtle amused smirk, lively curious gaze, NEVER bulging eyes, NEVER staring rounded eyes) breaking the fourth wall. The luminous midground and deep background (60%) reveal the story setting and oversized thematic visual metaphor in rich atmospheric depth.\n"
            f"   - SETUP [SOCIAL CONTRAST]: Two-shot profile angle across a table/counter demonstrating the conversational friction or literal misunderstanding spoken in this beat.\n"
            f"   - DISCOVERY [EUREKA BREAKTHROUGH]: Medium action shot at a demonstration station. Wide joyful eyes, sudden breakthrough clarity, reacting directly to the native rule being explained.\n"
            f"   - EXAMPLE [LIVING KINETIC MOTION]: ACTIVELY DEPICT THE EXACT EXAMPLE SENTENCE FROM THE SCRIPT IN DYNAMIC MOTION! Show the {p1_word} living out the specific action or situation described in the narration.\n"
            f"   - PAYOFF [CONFIDENT RESOLUTION]: Triumphant chest-up celebratory mastery in the story environment.\n"
            f"2. ZERO-DUPLICATE PROPS & REALISTIC ACTION: Give each scene distinct physical postures and unique focal objects. Strictly ban surreal fantasy magic effects.\n"
            f"3. CAMERA SHOTS (WAIST-UP / CHEST-UP ONLY): Keep characters comfortably close to camera so their faces remain large and detailed.\n"
            f"4. MULTI-CHARACTER GENDER SPECIFICATION: If more than 1 character is depicted, explicitly specify the sex of EACH character (e.g. 'one teen {p1_word} and one companion teen {p2_word}'). Strictly ban generic phrases like 'two teens'.\n"
            f"5. MANDATORY CHARACTER CONTINUITY: In EVERY scene prompt, repeat the exact high school student {p1_word} demographic (15-16yo, tall slender proportions), skin tone, eye color, hair color, hairstyle, and wardrobe established in the General Prompt.\n"
            f"6. LENGTH: Around 70-110 words per scene prompt.\n\n"
            f"Return ONLY a valid JSON object mapping each scene name in lowercase to its final prompt string."
        )

    if general_prompt:
        story_setting_block = general_prompt_block
    else:
        story_setting_block = f"OVERARCHING THEMATIC BASE SETTING:\n>> {anchor_environment} <<\n\n"

    return (
        f"INPUT\n\n"
        f"LANGUAGE: {language}\n\n"
        f"{ctx['gender_context']}"
        f"{ctx['personality_context']}"
        f"{ctx['voiceover_notice']}"
        f"SUBJECT: {subject}\n\n"
        f"CONTEXT: {situation}\n\n"
        f"{ctx['context_extra']}"
        f"LABEL: {label}\n\n"
        f"{ctx['palette_context']}\n\n"
        f"{ctx['idiom_rule']}"
        f"{story_setting_block}"
        f"FULL SCRIPT TEXT (THE COMPLETE STORY):\n{script_text}\n\n"
        f"---\n\n"
        f"SCENES TO STORYBOARD:\n"
        f"{scenes_block}\n\n"
        f"---\n\n"
        f"{director_task}"
    )




# ── Main builder ──────────────────────────────────────────────────────────────

class VisualPromptBuilder:
    """
    Generates Z-Image-Turbo visual prompts from script data using a local LLM.

    Parameters
    ----------
    api_base_url:
        OpenAI-compatible API base URL (e.g. ``http://127.0.0.1:8080/v1``).
    api_key:
        API key (any non-empty string works for llama.cpp).
    model_name:
        Model name identifier sent in the request.
    request_timeout:
        Maximum seconds to wait for the LLM response.
    """

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        model_name: str,
        request_timeout: float = 120.0,
        chunk_timeout: float = 25.0,
    ) -> None:
        timeout = httpx.Timeout(
            connect=10.0,
            read=chunk_timeout,
            write=15.0,
            pool=15.0,
        )
        self._client = OpenAI(
            base_url=api_base_url,
            api_key=api_key if api_key else "llama",
            timeout=timeout,
        )
        self._model = model_name
        self._chunk_timeout = chunk_timeout
        self._wall_timeout = request_timeout


    def check_connection(self) -> None:
        """Check if the local LLM server is reachable and responsive."""
        from config import check_llm_connection
        check_llm_connection(str(self._client.base_url), self._client.api_key, raise_on_error=True)

    def build_visual_prompt(
        self,
        script_text: str,
        label: str,
        scene_name: str,
        scene_text: str,
        script_id: str = "",
        speakers_gender: dict = None,
        video_type: str = "EXPRESSION",
        character_personalities: dict = None,
        topic: str = "",
        scenario: str = "",
        lexical_field: str = "",
        anchor_environment: str = "",
        existing_scene_prompts: dict = None,
        general_prompt: str = "",
        temperature: float = 0.75,
        max_retries: int = 3,
    ) -> str:
        """
        Generate a single Z-Image-Turbo visual prompt for a specific script scene.
        Uses token streaming with an active watchdog to prevent stalls and auto-recovers
        if the LLM server or slot gets stuck ("go ahead, don't stop").

        Parameters
        ----------
        script_text:
            Full script content from PROMPTS.csv.
        label:
            Metadata label string from METADATA.csv
            (e.g. ``"English | work | asking for help | assertiveness"``).
        scene_name:
            The name of the scene/section (e.g. "hook", "context").
        scene_text:
            The text specifically for this scene.
        script_id:
            Used only for log messages.
        speakers_gender:
            Dictionary mapping speaker names to genders.
        video_type:
            Type of video (EXPRESSION, ROLEPLAY, GAME).
        character_personalities:
            Dictionary mapping character names to personality and emotional roles.
        topic:
            Optional specific topic or expression string.
        scenario:
            Optional specific roleplay or situational setting.
        lexical_field:
            Optional lexical category / field (e.g. "Performance & Theater", "Cooking").
        anchor_environment:
            Optional locked physical story environment across all scenes of this script.
        existing_scene_prompts:
            Optional dictionary of other scene prompts in this script, used as anti-repetition memory.
        general_prompt:
            Optional overarching master visual prompt anchor.
        max_retries:
            Maximum number of retry attempts on stall or timeout.

        Returns
        -------
        str
            A detailed visual description ready for ComfyUI injection.

        Raises
        ------
        OpenAIError / RuntimeError
            If the LLM request fails after retries.
        """
        language, subject, situation = _parse_label(label)
        if general_prompt:
            anchor_environment = general_prompt
        elif not general_prompt and anchor_environment and len(anchor_environment) > 80:
            general_prompt = anchor_environment

        user_context = _build_user_context(
            script_text=script_text,
            language=language,
            subject=subject,
            situation=situation,
            label=label,
            scene_name=scene_name,
            scene_text=scene_text,
            speakers_gender=speakers_gender,
            video_type=video_type,
            character_personalities=character_personalities,
            topic=topic,
            scenario=scenario,
            lexical_field=lexical_field,
            anchor_environment=anchor_environment,
            existing_scene_prompts=existing_scene_prompts,
            general_prompt=general_prompt,
        )

        logger.info(
            "[%s] Generating visual prompt — %s / %s / %s",
            script_id, language, subject, situation,
        )

        last_error = None
        for attempt in range(1, max_retries + 1):
            stream = None
            start_t = time.time()
            collected: list[str] = []
            try:
                stream = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": _VISUAL_DIRECTOR_SYSTEM_PROMPT},
                        {"role": "user",   "content": user_context},
                    ],
                    max_tokens=2000,
                    temperature=temperature,
                    stream=True,
                )

                for chunk in stream:
                    if time.time() - start_t > self._wall_timeout:
                        raise TimeoutError(
                            f"LLM visual prompt exceeded wall timeout ({self._wall_timeout:.0f}s)"
                        )

                    delta = chunk.choices[0].delta if chunk.choices else None
                    content = delta.content if delta else None
                    if content:
                        collected.append(content)

                visual_prompt = "".join(collected).strip()
                if not visual_prompt:
                    raise ValueError(f"[{script_id}] LLM returned an empty visual prompt.")

                logger.info(
                    "[%s] Visual prompt generated (%d chars).", script_id, len(visual_prompt)
                )
                logger.debug("[%s] Prompt preview: %s…", script_id, visual_prompt[:120])
                time.sleep(0.2)  # Slot cooldown
                allow_gift_box = is_present_heteronym_topic(topic=topic, label=label)
                return sanitize_and_style_prompt(visual_prompt, allow_gift_box=allow_gift_box)

            except Exception as exc:
                last_error = exc
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass

                elapsed = int(time.time() - start_t)
                if attempt < max_retries:
                    logger.warning(
                        "[%s] LLM generation stalled/failed (%s) after %ds. "
                        "Auto-recovering slot and retrying (attempt %d/%d)... Go ahead, don't stop!",
                        script_id, exc, elapsed, attempt + 1, max_retries,
                    )
                    time.sleep(0.8 * attempt)
                else:
                    logger.error(
                        "[%s] Failed to generate visual prompt for %s after %d attempts: %s",
                        script_id, scene_name, max_retries, exc,
                    )

        raise last_error or RuntimeError(f"[{script_id}] Failed to generate visual prompt.")

    def build_storyboard_prompts(
        self,
        script_text: str,
        label: str,
        sections: dict[str, str],
        script_id: str = "",
        speakers_gender: dict = None,
        video_type: str = "EXPRESSION",
        character_personalities: dict = None,
        topic: str = "",
        scenario: str = "",
        lexical_field: str = "",
        anchor_environment: str = "",
        general_prompt: str = "",
        character_anchors: dict = None,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> dict[str, str]:
        """
        Generates a cohesive, non-repetitive visual storyboard for all scenes of a Short in a single pass.
        Guarantees:
        1. Micro-zone diversity within the thematic macro-environment.
        2. Zero repeated focal props across scenes.
        3. Varied camera framing across all scenes.
        4. Active depiction of the example sentence action.
        5. Creative visual metaphors and graphic wordplay across scenes.
        """
        language, subject, situation = _parse_label(label)
        if general_prompt:
            anchor_environment = general_prompt
        else:
            logger.info("[%s] General prompt anchor not provided; establishing master visual anchor first...", script_id)
            try:
                general_prompt = self.build_general_prompt(
                    script_text=script_text,
                    label=label,
                    script_id=script_id,
                    speakers_gender=speakers_gender,
                    video_type=video_type,
                    character_personalities=character_personalities,
                    topic=topic,
                    scenario=scenario,
                    lexical_field=lexical_field,
                    anchor_environment=anchor_environment,
                    temperature=temperature,
                )
                anchor_environment = general_prompt
            except Exception as exc:
                logger.warning("[%s] Failed to build general prompt for storyboard: %s", script_id, exc)
                general_prompt = anchor_environment

        storyboard_context = _build_storyboard_context(
            script_text=script_text,
            sections=sections,
            language=language,
            subject=subject,
            situation=situation,
            label=label,
            speakers_gender=speakers_gender,
            video_type=video_type,
            character_personalities=character_personalities,
            topic=topic,
            scenario=scenario,
            lexical_field=lexical_field,
            anchor_environment=anchor_environment,
            general_prompt=general_prompt,
            character_anchors=character_anchors,
        )

        logger.info(
            "[%s] Generating complete visual storyboard — %s / %s / %s",
            script_id, language, subject, situation,
        )

        profile = get_visual_profile(video_type)
        storyboard_system_prompt = (
            build_storyboard_system_prompt(profile.build_storyboard_system_grammar())
            if profile is not None
            else _STORYBOARD_DIRECTOR_SYSTEM_PROMPT
        )

        last_error = None
        storyboard_dict: dict[str, str] = {}
        for attempt in range(1, max_retries + 1):
            stream = None
            start_t = time.time()
            collected: list[str] = []
            try:
                stream = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": storyboard_system_prompt},
                        {"role": "user",   "content": storyboard_context},
                    ],
                    max_tokens=3500,
                    temperature=temperature,
                    stream=True,
                )

                for chunk in stream:
                    if time.time() - start_t > self._wall_timeout * 1.5:
                        raise TimeoutError(
                            f"LLM storyboard prompt exceeded wall timeout ({self._wall_timeout * 1.5:.0f}s)"
                        )

                    delta = chunk.choices[0].delta if chunk.choices else None
                    content = delta.content if delta else None
                    if content:
                        collected.append(content)

                full_response = "".join(collected).strip()
                if not full_response:
                    raise ValueError(f"[{script_id}] LLM returned an empty storyboard response.")

                parsed = _extract_json_payload(full_response)
                if parsed and isinstance(parsed, dict):
                    storyboard_dict = {
                        k.strip().lower(): str(v).strip()
                        for k, v in parsed.items()
                        if isinstance(v, (str, int, float)) and str(v).strip()
                    }
                    if storyboard_dict:
                        logger.info(
                            "[%s] Successfully parsed %d storyboard scene prompt(s) from JSON.",
                            script_id, len(storyboard_dict),
                        )
                        break

                logger.warning(
                    "[%s] Could not parse valid JSON storyboard from LLM response (attempt %d/%d). Retrying...",
                    script_id, attempt, max_retries,
                )
            except Exception as exc:
                last_error = exc
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
                elapsed = int(time.time() - start_t)
                logger.warning(
                    "[%s] Storyboard generation error (%s) after %ds. Retrying attempt %d/%d...",
                    script_id, exc, elapsed, attempt + 1, max_retries,
                )
                time.sleep(1.0 * attempt)

        # Validate that all requested active sections exist in storyboard_dict; auto-fill missing
        for sec_name, sec_text in sections.items():
            sec_lower = sec_name.strip().lower()
            if not sec_text.strip():
                continue
            if sec_lower not in storyboard_dict or not storyboard_dict[sec_lower]:
                logger.info(
                    "[%s] Scene '%s' missing from storyboard. Generating individually with general prompt anchor...",
                    script_id, sec_name,
                )
                try:
                    single_prompt = self.build_visual_prompt(
                        script_text=script_text,
                        label=label,
                        scene_name=sec_name,
                        scene_text=sec_text,
                        script_id=script_id,
                        speakers_gender=speakers_gender,
                        video_type=video_type,
                        character_personalities=character_personalities,
                        topic=topic,
                        scenario=scenario,
                        lexical_field=lexical_field,
                        anchor_environment=anchor_environment,
                        existing_scene_prompts=storyboard_dict,
                        general_prompt=general_prompt,
                    )
                    storyboard_dict[sec_lower] = single_prompt
                except Exception as exc:
                    logger.error("[%s] Failed fallback prompt for %s: %s", script_id, sec_name, exc)

        anchors = extract_or_build_character_anchors(
            general_prompt=general_prompt,
            speakers_gender=speakers_gender,
            video_type=video_type,
            character_anchors=character_anchors,
        )

        final_prompts: dict[str, str] = {}
        allow_gift_box = is_present_heteronym_topic(topic=topic, label=label)
        for sec_key, raw_prompt in storyboard_dict.items():
            prompt_str = raw_prompt.strip()
            # Only append continuity summary if prompt completely lacks character description
            has_character = any(w in prompt_str.lower() for w in ["student", "teen", "protagonist", "character", "girl", "boy", "actor", "actress", "man", "woman"])
            if not has_character and anchors.get("continuity_summary"):
                prompt_str = f"{prompt_str.rstrip('. ')}. {anchors['continuity_summary']}"

            final_prompts[sec_key] = sanitize_and_style_prompt(prompt_str, allow_gift_box=allow_gift_box)

        return final_prompts

    def build_general_prompt(
        self,
        script_text: str,
        label: str,
        script_id: str = "",
        speakers_gender: dict = None,
        video_type: str = "EXPRESSION",
        character_personalities: dict = None,
        topic: str = "",
        scenario: str = "",
        lexical_field: str = "",
        anchor_environment: str = "",
        guidance: str = "",
        temperature: float = 0.75,
        max_retries: int = 3,
    ) -> str:
        """
        Generates an overarching General Visual Prompt / Story World Anchor that defines
        the visual environment, thematic setting, protagonist demographic/wardrobe, and aesthetic
        for all scenes in this video.
        """
        language, subject, situation = _parse_label(label)
        if not anchor_environment:
            anchor_environment = resolve_anchor_environment(
                script_text=script_text,
                topic=topic,
                scenario=scenario,
                lexical_field=lexical_field,
                label=label,
                video_type=video_type,
            )

        has_two_characters = (
            video_type.upper() == "ROLEPLAY"
            or bool(speakers_gender and any("two" in str(k).lower() for k in speakers_gender))
        )
        if has_two_characters:
            p1_g = get_speaker_gender_safe(speakers_gender, "PERSON_ONE", "female")
            p2_g = get_speaker_gender_safe(speakers_gender, "PERSON_TWO", "male")
            p1_is_female = "f" in str(p1_g).lower() or "girl" in str(p1_g).lower()
            p2_is_female = "f" in str(p2_g).lower() or "girl" in str(p2_g).lower()
            p1_word = "girl" if p1_is_female else "boy"
            p2_word = "girl" if p2_is_female else "boy"

            c1_hair_example = (
                "dark wavy hair tied in an elegant ponytail or soft shoulder-length bob"
                if p1_is_female
                else "short textured dark hair with clean tapered sides and a neat side-part (NEVER buns, bobs, or ponytails for boys!)"
            )
            c2_hair_example = (
                "textured caramel-brown hair styled in soft shoulder-length waves or graceful braid"
                if p2_is_female
                else "short textured chestnut-brown hair with clean-cut neckline and defined sideburns (NEVER buns, bobs, or ponytails for boys!)"
            )

            character_directive = (
                f"2. Dual Lead Characters (MANDATORY EXACT SKIN TONE, EYE COLOR, GENDER-ACCURATE HAIR & THEMATIC WARDROBE CONTINUITY):\n"
                f"   - Character 1 (Left Position): An expressive 14-16-year-old high-school student {p1_word} (natural balanced teenage proportions, healthy youthful athletic build, NOT a child) positioned on the LEFT side of the frame.\n"
                f"     * Complexion & Eyes: Explicitly specify skin tone and eye color (e.g. 'warm tan skin, expressive dark brown cartoon eyes' or 'fair peach skin, lively green cartoon eyes')! NEVER omit skin tone!\n"
                f"     * Hair: Explicitly specify hair color and hairstyle (e.g. '{c1_hair_example}')!\n"
                f"     * Wardrobe: Explicitly specify authentic thematic costume garments and colors MATCHING THIS SPECIFIC SETTING ({anchor_environment}) — NEVER plain t-shirts/hoodies, and NEVER copy unrelated clothing!\n"
                f"   - Character 2 (Right Position): An energetic 14-16-year-old high-school student {p2_word} (natural balanced teenage proportions, healthy youthful athletic build, NOT a child) positioned on the RIGHT side of the frame.\n"
                f"     * Complexion & Eyes: Explicitly specify skin tone and eye color (e.g. 'fair peach skin, clear blue cartoon eyes' or 'warm olive skin, expressive dark hazel cartoon eyes')!\n"
                f"     * Hair: Explicitly specify contrasting hair color and hairstyle (e.g. '{c2_hair_example}')!\n"
                f"     * Wardrobe: Explicitly specify complementary authentic thematic costume garments and colors matching this setting!\n"
                f"   CRITICAL GENDER-ACCURATE HAIRSTYLE RULE:\n"
                f"   - For MALE characters: ALWAYS use short, distinctly masculine hairstyles (short textured side-part, neat tapered sides, crew-cut). STRICTLY FORBIDDEN FOR MALES: NO buns, NO chignons, NO bobs, NO ponytails, NO feminine long hair!\n"
                f"   - For FEMALE characters: ALWAYS use stylish feminine hairstyles (ponytails, soft shoulder-length waves, bobs with bangs). STRICTLY FORBIDDEN FOR FEMALES: NO masculine quiffs or buzz cuts!\n"
                f"   CRITICAL MULTI-CHARACTER RULE: You MUST explicitly describe the sex, skin tone, hair color, and wardrobe of BOTH characters! Strictly ban generic words like 'two teens' or 'the characters'!"
            )
        else:
            p_gend = get_speaker_gender_safe(speakers_gender, "NARRATOR", "") or get_speaker_gender_safe(speakers_gender, "PERSON_ONE", "male")
            is_female = "f" in str(p_gend).lower() or "girl" in str(p_gend).lower()
            gender_desc = "high-school student girl (approx. 14-16 years old, natural balanced teenage proportions, healthy youthful athletic build, NOT a child)" if is_female else "high-school student boy (approx. 14-16 years old, natural balanced teenage proportions, healthy youthful athletic build, NOT a child)"
            protagonist_hair = (
                "dark wavy hair tied in an elegant ponytail or chic shoulder-length bob"
                if is_female
                else "short textured dark hair with clean tapered sides and a neat side-part (NEVER buns or long hair for boys!)"
            )
            character_directive = (
                f"2. Protagonist (MANDATORY EXACT SKIN TONE, EYE COLOR, HAIR & WARDROBE CONTINUITY):\n"
                f"   - Primary Character: An expressive {gender_desc} with explicitly specified skin tone (e.g. 'warm tan skin' or 'fair peach skin'), eye color (e.g. 'dark brown cartoon eyes'), hair color and hairstyle (e.g. '{protagonist_hair}'), and an authentic thematic costume/wardrobe explicitly matching this setting (describe specific colors and garment types — NEVER plain generic t-shirts/hoodies).\n"
                f"   - Staging & Companion Rule: If any secondary character, peer, or companion appears, Character 1 is on the LEFT and Character 2 is on the RIGHT, each with explicitly specified sex, skin tone, hair color, and distinct thematic costumes (NEVER plain t-shirts/hoodies)!"
            )

        video_type_clean = (video_type or "EXPRESSION").strip().upper()
        profile = get_visual_profile(video_type_clean)
        if profile is not None:
            format_staging_directive = profile.build_format_staging_directive()
        elif video_type_clean == "GAME":
            format_staging_directive = (
                "5. FORMAT STAGING DIRECTIVE (GAME — FRONTAL DILEMMA & FOURTH-WALL EYE CONTACT):\n"
                "   - Hook Scene: Front-facing, centered medium eye-level shot under an intense overhead spotlight beam with clean vertical symmetry. Solo teen protagonist centered, making 100% direct fourth-wall eye contact into the camera lens with an expressive, animated dilemma expression.\n"
                "   - Answer Scene: Dynamic 3/4 asymmetrical medium action shot with forward kinetic momentum, celebrating eureka victory.\n"
                "   - Explanation Scene: Real-world narrative medium-wide shot (35mm lens) with deep spatial environment and 0% eye contact with camera (100% in-scene immersion).\n"
                "   - Crisp cast shadows on the floorboards, high focus on the dilemma."
            )
        elif video_type_clean in ["FUN_FACTS", "FUNFACTS", "FUNFACT"]:
            format_staging_directive = (
                "5. FORMAT STAGING DIRECTIVE (FUN_FACTS — MONUMENTAL SCALE OF WONDER):\n"
                "   - Establish a dramatic low-angle heroic perspective looking upward from low elevation.\n"
                "   - The teen protagonist is positioned in the lower third of the frame, head tilted upward in awe at a towering, imposing cultural anomaly, ancient clockwork, or giant historic relic.\n"
                "   - Volumetric lighting shafts or golden hour beams cutting through atmospheric haze, creating a striking scale contrast between the student and the wonder."
            )
        elif video_type_clean == "ROLEPLAY":
            format_staging_directive = (
                "5. FORMAT STAGING DIRECTIVE (ROLEPLAY — CINEMATIC THRESHOLD DIALOGUE):\n"
                "   - Establish a dynamic diagonal trajectory across a physical boundary (doorframe, table edge, counter, or curtain line).\n"
                "   - Characters are positioned across an active physical divide, engaged in close conversational drama. STRICTLY ZERO eye contact with camera (100% fourth-wall barrier).\n"
                "   - Directional cinematic side-key lighting, dramatic chiaroscuro shadows across faces, authentic interpersonal narrative tension."
            )
        else:  # EXPRESSION
            format_staging_directive = (
                "5. FORMAT STAGING DIRECTIVE (EXPRESSION — LAYERED DEPTH INSIDER GUIDE):\n"
                "   - Establish an angled foreground-and-background depth composition (35mm wide lens with layered Rule-of-Thirds depth planes).\n"
                "   - The foreground zone (occupying 35-40% of the frame, left or right) is reserved for the expressive teen guide, while the luminous midground and background (60%) showcase the expansive storybook setting and the oversized thematic visual metaphor in atmospheric depth.\n"
                "   - Warm atmospheric lighting with distinct depth separation between foreground and background."
            )

        system_prompt = (
            "You are a professional visual director for language-learning animated YouTube Shorts.\n"
            "Your task is to establish the overarching General Visual Prompt / Story World Anchor that will define "
            "the visual context, thematic environment, character appearance, and atmosphere for ALL scenes of this video.\n\n"
            "MANDATORY DIRECTIVES:\n"
            "1. Macro-Setting & Architecture: Describe a rich, authentic physical setting with architectural details, indoor depth, "
            "furniture, ambient props, atmospheric lighting, and soft cast shadows.\n"
            f"{character_directive}\n"
            "   Strictly ban generic modern street clothes (plain t-shirts/hoodies) and mature adults.\n"
            "3. Creative Visual Metaphor & Graphic Props in Environment:\n"
            "   Embrace the GRAPHIC / LITERAL SENSE of the expression or topic by placing relevant physical props naturally in the setting to make the world visually magnetic and fun "
            "(e.g., for 'a piece of cake', feature an elaborate multi-tiered cake on the display table; "
            "for 'proJECT vs PROject', camera tripods, clapperboard, and megaphone on the film shoot set; for travel/visiting, vintage luggage, train timetables, and architectural maps).\n"
            "   STRICT BAN ON GENERIC PROP CLICHÉS: NEVER use generic ribbon-wrapped gift boxes, mystery boxes, or present parcels unless the topic literally and explicitly discusses gifts or birthdays.\n"
            "4. Atmosphere & Style: Vibrant color palette, rich cinematic lighting, clean modern 2D cartoon narrative illustration, "
            "stylized 2D animation art style, vibrant flat colors, bold outlines, expressive facial design, large cartoon eyes with visible sclera and specular highlights, rich interior depth.\n"
            f"{format_staging_directive}\n"
            "6. STATIC STAGE SETUP ONLY (NO MOMENTARY DIALOGUE ACTIONS):\n"
            "   Describe the physical stage, setting props, and characters standing ready on set in their thematic costumes and positions matching the format staging above.\n"
            "   DO NOT describe temporary dialogue actions (such as shouting, covering ears, arguing, or gesturing) in this General Prompt! Temporary actions belong strictly to individual scene prompts.\n"
            "7. Keep the description rich, concrete, vivid, and around 110-180 words (detailed enough to establish specific character clothing, positions, and environmental props).\n"
            "8. ANTI-CLICHÉ BAN: Strictly DO NOT use generic AI clichés: BANNED are generic greenhouses or plant nurseries, plain empty classrooms/schools, pottery/ceramic workshops, flower shops, or generic coffee shops. Ground the setting authentically in the dialogue domain.\n"
            "9. Return ONLY the visual prompt text. No markdown formatting, no commentary."
        )

        user_content = (
            f"LANGUAGE / SUBJECT: {language} / {subject}\n"
            f"CONTEXT: {situation}\n"
            f"VIDEO TYPE: {video_type}\n"
            f"TOPIC: {topic}\n"
            f"SCENARIO: {scenario}\n"
            f"LEXICAL FIELD: {lexical_field}\n"
            f"THEMATIC BASE SETTING: {anchor_environment}\n\n"
            f"FULL SCRIPT TEXT (THE COMPLETE STORY):\n{script_text}\n\n"
        )
        if guidance:
            user_content += f"SPECIAL DIRECTOR GUIDANCE NOTES:\n{guidance}\n\n"
        user_content += "Create the overarching General Visual Prompt now:"

        logger.info("[%s] Generating general visual prompt — %s / %s", script_id, language, subject)

        last_error = None
        for attempt in range(1, max_retries + 1):
            stream = None
            start_t = time.time()
            collected: list[str] = []
            try:
                stream = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_content},
                    ],
                    max_tokens=2500,
                    temperature=temperature,
                    stream=True,
                )

                for chunk in stream:
                    if time.time() - start_t > self._wall_timeout:
                        raise TimeoutError(f"LLM general prompt exceeded wall timeout ({self._wall_timeout:.0f}s)")
                    delta = chunk.choices[0].delta if chunk.choices else None
                    content = delta.content if delta else None
                    if content:
                        collected.append(content)

                general_prompt = "".join(collected).strip()
                if not general_prompt:
                    raise ValueError(f"[{script_id}] LLM returned an empty general prompt.")

                logger.info("[%s] General visual prompt generated (%d chars).", script_id, len(general_prompt))
                time.sleep(0.2)
                allow_gift_box = is_present_heteronym_topic(topic=topic, label=label)
                return sanitize_and_style_prompt(general_prompt, allow_gift_box=allow_gift_box)

            except Exception as exc:
                last_error = exc
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
                elapsed = int(time.time() - start_t)
                if attempt < max_retries:
                    logger.warning(
                        "[%s] General prompt generation failed (%s) after %ds. Retrying attempt %d/%d...",
                        script_id, exc, elapsed, attempt + 1, max_retries,
                    )
                    time.sleep(0.8 * attempt)
                else:
                    logger.error("[%s] Failed to generate general prompt after %d attempts: %s", script_id, max_retries, exc)

        if anchor_environment:
            logger.warning("[%s] Falling back to default anchor_environment: %s", script_id, anchor_environment)
            return sanitize_and_style_prompt(anchor_environment)

        raise last_error or RuntimeError(f"[{script_id}] Failed to generate general prompt.")


