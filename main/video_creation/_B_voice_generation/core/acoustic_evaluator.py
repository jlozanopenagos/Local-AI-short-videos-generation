"""Acoustic Prominence Quality Gate and Multi-Candidate Evaluator.

Evaluates synthesized speech takes for syllable stress contrast, energy ratios,
and pronunciation fidelity using faster-whisper word-level alignment and RMS energy.

Part of Option B Architecture:
- Evaluates N candidate audio takes for stress-vital segments.
- Automatically rejects hallucinations, skipped words, and syllable stuttering.
- Selects the candidate with the highest acoustic prominence contrast score.
- Cleans up rejected candidates to conserve disk space.
"""

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
import soundfile as sf

logger = logging.getLogger(__name__)

# Global singleton for Whisper model to avoid reloading overhead across takes
_WHISPER_MODEL = None

NOUN_DETERMINERS = {
    "a", "an", "the", "this", "that", "these", "those",
    "my", "your", "his", "her", "its", "our", "their",
    "noun", "lovely", "big", "new", "great", "whole", "good"
}

VERB_MARKERS = {
    "to", "will", "would", "shall", "should", "can", "could",
    "may", "might", "must", "did", "do", "does", "verb",
    "i", "you", "he", "she", "it", "we", "they"
}


def get_whisper_model(model_size: str = "tiny", device: str = "cpu"):
    """Lazily load faster-whisper model singleton on CPU."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        try:
            # pyrefly: ignore[missing-import]
            from faster_whisper import WhisperModel
            # Attempt int8 first; fall back to float32 if needed
            try:
                _WHISPER_MODEL = WhisperModel(model_size, device=device, compute_type="int8")
            except Exception:
                _WHISPER_MODEL = WhisperModel(model_size, device=device, compute_type="float32")
        except Exception as exc:
            logger.warning(f"Could not load faster-whisper model: {exc}")
            return None
    return _WHISPER_MODEL


def detect_roles_in_text(text: str, target_words: List[str]) -> List[Tuple[str, str]]:
    """Determines whether each occurrence of target_words in text is a 'noun' or 'verb'.
    
    Uses both uppercase syllable markers (e.g. PREsent vs preSENT) and syntactic
    carrier phrases / determiners / verb markers.
    
    Returns:
        List of (token_matched, 'noun' | 'verb') in sequential appearance order.
    """
    if not text or not target_words:
        return []

    tokens = re.findall(r"[\w'-]+", text)
    occurrences = []

    # Map stems for flexible matching (e.g. 'present' -> 'pres')
    stems = {w.lower()[:4]: w.lower() for w in target_words}

    for i, token in enumerate(tokens):
        clean_tok = token.strip("'-").lower()
        matched_stem = None
        for stem in stems:
            if stem in clean_tok:
                matched_stem = stem
                break

        if not matched_stem:
            continue

        role = None
        raw = token.strip("'-")

        # 1. Visual casing is the absolute highest priority intent:
        # e.g. REcord, PERmit, PROject, PREsent -> NOUN (1st syllable stressed)
        # e.g. reCORD, perMIT, proJECT, preSENT -> VERB (2nd syllable stressed)
        raw_no_dash = raw.replace("-", "")
        if len(raw_no_dash) >= 4:
            if re.search(r'^[A-Z]{2,}[a-z]+', raw_no_dash) or (raw_no_dash[:2].isupper() and raw_no_dash[-2:].islower()):
                role = "noun"
            elif re.search(r'^[a-z]+[A-Z]{2,}', raw_no_dash) or (raw_no_dash[:2].islower() and raw_no_dash[-2:].isupper()):
                role = "verb" 

        # 2. Check preceding carrier / determiner context (closest marker takes precedence)
        if not role:
            for j in range(i - 1, max(-1, i - 4), -1):
                prev_tok = tokens[j].lower()
                if prev_tok in VERB_MARKERS:
                    role = "verb"
                    break
                elif prev_tok in NOUN_DETERMINERS:
                    role = "noun"
                    break

        # 3. Default fallback
        if not role:
            role = "noun"

        occurrences.append((token, role))

    return occurrences


def evaluate_acoustic_prominence(
    audio_path: Union[str, Path],
    target_words: List[str],
    text_context: str = ""
) -> Tuple[float, Dict[str, Any]]:
    """Evaluates the acoustic stress prominence of target heteronym words in an audio file.
    
    Args:
        audio_path: Path to the generated segment audio (.flac or .wav).
        target_words: List of target heteronyms (e.g. ['present'] or ['project']).
        text_context: Reference script text used to determine expected noun vs verb roles.
        
    Returns:
        (score, details_dict):
          - score: Higher is better (> 1.2 indicates distinct stress contrast).
                   Negative scores indicate errors (-10.0 for missing/garbled words).
          - details_dict: Detailed metrics including occurrences, ratios, and transcript.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        return -100.0, {"error": f"Audio file {audio_path} does not exist or is empty"}

    try:
        data, sr = sf.read(str(audio_path))
    except Exception as exc:
        return -100.0, {"error": f"Failed to read audio file: {exc}"}

    if len(data.shape) > 1:
        data = data[:, 0]  # Mono

    duration = len(data) / sr
    if duration < 0.2:
        return -100.0, {"error": f"Audio duration too short: {duration:.2f}s"}

    model = get_whisper_model()
    if model is None:
        # Fallback if whisper is unavailable: return neutral positive score
        return 1.0, {"warning": "faster-whisper model unavailable; bypass evaluation"}

    # Transcribe with word timestamps
    try:
        segments, _ = model.transcribe(str(audio_path), language="en", word_timestamps=True)
        words = []
        transcript_lines = []
        for s in segments:
            transcript_lines.append(s.text.strip())
            for w in (s.words or []):
                words.append((w.word.strip().lower(), w.start, w.end))
        full_transcript = " ".join(transcript_lines)
    except Exception as exc:
        logger.warning(f"Whisper transcription failed for {audio_path}: {exc}")
        return 1.0, {"warning": f"Whisper error: {exc}"}

    # Match expected roles from text context
    expected_roles = detect_roles_in_text(text_context, target_words)

    # Locate detected target words in Whisper transcript
    # Allow phonetic variant spellings that Whisper outputs for heteronym learner errors
    # (e.g. 'rycord', 'ry-cord' for intentional verb 'reCORD'; 'purmit' for 'PERmit')
    PHONETIC_WHISPER_VARIANTS = {
        "reco": ["ryco", "ri-c", "re-c", "ry-k"],
        "perm": ["purm"],
        "pres": ["priz"],
        "proj": ["pruh"],
        "obje": ["ubje"]
    }
    detected = []
    stems = {w.lower()[:4]: w.lower() for w in target_words}
    for w_text, st, en in words:
        clean_w = re.sub(r"[^\w]", "", w_text).lower()
        matched = False
        for stem in stems:
            if stem in clean_w:
                detected.append((w_text, st, en))
                matched = True
                break
            # Check phonetic variants
            for variant in PHONETIC_WHISPER_VARIANTS.get(stem, []):
                if variant in clean_w:
                    detected.append((w_text, st, en))
                    matched = True
                    break
            if matched:
                break

    if not detected:
        return -10.0, {
            "error": "Target words not detected in transcript",
            "transcript": full_transcript,
            "expected_count": len(expected_roles),
            "detected_count": 0
        }

    # Check for split word tokens (e.g., 'pro' followed by 'ject' as separate words)
    has_split_words = False
    for i in range(len(words) - 1):
        w1 = re.sub(r"[^\w]", "", words[i][0])
        w2 = re.sub(r"[^\w]", "", words[i + 1][0])
        if (w1 == "pro" and w2.startswith("ject")) or (w1 == "pre" and w2.startswith("sent")):
            has_split_words = True
            break

    # Penalty factor for missing occurrences or split tokens
    penalty = 1.0
    if len(expected_roles) > 0 and len(detected) < len(expected_roles):
        penalty *= 0.5 * (len(detected) / len(expected_roles))
    if has_split_words:
        penalty *= 0.2  # Severe penalty for BPE splitting ("pro ejct")

    occurrence_details = []
    ratios = []

    for idx, (w_text, st, en) in enumerate(detected):
        # Determine expected role for this occurrence
        if idx < len(expected_roles):
            role = expected_roles[idx][1]
        else:
            role = "noun" if idx == 0 else "verb"

        s_idx = max(0, int(st * sr))
        e_idx = min(len(data), int(en * sr))
        clip = data[s_idx:e_idx]

        if len(clip) < 50:
            continue

        # Trim leading and trailing low-energy silence to isolate vocalic syllables
        peak = np.max(np.abs(clip))
        th = peak * 0.08
        active_idx = np.where(np.abs(clip) > th)[0]
        if len(active_idx) > 20:
            clip = clip[active_idx[0]:active_idx[-1] + 1]

        mid = len(clip) // 2
        e1 = float(np.sqrt(np.mean(clip[:mid] ** 2)))
        e2 = float(np.sqrt(np.mean(clip[mid:] ** 2)))

        if role == "noun":
            # Noun: Syllable 1 prominence (E1 / E2 > 1.0)
            ratio = e1 / max(1e-5, e2)
        else:
            # Verb: Syllable 2 prominence (E2 / E1 > 1.0)
            ratio = e2 / max(1e-5, e1)

        ratios.append(ratio)
        occurrence_details.append({
            "word": w_text,
            "role": role,
            "start": round(st, 2),
            "end": round(en, 2),
            "e1": round(e1, 4),
            "e2": round(e2, 4),
            "ratio": round(ratio, 2)
        })

    if not ratios:
        return -5.0, {
            "error": "Could not extract syllable energy for detected words",
            "transcript": full_transcript
        }

    # Geometric mean of ratios ensures balanced contrast across multiple occurrences
    base_score = float(np.prod(ratios) ** (1.0 / len(ratios)))
    final_score = round(base_score * penalty, 2)

    details = {
        "score": final_score,
        "transcript": full_transcript,
        "occurrences": occurrence_details,
        "penalty": penalty,
        "split_words": has_split_words
    }

    return final_score, details


