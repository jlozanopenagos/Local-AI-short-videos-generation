"""
visual/types/expression/rules.py — Shot grammar, scene contracts, and staging rules for EXPRESSION shorts.
"""
from __future__ import annotations

from ..base import SceneSpec

EXPRESSION_SCENES = [
    SceneSpec(
        name="hook",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="35mm angled foreground-and-background depth composition (Rule of Thirds); protagonist 35-40% foreground, 3/4 turn",
        gaze="fourth_wall",
        emotion_arc="Engaging playful knowing smile, warm animated cartoon eyes sharing an insider secret",
        prop_rule="Luminous midground and background (60%) reveal the story setting and oversized thematic visual metaphor",
    ),
    SceneSpec(
        name="setup",
        render_mode="comfy",
        cast_in_frame="both",
        lens_and_angle="Two-shot profile angle across a table/counter",
        gaze="none",
        emotion_arc="Social friction, contrasting expectations, or literal misunderstanding",
        prop_rule="Collaborative micro-zone props illustrating the conversational contrast",
    ),
    SceneSpec(
        name="discovery",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Medium action shot at a demonstration station",
        gaze="none",
        emotion_arc="Wide joyful eyes, radiant smile of sudden clarity and breakthrough understanding",
        prop_rule="Demonstration workbench or discovery station props",
    ),
    SceneSpec(
        name="example",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Dynamic active motion shot (waist-up/medium-wide keeping face clear)",
        gaze="none",
        emotion_arc="Actively living out the specific example sentence in motion",
        prop_rule="Props directly enacting the physical verb/action of the example sentence",
    ),
    SceneSpec(
        name="payoff",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Triumphant chest-up celebratory medium close-up",
        gaze="none",
        emotion_arc="Confident mastery, warm satisfaction, comfortable relief",
        prop_rule="Celebration lounge or story environment resolution",
    ),
]

EXPRESSION_FORMAT_STAGING_DIRECTIVE = (
    "5. FORMAT STAGING DIRECTIVE (EXPRESSION — LAYERED DEPTH INSIDER GUIDE):\n"
    "   - Establish an angled foreground-and-background depth composition (35mm wide lens with layered Rule-of-Thirds depth planes).\n"
    "   - The foreground zone (occupying 35-40% of the frame, left or right) is reserved for the expressive teen guide, while the luminous midground and background (60%) showcase the expansive storybook setting and the oversized thematic visual metaphor in atmospheric depth.\n"
    "   - Warm atmospheric lighting with distinct depth separation between foreground and background."
)

EXPRESSION_ARCHETYPE_DIRECTIVE = (
    "VIDEO TYPE ARCHETYPE: EXPRESSION (Everyday Cultural Observation & Layered Depth)\n"
    "- Core World Objective: Natural, authentic slice-of-life environment demonstrating cultural phrases and idioms in everyday life.\n"
    "- Setting & Stage Setup: A vibrant, culturally authentic everyday setting with layered foreground and background depth (e.g. artisan boutique, sunlit courtyard, terrace, design atelier).\n"
    "- Protagonist & Ensemble: Solo teen high-school student protagonist living out the cultural scenario (unless dialogue requires a peer).\n"
    "- Setting Mood: Relatable everyday social observation, warm conversational rhythm, authentic cultural charm.\n"
    "- Mandatory Natural Props: Everyday authentic items grounding the scene (e.g. espresso cups, shopping baskets, bicycle, art supplies, notebooks).\n"
    "- World Anchor Directive: Define the environmental stage, lighting, and protagonist character design."
)
