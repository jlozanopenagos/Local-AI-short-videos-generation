"""
visual/types/fun_facts/prompts.py — Prompt builders for FUN_FACTS single-scene goals and storyboard tasks.
"""
from __future__ import annotations

from .rules import FUN_FACTS_FORMAT_STAGING_DIRECTIVE


def build_fun_facts_single_scene_goal(scene_lower: str, p1_word: str = "boy", p2_word: str = "girl") -> str:
    return (
        "SCENE GOAL — FUN_FACTS (THE SCALE OF WONDER):\n"
        "1. CAMERA & STAGING: Dramatic low-angle heroic 24mm wide shot looking up from low elevation. The 15yo student protagonist is framed in the lower third, tilting their head upward in jaw-dropped awe at an imposing, towering cultural anomaly, ancient clockwork, or historic marvel.\n"
        "2. FOURTH-WALL GAZE: The character does NOT look at the camera; their eyes are locked upward on the central wonder/artifact in fascination.\n"
        "3. LIGHTING: Volumetric lighting shafts or golden hour beams cutting through atmospheric haze, creating monumental scale contrast.\n"
        "4. Visually depict the authentic historical era, cultural setting, or physical origin of the phrase or fact.\n"
        "5. TEXT IS STRICTLY BANNED: NO words, letters, signs, chalkboards, or whiteboards."
    )


def build_fun_facts_storyboard_task(p1_word: str, p2_word: str = "girl") -> str:
    return (
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


def build_fun_facts_format_staging() -> str:
    return FUN_FACTS_FORMAT_STAGING_DIRECTIVE