def select_best_voice_candidate(
    candidate_paths: List[Path],
    target_words: List[str],
    text_context: str,
    dest_path: Path
) -> Path:
    """Evaluates multiple voice takes and promotes the highest scoring candidate to dest_path.
    
    Cleans up all non-winning candidate files to prevent disk pollution.
    
    Args:
        candidate_paths: List of file paths to generated candidate audio takes.
        target_words: Target heteronyms to audit for syllable prominence.
        text_context: Original text context to determine expected stress roles.
        dest_path: The target destination path for the winning segment audio.
        
    Returns:
        The dest_path containing the winning audio take.
    """
    dest_path = Path(dest_path)
    if not candidate_paths:
        return dest_path

    # If only a single candidate was generated, promote directly
    if len(candidate_paths) == 1:
        winner = candidate_paths[0]
        if winner != dest_path:
            shutil.move(str(winner), str(dest_path))
        return dest_path

    print(f"  [Acoustic Prominence Gate]: Evaluating {len(candidate_paths)} candidate takes for {target_words}...")

    scored_candidates = []
    for idx, cand in enumerate(candidate_paths, 1):
        try:
            score, details = evaluate_acoustic_prominence(cand, target_words, text_context)
            occ_summary = ", ".join([f"{o['role']}_ratio={o['ratio']}" for o in details.get("occurrences", [])])
            print(f"    Take #{idx} ({cand.name}): Score = {score:.2f} | {occ_summary or details.get('transcript', '')}")
            scored_candidates.append((cand, score, details))
        except Exception as exc:
            logger.warning(f"Error evaluating candidate {cand}: {exc}")
            scored_candidates.append((cand, -100.0, {"error": str(exc)}))

    # Pick the candidate with the highest score
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    winner_cand, best_score, best_details = scored_candidates[0]

    print(f"  -> Winner Selected: {winner_cand.name} (Contrast Score: {best_score:.2f})")

    # Move winner to dest_path
    try:
        if dest_path.exists():
            dest_path.unlink()
        shutil.move(str(winner_cand), str(dest_path))
    except Exception as exc:
        logger.error(f"Failed to move winning candidate {winner_cand} to {dest_path}: {exc}")
        # In case move failed, try copy
        shutil.copyfile(str(winner_cand), str(dest_path))

    # Clean up rejected candidates
    for cand, _, _ in scored_candidates:
        if cand != winner_cand and cand.exists():
            try:
                cand.unlink()
            except Exception:
                pass

    return dest_path


