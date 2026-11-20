"""
visual/types/expression/prompts.py — Prompt builders for EXPRESSION single-scene goals, progressions, and storyboard tasks.
Enforces 17-year-old late-teen 1:7 proportions, waist-up / mid-thigh cropped framing, and footwear omission on cropped shots.
"""
from __future__ import annotations

from .rules import EXPRESSION_FORMAT_STAGING_DIRECTIVE

EXPRESSION_STORYBOARD_SYSTEM_GRAMMAR = (
    "     * FOR EXPRESSION SHORTS (WAIST-UP LAYERED DEPTH & INSIDER REVELATION PROGRESSION):\n"
    "       - Hook [THE INSIDER GUIDE]: Waist-up / mid-thigh angled 35mm foreground-and-background depth composition (Rule of Thirds, cropped cleanly at hips/mid-thigh showing full shoulders, torso, upper trousers/skirt, and expressive hands — never full-body head-to-toe, omit footwear completely). The solo 17-year-old high-school senior protagonist (realistic late-teen 1:7 head-to-body proportions, defined jawline, proportional shoulders, lean athletic teenage build) occupies 40-45% of the foreground left or right, turned 3/4 toward the viewer with an active hand gesture or prop, engaging playful knowing smile, and lively simple black cartoon eyes breaking the fourth wall. The luminous midground and deep background reveal the story setting and oversized thematic visual metaphor in rich atmospheric depth.\n"
    "       - Setup [SOCIAL CONTRAST]: Waist-up or two-shot profile angle across a table/counter demonstrating the conversational friction or literal misunderstanding (omit footwear).\n"
    "       - Discovery [EUREKA BREAKTHROUGH]: Waist-up medium action shot at a demonstration station (omit footwear). Radiant smile of sudden clarity and understanding.\n"
    "       - Example [LIVING KINETIC MOTION]: Dynamic waist-up or mid-thigh action shot actively demonstrating the exact verb or example situation in full motion while keeping the character's facial expression clear and large (omit footwear).\n"
    "       - Payoff [CONFIDENT RESOLUTION]: Triumphant chest-up celebratory mastery in the story environment (cropped at mid-torso — omit footwear)."
)

EXPRESSION_SINGLE_SCENE_PROGRESSION = (
    "DISTINCT SCENE PROGRESSION FOR EXPRESSION SHORTS (CRITICAL — PREVENT IDENTICAL DUPLICATES):\n"
    "While all scenes share the story world above, EACH scene must depict a UNIQUE narrative beat, distinct physical action, and varied camera shot:\n"
    "- HOOK: Waist-up / mid-thigh angled 35mm foreground-and-background depth shot (Rule of Thirds, cropped cleanly at hips/mid-thigh — omit footwear). Protagonist occupying 40-45% foreground sharing an insider secret breaking the fourth wall.\n"
    "- SETUP: Waist-up two-shot or over-the-shoulder profile shot across counter/table (omit footwear). Conversational exchange or literal misunderstanding contrast.\n"
    "- DISCOVERY: Waist-up medium action shot at a demonstration station (omit footwear). Sudden breakthrough realization and physical gesture.\n"
    "- EXAMPLE: Dynamic waist-up or mid-thigh active motion shot (omit footwear). Character actively demonstrating the specific phrase in motion with a clearly visible face.\n"
    "- PAYOFF: Chest-up medium close-up celebratory shot (omit footwear). Triumphant mastery, confident relief, warm accomplishment."
)


def build_expression_single_scene_goal(scene_lower: str, p1_word: str = "boy", p2_word: str = "girl") -> str:
    base_rule = (
        "SCENE GOAL — REAL-WORLD SITUATIONAL STORYTELLING:\n"
        "1. AUTHENTIC SITUATION ONLY: Visually represent the ACTUAL REAL-WORLD SITUATION described in the script. Do NOT place characters in a classroom, school, or presentation studio.\n"
        "2. REAL HUMAN CHARACTERS: Depict everyday 17-year-old high-school senior characters (realistic late-teen 1:7 head-to-body proportions, defined jawline, proportional shoulders, lean athletic teenage build) experiencing the situation with genuine emotions and natural body language.\n"
        "3. TEXT IS STRICTLY BANNED: NO written text, letters, words, captions, logos, chalkboards, whiteboards, or screens anywhere in the image. Focus 100% on characters and environmental storytelling."
    )

    if scene_lower == "hook":
        scene_specific = (
            "\n4. HOOK (THE INSIDER GUIDE — WAIST-UP LAYERED DEPTH):\n"
            "CAMERA & COMPOSITION: Waist-up / mid-thigh angled foreground-and-background depth composition with a 35mm cinematic lens (Rule of Thirds, cropped cleanly at hips/mid-thigh showing full shoulders, torso, upper trousers/skirt, and expressive hands — never full-body head-to-toe, omit shoes/footwear completely). "
            "In the foreground left or right occupying 40-45% of the frame, the 17-year-old high-school senior protagonist turns 3/4 toward the viewer with an active hand gesture or holding a setting prop, sporting an engaging playful knowing smile and lively natural-sized simple black cartoon eyes while breaking the fourth wall. "
            "In the luminous midground and deep background, the authentic story setting extends in rich perspective, showcasing the oversized thematic visual metaphor in atmospheric ambient lighting. "
            "Zero text, zero speech bubbles, zero signs with words."
        )
    elif scene_lower == "setup":
        scene_specific = (
            "\n4. SETUP (SOCIAL CONTEXT & CONTRAST — WAIST-UP TWO-SHOT):\n"
            "Depict the social friction, contrasting expectations, or conversational exchange between characters across a table/counter (waist-up / mid-thigh framing — omit footwear) with expressive body language highlighting the misunderstanding, contrast, or tricky distinction."
        )
    elif scene_lower == "discovery":
        scene_specific = (
            "\n4. DISCOVERY (THE BREAKTHROUGH / TURNING POINT MOMENT):\n"
            "Show the breakthrough moment of realization happening naturally at a demonstration workbench or discovery station! Waist-up medium action shot (omit footwear): a companion or friend introduces the key insight or native touch, sparking a radiant smile of sudden clarity, relief, or confident realization on the character's face."
        )
    elif scene_lower == "example":
        scene_specific = (
            "\n4. EXAMPLE (REAL-WORLD USAGE MOMENT IN FULL ACTION):\n"
            "This scene visually captures the real-world example phrase in active motion! Dynamic waist-up or mid-thigh active motion shot (keeping facial expression large and clear, omit footwear) showing the characters actively living out the specific example sentence in the story environment with believable, dynamic body language. Illustrate the specific physical verb/action from the narration!"
        )
    elif scene_lower == "payoff":
        scene_specific = (
            "\n4. PAYOFF (CONFIDENT REAL-WORLD RESOLUTION):\n"
            "Show triumphant mastery, confident relief, or warm shared celebration in the story environment. Chest-up medium close-up celebratory shot (cropped at mid-torso — omit footwear): characters radiate success, comfort, and natural confidence."
        )
    else:
        scene_specific = (
            "\n4. VIBRANT NARRATIVE MOMENT: Illustrate the specific real-life action and emotion described in the scene text cleanly and expressively in waist-up framing (omit footwear) within the story setting."
        )

    return base_rule + scene_specific


