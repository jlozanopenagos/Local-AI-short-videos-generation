"""voice/types/game/mastering.py — Punchy TV quiz host DSP mastering preset (-15.0 LUFS)."""
from ...common.models import MasteringPreset

GAME_MASTERING_PRESET = MasteringPreset(
    name="game_punchy_host",
    target_lufs=-15.0,
    peak_ceiling=0.891,
    hpf_hz=85.0,
    mud_cut_hz=250.0,
    mud_cut_db=-2.5,
    mud_cut_q=1.1,
    warmth_hz=170.0,
    warmth_db=1.2,
    warmth_q=0.9,
    presence_hz=3500.0,
    presence_db=2.6,
    presence_q=0.9,
    air_hz=9000.0,
    air_db=1.0,
    deess_low_hz=5500.0,
    deess_high_hz=8500.0,
    deess_threshold_db=-22.0,
    deess_max_reduction_db=4.5,
    comp_threshold_db=-20.0,
    comp_ratio=3.2,
    comp_knee_db=5.5,
    comp_attack_ms=10.0,
    comp_release_ms=110.0,
)
