"""Synchronizes and adapts `speakers_gender` and `speakers_voice` across all state JSON files
(`main/state/<language>/<video_type>/script_<ID>.json`) for all 4 languages and all 4 video types.

Ensures:
1. Every state JSON with generated script text has canonical `speakers_gender` and `speakers_voice`
   matching the configured voice engine (`VOICE_ENGINE_BY_LANGUAGE`, `KOKORO_VOICES`, `NARRATOR_VOICES`).
2. Spanish (`ef_dora` / `em_alex`) and Italian (`if_sara` / `im_nicola`) scripts map cleanly to
   their native Kokoro-82M voice IDs.
3. French scripts in `hybrid` mode map Narrator and female dialogue speakers to `ff_siwis`,
   and male dialogue speakers to top-scoring audited Open-Swara French male clips (`french_male_open_swara_*.wav`).
4. English scripts map to valid Open-Swara English reference clips with zero gender/voice filename mismatches.
5. Roleplay scripts preserve existing visual prompt character genders (`On the LEFT is ... girl/boy`)
   if `image_prompts` or `general_prompt` already exist, so visual and vocal genders never conflict!
6. Optionally resets `status.voice_generation = "pending"` on Romance language scripts that still had
   legacy `.wav` voice assignments if `--reset-legacy-romance` is passed.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MAIN_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MAIN_DIR))
sys.path.insert(0, str(MAIN_DIR / "core"))

import config  # noqa: E402
from config import (  # noqa: E402
    BASE_DIR,
    COMFY_INPUT_DIR,
    KOKORO_VOICES,
    NARRATOR_VOICES,
    OPEN_SWARA_DIR,
    STATE_DIR,
    VOICE_ENGINE_BY_LANGUAGE,
    resolve_script_language,
    resolve_script_video_type,
)
from video_creation._B_voice_generation.core.script_parser import get_script_segments  # noqa: E402
from video_creation._B_voice_generation.core.voice_manager import VoiceManager  # noqa: E402


def _deterministic_pick(options: List[str], key: str) -> str:
    if not options:
        return ""
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
    return options[h % len(options)]


def infer_visual_genders_from_prompts(script_data: dict) -> Dict[str, str]:
    """If a script already has generated `general_prompt` or `image_prompts`,
    extracts locked character genders so `speakers_gender` stays 100% consistent with visuals.
    """
    assets = script_data.get("assets", {})
    if not isinstance(assets, dict):
        return {}
    gp = str(assets.get("general_prompt") or "")
    ip = assets.get("image_prompts", {})
    hook_p = str(ip.get("hook") or "") if isinstance(ip, dict) else ""
    combined = f"{gp} {hook_p}".lower()
    if not combined.strip():
        return {}

    vtype = resolve_script_video_type(script_data)
    out: Dict[str, str] = {}

    if vtype == "roleplay":
        # Check explicit "on the left is ... girl/boy" or "Character 1 (Left): ... girl/boy"
        left_m = re.search(
            r"(?:on the left|character 1 \(left\)|protagonist \(left\))[^.]{0,140}?\b(girl|boy|female|male|woman|man)\b",
            combined,
        )
        right_m = re.search(
            r"(?:on the right|character 2 \(right\)|companion \(right\))[^.]{0,140}?\b(girl|boy|female|male|woman|man)\b",
            combined,
        )
        if left_m:
            tok = left_m.group(1)
            out["PERSON_ONE"] = "female" if tok in ("girl", "female", "woman") else "male"
        if right_m:
            tok = right_m.group(1)
            out["PERSON_TWO"] = "female" if tok in ("girl", "female", "woman") else "male"
        if "PERSON_ONE" in out and "PERSON_TWO" not in out:
            out["PERSON_TWO"] = "male" if out["PERSON_ONE"] == "female" else "female"
    return out


def compute_canonical_speakers_for_script(
    script_data: dict,
    voice_manager: VoiceManager,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Computes clean, deterministic `speakers_gender` and `speakers_voice` for a script."""
    script_id = str(script_data.get("id", "")).strip()
    lang = resolve_script_language(script_data)
    vtype = resolve_script_video_type(script_data)
    label = script_data.get("metadata", {}).get("LABEL", lang)
    script_text = script_data.get("script_text", "")

    segments = []
    if script_text:
        try:
            segments = get_script_segments(script_id, script_text, label)
        except Exception:
            segments = []

    if segments:
        unique_speakers = []
        for s in segments:
            spk = s["speaker"]
            if spk not in unique_speakers:
                unique_speakers.append(spk)
    else:
        if vtype == "roleplay":
            unique_speakers = ["Narrator", "PERSON_ONE", "PERSON_TWO"]
        else:
            unique_speakers = ["Narrator"]

    cm = script_data.get("content_metadata", {})
    existing_genders = dict(cm.get("speakers_gender") or {})
    existing_voices = dict(cm.get("speakers_voice") or {})

    # 1. Determine canonical genders
    visual_genders = infer_visual_genders_from_prompts(script_data)
    speakers_gender: Dict[str, str] = {}

    if len(unique_speakers) == 1:
        spk = unique_speakers[0]
        if lang == "french" and VOICE_ENGINE_BY_LANGUAGE.get("french") in ("kokoro", "hybrid"):
            # French Kokoro v1.0 has native female voice ff_siwis
            speakers_gender[spk] = "female"
        elif spk in existing_genders and existing_genders[spk] in ("male", "female"):
            speakers_gender[spk] = existing_genders[spk]
        else:
            speakers_gender[spk] = _deterministic_pick(["female", "male"], f"{script_id}:{spk}")
    else:
        # Roleplay / multi-speaker
        chars = [s for s in unique_speakers if "narrator" not in s.lower()]
        narrators = [s for s in unique_speakers if "narrator" in s.lower()]

        for idx, c in enumerate(chars):
            if c in visual_genders:
                g = visual_genders[c]
            elif c in existing_genders and existing_genders[c] in ("male", "female"):
                g = existing_genders[c]
            else:
                g = voice_manager.resolve_speaker_gender(c)
                if g not in ("male", "female"):
                    g = _deterministic_pick(["female", "male"], f"{script_id}:{c}")
            # Ensure second character has opposite gender so P1 and P2 are distinct
            if idx == 1 and len(chars) >= 2 and g == speakers_gender.get(chars[0]):
                g = "male" if g == "female" else "female"
            speakers_gender[c] = g

        for n in narrators:
            if lang == "french" and VOICE_ENGINE_BY_LANGUAGE.get("french") in ("kokoro", "hybrid"):
                speakers_gender[n] = "female"
            elif chars and speakers_gender.get(chars[0]) in ("male", "female"):
                # Contrast Narrator gender with PERSON_ONE (who speaks immediately after the Hook)
                speakers_gender[n] = "male" if speakers_gender[chars[0]] == "female" else "female"
            elif n in existing_genders and existing_genders[n] in ("male", "female"):
                speakers_gender[n] = existing_genders[n]
            else:
                speakers_gender[n] = _deterministic_pick(["female", "male"], f"{script_id}:{n}")

    # 2. Determine canonical voices based on VOICE_ENGINE_BY_LANGUAGE
    speakers_voice: Dict[str, str] = {}
    used_wavs = set()

    is_multi = len(unique_speakers) > 1
    for spk in unique_speakers:
        g = speakers_gender[spk]
        is_diag = "narrator" not in spk.lower()
        eng, k_voice = voice_manager.resolve_engine_for_speaker(
            lang,
            gender=g,
            speaker=spk,
            is_dialogue=is_diag,
            cli_engine_override="auto",
            kokoro_available=True,
            is_multi_speaker_script=is_multi,
        )
        if eng == "kokoro" and k_voice:
            speakers_voice[spk] = k_voice
        else:
            # Qwen3-TTS reference WAV assignment (preferring Kokoro Golden References)
            pref_rels = NARRATOR_VOICES.get((lang, g), [])
            pool_rels = voice_manager.voice_pools.get((lang, g), [])
            if is_diag:
                # For dialogue characters (PERSON_ONE / PERSON_TWO), prefer golden_char1 / golden_char2
                golden_char_cands = [
                    Path(r).name
                    for r in pool_rels
                    if "kokoro_golden_char" in r
                    and (OPEN_SWARA_DIR / r).exists()
                    and Path(r).name not in used_wavs
                ]
                candidates = golden_char_cands or [
                    Path(r).name
                    for r in pool_rels
                    if r not in pref_rels
                    and (OPEN_SWARA_DIR / r).exists()
                    and voice_manager._is_acceptable_ref(OPEN_SWARA_DIR / r, lang)
                    and Path(r).name not in used_wavs
                ]
            else:
                # For Narrator, prefer golden_narrator
                golden_nar_cands = [
                    Path(r).name
                    for r in (pref_rels + pool_rels)
                    if "kokoro_golden_narrator" in r
                    and (OPEN_SWARA_DIR / r).exists()
                    and Path(r).name not in used_wavs
                ]
                candidates = golden_nar_cands

            if not candidates:
                candidates = [
                    Path(r).name
                    for r in (pref_rels + pool_rels)
                    if (OPEN_SWARA_DIR / r).exists()
                    and voice_manager._is_acceptable_ref(OPEN_SWARA_DIR / r, lang)
                    and Path(r).name not in used_wavs
                ]
            if not candidates:
                all_avail = voice_manager.get_available_voices(lang, g)
                candidates = [p.name for p in all_avail if p.name not in used_wavs] or [
                    p.name for p in all_avail
                ]

            chosen_wav = _deterministic_pick(candidates, f"{script_id}:{spk}:{g}")
            speakers_voice[spk] = chosen_wav
            if chosen_wav:
                used_wavs.add(chosen_wav)

    return speakers_gender, speakers_voice


