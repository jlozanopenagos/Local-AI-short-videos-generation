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
        lens_and_angle="Solo tight medium close-up on PERSON_ONE (85mm portrait lens, shallow depth of field)",
        gaze="none",
        emotion_arc="Intense facial acting, nervous or questioning body language, opening dilemma",
        prop_rule="PERSON_TWO strictly off-camera; dramatic key lighting",
    ),
    SceneSpec(
        name="dialogue_part_2",
        render_mode="comfy",
        cast_in_frame="p2",
        lens_and_angle="Solo 180-degree reverse-angle medium close-up on PERSON_TWO (85mm portrait lens)",
        gaze="none",
        emotion_arc="Calm, confident, reassuring mentorship expression as they articulate the explanation",
        prop_rule="PERSON_ONE strictly off-camera; warm fill light",
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
        lens_and_angle="Solo waist-up medium-wide dynamic action shot on PERSON_ONE (28mm/50mm lens)",
        gaze="none",
        emotion_arc="Standing or gesturing dynamically with clarity and newfound confidence",
        prop_rule="PERSON_TWO strictly off-camera; distinct camera distance and stance from Part 1",
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
