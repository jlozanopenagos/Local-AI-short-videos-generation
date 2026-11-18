"""
visual/types/roleplay/prompts.py — Prompt builders for ROLEPLAY single-scene goals and storyboard tasks.
"""
from __future__ import annotations

from .rules import ROLEPLAY_FORMAT_STAGING_DIRECTIVE


def build_roleplay_single_scene_goal(scene_lower: str, p1_word: str = "boy", p2_word: str = "girl") -> str:
    p1_g = p1_word.upper()
    p2_g = p2_word.upper()
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

    return (
        "SCENE GOAL — ROLEPLAY CONVERSATIONAL SCENARIO:\n"
        "1. Visually represent the EXACT REAL-WORLD SCENARIO described in the script (e.g. bakery counter, airport baggage claim, taxi cab, restaurant table, train station, doctor's office). Do NOT place characters in a classroom or school UNLESS the scenario is explicitly a school setting.\n"
        f"2. GENDER MATCHING & MULTI-CHARACTER RULE (CRITICAL): This is a two-person roleplay. You MUST explicitly describe the physical characters in the scene using the EXACT genders provided: PERSON_ONE is {p1_g} and PERSON_TWO is {p2_g}. If both characters appear in the image, NEVER use generic words like 'two teens' or 'the characters' without specifying their individual sex!\n"
        "3. EMOTIONAL ACTING & FACIAL EXPRESSIONS (CRITICAL): Characters MUST visibly display the emotions of this scene in their facial expressions and body language (e.g. nervous anxiety, friendly open gesture, amused smile, shock). Characters must look emotionally alive!\n"
        "4. TEXT IS STRICTLY BANNED: NO words, letters, signs, chalkboards, or screens."
        + shot_direction
    )


def build_roleplay_storyboard_task(p1_word: str, p2_word: str) -> str:
    p1 = p1_word.upper()
    p2 = p2_word.upper()
    return (
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


def build_roleplay_format_staging() -> str:
    return ROLEPLAY_FORMAT_STAGING_DIRECTIVE
