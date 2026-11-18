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
        lens_and_angle="Front-facing, centered medium eye-level shot under overhead spotlight with vertical symmetry",
        gaze="fourth_wall",
        emotion_arc="Lively animated dilemma face, amused raised eyebrow, slight thinking smirk, head tilted inquisitively",
        prop_rule="Authentic setting props weighing two choices; zero chalkboards/screens/quiz UI",
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
    "5. FORMAT STAGING DIRECTIVE (GAME — FRONTAL DILEMMA & FOURTH-WALL EYE CONTACT):\n"
    "   - Hook Scene: Front-facing, centered medium eye-level shot under an intense overhead spotlight beam with clean vertical symmetry. Solo teen protagonist centered, making 100% direct fourth-wall eye contact into the camera lens with an expressive, animated dilemma expression.\n"
    "   - Answer Scene: Dynamic 3/4 asymmetrical medium action shot with forward kinetic momentum, celebrating eureka victory.\n"
    "   - Explanation Scene: Real-world narrative medium-wide shot (35mm lens) with deep spatial environment and 0% eye contact with camera (100% in-scene immersion).\n"
    "   - Crisp cast shadows on the floorboards, high focus on the dilemma."
)
