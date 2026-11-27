"""
visual/types/game/prompts.py — Prompt builders for GAME single-scene goals, progressions, and storyboard tasks.
"""
from __future__ import annotations

from .rules import GAME_FORMAT_STAGING_DIRECTIVE

GAME_STORYBOARD_SYSTEM_GRAMMAR = (
    "     * FOR GAME SHORTS (WAIST-UP 3/4 DILEMMA TO ASYMMETRICAL BREAKTHROUGH PROGRESSION):\n"
    "       - Hook [THE LIVELY DILEMMA]: Waist-up 3/4-angled medium shot (50mm lens, cropped cleanly at hips/mid-thigh, showing full shoulders, torso, upper trousers/skirt, and expressive hands — never full-body head-to-toe, zero footwear mentioned) under warm dramatic directional spotlighting with rich environmental depth. The solo 19-year-old young adult protagonist (tall mature 1:7.5 head-to-body adult proportions, defined angular jawline, broad proportional shoulders, lean athletic young-adult build) turns 3/4 while making 100% direct fourth-wall eye contact, actively weighing two setting props or gestures with a confident raised eyebrow, subtle playful smirk, and expressive 2D animated eyes with clean white sclera, dark pupils, defined eyelids, and bright catchlights.\n"
    "       - Answer [THE EUREKA BREAKTHROUGH]: Dynamic 3/4 asymmetrical waist-up medium breakthrough shot with forward kinetic momentum (cropped at hips/mid-thigh — omit footwear)! Protagonist radiates joyful relief, confident smile, and forward kinetic momentum in the authentic setting.\n"
    "       - Explanation [REAL-WORLD IMMERSION]: Real-world narrative medium-wide shot (35mm lens) showing natural confident usage with 0% camera eye contact."
)

GAME_SINGLE_SCENE_PROGRESSION = (
    "DISTINCT SCENE PROGRESSION FOR GAME SHORTS (CRITICAL — PREVENT IDENTICAL DUPLICATES):\n"
    "While all scenes share the story world above, EACH scene must depict its unique GAME quiz beat and camera geometry:\n"
    "- HOOK: Waist-up 3/4-angled medium shot (50mm lens, cropped at hips/mid-thigh, zero footwear mentioned) under warm spotlighting. Solo 17-year-old senior making 100% direct fourth-wall eye contact, weighing two choices with playful confidence.\n"
    "- ANSWER: Dynamic 3/4 asymmetrical waist-up medium action shot with forward kinetic momentum (omit footwear). Triumphant relief celebrating the winning choice.\n"
    "- EXPLANATION: Real-world narrative medium-wide shot (35mm lens) with 0% camera eye contact. Practical real-life cultural immersion."
)


def build_game_single_scene_goal(scene_lower: str, p1_word: str = "boy", p2_word: str = "girl") -> str:
    if scene_lower == "hook":
        return (
            "SCENE GOAL — HOOK (THE WAIST-UP 3/4 DILEMMA):\n"
            "1. CAMERA & STAGING: Waist-up 3/4-angled medium shot (50mm lens, cropped cleanly at hips/mid-thigh, showing full shoulders, torso, upper trousers/skirt, and expressive hands — never full-body head-to-toe, omit shoes/footwear completely) under warm dramatic directional spotlighting with rich background depth. Solo 19-year-old young adult protagonist (tall mature 1:7.5 head-to-body adult proportions, defined angular jawline, broad proportional shoulders, lean athletic young-adult build) stands in a natural 3/4 turn weighing two authentic setting props in hand (solo character, no companion in hook).\n"
            "2. FOURTH-WALL GAZE: 100% DIRECT FOURTH-WALL EYE CONTACT WITH THE CAMERA LENS! The protagonist glances straight into the camera at the viewer while angled 3/4, breaking the fourth wall to pose the quiz dilemma!\n"
            "3. EXPRESSIVE ACTING: Confident young-adult dilemma face with an amused raised eyebrow, subtle playful thinking smirk, and expressive 2D animated eyes with clean white sclera, dark pupils, defined eyelids, and bright catchlights.\n"
            "4. Relatable, lively real-life environment matching the locked anchor setting. Do NOT place them in a school, classroom, or generic cafe.\n"
            "5. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict chalkboards, whiteboards, screens, tablets, smartphones showing text/options, quiz cards, buzzers, podiums, or countdown timers. Focus 100% on the human character dilemma and authentic setting."
        )
    elif scene_lower == "answer":
        return (
            "SCENE GOAL — ANSWER (THE ASYMMETRICAL BREAKTHROUGH):\n"
            "1. CAMERA & STAGING: Dynamic 3/4 asymmetrical waist-up medium action shot with forward kinetic momentum (cropped at hips/mid-thigh — omit shoes/footwear). The 17-year-old high-school senior protagonist breaks free from the dilemma with radiant clarity, joyful smile, and forward momentum in the authentic setting!\n"
            "2. The character visibly displays confident triumph, a joyful smile, or a thumbs-up gesture, joyfully holding or gesturing toward the correct choice.\n"
            "3. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict success screens, monitors, scoreboards, chalkboards, or digital displays. Focus 100% on the human emotional celebration."
        )
    elif scene_lower == "explanation":
        return (
            "SCENE GOAL — EXPLANATION (REAL-WORLD APPLICATION):\n"
            "1. CAMERA & STAGING: Real-world narrative medium-wide shot (35mm wide lens) showing native speakers naturally and smoothly using the target expression in the authentic real-world setting.\n"
            "2. FOURTH-WALL GAZE: STRICTLY 0% EYE CONTACT WITH THE CAMERA! 100% in-scene narrative immersion (looking at the environment, peers, or task).\n"
            "3. Natural body language, warm communicative atmosphere, and engaging social interaction demonstrating practical usage.\n"
            "4. ZERO-TOLERANCE TEXT & SCREEN BAN: NO text, NO chalkboards, NO screens, NO tablets, NO signs anywhere in the image."
        )
    else:
        return (
            "SCENE GOAL — 2D CARTOON SCENE:\n"
            "1. Illustrate the real-life situation cleanly and expressively in modern 2D cartoon animation style.\n"
            "2. ZERO-TOLERANCE TEXT & SCREEN BAN: NO text, NO chalkboards, NO screens, NO UI. Focus 100% on characters, environment, and visual storytelling."
        )