def _extract_voiced_pitches(audio_data: np.ndarray, sr: int) -> List[float]:
    if len(audio_data.shape) > 1:
        audio_data = audio_data[:, 0]
    frame_len = int(0.03 * sr)
    hop = int(0.01 * sr)
    pitches: List[float] = []

    for i in range(0, len(audio_data) - frame_len, hop):
        frame = audio_data[i:i + frame_len]
        energy = np.mean(frame ** 2)
        if energy < 0.0005:  # unvoiced or silence
            continue
        corr = np.correlate(frame, frame, mode='full')
        corr = corr[len(frame) - 1:]
        min_lag = int(sr / 450)  # max 450 Hz
        max_lag = int(sr / 75)   # min 75 Hz
        if max_lag >= len(corr):
            continue
        peak_lag = min_lag + np.argmax(corr[min_lag:max_lag])
        if corr[0] > 0 and (corr[peak_lag] / corr[0]) > 0.40:
            pitches.append(sr / peak_lag)
    return pitches


def compute_pitch_metrics(audio_data: np.ndarray, sr: int) -> Tuple[float, float, float]:
    """Computes mean pitch (F0), standard deviation, and variance ratio (std/mean) on voiced frames.
    Uses short-term autocorrelation with energy gating.
    Returns (mean_pitch_hz, std_pitch_hz, variance_ratio).
    """
    pitches = _extract_voiced_pitches(audio_data, sr)
    if len(pitches) < 8:
        return 0.0, 0.0, 0.0
    mean_f0 = float(np.mean(pitches))
    std_f0 = float(np.std(pitches))
    var_ratio = std_f0 / max(1.0, mean_f0)
    return round(mean_f0, 1), round(std_f0, 1), round(var_ratio, 3)


