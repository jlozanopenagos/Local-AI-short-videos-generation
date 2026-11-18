"""
visual/types/game/prompts.py — Prompt builders for GAME single-scene goals and storyboard tasks.
"""
from __future__ import annotations

from .rules import GAME_FORMAT_STAGING_DIRECTIVE


def build_game_single_scene_goal(scene_lower: str, p1_word: str = "boy", p2_word: str = "girl") -> str:
    if scene_lower == "hook":
        return (
            "SCENE GOAL — HOOK (THE FRONTAL DILEMMA):\n"
            "1. CAMERA & STAGING: Front-facing, centered medium eye-level shot under an intense overhead spotlight beam with clean vertical symmetry. Solo 16yo student protagonist has a natural healthy athletic build and is centered, weighing two choices with engaging personality (solo character, no companion in hook).\n"
            "2. FOURTH-WALL GAZE: 100% DIRECT FOURTH-WALL EYE CONTACT WITH THE CAMERA LENS! The protagonist looks straight into the camera at the viewer, breaking the fourth wall to confront the audience with the quiz dilemma!\n"
            "3. EXPRESSIVE ACTING: Lively animated dilemma face with an amused raised eyebrow, slight thinking dilemma smirk, head tilted inquisitively, and warm expressive cartoon eyes full of life and spark (NEVER wide bug eyes, NEVER unexpressive deadpan stare).\n"
            "4. Relatable, lively real-life environment matching the locked anchor setting. Do NOT place them in a school, classroom, or generic cafe.\n"
            "5. ZERO-TOLERANCE TEXT & SCREEN BAN: Do NOT depict chalkboards, whiteboards, screens, tablets, smartphones showing text/options, quiz cards, buzzers, podiums, or countdown timers. Focus 100% on the human character dilemma and authentic setting."
        )
    elif scene_lower == "answer":
        return (
            "SCENE GOAL — ANSWER (THE ASYMMETRICAL BREAKTHROUGH):\n"
            "1. CAMERA & STAGING: Dynamic 3/4 asymmetrical medium action shot with forward kinetic momentum. The character breaks free from the dilemma with radiant eureka relief, joyful smile, and forward momentum in the authentic setting!\n"
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


def build_game_format_staging() -> str:
    return GAME_FORMAT_STAGING_DIRECTIVE
