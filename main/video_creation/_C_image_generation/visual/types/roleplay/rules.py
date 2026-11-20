"""
visual/types/roleplay/rules.py — Shot grammar, scene contracts, and staging rules for ROLEPLAY shorts.
Locked to Q1 decision: 6 ComfyUI renders (hook, dialogue_part_1..4, payoff).
"""
from __future__ import annotations

from ..base import SceneSpec

ROLEPLAY_SCENES = [
    SceneSpec(
        name="hook",
        render_mode="comfy",
        cast_in_frame="both",
        lens_and_angle="Medium-wide 35mm establishing diagonal OTS two-shot crossing a physical threshold",
        gaze="none",
        emotion_arc="Pre-performance situational tension; characters lock eyes exclusively with each other",
        prop_rule="Physical threshold (archway, curtain edge, counter, doorway) with directional side-key lighting",
    ),
    SceneSpec(
        name="dialogue_part_1",
        render_mode="comfy",
        cast_in_frame="p1",
        lens_and_angle="Solo 3/4 angled waist-up medium dialogue shot on PERSON_ONE (50mm lens, turned 3/4 right looking off-camera toward PERSON_TWO, zero camera eye contact)",
        gaze="none",
        emotion_arc="Expressive questioning facial acting and anxious dilemma while speaking mid-sentence",
        prop_rule="PERSON_TWO strictly off-camera; active mid-sentence hand gesture or setting prop interaction; dramatic side-key lighting",
    ),
    SceneSpec(
        name="dialogue_part_2",
        render_mode="comfy",
        cast_in_frame="p2",
        lens_and_angle="180-degree reverse 3/4 angled waist-up medium dialogue shot on PERSON_TWO (50mm lens, turned 3/4 left looking off-camera toward PERSON_ONE, optional soft-focus foreground shoulder OTS cue, zero camera eye contact)",
        gaze="none",
        emotion_arc="Calm, confident, reassuring mentorship expression while articulating the explanation",
        prop_rule="PERSON_ONE off-camera or soft foreground shoulder edge; calm reassuring hand gesture or relaxed counter lean; warm fill light",
    ),
    SceneSpec(
        name="dialogue_part_3",
        render_mode="comfy",
        cast_in_frame="both",
        lens_and_angle="90-degree side profile or high-angle top-down two-shot (50mm lens)",
        gaze="none",
        emotion_arc="Collaborative environmental interaction breaking the solo close-up sequence",
        prop_rule="Both characters actively examining or manipulating an authentic physical prop from the setting",
    ),
    SceneSpec(
        name="dialogue_part_4",
        render_mode="comfy",
        cast_in_frame="p1",
        lens_and_angle="Solo medium-wide 3/4 dynamic motion shot on PERSON_ONE (35mm lens, wider knees-up/hips-up framing stepping forward or gesturing boldly with renewed confidence)",
        gaze="none",
        emotion_arc="Stepping forward or gesturing boldly with clarity and newfound confidence",
        prop_rule="PERSON_TWO strictly off-camera; distinct wider distance and active body stance from Part 1",
    ),
    SceneSpec(
        name="payoff",
        render_mode="comfy",
        cast_in_frame="both",
        lens_and_angle="Celebratory action two-shot in motion (28mm wide cinematic lens)",
        gaze="none",
        emotion_arc="Shared celebratory mastery and triumph in motion",
        prop_rule="Dramatic backlighting, dynamic movement",
    ),
]

ROLEPLAY_FORMAT_STAGING_DIRECTIVE = (
    "5. FORMAT STAGING DIRECTIVE (ROLEPLAY — CINEMATIC THRESHOLD DIALOGUE):\n"
    "   - Establish a dynamic diagonal trajectory across a physical boundary (doorframe, table edge, counter, or curtain line).\n"
    "   - Characters are positioned across an active physical divide, engaged in close conversational drama. STRICTLY ZERO eye contact with camera (100% fourth-wall barrier).\n"
    "   - Directional cinematic side-key lighting, dramatic chiaroscuro shadows across faces, authentic interpersonal narrative tension."
)

ROLEPLAY_ARCHETYPE_DIRECTIVE = (
    "VIDEO TYPE ARCHETYPE: ROLEPLAY (Character Drama & Cinematic Threshold Dialogue)\n"
    "- Core World Objective: Authentic conversational environment designed for interpersonal drama, debate, or collaborative discovery.\n"
    "- Setting & Stage Setup: A shared, culturally grounded space with rich physical depth (e.g. vintage friperie rack, gelateria counter, azulejo tapería bar, cobblestone arcade, colonial balcony, or harbor pier).\n"
    "- Characters & Dynamic: Two distinct high-school students (PERSON_ONE and PERSON_TWO) with complementary stylish culturally authentic venue wardrobe matching the city and location.\n"
    "- Setting Mood: Relatable interpersonal connection, engaging conversational atmosphere.\n"
    "- Mandatory Conversational Foil Props: Authentic physical objects anchoring their interaction (e.g. regional ceramics, vinyl sleeves, wicker baskets, pastries, travel bags).\n"
    "- World Anchor Directive: Define the spatial relationship, environment, and both character designs. Do NOT dictate transient facial expressions or momentary speech gestures."
)