def compute_intonation_metrics(audio_data: np.ndarray, sr: int) -> Dict[str, float]:
    """Computes terminal pitch rise ratio (last 25% vs first 75% voiced F0) and RMS peak contrast."""
    if len(audio_data.shape) > 1:
        audio_data = audio_data[:, 0]
    pitches = _extract_voiced_pitches(audio_data, sr)
    final_25pct_f0_ratio = 1.0
    f0_range_ratio = 0.0
    if len(pitches) >= 12:
        split_idx = max(4, int(len(pitches) * 0.75))
        body = pitches[:split_idx]
        tail = pitches[split_idx:]
        if body and tail:
            body_mean = float(np.mean(body))
            tail_mean = float(np.mean(tail))
            final_25pct_f0_ratio = tail_mean / max(1.0, body_mean)
        med_f0 = float(np.median(pitches))
        f0_range_ratio = float(np.percentile(pitches, 90) - np.percentile(pitches, 10)) / max(1.0, med_f0)

    hop = max(1, int(0.02 * sr))
    frame_rms = [float(np.sqrt(np.mean(audio_data[j:j + hop] ** 2))) for j in range(0, len(audio_data) - hop, hop)]
    active_rms = [r for r in frame_rms if r > 0.012]
    rms_peak_ratio = 1.0
    if len(active_rms) >= 6:
        med_rms = float(np.median(active_rms))
        p95_rms = float(np.percentile(active_rms, 95))
        rms_peak_ratio = p95_rms / max(1e-5, med_rms)

    return {
        "voiced_frames": float(len(pitches)),
        "final_25pct_f0_ratio": round(final_25pct_f0_ratio, 3),
        "f0_range_ratio": round(f0_range_ratio, 3),
        "rms_peak_ratio": round(rms_peak_ratio, 3),
    }