def build_game_storyboard_task(p1_word: str, p2_word: str = "girl") -> str:
    return (
        f"DIRECTOR'S GAME STORYBOARD TASK (WAIST-UP 3/4 DILEMMA TO ASYMMETRICAL TRIUMPH PROGRESSION):\n"
        f"Transform this game quiz into a cohesive storyboard where each scene faithfully depicts the specific question, answer, and explanation with exact camera geometry:\n"
        f"1. ARCHETYPE VISUAL GRAMMAR & SCENE MATRIX (MANDATORY):\n"
        f"   - HOOK [THE WAIST-UP 3/4 DILEMMA]: Waist-up 3/4-angled medium shot (50mm lens, cropped cleanly at hips/mid-thigh showing full shoulders, torso, upper trousers/skirt, and expressive hands — never full-body head-to-toe, omit shoes/footwear completely) under warm dramatic directional spotlighting with rich architectural depth. Solo 19-year-old young adult ({p1_word}) (tall mature 1:7.5 head-to-body adult proportions, defined angular jawline, broad proportional shoulders, lean athletic young-adult build) turns 3/4 while weighing two authentic setting props in hand. FOURTH-WALL GAZE: 100% direct fourth-wall eye contact with the camera lens, posing the quiz dilemma to the viewer! EXPRESSIVE ACTING: Confident amused raised eyebrow, subtle playful thinking smirk, and expressive 2D animated eyes with clean white sclera, dark pupils, defined eyelids, and bright catchlights. Solo character only (no companion in hook)!\n"
        f"   - ANSWER [THE ASYMMETRICAL BREAKTHROUGH]: Dynamic 3/4 asymmetrical waist-up medium action shot with forward kinetic momentum (cropped at hips/mid-thigh — omit shoes/footwear)! Protagonist {p1_word} breaks free from the dilemma with radiant relief, a triumphant sudden clarity smile, and forward kinetic energy, joyfully celebrating the winning choice in the setting.\n"
        f"   - EXPLANATION [REAL-WORLD IMMERSION]: Real-world narrative medium-wide shot (35mm wide lens) with deep spatial environment. Protagonist {p1_word} actively engages in the authentic cultural practice, ritual, or real-life application. FOURTH-WALL GAZE: STRICTLY 0% EYE CONTACT WITH THE CAMERA (100% in-scene narrative immersion).\n"
        f"2. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict chalkboards, whiteboards, screens, tablets, smartphones showing text/options, quiz cards, buzzers, podiums, or countdown timers. Completely ban all written words, letters, phrases, and quotes. If documents or papers appear, describe them strictly as containing abstract wavy cartoon doodle lines, 0% legible text. Focus 100% on the human character dilemma and authentic setting.\n"
        f"3. ZERO-AMBIGUITY GENDER RULE: Explicitly specify the sex of every character depicted. Character 1 protagonist MUST be a {p1_word.upper()}. Strictly ban generic words like 'two teens'.\n"
        f"4. MANDATORY CHARACTER CONTINUITY: In EVERY scene prompt, repeat the exact 19-year-old young adult ({p1_word}) demographic (tall mature 1:7.5 head-to-body adult proportions, defined angular jawline, broad proportional shoulders, lean athletic young-adult build), skin tone, expressive 2D animated eyes with clean white sclera and dark pupils, hair color, hairstyle, and layered upper + lower garments established in the General Prompt (and omit shoes/footwear in waist-up and medium shots so framing never pulls back full-body).\n"
        f"5. LENGTH: Around 70-110 words per scene prompt.\n\n"
        f"Return ONLY a valid JSON object mapping each scene name in lowercase (hook, answer, explanation) to its final prompt string."
    )


def build_game_format_staging() -> str:
    return GAME_FORMAT_STAGING_DIRECTIVE
