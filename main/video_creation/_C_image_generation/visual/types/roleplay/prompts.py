"""
visual/types/roleplay/prompts.py — Prompt builders for ROLEPLAY single-scene goals, progressions, and storyboard tasks.
Locked to Q1 (6 ComfyUI renders) and 3/4 angled waist-up solo dialogue coverage preserving 17-year-old late-teen proportions.
"""
from __future__ import annotations

from .rules import ROLEPLAY_FORMAT_STAGING_DIRECTIVE

ROLEPLAY_STORYBOARD_SYSTEM_GRAMMAR = (
    "     * FOR ROLEPLAY SHORTS (DYNAMIC 6-BEAT CINEMATIC DIALOGUE PROGRESSION):\n"
    "       - Hook [SCENARIO THRESHOLD TWO-SHOT]: Medium-wide 35mm diagonal shot crossing a physical threshold (archway, curtain edge, counter). STRICTLY ZERO FOURTH-WALL EYE CONTACT. Characters interact exclusively with each other in situational tension (waist-up / mid-thigh framing — omit footwear).\n"
    "       - Dialogue_Part_1 [SOLO 3/4 ANGLED WAIST-UP DIALOGUE ON PERSON_ONE]: 50mm lens, waist-up / mid-torso framing showing full shoulders, torso, and arms, turned 3/4 right looking off-camera toward PERSON_TWO (zero camera eye contact), active mid-sentence hand gesture or setting prop interaction, dramatic side-key lighting on PERSON_ONE showing dilemma or questioning (PERSON_TWO is strictly off-camera). Repeat complete locked layered upper + lower garments (omit footwear).\n"
    "       - Dialogue_Part_2 [180° REVERSE 3/4 ANGLED WAIST-UP DIALOGUE ON PERSON_TWO]: 50mm lens, 180° reverse 3/4 angle turned left looking off-camera toward PERSON_ONE (optional soft-focus foreground shoulder OTS cue, zero camera eye contact), waist-up / mid-torso framing, calm reassuring hand gesture or relaxed counter lean with warm fill light on PERSON_TWO. Repeat complete locked layered upper + lower garments (omit footwear).\n"
    "       - Dialogue_Part_3 [90° SIDE PROFILE / TOP-DOWN TWO-SHOT PROP INTERACTION]: 50mm lens. The camera shifts 90° to a side-profile or high-angle table overview showing BOTH characters actively examining or manipulating an authentic physical prop from the setting. Breaks the solo sequence with collaborative interaction.\n"
    "       - Dialogue_Part_4 [SOLO MEDIUM-WIDE 3/4 DYNAMIC MOTION ON PERSON_ONE]: 35mm lens. Wider knees-up / hips-up dynamic motion framing (clearly wider camera distance and active stepping-forward stance than Part 1) capturing PERSON_ONE gesturing boldly with clarity, confidence, and determination (PERSON_TWO is strictly off-camera; omit footwear).\n"
    "       - Payoff [CELEBRATORY TWO-SHOT]: 28mm wide cinematic lens, dramatic backlighting, shared celebratory triumph in motion."
)