def reference_median_pitch(path: Path) -> float | None:
    """Return a voiced median for a local reference, when measurable."""
    try:
        data, sr = sf.read(path)
    except (OSError, RuntimeError):
        return None
    if data.ndim > 1:
        data = data.mean(axis=1)
    voiced = _extract_voiced_pitches(data, sr)
    return float(np.median(voiced)) if len(voiced) >= 12 else None


def max_window_pitch_shift(data: np.ndarray, sr: int, reference_f0: float) -> float | None:
    """Compare two-second voiced windows in semitones to the cast reference."""
    shifts = []
    for start in range(0, len(data), sr):
        window = data[start:start + 2 * sr]
        if len(window) < sr:
            continue
        voiced = _extract_voiced_pitches(window, sr)
        if len(voiced) >= 12:
            shifts.append(float(12 * np.log2(np.median(voiced) / reference_f0)))
    return max(shifts, default=None)


def evaluate_voice_take(
    audio_path: Union[str, Path],
    target_text: str = "",
    language: str = "english",
    video_type: Optional[str] = None,
    section: Optional[str] = None,
    reference_f0: Optional[float] = None,
) -> Tuple[float, bool, List[str], Dict[str, Any]]:
    """Evaluates an individual synthesized speech take against per-language acoustic quality criteria:
    - Pitch variance (rejects flat robotic monotone per language floor)
    - Tempo / Speech rate (rejects sluggish or rushed tempo per language envelope)
    - Audio energy (rejects muffled / low RMS < 0.05)
    - Internal silence (rejects awkward mid-sentence freezes > 0.85s)
    - Intonation contour checks on `?` (terminal pitch rise) and `!` (dynamic RMS/F0 peak lift)

    Returns:
        (composite_score, passes_quality_gate, issues_list, metrics_dict)
    """
    audio_path = Path(audio_path)
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        return 0.0, False, ["File missing or empty"], {"error": "Missing file"}

    try:
        data, sr = sf.read(str(audio_path))
    except Exception as exc:
        return 0.0, False, [f"Unreadable audio: {exc}"], {"error": str(exc)}

    if len(data.shape) > 1:
        data = data[:, 0]

    duration = len(data) / sr
    if duration < 0.3:
        return 0.0, False, ["Duration too short (< 0.3s)"], {"duration": duration}

    rms = float(np.sqrt(np.mean(data ** 2)))
    mean_f0, std_f0, var_ratio = compute_pitch_metrics(data, sr)
    intonation = compute_intonation_metrics(data, sr)

    # Resolve language envelope when typed mode is enabled
    min_var_ratio = 0.110
    min_cps, max_cps, target_cps = 8.0, 19.0, 13.5
    min_rms = 0.05
    max_silence_allowed = 0.85
    max_mean_f0 = 285.0
    check_q = False
    check_exc = False
    min_q_ratio = 1.03
    min_exc_rms_ratio = 1.55

    try:
        try:
            from video_creation._B_voice_generation.voice.common.engine import is_typed_voice_enabled
            from video_creation._B_voice_generation.voice.languages import get_language_voice_profile
            from video_creation._B_voice_generation.voice.types import get_video_type_voice_profile
        except (ImportError, ModuleNotFoundError):
            try:
                from ..voice.common.engine import is_typed_voice_enabled  # type: ignore[no-redef]
                from ..voice.languages import get_language_voice_profile  # type: ignore[no-redef]
                from ..voice.types import get_video_type_voice_profile  # type: ignore[no-redef]
            except (ImportError, ValueError):
                from voice.common.engine import is_typed_voice_enabled  # type: ignore[no-redef]
                from voice.languages import get_language_voice_profile  # type: ignore[no-redef]
                from voice.types import get_video_type_voice_profile  # type: ignore[no-redef]

        if is_typed_voice_enabled(video_type or "", language):
            env = get_language_voice_profile(language).acoustic_gate
            min_var_ratio = env.min_pitch_variance
            min_cps = env.min_cps
            max_cps = env.max_cps
            target_cps = env.target_cps
            min_rms = env.min_rms
            max_silence_allowed = env.max_internal_silence
            max_mean_f0 = env.max_mean_f0
            check_q = env.check_question_rise
            check_exc = env.check_exclamation_lift
            min_q_ratio = env.min_question_f0_ratio
            min_exc_rms_ratio = env.min_exclamation_rms_ratio
            if video_type:
                v_prof = get_video_type_voice_profile(video_type)
                if v_prof.target_cps_override is not None:
                    target_cps = float(v_prof.target_cps_override)
                if v_prof.max_cps_override is not None:
                    max_cps = float(v_prof.max_cps_override)
    except Exception:
        pass

    # Calculate speech rate (characters per second of clean spoken text)
    clean_text = re.sub(r"\[.*?\]|\(.*?\)", "", target_text or "").strip()
    char_count = len(re.sub(r"\s+", "", clean_text))
    cps = char_count / max(0.1, duration) if char_count > 0 else target_cps

    # Check max internal silence (> 0.008 RMS threshold)
    hop = int(0.02 * sr)
    frame_rms = [np.sqrt(np.mean(data[j:j + hop] ** 2)) for j in range(0, len(data) - hop, hop)]
    max_silent_frames = 0
    cur_silent_frames = 0
    # Edge padding is trimmed during mastering. Count only quiet runs bounded by speech.
    heard_speech = False
    for r in frame_rms:
        if r >= 0.008:
            if heard_speech:
                max_silent_frames = max(max_silent_frames, cur_silent_frames)
            heard_speech = True
            cur_silent_frames = 0
        elif heard_speech:
            cur_silent_frames += 1
    max_silence_sec = max_silent_frames * 0.02

    issues = []

    # 1. Pitch Variance Check (reject monotone)
    if var_ratio < min_var_ratio:
        issues.append(f"Monotone / robotic pitch variance ({var_ratio*100:.1f}% < {min_var_ratio*100:.1f}%)")

    # 2. Tempo Check
    if char_count > 10:
        if cps < min_cps:
            issues.append(f"Sluggish / dragging tempo ({cps:.1f} chars/s < {min_cps:.1f})")
        elif cps > max_cps:
            issues.append(f"Rushed / slurred tempo ({cps:.1f} chars/s > {max_cps:.1f})")

    # 3. Energy Check
    if rms < min_rms:
        issues.append(f"Very low audio volume / muffled (RMS: {rms:.4f} < {min_rms})")

    # 4. Silence Freeze Check
    if duration > 2.5 and max_silence_sec > max_silence_allowed:
        issues.append(f"Internal silence freeze ({max_silence_sec:.2f}s > {max_silence_allowed:.2f}s)")

    # 5. Excessive Shrillness / High Pitch Check
    if mean_f0 > max_mean_f0:
        issues.append(f"Excessive shrillness / high pitch ({mean_f0:.1f} Hz > {max_mean_f0:.1f} Hz)")

    # 6. Punctuation Intonation Contour Checks (only when target_text contains ? or ! and enough voiced frames)
    sec_low = (section or "").lower()
    is_challenge_lock = (video_type or "").lower() == "game" and "challenge" in sec_low
    voiced_n = intonation.get("voiced_frames", 0.0)
    q_bonus = 0.0
    if not is_challenge_lock and voiced_n >= 12:
        if check_q and "?" in clean_text:
            q_ratio = intonation["final_25pct_f0_ratio"]
            q_bonus += min(0.15, max(0.0, (q_ratio - 1.0) * 0.8))
            if q_ratio < min_q_ratio and not (clean_text.rstrip().endswith(".")):
                issues.append(f"Flat question intonation (tail F0 ratio {q_ratio:.2f} < {min_q_ratio:.2f})")
        elif check_exc and "!" in clean_text:
            rms_ratio = intonation["rms_peak_ratio"]
            q_bonus += min(0.15, max(0.0, (rms_ratio - 1.2) * 0.15))
            if rms_ratio < min_exc_rms_ratio and var_ratio < (min_var_ratio + 0.025):
                issues.append(f"Flat exclamation energy (RMS peak ratio {rms_ratio:.2f} < {min_exc_rms_ratio:.2f})")

    window_shift = max_window_pitch_shift(data, sr, reference_f0) if reference_f0 else None
    if window_shift is not None and window_shift > 6.0:
        issues.append(f"Sustained high register (+{window_shift:.1f} semitones versus reference)")

    passes_gate = len(issues) == 0

    # Calculate continuous score [0.0 - 1.0+]
    pitch_score = min(1.0, max(0.0, (var_ratio - 0.08) / 0.08))
    tempo_diff = abs(cps - target_cps)
    tempo_score = min(1.0, max(0.0, 1.0 - (tempo_diff / 5.0)))
    energy_score = min(1.0, max(0.0, rms / 0.15))
    penalty = 0.5 ** len(issues)

    composite_score = round((0.40 * pitch_score + 0.40 * tempo_score + 0.20 * energy_score + q_bonus) * penalty, 2)

    metrics = {
        "duration": round(duration, 2),
        "mean_f0": mean_f0,
        "reference_f0": reference_f0,
        "max_window_shift_semitones": window_shift,
        "std_f0": std_f0,
        "pitch_variance": var_ratio,
        "pitch_score": round(pitch_score, 2),
        "cps": round(cps, 1),
        "tempo_score": round(tempo_score, 2),
        "rms": round(rms, 4),
        "max_internal_silence": round(max_silence_sec, 2),
        "final_25pct_f0_ratio": intonation["final_25pct_f0_ratio"],
        "rms_peak_ratio": intonation["rms_peak_ratio"],
        "score": composite_score,
        "passes_gate": passes_gate,
        "issues": issues
    }

    return composite_score, passes_gate, issues, metrics


