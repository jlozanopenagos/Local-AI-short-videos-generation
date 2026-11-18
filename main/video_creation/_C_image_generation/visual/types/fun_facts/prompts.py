"""
visual/types/fun_facts/prompts.py — Prompt builders for FUN_FACTS single-scene goals, progressions, and storyboard tasks.
Includes complete 5-scene camera grammar per Q8.
"""
from __future__ import annotations

from .rules import FUN_FACTS_FORMAT_STAGING_DIRECTIVE

FUN_FACTS_STORYBOARD_SYSTEM_GRAMMAR = (
    "     * FOR FUN_FACTS SHORTS (SCALE OF WONDER 5-BEAT PROGRESSION):\n"
    "       - Hook [THE SCALE OF WONDER]: Dramatic low-angle heroic 24mm wide shot looking up from floor level. The 14-16yo student protagonist in the lower third looks upward in jaw-dropped awe at an imposing, towering cultural anomaly or historic marvel. Upward gaze (0% camera eye contact), volumetric lighting shafts, monumental scale contrast.\n"
    "       - Setup [THE CURIOUS CLUE]: Medium 50mm eye-level investigative shot examining an authentic historical artifact, mechanism, or cultural clue with focused curiosity.\n"
    "       - Discovery [THE HIDDEN MECHANISM REVEAL]: Dynamic 35mm 3/4 medium action shot revealing the surprising historical or linguistic origin in active motion, with wide-eyed eureka fascination.\n"
    "       - Explanation [LIVING CULTURAL CONTEXT]: Medium-wide 35mm narrative shot demonstrating how the phenomenon or expression works in its real-world cultural environment.\n"
    "       - Payoff [MIND-BLOWN MASTERY]: Chest-up celebratory medium close-up (50mm lens) radiating amazed delight and trivia mastery."
)

FUN_FACTS_SINGLE_SCENE_PROGRESSION = (
    "DISTINCT SCENE PROGRESSION FOR FUN_FACTS SHORTS (CRITICAL — PREVENT IDENTICAL DUPLICATES):\n"
    "While all scenes share the story world above, EACH scene must depict a UNIQUE discovery beat, distinct physical action, and varied camera shot:\n"
    "- HOOK: Low-angle heroic 24mm wide shot looking up in jaw-dropped awe at a towering marvel.\n"
    "- SETUP: Medium 50mm eye-level investigative shot examining an authentic artifact or clue.\n"
    "- DISCOVERY: Dynamic 35mm 3/4 medium action shot revealing the hidden mechanism or origin in motion.\n"
    "- EXPLANATION: Medium-wide 35mm narrative shot showing practical cultural context.\n"
    "- PAYOFF: Chest-up celebratory medium close-up radiating amazed trivia mastery."
)


def build_fun_facts_single_scene_goal(scene_lower: str, p1_word: str = "boy", p2_word: str = "girl") -> str:
    base_header = (
        "SCENE GOAL — FUN_FACTS (SCALE OF WONDER & CULTURAL DISCOVERY):\n"
        "1. Visually depict the authentic historical era, cultural setting, or physical origin of the phrase or fact.\n"
        "2. TEXT IS STRICTLY BANNED: NO words, letters, signs, chalkboards, or whiteboards (any scrolls/books must show only abstract wavy cartoon doodle lines).\n"
    )
    if scene_lower == "hook":
        return (
            base_header
            + "3. HOOK [THE SCALE OF WONDER]: Dramatic low-angle heroic 24mm wide shot looking up from low elevation. The 14-16yo student protagonist is framed in the lower third, tilting their head upward in jaw-dropped awe at an imposing, towering cultural anomaly, ancient clockwork, or historic marvel. Eyes locked upward on the central wonder (0% camera eye contact), illuminated by volumetric lighting shafts."
        )
    elif scene_lower == "setup":
        return (
            base_header
            + "3. SETUP [THE CURIOUS CLUE]: Medium 50mm eye-level investigative shot at a study workbench or cultural display. The 14-16yo student protagonist leans in with intrigued curiosity to inspect a tactile artifact, mechanism, or historical clue."
        )
    elif scene_lower == "discovery":
        return (
            base_header
            + "3. DISCOVERY [THE HIDDEN MECHANISM REVEAL]: Dynamic 35mm 3/4 medium action shot. The protagonist actively demonstrates or uncovers the surprising historical/linguistic mechanism in motion, face lighting up with wide-eyed eureka fascination."
        )
    elif scene_lower == "explanation":
        return (
            base_header
            + "3. EXPLANATION [LIVING CULTURAL CONTEXT]: Medium-wide 35mm environmental immersion shot with rich architectural depth, showing how the phenomenon or expression operates naturally in real-world cultural life (0% camera eye contact)."
        )
    elif scene_lower == "payoff":
        return (
            base_header
            + "3. PAYOFF [MIND-BLOWN MASTERY]: Chest-up celebratory medium close-up (50mm lens) with warm rim lighting. The protagonist radiates amazed delight, confident satisfaction, and trivia mastery."
        )
    return (
        base_header
        + "3. CAMERA & STAGING: Illustrate this discovery beat clearly in waist-up or medium framing with expressive curiosity and authentic period/cultural props."
    )