def build_expression_storyboard_task(p1_word: str, p2_word: str = "girl") -> str:
    return (
        f"DIRECTOR'S EXPRESSION STORYBOARD TASK (WAIST-UP LAYERED DEPTH CHRONOLOGICAL 5-BEAT PROGRESSION):\n"
        f"Create a cohesive 5-scene visual storyboard where EVERY scene faithfully visualizes the specific narrative beat and spoken script text of that scene in CHRONOLOGICAL ORDER:\n"
        f"1. ARCHETYPE VISUAL GRAMMAR & SCENE MATRIX (MANDATORY):\n"
        f"   - HOOK [THE INSIDER GUIDE]: Waist-up / mid-thigh angled 35mm foreground-and-background depth composition (Rule of Thirds, cropped cleanly at hips/mid-thigh showing full shoulders, torso, upper trousers/skirt, and expressive hands — never full-body head-to-toe, omit shoes/footwear completely). The solo 17-year-old high-school senior protagonist {p1_word} (realistic late-teen 1:7 head-to-body proportions, defined jawline, proportional shoulders, lean athletic teenage build) occupies 40-45% foreground left or right, turned 3/4 toward the viewer with an active gesture or prop, playful knowing smile, and lively natural-sized simple black cartoon eyes breaking the fourth wall. The luminous midground and deep background reveal the story setting and oversized thematic visual metaphor in rich atmospheric depth.\n"
        f"   - SETUP [SOCIAL CONTRAST]: Waist-up two-shot profile angle across a table/counter (omit footwear) demonstrating the conversational friction or literal misunderstanding spoken in this beat.\n"
        f"   - DISCOVERY [EUREKA BREAKTHROUGH]: Waist-up medium action shot at a demonstration station (omit footwear). Wide joyful eyes, sudden breakthrough clarity, reacting directly to the native rule being explained.\n"
        f"   - EXAMPLE [LIVING KINETIC MOTION]: Dynamic waist-up or mid-thigh action shot actively depicting the exact example sentence from the script in motion while keeping the {p1_word}'s facial expression large and clear (omit footwear)! Show the {p1_word} living out the specific action or situation described in the narration.\n"
        f"   - PAYOFF [CONFIDENT RESOLUTION]: Triumphant chest-up celebratory mastery in the story environment (cropped at mid-torso — omit footwear).\n"
        f"2. ZERO-DUPLICATE PROPS & REALISTIC ACTION: Give each scene distinct physical postures and unique focal objects. Strictly ban surreal fantasy magic effects.\n"
        f"3. CAMERA SHOTS (WAIST-UP / CHEST-UP / MID-THIGH): Keep characters comfortably close to camera with zero footwear mentions in cropped shots so faces and late-teen 1:7 torso proportions remain crisp (never distant full-body figures).\n"
        f"4. MULTI-CHARACTER GENDER SPECIFICATION: If more than 1 character is depicted, explicitly specify the sex of EACH character (e.g. 'one 17-year-old senior {p1_word} and one companion 17-year-old senior {p2_word}'). Strictly ban generic phrases like 'two teens'.\n"
        f"5. MANDATORY CHARACTER CONTINUITY: In EVERY scene prompt, repeat the exact 17-year-old high-school senior {p1_word} demographic (realistic late-teen 1:7 head-to-body proportions, defined jawline, proportional shoulders, lean athletic teenage build), skin tone, simple black cartoon eyes, hair color, hairstyle, and layered upper + lower garments established in the General Prompt (omitting shoes/footwear in all cropped shots).\n"
        f"6. LENGTH: Around 70-110 words per scene prompt.\n\n"
        f"Return ONLY a valid JSON object mapping each scene name in lowercase (hook, setup, discovery, example, payoff) to its final prompt string."
    )


def build_expression_format_staging() -> str:
    return EXPRESSION_FORMAT_STAGING_DIRECTIVE
