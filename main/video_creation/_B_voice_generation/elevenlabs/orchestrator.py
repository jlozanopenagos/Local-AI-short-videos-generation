"""
elevenlabs/orchestrator.py — Self-contained Stage B voice synthesis orchestrator for ElevenLabs.

Zero ComfyUI / Qwen3-TTS imports. Reuses shared script parsing, pause choreography, and LUFS mastering.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Dict, List, Optional

import config
from config import get_script_output_dir

try:
    # pyrefly: ignore[missing-import]
    from core.state_manager import StateManager, resolve_lang_and_type
except (ImportError, ModuleNotFoundError):
    from state_manager import StateManager, resolve_lang_and_type  # type: ignore[no-redef]

from ..core.audio_processor import concatenate_audios, enforce_learner_pace_safety_net
from ..core.script_parser import extract_language_from_label, get_script_segments
from ..core.stress_enhancer import normalize_multiple_choice_options_for_tts
from ..voice.common.engine import resolve_voice_context
from ..voice.common.punctuation import prepare_tts_prosody_text
from .catalog import ElevenLabsVoiceCatalog
from .client import ElevenLabsClient
from .tags import (
    DEFAULT_ELEVENLABS_MODEL_ID,
    get_language_iso_code,
    normalize_elevenlabs_model,
    prepare_elevenlabs_text,
)


# Native ElevenLabs speaking speed per video type (ElevenLabs supports [0.7, 1.2]).
# Slightly gentler than 1.0 so Flash v2.5 / Multilingual v2 / v3 stay in learner-friendly WPM
# natively without triggering post-hoc ffmpeg atempo stretching.
_ELEVENLABS_NATIVE_SPEED: Dict[str, float] = {
    "roleplay": 0.94,
    "expression": 0.92,
    "game": 0.92,
    "fun_facts": 0.92,
}


def synthesize_script_voice_elevenlabs(
    script_data: Dict[str, Any],
    state_manager: StateManager,
    *,
    elevenlabs_client: Optional[ElevenLabsClient] = None,
    catalog: Optional[ElevenLabsVoiceCatalog] = None,
    model_id: Optional[str] = None,
    base_dir: Optional[Path] = None,
    manual_genders: Optional[Dict[str, str]] = None,
    force_fresh_cast: bool = False,
    explicit_accent: Optional[str] = None,
    mark_video_assembly_pending: bool = False,
    check_cancelled: Optional[Callable[[], bool]] = None,
) -> bool:
    """Synthesizes a complete multi-character script track using ElevenLabs per-segment TTS (Option A)."""
    script_id = script_data["id"]
    script_text = script_data.get("script_text", "")
    metadata = script_data.get("metadata", {})
    label = metadata.get("LABEL", "english")

    clean_language, _ = resolve_lang_and_type(script_id, script_data)
    if not clean_language or clean_language == "english":
        extracted = extract_language_from_label(label)
        if extracted != "english":
            clean_language = extracted

    video_type = config.resolve_script_video_type(script_data)
    norm_model = normalize_elevenlabs_model(model_id or getattr(config, "ELEVENLABS_MODEL_ID", DEFAULT_ELEVENLABS_MODEL_ID))

    lang_profile, type_profile, dialect_hint = resolve_voice_context(
        clean_language,
        video_type,
        script_data=script_data,
        explicit_accent=explicit_accent,
    )

    script_output_dir = get_script_output_dir(script_id, clean_language, base_dir, video_type=video_type)
    script_output_dir.mkdir(parents=True, exist_ok=True)

    for ext in ("segment_*.flac", "segment_*.wav"):
        for old_file in script_output_dir.glob(ext):
            try:
                old_file.unlink()
            except Exception:
                pass

    print("=" * 60)
    print(f"Processing Script ID: {script_id} [ELEVENLABS:{norm_model}]")
    print(f"Language: {clean_language.upper()} | Type: {video_type.upper()} (Label: {label})")
    print("=" * 60)

    narrator_only = video_type.lower() in {"game", "expression", "fun_facts"}
    segments = get_script_segments(
        script_id,
        script_text,
        label,
        narrator_only=narrator_only,
        merge_narration_paragraphs=narrator_only,
    )
    if not segments:
        script_dict = script_data.get("content_metadata", {}).get("script")
        if script_dict and isinstance(script_dict, dict):
            segments = get_script_segments(
                script_id,
                json.dumps(script_dict),
                label,
                narrator_only=narrator_only,
                merge_narration_paragraphs=narrator_only,
            )
            if segments:
                script_data["script_text"] = json.dumps(script_dict, indent=2)
                state_manager.save_script_state(script_id, script_data)

    if not segments:
        print(f"Error: Script {script_id} has no valid segments.")
        return False

    print(f"Found {len(segments)} segments to synthesize via ElevenLabs ({norm_model}).")

    client = elevenlabs_client or ElevenLabsClient()
    if check_cancelled is not None:
        client.check_cancelled = check_cancelled

    if catalog is None:
        history_path = Path(config.OUTPUT_DIR) / "voice_quality" / "elevenlabs_casting_history.json"
        catalog = ElevenLabsVoiceCatalog(history_path=history_path)

    unique_speakers = list(dict.fromkeys(seg["speaker"] for seg in segments))
    resolved_genders = dict(manual_genders) if manual_genders is not None else dict(
        script_data.get("content_metadata", {}).get("speakers_gender", {}) or {}
    )
    existing_el_voices = script_data.get("content_metadata", {}).get("speakers_elevenlabs_voice", {}) or {}

    voice_assignments, speakers_gender, resolved_accent = catalog.cast_script_voices(
        speakers=unique_speakers,
        language=clean_language,
        video_type=video_type,
        script_id=script_id,
        manual_genders=resolved_genders,
        existing_voice_ids=existing_el_voices,
        explicit_accent=explicit_accent or dialect_hint,
        force_fresh_cast=force_fresh_cast,
    )

    content_meta = script_data.setdefault("content_metadata", {})
    content_meta["speakers_gender"] = speakers_gender
    content_meta["speakers_elevenlabs_voice"] = {
        spk: ent.voice_id for spk, ent in voice_assignments.items()
    }

    lang_iso = get_language_iso_code(clean_language)
    segments_to_concat: List[Dict[str, Any]] = []
    total_credits_used = 0

    for i, seg in enumerate(segments):
        if check_cancelled is not None and check_cancelled():
            return False

        idx = seg["index"]
        speaker = seg["speaker"]
        is_narrator = speaker.casefold() == "narrator"
        sec_name = (seg.get("section") or "").lower()
        raw_text = seg.get("raw_text", seg["text"])
        emotion = seg.get("emotion") or ""

        voice_entry = voice_assignments[speaker]
        normalized_text = normalize_multiple_choice_options_for_tts(seg["text"], language=clean_language)
        prosody_text, prosody_flags = prepare_tts_prosody_text(
            text=normalized_text,
            raw_text=raw_text,
            language=clean_language,
            video_type=video_type,
            section=sec_name,
            is_stress_vital=False,
            use_option_micro_pauses=type_profile.use_option_micro_pauses,
            option_micro_pause_sec=type_profile.pauses.option_micro_pause,
            enforce_inverted_punctuation=lang_profile.enforce_inverted_punctuation,
            continuous_turn=True,
        )
        el_text = prepare_elevenlabs_text(
            prosody_text,
            emotion=emotion,
            section=sec_name,
            model_id=norm_model,
            is_narrator=is_narrator,
        )
        if not el_text:
            continue

        # Only pass prosody continuation context when the adjacent segment belongs to the SAME speaker.
        # Passing another character's line causes ElevenLabs to anticipate a continuation breath/syllable
        # right before the clip ends, producing an abrupt cut-off sound across Roleplay turn changes.
        prev_txt = segments[i - 1]["text"] if (i > 0 and segments[i - 1]["speaker"] == speaker) else None
        next_txt = segments[i + 1]["text"] if ((i + 1) < len(segments) and segments[i + 1]["speaker"] == speaker) else None
        native_speed = max(0.7, min(1.2, float(_ELEVENLABS_NATIVE_SPEED.get(video_type.lower(), 0.92))))
        dest_path = script_output_dir / f"segment_{idx:02d}_{speaker.replace(' ', '_')}.wav"

        print(f"--- Segment {idx}/{len(segments)} [{speaker}] -> {voice_entry.name} ({voice_entry.voice_id}) ---")
        try:
            saved_wav, seg_credits = client.synthesize_segment(
                voice_id=voice_entry.voice_id,
                text=el_text,
                dest_path=dest_path,
                model_id=norm_model,
                language_code=lang_iso,
                voice_settings={
                    "stability": voice_entry.stability,
                    "similarity_boost": voice_entry.similarity_boost,
                    "style": voice_entry.style,
                    "speed": native_speed,
                    "use_speaker_boost": True,
                },
                previous_text=prev_txt,
                next_text=next_txt,
            )
            total_credits_used += seg_credits
            print(f"  [ElevenLabs]: OK ({seg_credits} credits)")
        except InterruptedError:
            return False
        except Exception as exc:
            print(f"ElevenLabs API Error on segment {idx}: {exc}", file=sys.stderr)
            return False

        spoken_clean = re.sub(r"\[[^\]]+\]", " ", el_text)
        seg_words = len(spoken_clean.split())
        if type_profile is not None and type_profile.apply_pace_safety_net:
            target_wpm_mid = sum(type_profile.target_wpm_range) / 2.0
            stretched, factor, before_wpm, after_wpm = enforce_learner_pace_safety_net(
                saved_wav,
                word_count=seg_words,
                max_wpm=type_profile.max_wpm,
                target_wpm=target_wpm_mid,
                max_slowdown=0.07,
            )
            if stretched:
                print(f"  [Pace Safety Net]: Gently slowed {factor:.2f}x ({before_wpm:.0f} -> {after_wpm:.0f} WPM)")

        segments_to_concat.append({
            "index": idx,
            "path": saved_wav,
            "section": seg["section"],
            "speaker": speaker,
            "is_cliffhanger": bool(prosody_flags.get("is_cliffhanger", False)),
            "word_count": seg_words,
        })

    if not segments_to_concat:
        print(f"No synthesized segments available for {script_id}.")
        return False

    segments_to_concat.sort(key=lambda item: item["index"])
    master_path = script_output_dir / f"script_{script_id}_master.wav"

    try:
        with TemporaryDirectory(prefix=".voice-master-", dir=script_output_dir) as staging:
            staged_master = Path(staging) / master_path.name
            merged_file = concatenate_audios(
                segments_metadata=segments_to_concat,
                output_path=staged_master,
                pause_choreography=type_profile.pauses,
                mastering_preset=type_profile.mastering,
            )
            if merged_file:
                staged_timings = Path(staging) / "timings.json"
                timings = script_output_dir / "timings.json"
                backup = Path(staging) / "previous-timings.json"
                if timings.exists():
                    shutil.copyfile(timings, backup)
                staged_timings.replace(timings)
                try:
                    staged_master.replace(master_path)
                except OSError:
                    if backup.exists():
                        backup.replace(timings)
                    else:
                        timings.unlink(missing_ok=True)
                    raise
                merged_file = master_path

        if merged_file:
            print(f"Successfully generated ElevenLabs master audio: {merged_file} (~{total_credits_used} credits used)")
            assets = script_data.setdefault("assets", {})
            assets["audio_path"] = str(merged_file)
            status = script_data.setdefault("status", {})
            status["voice_generation"] = "done"
            if mark_video_assembly_pending:
                status["video_assembly"] = "pending"

            content_meta["voice_profile_meta"] = {
                "engine": "elevenlabs",
                "provider": "elevenlabs",
                "elevenlabs_model": norm_model,
                "dialect": resolved_accent,
                "video_type": type_profile.video_type,
                "credits_used": total_credits_used,
            }
            state_manager.save_script_state(script_id, script_data)

            for seg in segments_to_concat:
                try:
                    if seg["path"].exists():
                        seg["path"].unlink()
                except Exception:
                    pass
            return True
    except Exception as exc:
        print(f"Error during ElevenLabs audio merge: {exc}", file=sys.stderr)

    return False
