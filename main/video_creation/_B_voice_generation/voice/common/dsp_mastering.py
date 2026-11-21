"""
voice/common/dsp_mastering.py — Pure numpy + scipy broadcast vocal mastering chain.

Applies sub-rumble HPF, subtractive mud cut, warm chest lift, narrator presence EQ,
high-frequency air shelf, split-band sibilance de-esser, soft-knee RMS compressor,
ITU-R BS.1770 LUFS target leveling, and smooth lookahead true-peak ceiling limiting.
"""
from __future__ import annotations

from typing import Callable, Tuple

# pyrefly: ignore [missing-import]
import numpy as np

from .models import MasteringPreset


def _peaking_eq_sos(fc: float, sr: int, gain_db: float, q: float = 1.0) -> np.ndarray:
    """RBJ peaking EQ filter as single-section SOS."""
    if abs(gain_db) < 0.05 or fc <= 10.0 or fc >= 0.45 * sr:
        return np.array([[1.0, 0.0, 0.0, 1.0, 0.0, 0.0]], dtype=np.float64)
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * fc / float(sr)
    alpha = np.sin(w0) / (2.0 * max(0.1, q))
    cos_w0 = np.cos(w0)
    b0 = 1.0 + alpha * A
    b1 = -2.0 * cos_w0
    b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha / A
    return np.array([[b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]], dtype=np.float64)


def _high_shelf_sos(fc: float, sr: int, gain_db: float, slope: float = 0.7) -> np.ndarray:
    """RBJ high-shelf EQ filter as single-section SOS."""
    if abs(gain_db) < 0.05 or fc <= 20.0 or fc >= 0.45 * sr:
        return np.array([[1.0, 0.0, 0.0, 1.0, 0.0, 0.0]], dtype=np.float64)
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * fc / float(sr)
    cos_w0 = np.cos(w0)
    sin_w0 = np.sin(w0)
    alpha = (sin_w0 / 2.0) * np.sqrt(max(0.01, (A + 1.0 / A) * (1.0 / max(0.1, slope) - 1.0) + 2.0))
    two_sqrt_A_alpha = 2.0 * np.sqrt(A) * alpha
    b0 = A * ((A + 1.0) + (A - 1.0) * cos_w0 + two_sqrt_A_alpha)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w0)
    b2 = A * ((A + 1.0) + (A - 1.0) * cos_w0 - two_sqrt_A_alpha)
    a0 = (A + 1.0) - (A - 1.0) * cos_w0 + two_sqrt_A_alpha
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos_w0)
    a2 = (A + 1.0) - (A - 1.0) * cos_w0 - two_sqrt_A_alpha
    return np.array([[b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]], dtype=np.float64)


def _envelope_follower_blocks(
    mono_sq: np.ndarray,
    sr: int,
    attack_ms: float,
    release_ms: float,
    block_ms: float = 2.0,
) -> Tuple[np.ndarray, int]:
    """Fast C-vectorized RMS envelope at block resolution with attack/release smoothing."""
    n = len(mono_sq)
    block = max(16, int(round(block_ms * 0.001 * sr)))
    pad = (-n) % block
    if pad:
        mono_sq = np.pad(mono_sq, (0, pad), mode="constant")
    blocks = mono_sq.reshape(-1, block)
    block_rms = np.sqrt(np.mean(blocks, axis=1) + 1e-12)

    dt = block / float(sr)
    att_coeff = np.exp(-dt / max(1e-4, attack_ms * 0.001))
    rel_coeff = np.exp(-dt / max(1e-4, release_ms * 0.001))

    env = np.empty_like(block_rms)
    cur = float(block_rms[0]) if len(block_rms) else 0.0
    for idx, val in enumerate(block_rms):
        v = float(val)
        c = att_coeff if v > cur else rel_coeff
        cur = c * cur + (1.0 - c) * v
        env[idx] = cur

    # Linearly upsample block envelope to sample resolution
    x_blocks = (np.arange(len(env)) + 0.5) * block
    x_samples = np.arange(n, dtype=np.float64)
    return np.interp(x_samples, x_blocks, env), block


def _soft_knee_gain_db(level_db: np.ndarray, threshold_db: float, ratio: float, knee_db: float) -> np.ndarray:
    """Computes static compressor gain reduction (<= 0 dB) with smooth soft knee."""
    if ratio <= 1.0:
        return np.zeros_like(level_db)
    half_k = max(0.0, knee_db * 0.5)
    diff = level_db - threshold_db
    gr_db = np.zeros_like(level_db)

    if half_k > 0.0:
        in_knee = (diff > -half_k) & (diff < half_k)
        gr_db[in_knee] = (1.0 / ratio - 1.0) * ((diff[in_knee] + half_k) ** 2) / (2.0 * knee_db)
    above = diff >= half_k
    gr_db[above] = (1.0 / ratio - 1.0) * diff[above]
    return gr_db


