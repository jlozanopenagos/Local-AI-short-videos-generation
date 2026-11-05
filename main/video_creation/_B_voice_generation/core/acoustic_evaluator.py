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

import numpy as np
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

    # Phase 3 Precision Quality Gate: If all candidate takes fell below acceptable contrast (< 0.80),
    # fallback to verified studio clip from Heteronym Pronunciation Bank if available
    # ONLY IF the text being voiced is an isolated word demonstration or very short carrier (<= 3 words),
    # because replacing a full conversational sentence with an isolated word clip destroys the sentence!
    words_in_context = len(re.findall(r"[\w'-]+", text_context)) if text_context else 0
    if best_score < 0.80 and words_in_context <= 3:
        try:
            from video_creation._B_voice_generation.core.pronunciation_bank import get_pronunciation_clip
        except (ImportError, ModuleNotFoundError):
            try:
                from core.pronunciation_bank import get_pronunciation_clip
            except (ImportError, ModuleNotFoundError):
                get_pronunciation_clip = None

        if get_pronunciation_clip and len(target_words) == 1:
            target_word = target_words[0].lower()
            expected_roles = detect_roles_in_text(text_context, target_words)
            if len(expected_roles) == 1:
                role = expected_roles[0][1]
                bank_clip = get_pronunciation_clip(target_word, role)
                if bank_clip and bank_clip.exists():
                    print(f"  [Pronunciation Bank]: Low candidate score ({best_score:.2f} < 0.80) on short drill ({words_in_context} words). Fallback to verified studio clip: {bank_clip.name}")
                    if dest_path.exists():
                        dest_path.unlink()
                    shutil.copyfile(str(bank_clip), str(dest_path))
                    for cand, _, _ in scored_candidates:
                        if cand.exists():
                            try:
                                cand.unlink()
                            except Exception:
                                pass
                    return dest_path

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


def compute_pitch_metrics(audio_data: np.ndarray, sr: int) -> Tuple[float, float, float]:
    """Computes mean pitch (F0), standard deviation, and variance ratio (std/mean) on voiced frames.
    Uses short-term autocorrelation with energy gating.
    Returns (mean_pitch_hz, std_pitch_hz, variance_ratio).
    """
    if len(audio_data.shape) > 1:
        audio_data = audio_data[:, 0]
    frame_len = int(0.03 * sr)
    hop = int(0.01 * sr)
    pitches = []

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

    if len(pitches) < 8:
        return 0.0, 0.0, 0.0
    mean_f0 = float(np.mean(pitches))
    std_f0 = float(np.std(pitches))
    var_ratio = std_f0 / max(1.0, mean_f0)
    return round(mean_f0, 1), round(std_f0, 1), round(var_ratio, 3)


def evaluate_voice_take(
    audio_path: Union[str, Path],
    target_text: str = "",
    language: str = "english"
) -> Tuple[float, bool, List[str], Dict[str, Any]]:
    """Evaluates an individual synthesized speech take against acoustic quality criteria:
    - Pitch variance (rejects flat robotic monotone < 11.0%)
    - Tempo / Speech rate (rejects sluggish < 8.0 CPS or rushed > 19.0 CPS)
    - Audio energy (rejects muffled / low RMS < 0.05)
    - Internal silence (rejects awkward mid-sentence freezes > 0.85s)

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

    # Calculate speech rate (characters per second of clean spoken text)
    clean_text = re.sub(r"\[.*?\]|\(.*?\)", "", target_text or "").strip()
    char_count = len(re.sub(r"\s+", "", clean_text))
    cps = char_count / max(0.1, duration) if char_count > 0 else 12.0

    # Check max internal silence (> 0.01 threshold)
    hop = int(0.02 * sr)
    frame_rms = [np.sqrt(np.mean(data[j:j + hop] ** 2)) for j in range(0, len(data) - hop, hop)]
    max_silent_frames = 0
    cur_silent_frames = 0
    for r in frame_rms:
        if r < 0.008:
            cur_silent_frames += 1
            if cur_silent_frames > max_silent_frames:
                max_silent_frames = cur_silent_frames
        else:
            cur_silent_frames = 0
    max_silence_sec = max_silent_frames * 0.02

    issues = []

    # 1. Pitch Variance Check (reject monotone)
    if var_ratio < 0.110:
        issues.append(f"Monotone / robotic pitch variance ({var_ratio*100:.1f}% < 11.0%)")

    # 2. Tempo Check
    if char_count > 10:
        if cps < 8.0:
            issues.append(f"Sluggish / dragging tempo ({cps:.1f} chars/s < 8.0)")
        elif cps > 19.0:
            issues.append(f"Rushed / slurred tempo ({cps:.1f} chars/s > 19.0)")

    # 3. Energy Check
    if rms < 0.05:
        issues.append(f"Very low audio volume / muffled (RMS: {rms:.4f} < 0.05)")

    # 4. Silence Freeze Check
    if duration > 2.5 and max_silence_sec > 0.85:
        issues.append(f"Internal silence freeze ({max_silence_sec:.2f}s > 0.85s)")

    # 5. Excessive Shrillness / High Pitch Check (reject ear-fatiguing high pitch > 285.0 Hz)
    if mean_f0 > 285.0:
        issues.append(f"Excessive shrillness / high pitch ({mean_f0:.1f} Hz > 285.0 Hz)")

    passes_gate = len(issues) == 0

    # Calculate continuous score [0.0 - 1.0]
    pitch_score = min(1.0, max(0.0, (var_ratio - 0.08) / 0.08))
    target_cps = 13.5
    tempo_diff = abs(cps - target_cps)
    tempo_score = min(1.0, max(0.0, 1.0 - (tempo_diff / 8.0)))
    energy_score = min(1.0, max(0.0, rms / 0.15))
    penalty = 0.5 ** len(issues)

    composite_score = round((0.45 * pitch_score + 0.35 * tempo_score + 0.20 * energy_score) * penalty, 2)

    metrics = {
        "duration": round(duration, 2),
        "mean_f0": mean_f0,
        "std_f0": std_f0,
        "pitch_variance": var_ratio,
        "pitch_score": round(pitch_score, 2),
        "cps": round(cps, 1),
        "tempo_score": round(tempo_score, 2),
        "rms": round(rms, 4),
        "max_internal_silence": round(max_silence_sec, 2),
        "score": composite_score,
        "passes_gate": passes_gate,
        "issues": issues
    }

    return composite_score, passes_gate, issues, metrics


def select_best_general_candidate(
    candidate_paths: List[Path],
    target_text: str,
    language: str,
    dest_path: Path
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
        score, passes, issues, metrics = evaluate_voice_take(cand, target_text, language)
        issue_str = f" [Flagged: {', '.join(issues)}]" if issues else " [Clean]"
        print(f"    Take #{idx} ({cand.name}): Score = {score:.2f} | PitchVar: {metrics['pitch_variance']*100:.1f}% | Tempo: {metrics['cps']} c/s{issue_str}")
        scored.append((cand, score, passes, metrics))

    # Sort descending by score
    scored.sort(key=lambda x: x[1], reverse=True)
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
