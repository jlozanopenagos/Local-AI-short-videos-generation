"""
assembly/common/easing.py — Per-beat camera motion & cosine/quadratic easing expressions for FFmpeg zoompan.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


_SUPPORTED_CURVES = {"cosine", "ease_in", "ease_out", "linear"}


@dataclass(frozen=True)
class MotionSpec:
    """Normalized camera zoom & pan trajectory across a single scene clip.

    - ``z_start``, ``z_end``: zoom factors (>= 1.0).
    - ``x_start``, ``x_end``: normalized horizontal pan center in [0.0, 1.0] (0.5 = centered).
    - ``y_start``, ``y_end``: normalized vertical pan center in [0.0, 1.0] (0.5 = centered, <0.5 biases higher).
    - ``curve``: easing function ("cosine", "ease_in", "ease_out", "linear").
    """

    z_start: float = 1.0
    z_end: float = 1.08
    x_start: float = 0.5
    x_end: float = 0.5
    y_start: float = 0.46
    y_end: float = 0.46
    curve: str = "cosine"


def _clamp(val: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, float(val)))


def _ease_expression(progress_expr: str, curve: str) -> str:
    c = (curve or "cosine").strip().lower()
    if c not in _SUPPORTED_CURVES:
        raise ValueError(f"Unsupported easing curve '{curve}'. Expected one of {sorted(_SUPPORTED_CURVES)}.")
    if c == "cosine":
        return f"(1-cos(PI*{progress_expr}))/2"
    if c == "ease_in":
        return f"({progress_expr}*{progress_expr})"
    if c == "ease_out":
        return f"(1-(1-{progress_expr})*(1-{progress_expr}))"
    return progress_expr


def _interp(start: float, end: float, ease_expr: str) -> str:
    delta = end - start
    if abs(delta) < 1e-6:
        return f"{start:.4f}"
    if delta > 0:
        return f"{start:.4f}+{delta:.4f}*{ease_expr}"
    return f"{start:.4f}-{abs(delta):.4f}*{ease_expr}"


def build_zoompan_expressions(spec: MotionSpec, frames: int) -> Tuple[str, str, str]:
    """Builds FFmpeg zoompan `(z_expr, x_expr, y_expr)` for a `MotionSpec` over `frames` frames."""
    z_start = max(1.0, float(spec.z_start))
    z_end = max(1.0, float(spec.z_end))
    x_start = _clamp(spec.x_start, 0.0, 1.0)
    x_end = _clamp(spec.x_end, 0.0, 1.0)
    y_start = _clamp(spec.y_start, 0.0, 1.0)
    y_end = _clamp(spec.y_end, 0.0, 1.0)

    denom = max(1, int(frames) - 1)
    progress_expr = f"min(on/{denom},1)"
    ease_expr = _ease_expression(progress_expr, spec.curve)

    z_expr = _interp(z_start, z_end, ease_expr)

    if abs(x_start - 0.5) < 1e-6 and abs(x_end - 0.5) < 1e-6:
        x_expr = "iw/2-(iw/zoom/2)"
    elif abs(x_end - x_start) < 1e-6:
        x_expr = f"(iw-iw/zoom)*{x_start:.4f}"
    else:
        x_expr = f"(iw-iw/zoom)*({_interp(x_start, x_end, ease_expr)})"

    if abs(y_start - 0.5) < 1e-6 and abs(y_end - 0.5) < 1e-6:
        y_expr = "ih/2-(ih/zoom/2)"
    elif abs(y_end - y_start) < 1e-6:
        y_expr = f"(ih-ih/zoom)*{y_start:.4f}"
    else:
        y_expr = f"(ih-ih/zoom)*({_interp(y_start, y_end, ease_expr)})"

    return z_expr, x_expr, y_expr
