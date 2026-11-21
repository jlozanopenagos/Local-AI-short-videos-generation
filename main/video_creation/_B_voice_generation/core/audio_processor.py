import json
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import soundfile as sf
from pathlib import Path
from typing import Dict, List, Optional

def trim_audio_silence(
    data: np.ndarray,
    sr: int,
    threshold: float = 0.012,
    pad_leading: float = 0.025,
    pad_trailing: float = 0.05
) -> np.ndarray:
    """Trims both leading dead silence (from neural TTS latency) and trailing silence
    from generated segments to ensure crisp, human-like turn-taking pacing.
    """
    if len(data) == 0:
        return data
    abs_data = np.abs(data)
    if len(abs_data.shape) > 1:
        abs_data = np.max(abs_data, axis=1)
    non_silent = np.where(abs_data > threshold)[0]
    if len(non_silent) > 0:
        lead_samples = int(pad_leading * sr)
        trail_samples = int(pad_trailing * sr)
        start_idx = max(0, non_silent[0] - lead_samples)
        end_idx = min(len(data), non_silent[-1] + trail_samples)
        return data[start_idx:end_idx]
    return data

def trim_trailing_silence(data: np.ndarray, sr: int, threshold: float = 0.01, pad_seconds: float = 0.15) -> np.ndarray:
    """Trims trailing dead silence from generated TTS segments (backwards-compatible alias)."""
    return trim_audio_silence(data, sr, threshold=threshold, pad_leading=0.0, pad_trailing=pad_seconds)

