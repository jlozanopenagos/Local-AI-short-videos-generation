"""
assembly/common/pacing.py — Anchor-aware equal-time image pacing for Stage G video assembly.
"""
from __future__ import annotations

from typing import Any, Dict, FrozenSet, List


def compute_equalized_visual_durations(
    sections: List[Dict[str, Any]],
    audio_durations: List[float],
    locked_sections: FrozenSet[str] = frozenset(),
) -> List[float]:
    """Distributes visual screen time equally across each contiguous unlocked run of distinct images,
    while keeping locked sections (e.g. GAME `challenge` chalkboard and `pressure` countdown)
    strictly aligned to their exact spoken audio intervals.

    Always preserves exact cumulative total duration (`sum(out) == sum(audio_durations)`).
    """
    n = len(sections)
    if n == 0 or len(audio_durations) != n:
        return [float(d) for d in audio_durations]

    locked_lower = {s.strip().lower() for s in locked_sections}

    def _is_locked(sec_entry: Dict[str, Any]) -> bool:
        sec_name = str(sec_entry.get("section", "")).strip().lower()
        return (sec_name in locked_lower) or bool(sec_entry.get("is_chalkboard", False))

    out: List[float] = []
    i = 0
    while i < n:
        if _is_locked(sections[i]):
            out.append(round(float(audio_durations[i]), 4))
            i += 1
            continue

        start = i
        while i < n and not _is_locked(sections[i]):
            i += 1
        end = i
        k = end - start
        run_total = sum(float(audio_durations[j]) for j in range(start, end))

        if k == 1:
            out.append(round(run_total, 4))
        else:
            base = round(run_total / k, 4)
            for _ in range(k - 1):
                out.append(base)
            out.append(round(run_total - base * (k - 1), 4))

    return out