ROLEPLAY_SINGLE_SCENE_PROGRESSION = (
    "DISTINCT SCENE PROGRESSION FOR ROLEPLAY SHORTS (CRITICAL — 6-BEAT CINEMATIC COVERAGE):\n"
    "While all 6 scenes share the story world above, EACH scene must strictly follow its unique camera angle and subject coverage:\n"
    "- HOOK: Medium-wide 35mm threshold two-shot (both characters, 0% camera eye contact).\n"
    "- DIALOGUE_PART_1: Solo 50mm 3/4 angled waist-up / mid-torso shot on PERSON_ONE turned right looking off-camera toward PERSON_TWO, active mid-sentence hand gesture/prop (PERSON_TWO off-camera).\n"
    "- DIALOGUE_PART_2: 180° reverse 50mm 3/4 angled waist-up / mid-torso shot on PERSON_TWO turned left looking off-camera toward PERSON_ONE (or soft-focus foreground shoulder OTS cue), calm reassuring gesture or counter lean.\n"
    "- DIALOGUE_PART_3: 90° side profile or top-down 50mm two-shot prop interaction (both characters).\n"
    "- DIALOGUE_PART_4: Solo wider 35mm knees-up / hips-up 3/4 dynamic motion shot on PERSON_ONE stepping forward or gesturing boldly (PERSON_TWO off-camera).\n"
    "- PAYOFF: Celebratory 28mm wide action two-shot in motion (both characters)."
)


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
            f"\n6. CINEMATIC SHOT VARIATION — SOLO 3/4 ANGLED WAIST-UP DIALOGUE ON PERSON_ONE (50mm LENS): "
            f"Single-character 3/4 angled waist-up / mid-torso medium dialogue shot focused ENTIRELY on PERSON_ONE ({p1_g}), showing full shoulders, torso, arms, and upper trousers/skirt. "
            f"PERSON_ONE turns 3/4 right looking off-camera toward PERSON_TWO (zero straight-on frontal camera stare), mid-sentence with an active expressive hand gesture or touching a setting prop. "
            f"Dramatic side-key lighting with rich environmental depth; repeat their full locked layered upper + lower garments. "
            f"PERSON_TWO is strictly off-camera."
        )
    elif scene_lower in ["dialogue_part_2", "part_2"]:
        shot_direction = (
            f"\n6. CINEMATIC SHOT VARIATION — 180° REVERSE 3/4 ANGLED WAIST-UP DIALOGUE ON PERSON_TWO (50mm LENS): "
            f"Dramatic 180° reverse-angle camera switch! 3/4 angled waist-up / mid-torso medium dialogue shot focused on PERSON_TWO ({p2_g}), showing full shoulders, torso, arms, and upper trousers/skirt. "
            f"PERSON_TWO turns 3/4 left looking off-camera toward PERSON_ONE (optional soft-focus foreground shoulder OTS cue on frame edge, zero straight-on frontal camera stare), leaning relaxed against the counter/prop with a calm reassuring hand gesture and warm fill light. "
            f"Repeat their full locked layered upper + lower garments."
        )
    elif scene_lower in ["dialogue_part_3", "part_3"]:
        shot_direction = (
            f"\n6. CINEMATIC SHOT VARIATION — 90° SIDE PROFILE / TOP-DOWN TWO-SHOT PROP INTERACTION (50mm LENS): "
            f"Camera shifts 90° to a dynamic side profile or high-angle table overview! "
            f"Both characters (one {p1_g} and one {p2_g}) are visible actively examining or interacting with an authentic physical prop "
            f"(pointing to details, examining an item, interacting with objects on table/counter). "
            f"This breaks the solo dialogue sequence with collaborative environmental interaction."
        )
    elif scene_lower in ["dialogue_part_4", "part_4"]:
        shot_direction = (
            f"\n6. CINEMATIC SHOT VARIATION — SOLO MEDIUM-WIDE 3/4 DYNAMIC MOTION ON PERSON_ONE (35mm LENS): "
            f"Single-character wider knees-up / hips-up 3/4 dynamic motion shot focused ENTIRELY on PERSON_ONE ({p1_g}). "
            f"Clearly wider camera distance, dynamic forward-stepping posture, and bold physical movement from Part 1! "
            f"Capturing PERSON_ONE striding or gesturing boldly with clarity and newfound confidence; repeat their full locked layered upper + lower garments. "
            f"PERSON_TWO is strictly off-camera."
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
        f"To guarantee that no two images ever look like copies of each other AND preserve consistent 17-year-old late-teen 1:7 proportions, you MUST strictly follow this shot-by-shot coverage and camera matrix:\n\n"
        f"1. SCENE-BY-SCENE SUBJECT & CAMERA MATRIX (STRICTLY ENFORCED):\n"
        f"   - HOOK [ESTABLISHING TWO-SHOT (35mm LENS)]: Both characters in frame. Waist-up / mid-thigh 35mm establishing shot across table, counter, or threshold (omit footwear). Both {p1_word} and {p2_word} are visible engaged in dialogue. STRICTLY ZERO FOURTH-WALL EYE CONTACT.\n"
        f"   - DIALOGUE_PART_1 [SOLO 3/4 ANGLED WAIST-UP DIALOGUE ON PERSON_ONE (50mm LENS)]: ONLY PERSON_ONE ({p1_word}) is featured (PERSON_TWO is off-camera). Waist-up / mid-torso framing showing full shoulders, torso, arms, and upper trousers/skirt (never a tight static passport head-crop; omit footwear). Turned at a 3/4 angle looking off-camera toward PERSON_TWO (zero straight-on frontal camera stare), mid-sentence with an active hand gesture or holding/touching an authentic setting prop, under dramatic side-key lighting.\n"
        f"   - DIALOGUE_PART_2 [180° REVERSE 3/4 ANGLED WAIST-UP DIALOGUE ON PERSON_TWO (50mm LENS)]: 180° reverse-angle switch focusing on PERSON_TWO ({p2_word}) (PERSON_ONE is off-camera, or optional soft-focus foreground shoulder edge for over-the-shoulder depth). Waist-up / mid-torso framing showing full shoulders, torso, arms, and upper trousers/skirt (omit footwear), turned at a 3/4 reverse angle looking off-camera toward PERSON_ONE (zero straight-on frontal camera stare), leaning relaxed against a counter/railing or gesturing reassuringly with warm fill light.\n"
        f"   - DIALOGUE_PART_3 [90° SIDE PROFILE / TOP-DOWN TWO-SHOT PROP INTERACTION (50mm LENS)]: Both characters in frame! Camera shifts 90° to a dynamic side profile or high-angle table overview. Both {p1_word} and {p2_word} are visible actively examining or manipulating an authentic physical prop (menu, map, book, tool, coffee cup, document with cartoon doodles).\n"
        f"   - DIALOGUE_PART_4 [SOLO MEDIUM-WIDE 3/4 DYNAMIC MOTION ON PERSON_ONE (35mm LENS)]: ONLY PERSON_ONE ({p1_word}) is in frame. Clearly wider knees-up / hips-up 35mm framing and distinct stepping-forward posture from Part 1 (omit footwear), showing {p1_word} moving or gesturing boldly with clarity and newfound confidence. PERSON_TWO is strictly off-camera!\n"
        f"   - PAYOFF [CELEBRATORY ACTION TWO-SHOT (28mm LENS)]: Both characters in dynamic motion. 28mm wide cinematic lens, dramatic backlighting, shared celebratory mastery.\n\n"
        f"2. ZERO-AMBIGUITY CHARACTER DESCRIPTION, FULL OUTFIT & OFF-CAMERA EYELINE:\n"
        f"   - For solo dialogue shots (dialogue_part_1, dialogue_part_2, dialogue_part_4): Explicitly describe ONLY the single featured 17-year-old high-school senior {p1_word}/{p2_word} with BOTH their locked layered top garment AND locked lower garment (trousers, chinos, or skirt — omit shoes/footwear), an active hand gesture or prop interaction, and a 3/4 off-camera gaze toward their partner. Include: 'Single character 3/4 angled waist-up dialogue shot. Looking off-camera toward conversation partner.' (Do NOT allow arms hanging stiffly straight down at sides.)\n"
        f"   - For two-shots (hook, dialogue_part_3, payoff): Explicitly specify the sex of EACH character (e.g. 'one 17-year-old high-school senior {p1_word}' and 'one 17-year-old high-school senior {p2_word}') and both complete outfits (omit footwear in cropped shots). Strictly ban generic words like 'the characters'!\n\n"
        f"3. LENGTH: Around 75-115 words per scene prompt.\n\n"
        f"Return ONLY a valid JSON object mapping all 6 scene names in lowercase (hook, dialogue_part_1, dialogue_part_2, dialogue_part_3, dialogue_part_4, payoff) to their final prompt string."
    )


def build_roleplay_format_staging() -> str:
    return ROLEPLAY_FORMAT_STAGING_DIRECTIVE