def create_k_weighting_filter(fs: int):
    """Generates coefficients for ITU-R BS.1770 K-weighting pre-filter and RLB filter."""
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = np.tan(np.pi * f0 / fs)
    Vh = 10.0 ** (G / 20.0)
    Vb = Vh ** 0.4996667741545416
    a0 = 1.0 + K / Q + K * K
    b_pre = [(Vh + Vb * K / Q + K * K) / a0, 2.0 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a_pre = [1.0, 2.0 * (K * K - 1.0) / a0, (1.0 - K / Q + K * K) / a0]

    f0, Q = 38.13547087602444, 0.5003270373238773
    K = np.tan(np.pi * f0 / fs)
    a0 = 1.0 + K / Q + K * K
    b_rlb = [1.0 / a0, -2.0 / a0, 1.0 / a0]
    a_rlb = [1.0, 2.0 * (K * K - 1.0) / a0, (1.0 - K / Q + K * K) / a0]
    return (b_pre, a_pre), (b_rlb, a_rlb)

def measure_lufs(data: np.ndarray, sr: int) -> float:
    """Calculates integrated loudness in LUFS according to ITU-R BS.1770."""
    if len(data) == 0:
        return -70.0
    mono = np.mean(data, axis=1) if len(data.shape) > 1 else data
    try:
        # pyrefly: ignore[missing-import]
        from scipy import signal
        (b_pre, a_pre), (b_rlb, a_rlb) = create_k_weighting_filter(sr)
        y1 = signal.lfilter(b_pre, a_pre, mono)
        y2 = signal.lfilter(b_rlb, a_rlb, y1)
        ms = np.mean(y2 ** 2)
        if ms <= 1e-12:
            return -70.0
        return float(-0.691 + 10.0 * np.log10(ms))
    except Exception:
        # Fallback approximation via RMS
        rms = float(np.sqrt(np.mean(mono ** 2)))
        if rms <= 1e-6:
            return -70.0
        return float(-0.691 + 20.0 * np.log10(rms))

def master_and_normalize_audio(
    data: np.ndarray,
    sr: int,
    target_lufs: float = -16.0,
    peak_ceiling: float = 0.891,
    mastering_preset=None,
) -> tuple:
    """Applies studio post-processing and EBU R128 loudness normalization:
    When `mastering_preset` is supplied (typed mode), runs the per-type DSP vocal chain
    (HPF, mud cut, warmth, narrator clarity boost EQ, split-band de-esser, RMS compressor,
    ITU-R BS.1770 LUFS target, and soft-clip ceiling limiter).
    Returns:
        (mastered_data, original_lufs, final_lufs)
    """
    if len(data) == 0:
        return data, -70.0, -70.0

    if mastering_preset is not None:
        try:
            try:
                from video_creation._B_voice_generation.voice.common.dsp_mastering import apply_vocal_mastering
            except (ImportError, ModuleNotFoundError):
                try:
                    from ..voice.common.dsp_mastering import apply_vocal_mastering  # type: ignore[no-redef]
                except (ImportError, ValueError):
                    from voice.common.dsp_mastering import apply_vocal_mastering  # type: ignore[no-redef]
            return apply_vocal_mastering(data, sr, mastering_preset, measure_lufs)
        except Exception:
            pass

    try:
        # pyrefly: ignore[missing-import]
        from scipy import signal
        # 1. 80Hz rumble cut
        b_hp, a_hp = signal.butter(2, 80 / (sr / 2), btype='highpass')
        cleaned = signal.lfilter(b_hp, a_hp, data, axis=0)
    except Exception:
        cleaned = data.copy()

    # 2. Measure loudness
    cur_lufs = measure_lufs(cleaned, sr)
    if cur_lufs > -60.0:
        gain_db = target_lufs - cur_lufs
        # Limit extreme gain jumps (-24dB to +24dB)
        gain_db = max(-24.0, min(24.0, gain_db))
        gain_lin = 10.0 ** (gain_db / 20.0)
        boosted = cleaned * gain_lin
    else:
        boosted = cleaned

    # 3. Soft peak limiter (prevent clipping above peak_ceiling)
    abs_b = np.abs(boosted)
    peak = np.max(abs_b)
    if peak > peak_ceiling:
        scale = peak_ceiling / peak
        boosted = boosted * scale

    final_lufs = measure_lufs(boosted, sr)
    return boosted.astype(np.float32), cur_lufs, final_lufs


def _resolve_transition_pause(prev_seg: Dict, cur_seg: Dict, pauses: Dict[str, float], pause_choreography=None) -> float:
    prev_sec = (prev_seg.get("section") or "").lower()
    cur_sec = (cur_seg.get("section") or "").lower()
    is_prev_diag = "dialogue" in prev_sec
    is_cur_diag = "dialogue" in cur_sec

    # MUST-KEEP: Quiz countdown pause before answer reveal
    if prev_sec == "pressure" and cur_sec == "answer":
        if pause_choreography is not None:
            return float(pause_choreography.pressure_gap)
        return float(pauses.get("pressure_gap", 2.20))

    if pause_choreography is not None:
        if cur_sec in ("discovery", "reveal") and prev_sec != cur_sec and pause_choreography.pre_discovery_gap is not None:
            return float(pause_choreography.pre_discovery_gap)
        if prev_sec == "hook" and cur_sec != "hook" and pause_choreography.hook_to_next_gap is not None:
            return float(pause_choreography.hook_to_next_gap)
        if prev_sec == "answer" and cur_sec == "explanation" and pause_choreography.answer_to_explanation_gap is not None:
            return float(pause_choreography.answer_to_explanation_gap)
        if is_prev_diag and not is_cur_diag and cur_sec == "payoff" and pause_choreography.dialogue_to_payoff_gap is not None:
            return float(pause_choreography.dialogue_to_payoff_gap)
        if is_prev_diag and is_cur_diag:
            if prev_seg["speaker"] != cur_seg["speaker"]:
                if prev_seg.get("is_cliffhanger"):
                    return float(pause_choreography.dialogue_cliffhanger_gap)
                return float(pause_choreography.dialogue_gap)
            return float(pause_choreography.dialogue_section_gap)
        if prev_sec != cur_sec:
            return float(pause_choreography.section_gap)
        if prev_seg["speaker"] != cur_seg["speaker"]:
            return float(pause_choreography.dialogue_gap)
        return float(pause_choreography.paragraph_gap)

    if is_prev_diag and is_cur_diag:
        if prev_seg["speaker"] != cur_seg["speaker"]:
            return float(pauses.get("dialogue_gap", 0.08))
        return float(pauses.get("dialogue_section_gap", 0.12))
    if prev_sec != cur_sec:
        return float(pauses.get("section_gap", 0.30))
    if prev_seg["speaker"] != cur_seg["speaker"]:
        return float(pauses.get("dialogue_gap", 0.08))
    return float(pauses.get("paragraph_gap", 0.20))


def concatenate_audios(
    segments_metadata: List[Dict],
    output_path: Path,
    pauses: Optional[Dict[str, float]] = None,
    pause_choreography=None,
    mastering_preset=None,
) -> Optional[Path]:
    """Concatenates multiple audio segment files into a single master audio file.
    Inserts silent pauses based on transition types (or per-type PauseChoreography in typed mode).
    """
    if not segments_metadata:
        print("No segments provided for audio concatenation.")
        return None

    if not pauses:
        try:
            import config
            pauses = getattr(config, "DEFAULT_PAUSES", None)
        except Exception:
            pauses = None
        if not pauses:
            pauses = {
                "section_gap": 0.35,
                "dialogue_section_gap": 0.20,
                "dialogue_gap": 0.15,
                "paragraph_gap": 0.20,
                "pressure_gap": 2.20
            }

    combined_data = []
    master_samplerate = None
    num_channels = 1

    current_sample = 0
    section_timings = {}

    for i, seg in enumerate(segments_metadata):
        path = Path(seg["path"])
        if not path.exists():
            print(f"Warning: Audio file {path} not found. Skipping.")
            continue

        data, sr = sf.read(str(path))
        # Trim both leading dead latency and trailing dead silence
        data = trim_audio_silence(data, sr, threshold=0.012, pad_leading=0.025, pad_trailing=0.05)

        if master_samplerate is None:
            master_samplerate = sr
            if len(data.shape) > 1:
                num_channels = data.shape[1]
            else:
                num_channels = 1

        if sr != master_samplerate:
            print(f"Warning: Samplerate mismatch for {path.name} ({sr} vs master {master_samplerate}).")

        # Insert pause if this is not the first segment
        if i > 0 and combined_data:
            prev_seg = segments_metadata[i - 1]
            pause_duration = _resolve_transition_pause(prev_seg, seg, pauses, pause_choreography=pause_choreography)

            if pause_duration > 0:
                num_pause_samples = int(pause_duration * master_samplerate)
                if num_channels > 1:
                    silence = np.zeros((num_pause_samples, num_channels), dtype=data.dtype)
                else:
                    silence = np.zeros(num_pause_samples, dtype=data.dtype)
                combined_data.append(silence)
                current_sample += num_pause_samples

        section = seg["section"]
        if section not in section_timings:
            section_timings[section] = {"start": current_sample / master_samplerate, "end": 0.0}

        combined_data.append(data)
        current_sample += len(data)
        section_timings[section]["end"] = current_sample / master_samplerate

    if combined_data:
        merged = np.concatenate(combined_data, axis=0)
        target_lufs = float(mastering_preset.target_lufs) if mastering_preset is not None else -16.0
        peak_ceiling = float(mastering_preset.peak_ceiling) if mastering_preset is not None else 0.891
        mastered, cur_lufs, final_lufs = master_and_normalize_audio(
            merged,
            master_samplerate,
            target_lufs=target_lufs,
            peak_ceiling=peak_ceiling,
            mastering_preset=mastering_preset,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), mastered, master_samplerate)
        preset_tag = f" [{mastering_preset.name}]" if mastering_preset is not None else ""
        print(f"Merged audio successfully mastered{preset_tag} ({cur_lufs:.1f} -> {final_lufs:.1f} LUFS) and saved to: {output_path}")

        # Save timings map
        timings_path = output_path.parent / "timings.json"
        with timings_path.open("w", encoding="utf-8") as f:
            json.dump(section_timings, f, indent=2)

        return output_path

    return None
