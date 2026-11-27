"""voice/types/roleplay/mastering.py — Balanced theatrical dialogue DSP preset (-16.0 LUFS)."""
from ...common.models import MasteringPreset

ROLEPLAY_MASTERING_PRESET = MasteringPreset(
    name="roleplay_theatrical",
    target_lufs=-16.0,
    peak_ceiling=0.891,
    hpf_hz=80.0,
    mud_cut_hz=240.0,
    mud_cut_db=-2.0,
    mud_cut_q=1.1,
    warmth_hz=165.0,
    warmth_db=0.8,
    warmth_q=0.9,
    presence_hz=3200.0,
    presence_db=1.5,
    presence_q=1.0,
    air_hz=9500.0,
    air_db=0.8,
    deess_low_hz=5500.0,
    deess_high_hz=8500.0,
    deess_threshold_db=-21.0,
    deess_max_reduction_db=3.5,
    comp_threshold_db=-18.0,
    comp_ratio=2.2,
    comp_knee_db=7.0,
    comp_attack_ms=15.0,
    comp_release_ms=140.0,
)
