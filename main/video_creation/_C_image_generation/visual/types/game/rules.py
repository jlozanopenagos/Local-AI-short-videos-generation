"""
visual/types/game/rules.py — Shot grammar, scene contracts, and staging rules for GAME shorts.
"""
from __future__ import annotations

from ..base import SceneSpec

GAME_SCENES = [
    SceneSpec(
        name="hook",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Waist-up 3/4-angled medium shot (50mm lens, cropped cleanly at hips/mid-thigh, showing full shoulders, torso, and expressive hands — omit footwear) under warm dramatic directional spotlighting",
        gaze="fourth_wall",
        emotion_arc="Confident playful dilemma expression, raised eyebrow, subtle knowing smirk while weighing two props in hand",
        prop_rule="Authentic setting props held/compared at chest height; zero chalkboards/screens/quiz UI",
    ),
    SceneSpec(
        name="challenge",
        render_mode="chalkboard",
        cast_in_frame="none",
        lens_and_angle="Native CPU FreeType typography on empty_chalkboard.png",
        gaze="none",
        emotion_arc="Localized interactive quiz prompt and candidate options",
        prop_rule="100% target language header and options",
    ),
    SceneSpec(
        name="pressure",
        render_mode="static",
        cast_in_frame="solo",
        lens_and_angle="Static pre-made language waiting illustration (zero-copy)",
        gaze="fourth_wall",
        emotion_arc="Countdown suspense",
        prop_rule="Static central asset",
    ),
    SceneSpec(
        name="answer",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Dynamic 3/4 asymmetrical medium action shot with forward kinetic momentum",
        gaze="none",
        emotion_arc="Radiant eureka relief, joyful smile, triumphant celebration",
        prop_rule="Holding or gesturing toward the winning choice; zero scoreboards/screens",
    ),
    SceneSpec(
        name="explanation",
        render_mode="comfy",
        cast_in_frame="solo",
        lens_and_angle="Real-world narrative medium-wide shot (35mm wide lens) with deep spatial environment",
        gaze="none",
        emotion_arc="Natural confident practical usage in the real-world cultural setting",
        prop_rule="Authentic cultural practice or real-life application; zero text/screens",
    ),
]

GAME_FORMAT_STAGING_DIRECTIVE = (
    "5. FORMAT STAGING DIRECTIVE (GAME — WAIST-UP 3/4 DILEMMA & FOURTH-WALL EYE CONTACT):\n"
    "   - Hook Scene: Waist-up 3/4-angled medium shot (50mm lens, cropped cleanly at hips/mid-thigh — omit footwear) under warm dramatic directional spotlighting with rich environmental depth. Solo 17-year-old high-school senior protagonist turned 3/4 while making 100% direct fourth-wall eye contact into the camera lens with a confident, playful raised-eyebrow dilemma expression and active hand/prop gesture.\n"
    "   - Answer Scene: Dynamic 3/4 asymmetrical waist-up medium action shot with forward kinetic momentum, celebrating eureka victory (omit footwear).\n"
    "   - Explanation Scene: Real-world narrative medium-wide shot (35mm lens) with deep spatial environment and 0% eye contact with camera (100% in-scene immersion).\n"
    "   - Rich warm/cool cast shadows across the authentic venue and clear focus on late-teen facial acting."
)

GAME_ARCHETYPE_DIRECTIVE = (
    "VIDEO TYPE ARCHETYPE: GAME / QUIZ (Interactive Challenge Arena & Staged Dilemma-to-Triumph)\n"
    "- Core World Objective: Dynamic interactive challenge setting where the protagonist tackles a puzzle or linguistic dilemma.\n"
    "- Setting & Stage Setup: Establish a vibrant culturally grounded venue or landmark courtyard (e.g. historic covered market hall, vintage vinyl shop, sunlit tiled plaza, coastal pier, or traditional pastry counter) equipped for hands-on visual comparison.\n"
    "- Protagonist & Ensemble: Solo teen high-school student protagonist (NEVER include a second character unless explicitly specified in script dialogue).\n"
    "- Setting Mood: Energetic concentration, suspenseful countdown tension, active problem-solving.\n"
    "- Mandatory Challenge Props: Concrete non-text objects representing choices or tasks (e.g. an hourglass timer, vintage brass scales, vinyl records, regional ceramic objects). STRICT BAN ON TEXT: NO placards, NO scorecards, NO writing.\n"
    "- World Anchor Directive: Define the stage architecture, lighting, and protagonist character design with stylish culturally authentic venue attire. Do NOT generate transient facial expressions (smirks, winks) or fourth-wall gaze commands."
)
