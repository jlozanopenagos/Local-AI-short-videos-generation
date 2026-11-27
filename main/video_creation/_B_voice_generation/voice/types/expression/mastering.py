"""voice/types/expression/mastering.py — Boosted viral narrator DSP preset (-15.2 LUFS)."""
from ...common.models import MasteringPreset

EXPRESSION_MASTERING_PRESET = MasteringPreset(
    name="expression_boosted_narrator",
    target_lufs=-15.2,
    peak_ceiling=0.891,
    hpf_hz=85.0,
    mud_cut_hz=260.0,
    mud_cut_db=-2.5,
    mud_cut_q=1.1,
    warmth_hz=175.0,
    warmth_db=1.5,
    warmth_q=0.9,
    presence_hz=3500.0,
    presence_db=1.8,
    presence_q=0.9,
    air_hz=9500.0,
    air_db=1.0,
    deess_low_hz=5500.0,
    deess_high_hz=8500.0,
    deess_threshold_db=-22.0,
    deess_max_reduction_db=4.5,
    comp_threshold_db=-19.5,
    comp_ratio=2.9,
    comp_knee_db=6.0,
    comp_attack_ms=11.0,
    comp_release_ms=120.0,
)
