"""
voice/common/models.py — Typed configuration dataclasses for Stage B modular voice profiles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class SamplingProfile:
    """Qwen3-TTS decoding sampling parameters."""

    temperature: float
    top_p: float
    top_k: int
    subtalker_temperature: float
    repetition_penalty: float


@dataclass(frozen=True)
class AcousticGateEnvelope:
    """Per-language acoustic pass/retry thresholds for synthesized takes."""

    min_pitch_variance: float
    min_cps: float
    max_cps: float
    target_cps: float
    min_rms: float = 0.05
    max_internal_silence: float = 0.85
    max_mean_f0: float = 285.0
    check_question_rise: bool = True
    min_question_f0_ratio: float = 1.03
    check_exclamation_lift: bool = True
    min_exclamation_rms_ratio: float = 1.55


@dataclass(frozen=True)
class PauseChoreography:
    """Per-video-type tactical pause durations (seconds) between narrative beats."""

    section_gap: float = 0.35
    dialogue_section_gap: float = 0.20
    dialogue_gap: float = 0.15
    dialogue_cliffhanger_gap: float = 0.24
    paragraph_gap: float = 0.20
    pressure_gap: float = 2.20
    hook_to_next_gap: Optional[float] = None
    pre_discovery_gap: Optional[float] = None
    dialogue_to_payoff_gap: Optional[float] = None
    answer_to_explanation_gap: Optional[float] = None
    option_micro_pause: float = 0.0

    def to_legacy_dict(self) -> Dict[str, float]:
        return {
            "section_gap": self.section_gap,
            "dialogue_section_gap": self.dialogue_section_gap,
            "dialogue_gap": self.dialogue_gap,
            "paragraph_gap": self.paragraph_gap,
            "pressure_gap": self.pressure_gap,
        }


@dataclass(frozen=True)
class MasteringPreset:
    """Broadcast-grade DSP vocal EQ, de-essing, compression, and loudness preset."""

    name: str
    target_lufs: float = -16.0
    peak_ceiling: float = 0.891
    hpf_hz: float = 80.0
    mud_cut_hz: float = 260.0
    mud_cut_db: float = -2.0
    mud_cut_q: float = 1.1
    warmth_hz: float = 170.0
    warmth_db: float = 1.2
    warmth_q: float = 0.9
    presence_hz: float = 3400.0
    presence_db: float = 2.8
    presence_q: float = 1.0
    air_hz: float = 9500.0
    air_db: float = 1.2
    deess_low_hz: float = 5500.0
    deess_high_hz: float = 8500.0
    deess_threshold_db: float = -22.0
    deess_max_reduction_db: float = 4.5
    comp_threshold_db: float = -19.5
    comp_ratio: float = 3.0
    comp_knee_db: float = 6.0
    comp_attack_ms: float = 12.0
    comp_release_ms: float = 120.0


@dataclass(frozen=True)
class LanguageVoiceProfile:
    """Linguistic and prosodic fingerprint for one target language."""

    language: str
    display_name: str
    default_accent_weights: Dict[str, float]
    narrator_sampling: SamplingProfile
    dialogue_sampling: SamplingProfile
    question_temp_delta: float
    exclamation_temp_delta: float
    acoustic_gate: AcousticGateEnvelope
    enforce_inverted_punctuation: bool
    instruct_prosody_hint: str
    accent_instruct_hints: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class VideoTypeVoiceProfile:
    """Vocal persona, beat energy, pause choreography, and DSP mastering profile for a video type."""

    video_type: str
    pauses: PauseChoreography
    mastering: MasteringPreset
    beat_sampling_deltas: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    high_impact_sections: Tuple[str, ...] = ("hook", "payoff", "cta", "reveal", "discovery")
    use_option_micro_pauses: bool = False
    neutral_challenge_lock: bool = False
    support_multi_energy_roles: bool = False
    preferred_narrator_archetypes: Tuple[str, ...] = ("warm_narrator", "energetic_host")


@dataclass(frozen=True)
class VoiceBankEntry:
    """One audited reference audio take registered in the curated Voice Bank."""

    voice_id: str
    speaker_id: str
    language: str
    gender: str
    accent: str
    energy_tier: str
    archetypes: Tuple[str, ...]
    rel_path: str
    ref_text: str
    source: str
    f0_mean: float = 0.0
    f0_var: float = 0.0
    snr_db: float = 0.0
    lang_prob: float = 1.0
    active: bool = True