def apply_vocal_mastering(
    data: np.ndarray,
    sr: int,
    preset: MasteringPreset,
    lufs_fn: Callable[[np.ndarray, int], float],
) -> Tuple[np.ndarray, float, float]:
    """Runs the full per-type studio mastering chain on mono or stereo audio arrays.

    Returns:
        `(mastered_float32, original_lufs, final_lufs)`
    """
    if len(data) == 0:
        return data.astype(np.float32), -70.0, -70.0

    orig_lufs = float(lufs_fn(data, sr))
    x = np.nan_to_num(np.asarray(data, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    is_stereo = x.ndim > 1

    try:
        # pyrefly: ignore [missing-import]
        from scipy import signal

        # 1. Sub-rumble Butterworth HPF
        nyq = 0.5 * float(sr)
        hp_wn = max(0.0005, min(0.95, preset.hpf_hz / nyq))
        sos_hp = signal.butter(2, hp_wn, btype="highpass", output="sos")

        # 2. Subtractive mud cut + warm chest body + front-of-mix clarity presence + air shelf
        sos_mud = _peaking_eq_sos(preset.mud_cut_hz, sr, preset.mud_cut_db, preset.mud_cut_q)
        sos_warm = _peaking_eq_sos(preset.warmth_hz, sr, preset.warmth_db, preset.warmth_q)
        sos_pres = _peaking_eq_sos(preset.presence_hz, sr, preset.presence_db, preset.presence_q)
        sos_air = _high_shelf_sos(preset.air_hz, sr, preset.air_db)

        sos_chain = np.vstack([sos_hp, sos_mud, sos_warm, sos_pres, sos_air])
        y = signal.sosfilt(sos_chain, x, axis=0)

        # 3. Split-band dynamic de-esser (tames harsh sibilance while leaving body intact)
        sib_low = max(100.0, preset.deess_low_hz)
        sib_high = min(0.45 * sr, preset.deess_high_hz)
        if sib_high > sib_low + 200.0 and len(y) > 64:
            sos_sib = signal.butter(2, [sib_low / nyq, sib_high / nyq], btype="bandpass", output="sos")
            sib_band = signal.sosfilt(sos_sib, y, axis=0)
            sib_mono = np.mean(sib_band, axis=1) if is_stereo else sib_band
            sib_env, _ = _envelope_follower_blocks(sib_mono ** 2, sr, attack_ms=2.0, release_ms=45.0, block_ms=2.0)
            sib_db = 20.0 * np.log10(np.maximum(sib_env, 1e-7))
            deess_gr_db = np.clip(
                -(np.maximum(0.0, sib_db - preset.deess_threshold_db) * 0.65),
                -abs(preset.deess_max_reduction_db),
                0.0,
            )
            deess_atten = 1.0 - (10.0 ** (deess_gr_db / 20.0))
            if is_stereo:
                y = y - sib_band * deess_atten[:, None]
            else:
                y = y - sib_band * deess_atten

        # 4. Smooth soft-knee RMS vocal compressor
        if preset.comp_ratio > 1.01 and len(y) > 64:
            y_mono = np.mean(y, axis=1) if is_stereo else y
            env, _ = _envelope_follower_blocks(
                y_mono ** 2,
                sr,
                attack_ms=preset.comp_attack_ms,
                release_ms=preset.comp_release_ms,
                block_ms=2.5,
            )
            level_db = 20.0 * np.log10(np.maximum(env, 1e-7))
            gr_db = _soft_knee_gain_db(level_db, preset.comp_threshold_db, preset.comp_ratio, preset.comp_knee_db)
            comp_gain = 10.0 ** (gr_db / 20.0)
            if is_stereo:
                y = y * comp_gain[:, None]
            else:
                y = y * comp_gain
    except Exception:
        y = x.copy()

    # 5. ITU-R BS.1770 LUFS target leveling
    post_eq_lufs = float(lufs_fn(y, sr))
    if post_eq_lufs > -60.0:
        gain_db = max(-24.0, min(24.0, preset.target_lufs - post_eq_lufs))
        y = y * (10.0 ** (gain_db / 20.0))

    # 6. Smooth soft-clip peak limiter above 85% of ceiling so loudness isn't pulled down by 1 transient
    ceiling = float(preset.peak_ceiling)
    knee_start = ceiling * 0.85
    abs_y = np.abs(y)
    max_peak = float(np.max(abs_y)) if len(abs_y) else 0.0
    if max_peak > knee_start:
        headroom = max(1e-5, ceiling - knee_start)
        over = np.maximum(0.0, abs_y - knee_start)
        compressed_abs = np.where(
            abs_y > knee_start,
            knee_start + headroom * np.tanh(over / headroom),
            abs_y,
        )
        y = np.sign(y) * compressed_abs
        final_peak = float(np.max(np.abs(y)))
        if final_peak > ceiling:
            y = y * (ceiling / final_peak)

    y = np.nan_to_num(y, nan=0.0, posinf=ceiling, neginf=-ceiling).astype(np.float32)
    final_lufs = float(lufs_fn(y, sr))
    return y, orig_lufs, final_lufs
