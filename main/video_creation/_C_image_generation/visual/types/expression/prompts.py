"""
visual/types/expression/prompts.py — Prompt builders for EXPRESSION single-scene goals, progressions, and storyboard tasks.
Includes Q3 (14-16yo), Q4 (natural balanced proportions), and Q7 (waist-up/medium-wide action for example).
"""
from __future__ import annotations

from .rules import EXPRESSION_FORMAT_STAGING_DIRECTIVE

EXPRESSION_STORYBOARD_SYSTEM_GRAMMAR = (
    "     * FOR EXPRESSION SHORTS (LAYERED DEPTH & INSIDER REVELATION PROGRESSION):\n"
    "       - Hook [THE INSIDER GUIDE]: 35mm angled foreground-and-background depth composition (Rule of Thirds). The 14-16yo student protagonist occupies the foreground left or right (35-40%), turned 3/4 toward the viewer with an engaging, playful knowing smile and warm animated cartoon eyes, sharing an insider secret with natural relaxed facial acting (subtle amused smirk, lively curious gaze, NEVER bulging eyes, NEVER staring rounded eyes) breaking the fourth wall. The luminous midground and deep background (60%) reveal the story setting and oversized thematic visual metaphor in rich atmospheric depth.\n"
    "       - Setup [SOCIAL CONTRAST]: Two-shot profile angle across a table/counter demonstrating the conversational friction or literal misunderstanding.\n"
    "       - Discovery [EUREKA BREAKTHROUGH]: Medium action shot at a demonstration station. Radiant smile of sudden clarity and understanding.\n"
    "       - Example [LIVING KINETIC MOTION]: Dynamic waist-up or medium-wide action shot actively demonstrating the exact verb or example situation in full motion while keeping the character's facial expression clear and large.\n"
    "       - Payoff [CONFIDENT RESOLUTION]: Triumphant chest-up celebratory mastery in the story environment."
)

EXPRESSION_SINGLE_SCENE_PROGRESSION = (
    "DISTINCT SCENE PROGRESSION FOR EXPRESSION SHORTS (CRITICAL — PREVENT IDENTICAL DUPLICATES):\n"
    "While all scenes share the story world above, EACH scene must depict a UNIQUE narrative beat, distinct physical action, and varied camera shot:\n"
    "- HOOK: 35mm angled foreground-and-background depth shot (Rule of Thirds). Protagonist in foreground (35-40%) sharing an insider secret breaking the fourth wall.\n"
    "- SETUP: Two-shot or over-the-shoulder profile shot. Conversational exchange or literal misunderstanding contrast.\n"
    "- DISCOVERY: Medium action shot at a demonstration station. Sudden breakthrough realization and physical gesture.\n"
    "- EXAMPLE: Dynamic waist-up or medium-wide active motion shot. Character actively demonstrating the specific phrase in motion with a clearly visible face.\n"
    "- PAYOFF: Chest-up medium close-up celebratory shot. Triumphant mastery, confident relief, warm accomplishment."
)


def build_expression_single_scene_goal(scene_lower: str, p1_word: str = "boy", p2_word: str = "girl") -> str:
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
            "In the foreground left or right occupying 35-40% of the frame, the 14-16yo student protagonist turns 3/4 toward the viewer with an engaging, playful knowing smile and natural relaxed cartoon eyes, sharing an insider secret with friendly confidence (subtle amused smirk, lively spark in the eyes, NEVER bulging or wide bug eyes) breaking the fourth wall. "
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
            "This scene visually captures the real-world example phrase in active motion! Dynamic waist-up or medium-wide active motion shot (keeping facial expression large and clear) showing the characters actively living out the specific example sentence in the story environment with believable, dynamic body language. Illustrate the specific physical verb/action from the narration!"
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

    return base_rule + scene_specific


def build_expression_storyboard_task(p1_word: str, p2_word: str = "girl") -> str:
    return (
        f"DIRECTOR'S EXPRESSION STORYBOARD TASK (LAYERED DEPTH CHRONOLOGICAL 5-BEAT PROGRESSION):\n"
        f"Create a cohesive 5-scene visual storyboard where EVERY scene faithfully visualizes the specific narrative beat and spoken script text of that scene in CHRONOLOGICAL ORDER:\n"
        f"1. ARCHETYPE VISUAL GRAMMAR & SCENE MATRIX (MANDATORY):\n"
        f"   - HOOK [THE INSIDER GUIDE]: 35mm angled foreground-and-background depth composition (Rule of Thirds). The 14-16yo student protagonist {p1_word} occupies the foreground left or right (35-40%), turned 3/4 toward the viewer with an engaging, playful knowing smile and warm animated cartoon eyes, sharing an insider secret with natural relaxed facial acting (subtle amused smirk, lively curious gaze, NEVER bulging eyes, NEVER staring rounded eyes) breaking the fourth wall. The luminous midground and deep background (60%) reveal the story setting and oversized thematic visual metaphor in rich atmospheric depth.\n"
        f"   - SETUP [SOCIAL CONTRAST]: Two-shot profile angle across a table/counter demonstrating the conversational friction or literal misunderstanding spoken in this beat.\n"
        f"   - DISCOVERY [EUREKA BREAKTHROUGH]: Medium action shot at a demonstration station. Wide joyful eyes, sudden breakthrough clarity, reacting directly to the native rule being explained.\n"
        f"   - EXAMPLE [LIVING KINETIC MOTION]: Dynamic waist-up or medium-wide action shot actively depicting the exact example sentence from the script in motion while keeping the {p1_word}'s facial expression large and clear! Show the {p1_word} living out the specific action or situation described in the narration.\n"
        f"   - PAYOFF [CONFIDENT RESOLUTION]: Triumphant chest-up celebratory mastery in the story environment.\n"
        f"2. ZERO-DUPLICATE PROPS & REALISTIC ACTION: Give each scene distinct physical postures and unique focal objects. Strictly ban surreal fantasy magic effects.\n"
        f"3. CAMERA SHOTS (WAIST-UP / CHEST-UP / MEDIUM-WIDE): Keep characters comfortably close to camera so their faces and eyes remain large and detailed (never distant tiny figures).\n"
        f"4. MULTI-CHARACTER GENDER SPECIFICATION: If more than 1 character is depicted, explicitly specify the sex of EACH character (e.g. 'one teen {p1_word} and one companion teen {p2_word}'). Strictly ban generic phrases like 'two teens'.\n"
        f"5. MANDATORY CHARACTER CONTINUITY: In EVERY scene prompt, repeat the exact high school student {p1_word} demographic (14-16yo, natural balanced teenage proportions, healthy youthful athletic build, NOT a child), skin tone, eye color, hair color, hairstyle, and wardrobe established in the General Prompt.\n"
        f"6. LENGTH: Around 70-110 words per scene prompt.\n\n"
        f"Return ONLY a valid JSON object mapping each scene name in lowercase (hook, setup, discovery, example, payoff) to its final prompt string."
    )


def build_expression_format_staging() -> str:
    return EXPRESSION_FORMAT_STAGING_DIRECTIVE
