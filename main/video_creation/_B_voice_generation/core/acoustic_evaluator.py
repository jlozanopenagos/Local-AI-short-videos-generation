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

        # 1. Check uppercase syllable notation (e.g. PREsent vs preSENT)
        if len(raw) >= 4:
            if raw[:3].isupper() and raw[-3:].islower():
                role = "noun"
            elif raw[:3].islower() and raw[-3:].isupper():
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
    detected = []
    stems = {w.lower()[:4]: w.lower() for w in target_words}
    for w_text, st, en in words:
        clean_w = re.sub(r"[^\w]", "", w_text)
        for stem in stems:
            if stem in clean_w:
                detected.append((w_text, st, en))
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
    if best_score < 0.80:
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
                    print(f"  [Pronunciation Bank]: Low candidate score ({best_score:.2f} < 0.80). Fallback to verified studio clip: {bank_clip.name}")
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
