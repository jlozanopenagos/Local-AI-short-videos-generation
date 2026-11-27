"""
elevenlabs/catalog.py — Curated commercial-safe multilingual ElevenLabs voice catalog & casting engine.

Features:
- Separate from local Qwen3-TTS / ComfyUI voice bank (no .wav path mixing).
- 60% Neutral LatAm / 40% Castilian Spain weighted Spanish accent rotation.
- Persisted anti-repetition history (`elevenlabs_casting_history.json`) and 3-speaker uniqueness for Roleplay.
- Supports user overrides via optional `elevenlabs/voice_catalog.json` file.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


@dataclass(frozen=True)
class ElevenLabsVoiceEntry:
    voice_id: str
    name: str
    language: str          # english | spanish | french | italian | multilingual
    gender: str            # male | female
    accent: str            # en_us_neutral | en_uk_neutral | es_latam_neutral | es_spain_castilian | fr_standard | it_standard
    archetypes: Tuple[str, ...]  # warm_narrator | energetic_host | roleplay_actor
    stability: float = 0.50
    similarity_boost: float = 0.78
    style: float = 0.35


# Commercial-safe ElevenLabs premade multilingual voices (work across Eleven v3, Multilingual v2, Flash v2.5)
# Users can customize or expand with Voice Library IDs in `elevenlabs/voice_catalog.json`.
DEFAULT_ELEVENLABS_VOICES: Tuple[ElevenLabsVoiceEntry, ...] = (
    # --- ENGLISH (US & UK) ---
    ElevenLabsVoiceEntry("EXAVITQu4vr4xnSDxMaL", "Sarah", "english", "female", "en_us_neutral", ("warm_narrator", "roleplay_actor"), 0.48, 0.78, 0.35),
    ElevenLabsVoiceEntry("cgSgspJ2msm6clMCkdW9", "Jessica", "english", "female", "en_us_neutral", ("roleplay_actor", "energetic_host"), 0.45, 0.78, 0.42),
    ElevenLabsVoiceEntry("FGY2WhTYpPnrIDTdsKH5", "Laura", "english", "female", "en_us_neutral", ("energetic_host", "roleplay_actor"), 0.46, 0.78, 0.40),
    ElevenLabsVoiceEntry("Xb7hH8MSUJpSbSDYk0k2", "Alice", "english", "female", "en_uk_neutral", ("warm_narrator", "roleplay_actor"), 0.50, 0.78, 0.32),
    ElevenLabsVoiceEntry("pFZP5JQG7iQjIQuC4Bku", "Lily", "english", "female", "en_uk_neutral", ("warm_narrator", "roleplay_actor"), 0.50, 0.78, 0.32),
    ElevenLabsVoiceEntry("CwhRBWXzGAHq8TQ4Fs17", "Roger", "english", "male", "en_us_neutral", ("warm_narrator", "energetic_host"), 0.50, 0.78, 0.35),
    ElevenLabsVoiceEntry("iP95p4xoKVk53GoZ742B", "Chris", "english", "male", "en_us_neutral", ("roleplay_actor", "warm_narrator"), 0.45, 0.78, 0.40),
    ElevenLabsVoiceEntry("TX3LPaxmHKxFdv7VOQHJ", "Liam", "english", "male", "en_us_neutral", ("roleplay_actor", "energetic_host"), 0.45, 0.78, 0.42),
    ElevenLabsVoiceEntry("JBFqnCBsd6RMkjVDRZzb", "George", "english", "male", "en_uk_neutral", ("warm_narrator", "roleplay_actor"), 0.50, 0.78, 0.34),
    ElevenLabsVoiceEntry("onwK4e9ZLuTAKqWW03F9", "Daniel", "english", "male", "en_uk_neutral", ("warm_narrator", "energetic_host"), 0.50, 0.78, 0.32),

    # --- SPANISH (60% Neutral LatAm / 40% Castilian Spain) ---
    ElevenLabsVoiceEntry("cgSgspJ2msm6clMCkdW9", "Jessica (ES-LatAm)", "spanish", "female", "es_latam_neutral", ("roleplay_actor", "energetic_host"), 0.45, 0.78, 0.42),
    ElevenLabsVoiceEntry("EXAVITQu4vr4xnSDxMaL", "Sarah (ES-LatAm)", "spanish", "female", "es_latam_neutral", ("warm_narrator", "roleplay_actor"), 0.48, 0.78, 0.36),
    ElevenLabsVoiceEntry("XrExE9yKIg1WjnnlVkGX", "Matilda (ES-LatAm)", "spanish", "female", "es_latam_neutral", ("warm_narrator", "energetic_host", "roleplay_actor"), 0.48, 0.78, 0.38),
    ElevenLabsVoiceEntry("FGY2WhTYpPnrIDTdsKH5", "Laura (ES-Spain)", "spanish", "female", "es_spain_castilian", ("roleplay_actor", "energetic_host"), 0.45, 0.78, 0.42),
    ElevenLabsVoiceEntry("Xb7hH8MSUJpSbSDYk0k2", "Alice (ES-Spain)", "spanish", "female", "es_spain_castilian", ("warm_narrator", "roleplay_actor"), 0.50, 0.78, 0.35),
    ElevenLabsVoiceEntry("iP95p4xoKVk53GoZ742B", "Chris (ES-LatAm)", "spanish", "male", "es_latam_neutral", ("roleplay_actor", "warm_narrator"), 0.45, 0.78, 0.40),
    ElevenLabsVoiceEntry("TX3LPaxmHKxFdv7VOQHJ", "Liam (ES-LatAm)", "spanish", "male", "es_latam_neutral", ("roleplay_actor", "energetic_host"), 0.45, 0.78, 0.42),
    ElevenLabsVoiceEntry("cjVigY5qzO86Huf0OWal", "Eric (ES-LatAm)", "spanish", "male", "es_latam_neutral", ("warm_narrator", "energetic_host"), 0.48, 0.78, 0.36),
    ElevenLabsVoiceEntry("bIHbv24MWmeRgasZH58o", "Will (ES-Spain)", "spanish", "male", "es_spain_castilian", ("roleplay_actor", "warm_narrator"), 0.46, 0.78, 0.40),
    ElevenLabsVoiceEntry("nPczCjzI2devNBz1zQrb", "Brian (ES-Spain)", "spanish", "male", "es_spain_castilian", ("warm_narrator", "energetic_host", "roleplay_actor"), 0.50, 0.78, 0.35),

    # --- FRENCH ---
    ElevenLabsVoiceEntry("EXAVITQu4vr4xnSDxMaL", "Sarah (FR)", "french", "female", "fr_standard", ("warm_narrator", "roleplay_actor"), 0.48, 0.78, 0.36),
    ElevenLabsVoiceEntry("cgSgspJ2msm6clMCkdW9", "Jessica (FR)", "french", "female", "fr_standard", ("roleplay_actor", "energetic_host"), 0.45, 0.78, 0.42),
    ElevenLabsVoiceEntry("pFZP5JQG7iQjIQuC4Bku", "Lily (FR)", "french", "female", "fr_standard", ("warm_narrator", "roleplay_actor"), 0.48, 0.78, 0.36),
    ElevenLabsVoiceEntry("iP95p4xoKVk53GoZ742B", "Chris (FR)", "french", "male", "fr_standard", ("roleplay_actor", "warm_narrator"), 0.46, 0.78, 0.40),
    ElevenLabsVoiceEntry("TX3LPaxmHKxFdv7VOQHJ", "Liam (FR)", "french", "male", "fr_standard", ("roleplay_actor", "energetic_host"), 0.45, 0.78, 0.42),
    ElevenLabsVoiceEntry("onwK4e9ZLuTAKqWW03F9", "Daniel (FR)", "french", "male", "fr_standard", ("warm_narrator", "energetic_host"), 0.50, 0.78, 0.35),

    # --- ITALIAN ---
    ElevenLabsVoiceEntry("XrExE9yKIg1WjnnlVkGX", "Matilda (IT)", "italian", "female", "it_standard", ("warm_narrator", "roleplay_actor"), 0.48, 0.78, 0.38),
    ElevenLabsVoiceEntry("cgSgspJ2msm6clMCkdW9", "Jessica (IT)", "italian", "female", "it_standard", ("roleplay_actor", "energetic_host"), 0.45, 0.78, 0.42),
    ElevenLabsVoiceEntry("FGY2WhTYpPnrIDTdsKH5", "Laura (IT)", "italian", "female", "it_standard", ("energetic_host", "roleplay_actor"), 0.46, 0.78, 0.40),
    ElevenLabsVoiceEntry("TX3LPaxmHKxFdv7VOQHJ", "Liam (IT)", "italian", "male", "it_standard", ("roleplay_actor", "energetic_host"), 0.45, 0.78, 0.42),
    ElevenLabsVoiceEntry("iP95p4xoKVk53GoZ742B", "Chris (IT)", "italian", "male", "it_standard", ("roleplay_actor", "warm_narrator"), 0.46, 0.78, 0.40),
    ElevenLabsVoiceEntry("cjVigY5qzO86Huf0OWal", "Eric (IT)", "italian", "male", "it_standard", ("warm_narrator", "energetic_host"), 0.48, 0.78, 0.36),
)

# User-approved ElevenLabs accent weights (Spanish: 60% LatAm / 40% Castilian Spain)
ELEVENLABS_ACCENT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "english": {"en_us_neutral": 0.70, "en_uk_neutral": 0.30},
    "spanish": {"es_latam_neutral": 0.60, "es_spain_castilian": 0.40},
    "french": {"fr_standard": 1.0},
    "italian": {"it_standard": 1.0},
}

# Exact 5-slot interleaved cycle for 60% LatAm / 40% Castilian Spain
_SPANISH_60_40_CYCLE = (
    "es_latam_neutral",
    "es_spain_castilian",
    "es_latam_neutral",
    "es_spain_castilian",
    "es_latam_neutral",
)


def _script_num(script_id: Optional[str]) -> int:
    if not script_id:
        return 0
    digits = re.findall(r"\d+", str(script_id))
    if digits:
        return int(digits[-1])
    return int(hashlib.sha256(str(script_id).encode("utf-8")).hexdigest()[:8], 16)


def pick_elevenlabs_accent(
    language: str,
    script_id: Optional[str] = None,
    explicit_accent: Optional[str] = None,
) -> str:
    """Picks accent deterministically per script_id (Spanish uses exact 60% LatAm / 40% Castilian Spain)."""
    lang = (language or "english").strip().lower()
    weights = ELEVENLABS_ACCENT_WEIGHTS.get(lang, {})
    if explicit_accent and explicit_accent.strip().lower() in weights:
        return explicit_accent.strip().lower()

    if lang == "spanish":
        return _SPANISH_60_40_CYCLE[_script_num(script_id) % len(_SPANISH_60_40_CYCLE)]

    if lang == "english":
        # 70/30 US/UK interleaved over 10 slots
        slot = _script_num(script_id) % 10
        return "en_uk_neutral" if slot in (2, 5, 8) else "en_us_neutral"

    return next(iter(weights.keys()), "neutral")


class ElevenLabsVoiceCatalog:
    """Manages commercial-safe ElevenLabs voice casting with anti-repetition and 3-speaker uniqueness."""

    def __init__(
        self,
        catalog_path: Optional[Path] = None,
        history_path: Optional[Path] = None,
        max_history: int = 60,
    ):
        self.catalog_path = catalog_path or (Path(__file__).parent / "voice_catalog.json")
        self.history_path = history_path
        self.max_history = max(2, max_history)
        self.entries: List[ElevenLabsVoiceEntry] = self._load_entries()
        self._recent: Dict[Tuple[str, str], List[str]] = {}
        self._load_history()

    def _load_entries(self) -> List[ElevenLabsVoiceEntry]:
        if self.catalog_path and self.catalog_path.exists():
            try:
                raw = json.loads(self.catalog_path.read_text(encoding="utf-8"))
                items = raw.get("voices", raw) if isinstance(raw, dict) else raw
                parsed: List[ElevenLabsVoiceEntry] = []
                for item in items:
                    if not isinstance(item, dict) or not item.get("voice_id"):
                        continue
                    archs = item.get("archetypes") or ("warm_narrator",)
                    if isinstance(archs, str):
                        archs = [archs]
                    parsed.append(
                        ElevenLabsVoiceEntry(
                            voice_id=str(item["voice_id"]).strip(),
                            name=str(item.get("name") or item["voice_id"]).strip(),
                            language=str(item.get("language") or "english").strip().lower(),
                            gender=str(item.get("gender") or "female").strip().lower(),
                            accent=str(item.get("accent") or "neutral").strip().lower(),
                            archetypes=tuple(str(a).strip().lower() for a in archs if a),
                            stability=float(item.get("stability", 0.48)),
                            similarity_boost=float(item.get("similarity_boost", 0.78)),
                            style=float(item.get("style", 0.36)),
                        )
                    )
                if parsed:
                    return parsed
            except Exception:
                pass
        return list(DEFAULT_ELEVENLABS_VOICES)

    def _load_history(self) -> None:
        if not self.history_path or not self.history_path.exists():
            return
        try:
            payload = json.loads(self.history_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                for k, v in payload.items():
                    if ":" in k and isinstance(v, list):
                        lang, gend = k.split(":", 1)
                        self._recent[(lang.lower(), gend.lower())] = [str(x) for x in v][-self.max_history :]
        except Exception:
            pass

    def _save_history(self) -> None:
        if not self.history_path:
            return
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            out = {f"{l}:{g}": vals[-self.max_history :] for (l, g), vals in sorted(self._recent.items()) if vals}
            self.history_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except Exception:
            pass

    def find_by_voice_id(self, voice_id: str, language: Optional[str] = None) -> Optional[ElevenLabsVoiceEntry]:
        vid = (voice_id or "").strip()
        if not vid:
            return None
        lang_low = (language or "").strip().lower()
        for e in self.entries:
            if e.voice_id == vid and (not lang_low or e.language == lang_low):
                return e
        for e in self.entries:
            if e.voice_id == vid:
                return e
        return None

    def cast_script_voices(
        self,
        speakers: Sequence[str],
        language: str,
        *,
        video_type: str = "expression",
        script_id: Optional[str] = None,
        manual_genders: Optional[Dict[str, str]] = None,
        existing_voice_ids: Optional[Dict[str, str]] = None,
        explicit_accent: Optional[str] = None,
        force_fresh_cast: bool = False,
    ) -> Tuple[Dict[str, ElevenLabsVoiceEntry], Dict[str, str], str]:
        """Assigns distinct ElevenLabs voices for every speaker in a script.
        Returns `(speaker_entries, speaker_genders, resolved_accent)`.
        """
        lang = (language or "english").strip().lower()
        accent = pick_elevenlabs_accent(lang, script_id=script_id, explicit_accent=explicit_accent)
        vtype_low = (video_type or "expression").strip().lower()

        narrator_keys = [s for s in speakers if "narrator" in s.lower()]
        char_keys = [s for s in speakers if "narrator" not in s.lower()]
        ordered_speakers = char_keys + narrator_keys

        # Resolve genders (opposite genders for P1/P2 when unspecified)
        genders: Dict[str, str] = {}
        manual_g = manual_genders or {}
        for idx, spk in enumerate(char_keys):
            if spk in manual_g and manual_g[spk] in ("male", "female"):
                genders[spk] = manual_g[spk]
            else:
                genders[spk] = "female" if idx % 2 == 0 else "male"

        for narr in narrator_keys:
            if narr in manual_g and manual_g[narr] in ("male", "female"):
                genders[narr] = manual_g[narr]
            elif char_keys:
                genders[narr] = "male" if genders[char_keys[0]] == "female" else "female"
            else:
                genders[narr] = "female" if (_script_num(script_id) % 2 == 1) else "male"

        used_voice_ids: Set[str] = set()
        assignments: Dict[str, ElevenLabsVoiceEntry] = {}
        existing = {} if force_fresh_cast else (existing_voice_ids or {})

        for spk in ordered_speakers:
            gend = genders[spk]
            is_narrator = "narrator" in spk.lower()

            # Reuse saved ElevenLabs voice_id if present and not colliding
            saved_id = str(existing.get(spk) or "").strip()
            if saved_id and saved_id not in used_voice_ids:
                ent = self.find_by_voice_id(saved_id, language=lang)
                if ent is not None:
                    assignments[spk] = ent
                    used_voice_ids.add(ent.voice_id)
                    continue
                # Preserve custom user Voice Library ID even if not in default list
                assignments[spk] = ElevenLabsVoiceEntry(
                    voice_id=saved_id,
                    name=saved_id,
                    language=lang,
                    gender=gend,
                    accent=accent,
                    archetypes=("warm_narrator", "roleplay_actor"),
                )
                used_voice_ids.add(saved_id)
                continue

            # Candidate pool for language + gender
            pool = [e for e in self.entries if e.language == lang and e.gender == gend and e.voice_id not in used_voice_ids]
            if not pool:
                pool = [e for e in self.entries if e.language == lang and e.voice_id not in used_voice_ids]
            if not pool:
                pool = [e for e in self.entries if e.gender == gend and e.voice_id not in used_voice_ids]
            if not pool:
                pool = list(self.entries)

            # Accent preference
            acc_pool = [e for e in pool if e.accent == accent]
            if acc_pool:
                pool = acc_pool

            # Role/archetype preference
            if is_narrator:
                pref_archs = ("energetic_host", "warm_narrator") if vtype_low == "game" else ("warm_narrator", "roleplay_actor")
            else:
                pref_archs = ("roleplay_actor",)
            arch_pool = [e for e in pool if any(a in e.archetypes for a in pref_archs)]
            if arch_pool:
                pool = arch_pool

            # Full-cycle LRU anti-repetition: use every unheard voice before repeating any voice;
            # once all voices in the pool have been heard, pick the least-recently-used voice.
            hist = self._recent.get((lang, gend), [])
            if hist and len(pool) > 1:
                unheard = [e for e in pool if e.voice_id not in hist]
                if unheard:
                    pool = unheard
                else:
                    rank = {vid: pos for pos, vid in enumerate(hist)}
                    min_rank = min(rank.get(e.voice_id, -1) for e in pool)
                    lru_pool = [e for e in pool if rank.get(e.voice_id, -1) == min_rank]
                    if lru_pool:
                        pool = lru_pool

            role_salt = 0 if is_narrator else (int(hashlib.sha256(spk.lower().encode("utf-8")).hexdigest()[:8], 16) % len(pool))
            chosen = pool[(_script_num(script_id) + role_salt) % len(pool)]

            assignments[spk] = chosen
            used_voice_ids.add(chosen.voice_id)
            hist_list = self._recent.setdefault((lang, gend), [])
            if chosen.voice_id in hist_list:
                hist_list.remove(chosen.voice_id)
            hist_list.append(chosen.voice_id)
            if len(hist_list) > self.max_history:
                del hist_list[0 : len(hist_list) - self.max_history]

        self._save_history()
        return assignments, genders, accent
