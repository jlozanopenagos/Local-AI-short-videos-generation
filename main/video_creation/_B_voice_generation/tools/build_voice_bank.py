"""
tools/build_voice_bank.py — Offline Two-Stage Reference Voice Bank Builder.

Stage 1: Synthesizes native `baseline` reference clips via `Qwen3-TTS-12Hz-1.7B-VoiceDesign`
         using native scripts and audits them with AcousticGate + Whisper.
Stage 2: Unloads VoiceDesign (single-model 6GB VRAM discipline), then clones same-speaker
         Roleplay acting variants from each baseline clip via `1.7B-Base` ICL.
"""
from __future__ import annotations

import argparse
import shutil
from tempfile import NamedTemporaryFile
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root, main, and _B_voice_generation are importable
THIS_DIR = Path(__file__).resolve().parent
STAGE_B_DIR = THIS_DIR.parent
MAIN_DIR = STAGE_B_DIR.parents[1]
CORE_DIR = MAIN_DIR / "core"
for p in (str(MAIN_DIR), str(CORE_DIR), str(STAGE_B_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import config  # pyrefly: ignore[missing-import]
from config import (  # pyrefly: ignore[missing-import]
    COMFY_API_URL,
    COMFY_INPUT_DIR,
    COMFY_OUTPUT_DIR,
    OPEN_SWARA_DIR,
    REF_TRANSCRIPTS_PATH,
    VOICE_BANK_DIR,
    VOICE_DESIGN_WORKFLOW_PATH,
    VOICE_WORKFLOW_PATH,
    require_services,
)

try:
    from video_creation._B_voice_generation.core.acoustic_evaluator import (
        compute_pitch_metrics,
        evaluate_voice_take,
        get_whisper_model,
    )
    from video_creation._B_voice_generation.core.audio_processor import trim_audio_silence
    from video_creation._B_voice_generation.core.comfy_client import ComfyClient
    from video_creation._B_voice_generation.core.voice_manager import VoiceManager
    from video_creation._B_voice_generation.voice.common.bank_manifest import sanitize_ref_transcript
except (ImportError, ModuleNotFoundError):
    from core.acoustic_evaluator import (  # type: ignore[no-redef]
        compute_pitch_metrics,
        evaluate_voice_take,
        get_whisper_model,
    )
    from core.audio_processor import trim_audio_silence  # type: ignore[no-redef]
    from core.comfy_client import ComfyClient  # type: ignore[no-redef]
    from core.voice_manager import VoiceManager  # type: ignore[no-redef]
    from voice.common.bank_manifest import sanitize_ref_transcript  # type: ignore[no-redef]

DEFAULT_PERSONAS_PATH = STAGE_B_DIR / "data" / "voice_bank_personas.json"

_LANG_ISO = {
    "english": "en",
    "french": "fr",
    "spanish": "es",
    "italian": "it",
}

_ALLOWED_SPANISH_ACCENTS = {"es_latam_neutral", "es_spain_castilian"}


def load_persona_catalog(catalog_path: Path = DEFAULT_PERSONAS_PATH) -> Dict[str, Any]:
    """Loads and validates the `voice_bank_personas.json` catalog."""
    data = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    personas = data.get("personas", [])
    if not personas:
        raise ValueError(f"Persona catalog at {catalog_path} contains no personas.")
    seen_ids = set()
    for p in personas:
        sid = p["speaker_id"]
        if sid in seen_ids:
            raise ValueError(f"Duplicate speaker_id in persona catalog: {sid}")
        seen_ids.add(sid)
        lang = p["language"].strip().lower()
        if lang not in _LANG_ISO:
            raise ValueError(f"Unsupported language '{lang}' for persona {sid}")
        if lang == "spanish" and p["accent"] not in _ALLOWED_SPANISH_ACCENTS:
            raise ValueError(
                f"Persona {sid} uses non-neutral Spanish accent '{p['accent']}'. "
                f"Allowed: {sorted(_ALLOWED_SPANISH_ACCENTS)}"
            )
    return data


def clean_ref_transcripts_file(ref_path: Path = REF_TRANSCRIPTS_PATH) -> Tuple[int, int]:
    """Repairs known Whisper typos in `ref_transcripts.json` in-place. Returns `(total, modified)`."""
    if not ref_path or not ref_path.exists():
        return 0, 0
    raw = json.loads(ref_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return 0, 0
    modified = 0
    cleaned = {}
    for k, val in raw.items():
        orig = str(val.get("text", val)) if isinstance(val, dict) else str(val)
        fixed = sanitize_ref_transcript(orig, audio_name=Path(k).name)
        if fixed != orig:
            modified += 1
        cleaned[k] = fixed
    if modified > 0:
        ref_path.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(raw), modified


def _normalize_reference_clip(src_path: Path, dest_wav_path: Optional[Path] = None, target_lufs: float = -18.0) -> Dict[str, float]:
    """Trims dead edge silence, normalizes level gently, and writes standard PCM_16 WAV."""
    # pyrefly: ignore[missing-import]
    import numpy as np
    # pyrefly: ignore[missing-import]
    import soundfile as sf

    try:
        from video_creation._B_voice_generation.core.audio_processor import measure_lufs
    except (ImportError, ModuleNotFoundError):
        from core.audio_processor import measure_lufs  # type: ignore[no-redef]

    out_path = dest_wav_path or src_path
    data, sr = sf.read(str(src_path))
    if data.ndim > 1:
        data = np.mean(data, axis=1)
    trimmed = trim_audio_silence(data, sr, threshold=0.01, pad_leading=0.04, pad_trailing=0.08)
    cur_lufs = measure_lufs(trimmed, sr)
    if cur_lufs > -60.0:
        gain_db = max(-12.0, min(12.0, target_lufs - cur_lufs))
        trimmed = trimmed * (10.0 ** (gain_db / 20.0))
    peak = float(np.max(np.abs(trimmed))) if len(trimmed) else 0.0
    if peak > 0.92:
        trimmed = trimmed * (0.92 / peak)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), trimmed.astype(np.float32), sr, subtype="PCM_16")
    if src_path != out_path and src_path.exists():
        try:
            src_path.unlink()
        except Exception:
            pass

    mean_f0, _, f0_var = compute_pitch_metrics(trimmed, sr)
    rms = float(np.sqrt(np.mean(trimmed ** 2))) if len(trimmed) else 0.0
    snr_approx = round(20.0 * np.log10(max(rms, 1e-6) / 1e-3), 1)
    duration_s = round(len(trimmed) / float(max(1, sr)), 2)
    return {"f0_mean": mean_f0, "f0_var": f0_var, "snr_db": snr_approx, "duration_s": duration_s}


def _save_manifest_merged(manifest_path: Path, new_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merges `new_entries` into existing `voice_bank_manifest.json` keyed by `voice_id` and persists atomically."""
    merged_by_id: Dict[str, Dict[str, Any]] = {}
    if manifest_path.exists():
        try:
            prev = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in (prev.get("voices", []) if isinstance(prev, dict) else []):
                if isinstance(item, dict) and item.get("voice_id"):
                    merged_by_id[str(item["voice_id"])] = item
        except Exception:
            pass
    for item in new_entries:
        if item and item.get("voice_id"):
            merged_by_id[str(item["voice_id"])] = item
    ordered = sorted(
        merged_by_id.values(),
        key=lambda v: (str(v.get("language", "")), str(v.get("gender", "")), str(v.get("speaker_id", "")), str(v.get("energy_tier", ""))),
    )
    payload = {"version": "1.0", "voices": ordered}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", dir=manifest_path.parent, encoding="utf-8", delete=False) as stream:
        temp_path = Path(stream.name)
        json.dump(payload, stream, indent=2, ensure_ascii=False)
    try:
        temp_path.replace(manifest_path)
    finally:
        temp_path.unlink(missing_ok=True)
    return ordered


def promote_audition_voices(source: Path, destination: Path, speaker_ids: list[str], *, dry_run: bool) -> dict:
    """Publish reviewed, passing audition clips without rebuilding or replacing existing voices."""
    source, destination = source.resolve(), destination.resolve()
    if source == destination or not speaker_ids:
        raise ValueError("Choose a separate audition bank and explicit speaker IDs.")
    manifest_name = "voice_bank_manifest.json"
    staged = json.loads((source / manifest_name).read_text(encoding="utf-8"))["voices"]
    manifest_path = destination / manifest_name
    existing = json.loads(manifest_path.read_text(encoding="utf-8"))["voices"] if manifest_path.exists() else []
    by_id = {entry["voice_id"]: entry for entry in existing}
    existing_paths = {Path(entry["rel_path"]).as_posix().casefold() for entry in existing}
    selected = [
        entry for entry in staged
        if entry["speaker_id"] in speaker_ids and entry["active"] and entry["lang_prob"] >= 0.95
    ]
    passing_baselines = {entry["speaker_id"] for entry in selected if entry["energy_tier"] == "baseline"}
    if missing := set(speaker_ids) - passing_baselines:
        raise ValueError(f"No passing audition baseline for {', '.join(sorted(missing))}.")

    copies = []
    seen_ids, seen_paths = set(), set()
    for entry in selected:
        rel = Path(entry["rel_path"])
        path_key = rel.as_posix().casefold()
        voice_id = entry["voice_id"]
        if voice_id in seen_ids or path_key in seen_paths:
            raise ValueError(f"Duplicate audition reference: {voice_id} ({rel})")
        seen_ids.add(voice_id)
        seen_paths.add(path_key)
        origin, target = (source / rel).resolve(), (destination / rel).resolve()
        if rel.is_absolute() or not origin.is_relative_to(source) or not target.is_relative_to(destination):
            raise ValueError(f"Reference path escapes its voice bank: {rel}")
        if origin.suffix.lower() != ".wav" or not origin.is_file() or not origin.stat().st_size:
            raise ValueError(f"Missing audition WAV: {origin}")
        if entry["voice_id"] in by_id:
            if by_id[entry["voice_id"]] == entry and target.is_file() and target.read_bytes() == origin.read_bytes():
                continue
            raise ValueError(f"Voice ID already exists: {entry['voice_id']}")
        if path_key in existing_paths or (
            target.exists() and target.read_bytes() != origin.read_bytes()
        ):
            raise ValueError(f"Voice path already exists: {target}")
        copies.append((entry, origin, target))

    if copies and not dry_run:
        for _, origin, target in copies:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                with origin.open("rb") as audio:
                    output = target.open("xb")
                    try:
                        with output:
                            shutil.copyfileobj(audio, output)
                    except OSError:
                        target.unlink(missing_ok=True)
                        raise
        _save_manifest_merged(manifest_path, [entry for entry, _, _ in copies])

    return {"dry_run": dry_run, "speaker_ids": sorted(passing_baselines),
            "new_clips": len(copies), "manifest_path": str(manifest_path)}


def _verify_whisper_language(wav_path: Path, expected_lang: str) -> float:
    model = get_whisper_model()
    if model is None:
        return 1.0
    try:
        _, info = model.transcribe(str(wav_path), language=None, word_timestamps=False)
        det_lang = getattr(info, "language", "")
        prob = float(getattr(info, "language_probability", 1.0))
        if det_lang == _LANG_ISO.get(expected_lang, expected_lang):
            return round(prob, 3)
        return 0.0
    except Exception:
        return 1.0


def _compute_spectral_gender_metrics(audio_data, sr: int) -> Tuple[float, float, float]:
    """Computes `(hps_f0, p25_f0, mf_energy_ratio)` via 3-harmonic HPS and low/high band spectral energy."""
    # pyrefly: ignore[missing-import]
    import numpy as np

    x = np.asarray(audio_data, dtype=np.float64)
    if x.ndim > 1:
        x = x[:, 0]
    frame = max(256, int(0.05 * sr))
    hop = max(128, int(0.02 * sr))
    if len(x) < frame:
        return 0.0, 0.0, 0.0
    win = np.hanning(frame)
    nfft = frame * 4
    freqs = np.fft.rfftfreq(nfft, 1.0 / sr)
    n_hps = (nfft // 2 + 1) // 3
    f_hps = freqs[:n_hps]
    mask = (f_hps >= 75.0) & (f_hps <= 380.0)
    low_m = (freqs >= 80.0) & (freqs <= 165.0)
    high_f = (freqs >= 180.0) & (freqs <= 340.0)
    if not np.any(mask) or not np.any(low_m) or not np.any(high_f):
        return 0.0, 0.0, 0.0

    f0s: List[float] = []
    e_low: List[float] = []
    e_high: List[float] = []
    for i in range(0, len(x) - frame, hop):
        w = x[i : i + frame]
        if float(np.mean(w * w)) < 0.001:
            continue
        spec = np.abs(np.fft.rfft(w * win, n=nfft))
        e_low.append(float(np.max(spec[low_m])))
        e_high.append(float(np.max(spec[high_f])))
        hps = spec[:n_hps] * spec[0 : n_hps * 2 : 2] * spec[0 : n_hps * 3 : 3]
        f0s.append(float(f_hps[mask][int(np.argmax(hps[mask]))]))
    if len(f0s) < 4:
        return 0.0, 0.0, 0.0
    hps_med = round(float(np.median(f0s)), 1)
    p25_val = round(float(np.percentile(f0s, 25)), 1)
    mf_ratio = round(float(np.median(e_low) / max(1e-6, float(np.median(e_high)))), 3)
    return hps_med, p25_val, mf_ratio


def _compute_hps_median_f0(audio_data, sr: int) -> float:
    """Computes octave-proof fundamental F0 (Hz) via 3-harmonic Harmonic Product Spectrum (HPS)."""
    return _compute_spectral_gender_metrics(audio_data, sr)[0]


def _passes_gender_pitch_gate(
    gender: str,
    mean_f0: float,
    p25_f0: Optional[float] = None,
    mf_energy_ratio: Optional[float] = None,
    *,
    lower_register: bool = False,
) -> Tuple[bool, str]:
    """Rejects gender-flipped or childlike/shrill baseline draws using HPS F0, P25 F0, and M/F energy ratio."""
    gend = (gender or "").strip().lower()
    if mean_f0 <= 0.0:
        return False, f"Unvoiced / missing HPS F0 ({mean_f0:.1f} Hz)"
    if gend == "male":
        if not (85.0 <= mean_f0 <= 195.0):
            return False, f"Male HPS pitch out of range ({mean_f0:.1f} Hz; expected 85-195 Hz)"
        if mf_energy_ratio is not None and mf_energy_ratio < 0.08:
            return False, f"Male low-band ratio too thin (M/F_E={mf_energy_ratio:.2f} < 0.08; likely female)"
        return True, ""
    min_f0, max_f0, min_p25, max_ratio = (
        (175.0, 245.0, 160.0, 0.10) if lower_register else (200.0, 285.0, 195.0, 0.05)
    )
    if not (min_f0 <= mean_f0 <= max_f0):
        return False, f"Female HPS pitch out of range ({mean_f0:.1f} Hz; expected {min_f0:g}-{max_f0:g} Hz)"
    if p25_f0 is not None and p25_f0 < min_p25:
        return False, f"Female P25 pitch too low ({p25_f0:.1f} Hz < {min_p25:g} Hz)"
    if mf_energy_ratio is not None and mf_energy_ratio > max_ratio:
        return False, f"Female low-band energy too heavy (M/F_E={mf_energy_ratio:.3f} > {max_ratio:g})"
    return True, ""


def _run_voicedesign_take(
    client: ComfyClient,
    template: Dict[str, Any],
    text: str,
    voice_instruction: str,
    language: str,
    seed: int,
    dest_path: Path,
) -> Path:
    wf = json.loads(json.dumps(template))
    if "36" in wf and "inputs" in wf["36"]:
        wf["36"]["inputs"]["text"] = text
        wf["36"]["inputs"]["voice_instruction"] = voice_instruction
        wf["36"]["inputs"]["language"] = language.capitalize()
        wf["36"]["inputs"]["seed"] = seed
        wf["36"]["inputs"]["temperature"] = 0.85
        wf["36"]["inputs"]["subtalker_temperature"] = 0.82
    if "8" in wf and "inputs" in wf["8"]:
        wf["8"]["inputs"]["filename_prefix"] = f"audio/vd_{uuid.uuid4().hex[:8]}"

    client.ensure_clean_slate()
    prompt_id = client.queue_prompt(wf)
    history = client.poll_for_completion(prompt_id, timeout_seconds=300)
    outputs = history.get("outputs", {})
    save_id = "8" if "8" in outputs else next((nid for nid, out in outputs.items() if "audio" in out), None)
    if not save_id:
        raise RuntimeError(f"SaveAudio node missing from VoiceDesign history: {outputs}")
    info = outputs[save_id]["audio"][0]
    subfolder = info.get("subfolder", "audio")
    client.download_file(info["filename"], subfolder, info.get("type", "output"), dest_path)
    if client.comfy_output_dir:
        src_file = client.comfy_output_dir / subfolder / info["filename"]
        if src_file.exists():
            try:
                src_file.unlink()
            except Exception:
                pass
    return dest_path


def _generate_baseline_for_persona(
    persona: Dict[str, Any],
    client: ComfyClient,
    vd_template: Dict[str, Any],
    bank_dir: Path,
    force: bool = False,
    max_candidates: int = 2,
) -> Optional[Dict[str, Any]]:
    lang = persona["language"].lower()
    gend = persona["gender"].lower()
    sid = persona["speaker_id"]
    out_dir = bank_dir / lang / gend
    out_dir.mkdir(parents=True, exist_ok=True)
    final_wav = out_dir / f"{lang}_{gend}_{sid}_baseline.wav"

    # A staged lower-register clip must meet the same gate when a build resumes.
    import soundfile as sf

    if final_wav.exists() and not force:
        stats = _normalize_reference_clip(final_wav, final_wav) if final_wav.stat().st_size > 0 else {"f0_mean": 0.0, "f0_var": 0.0, "snr_db": 0.0, "duration_s": 0.0}
        lang_prob = _verify_whisper_language(final_wav, lang)
        active = lang_prob >= 0.90
        if persona.get("lower_register"):
            data, sr = sf.read(final_wav)
            f0, p25, ratio = _compute_spectral_gender_metrics(data, sr)
            pitch_ok, _ = _passes_gender_pitch_gate(gend, f0, p25, ratio, lower_register=True)
            active = lang_prob >= 0.95 and pitch_ok
            stats.update(f0_hps=f0, mf_ratio=ratio)
        print(f"    [Skip existing] {final_wav.name} | dur={stats['duration_s']}s | f0_var={stats['f0_var']*100:.1f}% | lang_prob={lang_prob}", flush=True)
        return {
            "voice_id": f"{sid}_baseline",
            "speaker_id": sid,
            "language": lang,
            "gender": gend,
            "accent": persona["accent"],
            "energy_tier": "baseline",
            "archetypes": persona["archetypes"],
            "rel_path": f"{lang}/{gend}/{final_wav.name}",
            "ref_text": persona["ref_text"],
            "source": "voice_design",
            "lang_prob": lang_prob,
            "active": active,
            **stats,
        }

    candidates: List[Tuple[Path, float, float, float, bool, float, float, float]] = []
    num_takes = max(1, int(max_candidates))
    max_attempts = max(num_takes, 5)
    for idx in range(max_attempts):
        if idx >= num_takes and any(c[4] and c[2] >= 0.96 for c in candidates):
            break
        seed = int(persona["seed"]) + idx * 137
        tmp_flac = out_dir / f"{sid}_cand{idx+1}.flac"
        _run_voicedesign_take(
            client=client,
            template=vd_template,
            text=persona["ref_text"],
            voice_instruction=persona["voice_instruction"],
            language=lang,
            seed=seed,
            dest_path=tmp_flac,
        )
        data, sr = sf.read(str(tmp_flac))
        if data.ndim > 1:
            data = data[:, 0]
        hps_f0, p25_f0, mf_ratio = _compute_spectral_gender_metrics(data, sr)
        gender_ok, gender_issue = _passes_gender_pitch_gate(
            gend,
            hps_f0,
            p25_f0=p25_f0,
            mf_energy_ratio=mf_ratio,
            lower_register=persona.get("lower_register", False),
        )
        score, passes_gate, _, metrics = evaluate_voice_take(tmp_flac, target_text=persona["ref_text"], language=lang)
        lang_prob = _verify_whisper_language(tmp_flac, lang)
        rank = (
            (10.0 if gender_ok else 0.0)
            + (5.0 if lang_prob >= 0.96 else 0.0)
            + score
            + (0.25 * lang_prob)
            + (0.15 if metrics.get("final_25pct_f0_ratio", 1.0) >= 1.03 else 0.0)
        )
        if not gender_ok:
            print(f"    [Cand {idx+1} gender-pitch warn]: {gender_issue}", flush=True)
        candidates.append((tmp_flac, rank, lang_prob, score, gender_ok, hps_f0, p25_f0, mf_ratio))
        if passes_gate and gender_ok and (
            (idx == 0 and lang_prob >= 0.97 and score >= 0.78)
            or (idx >= 1 and lang_prob >= 0.96)
        ):
            break

    candidates.sort(key=lambda item: item[1], reverse=True)
    best_path, _, best_prob, best_score, best_gender_ok, best_hps_f0, _, best_mf_ratio = candidates[0]
    stats = _normalize_reference_clip(best_path, final_wav)
    norm_data, norm_sr = sf.read(str(final_wav))
    norm_hps, norm_p25, norm_mf = _compute_spectral_gender_metrics(norm_data, norm_sr)
    final_hps_f0 = norm_hps or best_hps_f0
    final_mf_ratio = norm_mf if norm_hps > 0.0 else best_mf_ratio
    for p, _, _, _, _, _, _, _ in candidates[1:]:
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

    print(
        f"    [Built] {final_wav.name} | dur={stats['duration_s']}s | hps_f0={final_hps_f0}Hz | p25={norm_p25}Hz | "
        f"M/F_E={final_mf_ratio:.3f} | f0_var={stats['f0_var']*100:.1f}% | lang_prob={best_prob} | "
        f"gender_ok={best_gender_ok} | score={best_score:.2f}",
        flush=True,
    )
    return {
        "voice_id": f"{sid}_baseline",
        "speaker_id": sid,
        "language": lang,
        "gender": gend,
        "accent": persona["accent"],
        "energy_tier": "baseline",
        "archetypes": persona["archetypes"],
        "rel_path": f"{lang}/{gend}/{final_wav.name}",
        "ref_text": persona["ref_text"],
        "source": "voice_design",
        "lang_prob": best_prob,
        "active": bool(best_prob >= 0.95 and best_gender_ok),
        "f0_hps": final_hps_f0,
        "mf_ratio": final_mf_ratio,
        **stats,
    }


_ROLEPLAY_VARIANT_DELIVERY = {
    "high_energy": "Playful excitement, quick and conversational, with a clear stress on the key word.",
    "surprised_urgent": "Restrained urgency, speaking quickly with a brief hesitation and a steady register.",
    "reassuring": "Reassure a worried friend, with warm emphasis and an unhurried landing.",
    "frustrated": "Hold back irritation, using clipped consonants and firm stress in a steady register.",
    "embarrassed": "Sound briefly flustered, hesitate, then recover with a quieter, matter-of-fact finish.",
}


def _generate_roleplay_variants(
    baseline_entry: Dict[str, Any],
    persona: Dict[str, Any],
    variant_texts: Dict[str, str],
    base_client: ComfyClient,
    bank_dir: Path,
    comfy_input_dir: Path,
    force: bool = False,
    max_candidates: int = 2,
) -> List[Dict[str, Any]]:
    """Clones `high_energy` & `surprised_urgent` takes from the exact baseline WAV via 1.7B-Base."""
    import shutil
    # pyrefly: ignore[missing-import]
    import soundfile as sf

    lang = baseline_entry["language"]
    gend = baseline_entry["gender"]
    sid = baseline_entry["speaker_id"]
    out_dir = bank_dir / lang / gend
    baseline_wav = bank_dir / baseline_entry["rel_path"]
    if not baseline_entry["active"] or not baseline_wav.exists():
        return []

    ref_copy = comfy_input_dir / baseline_wav.name
    shutil.copy2(baseline_wav, ref_copy)

    created: List[Dict[str, Any]] = []
    num_takes = max(1, int(max_candidates))
    try:
        for tier_index, tier in enumerate(_ROLEPLAY_VARIANT_DELIVERY, start=1):
            target_text = variant_texts.get(tier)
            if not target_text:
                continue
            final_wav = out_dir / f"{lang}_{gend}_{sid}_{tier}.wav"
            if final_wav.exists() and not force:
                stats = _normalize_reference_clip(final_wav, final_wav)
                active = True
                if persona.get("lower_register"):
                    data, sr = sf.read(final_wav)
                    f0, p25, ratio = _compute_spectral_gender_metrics(data, sr)
                    active, _ = _passes_gender_pitch_gate(gend, f0, p25, ratio, lower_register=True)
                    stats.update(f0_hps=f0, mf_ratio=ratio)
                print(f"    [Skip variant] {final_wav.name} | dur={stats['duration_s']}s | f0_var={stats['f0_var']*100:.1f}%", flush=True)
                created.append({
                    **baseline_entry,
                    "voice_id": f"{sid}_{tier}",
                    "energy_tier": tier,
                    "rel_path": f"{lang}/{gend}/{final_wav.name}",
                    "ref_text": target_text,
                    "active": active,
                    **stats,
                })
                continue

            best_cands: List[Tuple[Path, float, float, float, float, bool]] = []
            for idx in range(num_takes):
                seed = int(persona["seed"]) + (1000 * tier_index) + idx * 111
                tmp_flac = out_dir / f"{sid}_{tier}_c{idx+1}.flac"
                base_client.generate_voice_segment(
                    ref_audio_name=baseline_wav.name,
                    target_text=target_text,
                    language=lang,
                    gender=gend,
                    context=f"Character roleplay actor performing {tier} line in {lang}",
                    emotion=tier,
                    energy="medium",
                    style="natural conversational dialogue",
                    delivery_direction=_ROLEPLAY_VARIANT_DELIVERY[tier],
                    output_prefix=f"audio/var_{sid}_{tier}_{idx+1}",
                    dest_path=tmp_flac,
                    seed=seed,
                    use_icl=True,
                    ref_text=baseline_entry["ref_text"],
                    sampling_overrides={"temperature": 0.88, "subtalker_temperature": 0.83},
                    accent_hint=baseline_entry["accent"],
                )
                data, sr = sf.read(str(tmp_flac))
                if data.ndim > 1:
                    data = data[:, 0]
                var_f0, var_p25, var_mf = _compute_spectral_gender_metrics(data, sr)
                var_gender_ok = (80.0 <= var_f0 <= 215.0 and var_mf >= 0.06) if gend == "male" else (195.0 <= var_f0 <= 295.0 and var_mf <= 0.06)
                if persona.get("lower_register"):
                    var_gender_ok, _ = _passes_gender_pitch_gate(
                        gend, var_f0, var_p25, var_mf, lower_register=True,
                    )
                score, _, _, metrics = evaluate_voice_take(tmp_flac, target_text=target_text, language=lang)
                rank = (
                    (10.0 if var_gender_ok else 0.0)
                    + score
                    + 0.25 * metrics.get("pitch_variance", 0.0)
                )
                best_cands.append((tmp_flac, rank, score, var_f0, var_mf, var_gender_ok))

            best_cands.sort(key=lambda item: item[1], reverse=True)
            best_score = best_cands[0][2]
            best_var_f0 = best_cands[0][3]
            best_var_mf = best_cands[0][4]
            stats = _normalize_reference_clip(best_cands[0][0], final_wav)
            for p, _, _, _, _, _ in best_cands[1:]:
                if p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass

            print(
                f"    [Variant] {final_wav.name} | dur={stats['duration_s']}s | hps_f0={best_var_f0}Hz | M/F_E={best_var_mf:.3f} | "
                f"f0_var={stats['f0_var']*100:.1f}% | score={best_score:.2f}",
                flush=True,
            )
            created.append({
                "voice_id": f"{sid}_{tier}",
                "speaker_id": sid,
                "language": lang,
                "gender": gend,
                "accent": baseline_entry["accent"],
                "energy_tier": tier,
                "archetypes": baseline_entry["archetypes"],
                "rel_path": f"{lang}/{gend}/{final_wav.name}",
                "ref_text": target_text,
                "source": "voice_design",
                "lang_prob": baseline_entry.get("lang_prob", 1.0),
                "active": best_cands[0][5] if persona.get("lower_register") else True,
                "f0_hps": best_var_f0,
                "mf_ratio": best_var_mf,
                **stats,
            })
    finally:
        if ref_copy.exists():
            try:
                ref_copy.unlink()
            except Exception:
                pass
    return created


def build_voice_bank(
    *,
    personas_path: Path = DEFAULT_PERSONAS_PATH,
    bank_dir: Path = VOICE_BANK_DIR,
    language_filter: Optional[str] = None,
    speaker_ids: Optional[List[str]] = None,
    limit: Optional[int] = None,
    force: bool = False,
    skip_variants: bool = False,
    dry_run: bool = False,
    clean_transcripts: bool = True,
    candidates: int = 2,
    auditions_only: bool = False,
) -> Dict[str, Any]:
    """Builds or dry-run validates the VoiceDesign reference voice bank + Roleplay energy variants."""
    catalog = load_persona_catalog(personas_path)
    personas = catalog["personas"]
    if auditions_only:
        if bank_dir.resolve() == VOICE_BANK_DIR.resolve():
            raise ValueError("Use a separate --bank-dir for auditions.")
        personas = [p for p in personas if p.get("audition")]
    elif not speaker_ids:
        personas = [p for p in personas if not p.get("audition")]
    if language_filter:
        lang_low = language_filter.strip().lower()
        personas = [p for p in personas if p["language"].lower() == lang_low]
    if speaker_ids:
        target_ids = {s.strip() for s in speaker_ids if s and s.strip()}
        personas = [p for p in personas if p["speaker_id"] in target_ids]
    if limit is not None:
        personas = personas[: max(0, int(limit))]

    if not VOICE_DESIGN_WORKFLOW_PATH.exists():
        raise FileNotFoundError(f"VoiceDesign workflow not found: {VOICE_DESIGN_WORKFLOW_PATH}")
    if not VOICE_WORKFLOW_PATH.exists():
        raise FileNotFoundError(f"Base VoiceClone workflow not found: {VOICE_WORKFLOW_PATH}")

    if clean_transcripts and not dry_run:
        total_t, mod_t = clean_ref_transcripts_file(REF_TRANSCRIPTS_PATH)
        print(f"[Transcript Cleaner] Audited {total_t} ref_transcripts entries; repaired {mod_t} typos.", flush=True)

    roleplay_personas = [p for p in personas if "roleplay_actor" in p.get("archetypes", [])]
    variant_prompts = catalog.get("energy_variant_prompts", {})
    variants_by_speaker = {
        p["speaker_id"]: {
            **variant_prompts.get(p["language"], {}),
            **p.get("acting_variant_prompts", {}),
        }
        for p in roleplay_personas
    }
    planned_variants = sum(len(prompts) for prompts in variants_by_speaker.values())
    by_lang: Dict[str, int] = {}
    for p in personas:
        by_lang[p["language"]] = by_lang.get(p["language"], 0) + 1

    manifest_path = bank_dir / "voice_bank_manifest.json"
    if dry_run:
        return {
            "dry_run": True,
            "personas_count": len(personas),
            "roleplay_actors": len(roleplay_personas),
            "planned_baseline_clips": len(personas),
            "planned_variant_clips": 0 if skip_variants else planned_variants,
            "candidates": candidates,
            "by_language": by_lang,
            "bank_dir": str(bank_dir),
            "manifest_path": str(manifest_path),
        }

    try:
        # pyrefly: ignore[missing-import]
        from core.llama_manager import ensure_llama_stopped
        ensure_llama_stopped()
    except Exception:
        pass

    require_services(comfy=True)
    vd_template = json.loads(VOICE_DESIGN_WORKFLOW_PATH.read_text(encoding="utf-8"))
    vd_client = ComfyClient(COMFY_API_URL, VOICE_WORKFLOW_PATH, COMFY_OUTPUT_DIR)

    bank_dir.mkdir(parents=True, exist_ok=True)
    voices_entries: List[Dict[str, Any]] = []

    print(f"\n[Stage 1/2] Synthesizing {len(personas)} baseline VoiceDesign speakers (max_candidates={candidates})...", flush=True)
    baselines: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for p in personas:
        print(f"  -> {p['speaker_id']} ({p['language']}/{p['gender']}, accent={p['accent']})", flush=True)
        ent = _generate_baseline_for_persona(
            p,
            vd_client,
            vd_template,
            bank_dir,
            force=force,
            max_candidates=candidates,
        )
        if ent:
            voices_entries.append(ent)
            baselines.append((p, ent))
            _save_manifest_merged(manifest_path, voices_entries)

    # Free VoiceDesign VRAM before loading 1.7B-Base (6GB VRAM discipline)
    vd_client.free_memory(unload_models=True)

    if not skip_variants:
        roleplay_targets = [(p, ent) for p, ent in baselines if "roleplay_actor" in p.get("archetypes", [])]
        variant_count = sum(len(variants_by_speaker[p["speaker_id"]]) for p, _ in roleplay_targets)
        print(f"\n[Stage 2/2] Cloning {variant_count} same-speaker Roleplay energy variants via 1.7B-Base...", flush=True)
        base_client = ComfyClient(COMFY_API_URL, VOICE_WORKFLOW_PATH, COMFY_OUTPUT_DIR)
        for p, ent in roleplay_targets:
            v_texts = variants_by_speaker[p["speaker_id"]]
            variants = _generate_roleplay_variants(
                baseline_entry=ent,
                persona=p,
                variant_texts=v_texts,
                base_client=base_client,
                bank_dir=bank_dir,
                comfy_input_dir=COMFY_INPUT_DIR,
                force=force,
                max_candidates=candidates,
            )
            if variants:
                voices_entries.extend(variants)
                _save_manifest_merged(manifest_path, voices_entries)

    final_entries = _save_manifest_merged(manifest_path, voices_entries)
    print(f"\n[Done] Manifest now contains {len(final_entries)} Voice Bank entries at {manifest_path}", flush=True)
    return {
        "dry_run": False,
        "voices_count": len(final_entries),
        "new_or_updated_count": len(voices_entries),
        "manifest_path": str(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build curated 1.7B-VoiceDesign reference voice bank + Roleplay variants.")
    parser.add_argument("--bank-dir", type=Path, default=VOICE_BANK_DIR, help="Output bank directory for staging auditions")
    parser.add_argument("--language", type=str, default=None, choices=["english", "french", "spanish", "italian"], help="Filter to one language")
    parser.add_argument("--auditions-only", action="store_true", help="Build only the new audition personas")
    parser.add_argument("--promote-from", type=Path, help="Copy reviewed voices from this audition bank into --bank-dir")
    parser.add_argument("--speaker-ids", type=str, default=None, help="Comma-separated speaker_ids to rebuild selectively")
    parser.add_argument("--limit", type=int, default=None, help="Maximum personas to process")
    parser.add_argument("--candidates", type=int, default=2, help="Max candidate takes per clip (default: 2)")
    parser.add_argument("--force", action="store_true", help="Regenerate clips even if they already exist")
    parser.add_argument("--skip-variants", action="store_true", help="Only build Stage 1 baseline clips")
    parser.add_argument("--clean-ref-transcripts", action="store_true", help="Clean Whisper typos in ref_transcripts.json even on dry-run")
    parser.add_argument("--dry-run", action="store_true", help="Validate persona catalog and workflows without calling ComfyUI")
    args = parser.parse_args()

    if args.clean_ref_transcripts and args.dry_run:
        total, mod = clean_ref_transcripts_file(REF_TRANSCRIPTS_PATH)
        print(f"[Transcript Cleaner] Audited {total} entries; repaired {mod} typos.")

    speaker_ids_list = [s.strip() for s in args.speaker_ids.split(",") if s.strip()] if args.speaker_ids else None
    if args.promote_from:
        if not speaker_ids_list:
            parser.error("--promote-from requires --speaker-ids")
        print(json.dumps(promote_audition_voices(
            args.promote_from, args.bank_dir, speaker_ids_list, dry_run=args.dry_run,
        ), indent=2))
        return 0
    summary = build_voice_bank(
        bank_dir=args.bank_dir,
        language_filter=args.language,
        speaker_ids=speaker_ids_list,
        limit=args.limit,
        force=args.force,
        skip_variants=args.skip_variants,
        dry_run=args.dry_run,
        clean_transcripts=not args.dry_run and args.bank_dir.resolve() == VOICE_BANK_DIR.resolve(),
        candidates=args.candidates,
        auditions_only=args.auditions_only,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
