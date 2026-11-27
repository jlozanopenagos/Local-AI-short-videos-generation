"""
assembly/common/audio_mix.py — Per-type BGM volume envelope expressions for FFmpeg `volume(eval=frame)`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class AudioEnvelopeSegment:
    """Time-windowed BGM volume adjustment anchored to a named script section."""

    section: str
    volume: float
    head_seconds: Optional[float] = None


@dataclass(frozen=True)
class AudioMixSpec:
    """Audio ducking & closure swell configuration for background music."""

    base_volume: float = 0.05
    closure_volume: float = 0.08
    segments: Tuple[AudioEnvelopeSegment, ...] = ()


def build_bgm_volume_expr(
    spec: AudioMixSpec,
    timings: Optional[Dict[str, Dict[str, float]]],
    opening_offset: float = 0.0,
    main_duration: float = 0.0,
    closure_duration: float = 0.0,
    volume_scale: float = 1.0,
) -> str:
    """
    Constructs an FFmpeg `volume` expression evaluated per frame (`eval='frame'`)
    with base bed, section-level boosts/dips, and closure swell.
    """
    scale = max(0.0, float(volume_scale))
    base = round(spec.base_volume * scale, 5)
    terms = [f"{base:.5f}"]

    norm_timings: Dict[str, Dict[str, float]] = {}
    if isinstance(timings, dict):
        for k, v in timings.items():
            if isinstance(v, dict) and "start" in v and "end" in v:
                norm_timings[str(k).strip().lower()] = v

    for seg in spec.segments:
        sec_info = norm_timings.get(seg.section.strip().lower())
        if not sec_info:
            continue
        t0 = round(opening_offset + float(sec_info["start"]), 3)
        t1 = round(opening_offset + float(sec_info["end"]), 3)
        if seg.head_seconds is not None:
            t1 = round(min(t1, t0 + float(seg.head_seconds)), 3)
        if t1 <= t0:
            continue
        delta = round(seg.volume * scale - base, 5)
        if abs(delta) > 1e-6:
            terms.append(f"{delta:+.5f}*between(t,{t0:.3f},{t1:.3f})")

    if closure_duration > 0 and main_duration > 0:
        c0 = round(opening_offset + float(main_duration), 3)
        c1 = round(c0 + float(closure_duration), 3)
        c_delta = round(spec.closure_volume * scale - base, 5)
        if abs(c_delta) > 1e-6:
            terms.append(f"{c_delta:+.5f}*between(t,{c0:.3f},{c1:.3f})")

    return "".join(terms)
