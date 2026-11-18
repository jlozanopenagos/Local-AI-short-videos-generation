"""
visual/types/fun_facts/rules.py — Shot grammar, scene contracts, and staging rules for FUN_FACTS shorts.
"""
from __future__ import annotations

from ..base import SceneSpec

FUN_FACTS_SCENES = [
    SceneSpec(
        name="hook",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Dramatic low-angle heroic 24mm wide shot looking up from floor level",
        gaze="upward",
        emotion_arc="Jaw-dropped awe at an imposing cultural anomaly or historic marvel",
        prop_rule="Towering cultural anomaly, ancient clockwork, or historic marvel with volumetric light shafts",
    ),
    SceneSpec(
        name="setup",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Medium collaborative inspection framing",
        gaze="none",
        emotion_arc="Intrigue and investigative curiosity",
        prop_rule="Inspecting artifacts/scrolls with abstract wavy cartoon scribble lines (0% text)",
    ),
    SceneSpec(
        name="discovery",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Dynamic medium action reveal framing",
        gaze="none",
        emotion_arc="Fascinating historical/linguistic discovery in motion",
        prop_rule="Revealing the physical origin or mechanism of the curiosity",
    ),
    SceneSpec(
        name="explanation",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Medium-wide environmental immersion shot",
        gaze="none",
        emotion_arc="Clear understanding of how the phenomenon works in context",
        prop_rule="Authentic cultural or historical props in use",
    ),
    SceneSpec(
        name="payoff",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Medium close-up celebratory framing",
        gaze="none",
        emotion_arc="Mind-blown celebratory outro celebrating trivia mastery",
        prop_rule="Triumphant conclusion in the story world",
    ),
]

FUN_FACTS_FORMAT_STAGING_DIRECTIVE = (
    "5. FORMAT STAGING DIRECTIVE (FUN_FACTS — MONUMENTAL SCALE OF WONDER):\n"
    "   - Establish a dramatic low-angle heroic perspective looking upward from low elevation.\n"
    "   - The teen protagonist is positioned in the lower third of the frame, head tilted upward in awe at a towering, imposing cultural anomaly, ancient clockwork, or giant historic relic.\n"
    "   - Volumetric lighting shafts or golden hour beams cutting through atmospheric haze, creating a striking scale contrast between the student and the wonder."
)
