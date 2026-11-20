"""
visual/types/fun_facts/rules.py — Shot grammar, scene contracts, and staging rules for FUN_FACTS shorts.
Includes complete 5-scene camera grammar (Q8).
"""
from __future__ import annotations

from ..base import SceneSpec

FUN_FACTS_SCENES = [
    SceneSpec(
        name="hook",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Dramatic low-angle heroic 28mm wide shot framed from mid-thigh/waist up looking sharply upward at the towering cultural wonder (cropped cleanly at hips/mid-thigh — omit footwear)",
        gaze="upward",
        emotion_arc="Jaw-dropped awe at an imposing cultural anomaly or historic marvel",
        prop_rule="Towering cultural anomaly, ancient clockwork, or historic marvel with volumetric light shafts",
    ),
    SceneSpec(
        name="setup",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Waist-up medium 50mm eye-level investigative shot beside a carved stone ledge or cultural display (omit footwear)",
        gaze="none",
        emotion_arc="Intrigue, focused curiosity, examining the mysterious clue or origin",
        prop_rule="Authentic historical artifact, brass instrument, or parchment scroll with abstract wavy cartoon scribble lines (0% text)",
    ),
    SceneSpec(
        name="discovery",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Dynamic 35mm 3/4 waist-up medium action shot revealing the mechanism or origin in motion (omit footwear)",
        gaze="none",
        emotion_arc="Wide-eyed eureka fascination as the hidden cultural/linguistic connection is revealed",
        prop_rule="Physical demonstration of the historical origin or mechanism in active motion",
    ),
    SceneSpec(
        name="explanation",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Medium-wide 35mm environmental immersion shot with rich architectural depth",
        gaze="none",
        emotion_arc="Confident, engaged appreciation of how the phenomenon or phrase lives in real culture",
        prop_rule="Authentic cultural or historical props in practical real-world context",
    ),
    SceneSpec(
        name="payoff",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Chest-up celebratory medium close-up (50mm lens) with warm dramatic rim lighting",
        gaze="none",
        emotion_arc="Mind-blown celebratory delight and proud trivia mastery",
        prop_rule="Triumphant conclusion in the story world",
    ),
]

FUN_FACTS_FORMAT_STAGING_DIRECTIVE = (
    "5. FORMAT STAGING DIRECTIVE (FUN_FACTS — MONUMENTAL SCALE OF WONDER):\n"
    "   - Establish a dramatic low-angle heroic perspective framed from mid-thigh/waist up looking upward toward towering architecture (cropped cleanly at hips/mid-thigh in the lower foreground — omit footwear).\n"
    "   - The 17-year-old high-school senior protagonist is positioned waist-up in the lower foreground, head tilted upward in awe at a towering, imposing cultural anomaly, ancient clockwork, or giant historic relic.\n"
    "   - Volumetric lighting shafts or golden hour beams cutting through atmospheric haze, creating a striking scale contrast between the teenager and the wonder."
)

FUN_FACTS_ARCHETYPE_DIRECTIVE = (
    "VIDEO TYPE ARCHETYPE: FUN FACTS (Curiosity & Monumental Scale of Wonder)\n"
    "- Core World Objective: Atmospheric documentary environment evoking discovery, history, and cultural wonder.\n"
    "- Setting & Stage Setup: Monumental, richly detailed location with soaring vertical scale and architectural depth (e.g. iconic cultural landmark, ancient stone monument, soaring stained-glass nave, or grand historic railway concourse).\n"
    "- Protagonist & Ensemble: Solo teen high-school student explorer immersed in the environment wearing stylish culturally authentic venue attire.\n"
    "- Setting Mood: Wonder, intellectual curiosity, awe, and mystery.\n"
    "- Mandatory Discovery Props: Concrete objects of investigation (e.g. brass compasses, antique instruments, vintage maps without text, architectural miniature models).\n"
    "- World Anchor Directive: Define the monumental physical environment, atmospheric depth, and protagonist character design."
)
