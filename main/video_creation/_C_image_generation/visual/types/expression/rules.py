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
        lens_and_angle="Waist-up / mid-thigh angled 35mm foreground-and-background depth composition (Rule of Thirds, cropped cleanly at hips/mid-thigh — omit footwear); protagonist 40-45% foreground, 3/4 turn",
        gaze="fourth_wall",
        emotion_arc="Engaging playful knowing smile, expressive 2D animated eyes with clean white sclera and dark pupils sharing an insider secret",
        prop_rule="Luminous midground and background reveal the story setting and oversized thematic visual metaphor while protagonist holds or gestures toward a setting prop",
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
        prop_rule="Shop counter or cultural landmark display props",
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
        prop_rule="Vibrant cultural story environment resolution",
    ),
]

EXPRESSION_FORMAT_STAGING_DIRECTIVE = (
    "5. FORMAT STAGING DIRECTIVE (EXPRESSION — WAIST-UP LAYERED DEPTH INSIDER GUIDE):\n"
    "   - Establish a waist-up / mid-thigh angled foreground-and-background depth composition (35mm lens with layered Rule-of-Thirds depth planes, cropped at hips/mid-thigh — omit footwear).\n"
    "   - The foreground zone (occupying 40-45% of the frame, left or right) is reserved for the expressive 17-year-old high-school senior guide framed waist-up showing full shoulders, torso, upper trousers/skirt, and expressive hands, while the luminous midground and background showcase the expansive setting and the oversized thematic visual metaphor in atmospheric depth.\n"
    "   - Warm atmospheric lighting with distinct depth separation between foreground and background."
)

EXPRESSION_ARCHETYPE_DIRECTIVE = (
    "VIDEO TYPE ARCHETYPE: EXPRESSION (Everyday Cultural Observation & Layered Depth)\n"
    "- Core World Objective: Natural, authentic slice-of-life environment demonstrating cultural phrases and idioms in everyday life.\n"
    "- Setting & Stage Setup: A vibrant, culturally authentic everyday street, market, or venue with layered foreground and background depth (e.g. vintage friperie, gelateria, azulejo tapería, coastal boardwalk, historic bookshop).\n"
    "- Protagonist & Ensemble: Solo teen high-school student protagonist living out the cultural scenario (unless dialogue requires a peer).\n"
    "- Setting Mood: Relatable everyday social observation, warm conversational rhythm, authentic cultural charm.\n"
    "- Mandatory Natural Props: Everyday authentic items grounding the scene (e.g. ceramics, bicycles, vinyl sleeves, shopping baskets, travel notebooks).\n"
    "- World Anchor Directive: Define the environmental stage, lighting, and protagonist character design with stylish culturally authentic venue attire."
)
