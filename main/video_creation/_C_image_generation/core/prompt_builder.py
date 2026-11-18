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
    CharacterCast,
    get_speaker_gender_safe,
    resolve_default_speakers_gender,
    sanitize_character_hair,
    _split_sentences_safe,
    _clean_character_clause,
    build_character_cast,
    extract_or_build_character_anchors,
    persist_character_anchors_in_state,
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
        companion_word = p2_word
        gender_desc = f"high school student {gender_word}"
        gender_context = (
            f"MANDATORY CHARACTER DEMOGRAPHIC & THEMATIC WARDROBE (14-16 YEARS OLD):\n"
            f"- PROTAGONIST (Primary Character 1): MUST visually appear as an expressive high school student {gender_word.upper()} (approx. 14-16 years old {gender_desc}, natural balanced teenage proportions, healthy youthful athletic build, NOT a child).\n"
            f"- WARDROBE: The {gender_word} MUST wear an authentic costume or attire explicitly matching the thematic setting (e.g. theater stage costume/vest, chef uniform, studio apron, lab coat). Strictly ban generic casual clothes (plain t-shirts/hoodies)!\n"
            f"CRITICAL MULTI-CHARACTER RULE: If a secondary companion appears in a two-shot (such as setup), explicitly specify their individual sex and gender-accurate hairstyle (e.g. 'one teen {gender_word} and one companion teen {companion_word}', NEVER give a boy long feminine hair or a girl sideburns/quiff, and NEVER use generic words like 'two students' or 'friends')!\n"
            f"CRITICAL RULE: Primary Protagonist MUST be a {gender_word.upper()} ({gender_desc}). Strictly ban mature adult faces, wrinkles, childish proportions, and generic t-shirts!\n\n"
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
    profile = get_visual_profile(video_type_upper) or get_visual_profile("EXPRESSION")
    if profile is not None:
        text_rule = profile.build_single_scene_goal(scene_lower, p1_word, p2_word)
    else:
        from ..visual.types.expression.profile import ExpressionVisualProfile
        text_rule = ExpressionVisualProfile().build_single_scene_goal(scene_lower, p1_word, p2_word)

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
        has_two_chars = char_anchors.get("has_two_characters") in (True, "True") or video_type.strip().upper() == "ROLEPLAY"
        if has_two_chars:
            char_continuity_lines = (
                f"   - Character 1 (Protagonist / PERSON_ONE): {char_anchors['char1_desc']}\n"
                f"   - Character 2 (Counterpart / PERSON_TWO): {char_anchors['char2_desc']}\n"
            )
        else:
            char_continuity_lines = (
                f"   - Solo Protagonist: {char_anchors['char1_desc']} (SOLO protagonist format — do NOT add a second companion unless the specific scene beat requires social contrast).\n"
            )
        general_prompt_block = (
            "MASTER STORY WORLD, PHYSICAL SETTING & CHARACTER ANCHOR (FROM GENERAL PROMPT):\n"
            f">> {general_prompt} <<\n\n"
            "CRITICAL STORY WORLD, SETTING & CHARACTER CONTINUITY DIRECTIVE (ABSOLUTE PRECEDENCE):\n"
            "1. MANDATORY PHYSICAL SETTING: All scenes below MUST strictly take place inside the exact physical setting "
            "established in this General Prompt! Micro-zones, props, architecture, and lighting must belong to this specific story world. "
            "NEVER relocate scenes to a different or unrelated location (e.g. if General Prompt establishes a sunny vintage park skate plaza, "
            "every scene MUST take place in that skate plaza or adjacent park area; NEVER switch the environment to a kitchen, restaurant, or classroom).\n"
            "2. MANDATORY CHARACTER CONTINUITY:\n"
            f"{char_continuity_lines}"
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
    profile = get_visual_profile(video_type_upper) or get_visual_profile("EXPRESSION")
    if profile is not None:
        director_task = profile.build_storyboard_director_task(p1_word, p2_word)
    else:
        from ..visual.types.expression.profile import ExpressionVisualProfile
        director_task = ExpressionVisualProfile().build_storyboard_director_task(p1_word, p2_word)

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

        video_type_clean = (video_type or "EXPRESSION").strip().upper()
        profile = get_visual_profile(video_type_clean)
        has_two_characters = (
            (profile.has_two_characters_default if profile is not None else video_type_clean == "ROLEPLAY")
            or bool(speakers_gender and any("two" in str(k).lower() for k in speakers_gender))
        )
        if has_two_characters:
            resolved_sg = resolve_default_speakers_gender(speakers_gender, video_type="ROLEPLAY")
            p1_g = resolved_sg.get("PERSON_ONE", "male")
            p2_g = resolved_sg.get("PERSON_TWO", "female")
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
                else "short textured dark hair with clean tapered sides and a neat side-part (NEVER buns, bobs, ponytails, or long hair for boys!)"
            )
            if video_type_clean in ("GAME", "QUIZ", "FUN_FACTS", "FUNFACTS", "FUNFACT", "FACTS"):
                companion_rule = (
                    "   - SOLO PROTAGONIST MANDATE (CRITICAL): This is a SOLO protagonist format! "
                    "Describe ONLY this single primary character on set. Strictly DO NOT include a second character, companion, or peer in the General Prompt!"
                )
            else:
                companion_rule = (
                    "   - Staging & Companion Rule: If a secondary character or peer is genuinely needed by the story, Character 1 is on the LEFT and Character 2 is on the RIGHT, each with explicitly specified sex, skin tone, hair color, and distinct thematic costumes (NEVER plain t-shirts/hoodies)!"
                )
            character_directive = (
                f"2. Protagonist (MANDATORY EXACT SKIN TONE, EYE COLOR, HAIR & WARDROBE CONTINUITY):\n"
                f"   - Primary Character: An expressive {gender_desc} with explicitly specified skin tone (e.g. 'warm tan skin' or 'fair peach skin'), eye color (e.g. 'dark brown cartoon eyes'), hair color and hairstyle (e.g. '{protagonist_hair}'), and an authentic thematic costume/wardrobe explicitly matching this setting (describe specific colors and garment types — NEVER plain generic t-shirts/hoodies).\n"
                f"{companion_rule}"
            )

        video_type_clean = (video_type or "EXPRESSION").strip().upper()
        profile = get_visual_profile(video_type_clean) or get_visual_profile("EXPRESSION")
        if profile is not None:
            format_staging_directive = profile.build_format_staging_directive()
        else:
            from ..visual.types.expression.profile import ExpressionVisualProfile
            format_staging_directive = ExpressionVisualProfile().build_format_staging_directive()

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