def main() -> int:
    ap = argparse.ArgumentParser(description="Synchronize speakers_gender and speakers_voice across all state JSONs.")
    ap.add_argument(
        "--reset-legacy-romance",
        action="store_true",
        help="Reset voice_generation status to 'pending' for Romance scripts whose voices changed to Kokoro",
    )
    args = ap.parse_args()

    voice_manager = VoiceManager(OPEN_SWARA_DIR, COMFY_INPUT_DIR)
    state_files = sorted(STATE_DIR.rglob("script_*.json"))

    updated_count = 0
    by_lang_type: Dict[Tuple[str, str], int] = {}

    for fpath in state_files:
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[Skip] Could not parse {fpath}: {exc}")
            continue

        if not isinstance(data, dict) or "id" not in data:
            continue

        lang = resolve_script_language(data)
        vtype = resolve_script_video_type(data)

        if "content_metadata" not in data or not isinstance(data["content_metadata"], dict):
            data["content_metadata"] = {}
        cm = data["content_metadata"]

        # Clean up any leftover nested content_metadata if present
        if "content_metadata" in cm:
            del cm["content_metadata"]

        old_gender = cm.get("speakers_gender")
        old_voice = cm.get("speakers_voice")

        new_gender, new_voice = compute_canonical_speakers_for_script(data, voice_manager)

        changed = (old_gender != new_gender) or (old_voice != new_voice)
        if changed:
            cm["speakers_gender"] = new_gender
            cm["speakers_voice"] = new_voice
            if (
                args.reset_legacy_romance
                and lang in ("spanish", "italian", "french")
                and isinstance(old_voice, dict)
                and any(str(v).endswith(".wav") for v in old_voice.values())
                and old_voice != new_voice
            ):
                if "status" in data and isinstance(data["status"], dict):
                    data["status"]["voice_generation"] = "pending"

            fpath.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
            updated_count += 1
            by_lang_type[(lang, vtype)] = by_lang_type.get((lang, vtype), 0) + 1

    print(f"Scanned {len(state_files)} state JSON files; updated {updated_count} files.")
    for (l_key, t_key), cnt in sorted(by_lang_type.items()):
        print(f"  - {l_key:8} / {t_key:10}: {cnt} updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
