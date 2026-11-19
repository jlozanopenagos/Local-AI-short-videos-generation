"""
assembly/common/transitions.py — Frame-accurate xfade duration budgeting and filter-graph chaining.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Tuple

# pyrefly: ignore [missing-import]
import ffmpeg


@dataclass(frozen=True)
class TransitionSpec:
    """Smooth FFmpeg `xfade` transition specification between two adjacent scene clips."""

    name: str = "fade"
    duration: float = 0.22


def compute_clip_render_durations(
    scene_durations: List[float],
    transitions: List[TransitionSpec],
    fps: int = 25,
) -> Tuple[List[float], List[float], List[float]]:
    """
    Computes frame-aligned `(render_durations, effective_xfades, offsets)` so that
    chaining non-overlapping audio timing windows with FFmpeg `xfade` preserves
    exact cumulative A/V synchronization (`offsets[-1] + scene_durations[-1] == total_duration`).
    """
    n = len(scene_durations)
    if n == 0:
        return [], [], []
    if n == 1:
        frames_0 = max(2, int(round(scene_durations[0] * fps)))
        return [round(frames_0 / fps, 4)], [], []

    # Snap cumulative audio cut points to exact integer frames to prevent drift or xfade underflows
    cum_frames: List[int] = []
    running_sec = 0.0
    for idx, dur in enumerate(scene_durations):
        running_sec += max(0.08, float(dur))
        target_cum = max(
            (cum_frames[-1] + 2) if cum_frames else 2,
            int(round(running_sec * fps)),
        )
        cum_frames.append(target_cum)

    snapped_scene_frames = [
        cum_frames[0] if i == 0 else cum_frames[i] - cum_frames[i - 1]
        for i in range(n)
    ]

    effective_xfades: List[float] = []
    xfade_frames_list: List[int] = []
    offsets: List[float] = []

    for i in range(n - 1):
        tr = transitions[i] if i < len(transitions) else TransitionSpec()
        dur_a = snapped_scene_frames[i] / fps
        dur_b = snapped_scene_frames[i + 1] / fps
        tr_name = (tr.name or "").strip().lower()
        if tr_name in ("none", "", "cut") or tr.duration <= 0 or min(dur_a, dur_b) < 0.30:
            t_frames = 0
        else:
            raw_t = min(float(tr.duration), dur_a * 0.38, dur_b * 0.38)
            t_frames = max(1, int(round(raw_t * fps)))
        # Ensure overlap cannot consume entire previous or next clip
        max_allowed_frames = max(0, min(snapped_scene_frames[i] - 1, snapped_scene_frames[i + 1] - 1))
        t_frames = min(t_frames, max_allowed_frames)
        xfade_frames_list.append(t_frames)
        effective_xfades.append(round(t_frames / fps, 4))
        offsets.append(round(cum_frames[i] / fps, 4))

    render_durations: List[float] = []
    for i in range(n - 1):
        render_frames = snapped_scene_frames[i] + xfade_frames_list[i]
        render_durations.append(round(render_frames / fps, 4))
    render_durations.append(round(snapped_scene_frames[-1] / fps, 4))

    return render_durations, effective_xfades, offsets


def chain_clips_with_xfade(
    streams: List[Any],
    transitions: List[TransitionSpec],
    effective_xfades: List[float],
    offsets: List[float],
) -> Any:
    """Chains normalized 25fps video streams via `xfade` (falling back to `concat` when xfade duration is 0)."""
    if not streams:
        raise ValueError("Cannot chain an empty list of video streams.")
    cur = streams[0]
    for i in range(len(streams) - 1):
        eff_t = effective_xfades[i] if i < len(effective_xfades) else 0.0
        tr = transitions[i] if i < len(transitions) else TransitionSpec()
        if eff_t > 0.0:
            cur = ffmpeg.filter(
                [cur, streams[i + 1]],
                "xfade",
                transition=tr.name,
                duration=eff_t,
                offset=offsets[i],
            )
        else:
            cur = ffmpeg.concat(cur, streams[i + 1], v=1, a=0)
    return cur