def select_best_general_candidate(
    candidate_paths: List[Path],
    target_text: str,
    language: str,
    dest_path: Path,
    video_type: Optional[str] = None,
    section: Optional[str] = None,
) -> Path:
    """Evaluates multiple voice takes and promotes the highest scoring candidate to dest_path.
    Cleans up all non-winning candidate files.
    """
    dest_path = Path(dest_path)
    if not candidate_paths:
        return dest_path

    if len(candidate_paths) == 1:
        winner = candidate_paths[0]
        if winner != dest_path:
            shutil.move(str(winner), str(dest_path))
        return dest_path

    print(f"  [Quality Gate]: Evaluating {len(candidate_paths)} candidate takes...")
    scored = []
    for idx, cand in enumerate(candidate_paths, 1):
        score, passes, issues, metrics = evaluate_voice_take(
            cand,
            target_text,
            language,
            video_type=video_type,
            section=section,
        )
        issue_str = f" [Flagged: {', '.join(issues)}]" if issues else " [Clean]"
        print(f"    Take #{idx} ({cand.name}): Score = {score:.2f} | PitchVar: {metrics['pitch_variance']*100:.1f}% | Tempo: {metrics['cps']} c/s{issue_str}")
        scored.append((cand, score, passes, metrics))

    # Prefer a take that passed the checks, then compare scores.
    scored.sort(key=lambda x: (x[2], x[1]), reverse=True)
    winner_cand, best_score, best_passes, best_metrics = scored[0]

    print(f"  -> Winner Selected: {winner_cand.name} (Score: {best_score:.2f}, PitchVar: {best_metrics['pitch_variance']*100:.1f}%)")

    # Move winner to dest_path
    if dest_path.exists():
        dest_path.unlink()
    shutil.move(str(winner_cand), str(dest_path))

    # Clean up rejected candidates
    for cand, _, _, _ in scored:
        if cand != winner_cand and cand.exists():
            try:
                cand.unlink()
            except Exception:
                pass

    return dest_path