def build_fun_facts_storyboard_task(p1_word: str, p2_word: str = "girl") -> str:
    return (
        f"DIRECTOR'S FUN FACTS STORYBOARD TASK (SCALE OF WONDER 5-BEAT PROGRESSION):\n"
        f"Transform this curiosity script into a visually stunning, narrative-faithful 5-scene storyboard:\n"
        f"1. ARCHETYPE VISUAL GRAMMAR & SCENE MATRIX (MANDATORY):\n"
        f"   - HOOK [THE SCALE OF WONDER]: Dramatic low-angle heroic 24mm wide shot looking up from floor level. Protagonist {p1_word} in lower third looking upward in jaw-dropped awe at an imposing, towering cultural anomaly or historic marvel. Upward gaze, volumetric lighting shafts, monumental scale contrast.\n"
        f"   - SETUP [THE CURIOUS CLUE]: Medium 50mm eye-level investigative shot. Protagonist {p1_word} examines an authentic artifact, mechanism, or historical clue with focused intrigue in a distinct micro-zone.\n"
        f"   - DISCOVERY [THE HIDDEN MECHANISM REVEAL]: Dynamic 35mm 3/4 medium action shot revealing the surprising historical or linguistic origin in active motion, with wide-eyed eureka fascination.\n"
        f"   - EXPLANATION [LIVING CULTURAL CONTEXT]: Medium-wide 35mm narrative shot demonstrating how the phenomenon or expression works in its real-world cultural setting (0% camera eye contact).\n"
        f"   - PAYOFF [MIND-BLOWN MASTERY]: Chest-up celebratory medium close-up (50mm lens) celebrating trivia mastery with amazed delight.\n"
        f"2. ZERO-TOLERANCE TEXT BAN: Do NOT include words, quotes, letters, phrases, vocabulary words, or complete sentences in the visual prompt! If scrolls, books, parchment, signs, or artifacts are depicted, describe them strictly as containing 'abstract wavy cartoon scribble lines, graphic doodle curves, or decorative geometric diagrams representing text, completely devoid of legible alphabet letters, words, or typography'.\n"
        f"3. ZERO-AMBIGUITY GENDER RULE: Explicitly specify the sex of every character depicted. Character 1 protagonist MUST be a {p1_word.upper()}. Strictly ban generic words like 'two teens'.\n"
        f"4. MANDATORY CHARACTER CONTINUITY: In EVERY scene prompt, repeat the exact 14-16-year-old high-school student {p1_word} demographic (natural balanced teenage proportions, healthy youthful athletic build, mature teenage features, NOT a child), skin tone, simple black cartoon eyes, hair color, hairstyle, and wardrobe established in the General Prompt.\n"
        f"5. LENGTH: Around 70-110 words per scene prompt.\n\n"
        f"Return ONLY a valid JSON object mapping each scene name in lowercase (hook, setup, discovery, explanation, payoff) to its final prompt string."
    )


def build_fun_facts_format_staging() -> str:
    return FUN_FACTS_FORMAT_STAGING_DIRECTIVE
