"""voice/types/game/pauses.py — Tactical quiz pause choreography with option micro-pauses & 2.20s pressure_gap."""
from ...common.models import PauseChoreography

GAME_PAUSE_CHOREOGRAPHY = PauseChoreography(
    section_gap=0.30,
    dialogue_section_gap=0.18,
    dialogue_gap=0.14,
    dialogue_cliffhanger_gap=0.22,
    paragraph_gap=0.18,
    pressure_gap=2.20,  # MUST-KEEP: countdown window before answer reveal
    hook_to_next_gap=0.22,
    answer_to_explanation_gap=0.28,
    option_micro_pause=0.26,
)
