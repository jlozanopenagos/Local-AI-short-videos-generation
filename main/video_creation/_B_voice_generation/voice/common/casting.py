"""
voice/common/casting.py — Anti-repetition voice casting, neutral dialect routing, and 3-speaker separation.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from .bank_manifest import (
    KOKORO_ALIAS_CANONICAL_SPEAKER,
    LOW_QUALITY_OPEN_SWARA,
    VoiceBankManifest,
)
from .models import LanguageVoiceProfile, VoiceBankEntry


# Listening & acoustic-audit feedback: keep these available only for explicit casts and fallback.
_NARRATOR_FALLBACK_SPEAKERS = frozenset({
    "en_m_intimate_storyteller_09",  # Too understated / low HNR on games.
    "en_m_us_host_01",              # Delivery sounded shouted.
    "it_m_intimate_storyteller_09",  # Low HNR / raspy on games.
    "es_f_intimate_storyteller_09",  # Too understated for high-energy narration.
    "fr_f_intimate_storyteller_09",  # Too understated for high-energy narration.
    "en_f_narrator_low_07",          # Flat/low-energy baseline.
    "fr_f_narrator_low_07",          # Flat/low-energy baseline.
    "it_f_narrator_low_07",          # Flat/low-energy baseline.
    "es_f_narrator_low_07",          # Flat/low-energy baseline.
})

# Understated / actor-only speaker substrings never preferred as GAME quiz hosts or FUN_FACTS narrators.
_GAME_EXCLUDED_SUBSTRINGS = (
    "intimate_storyteller",
    "narrator_low",
    "roleplay_dry",
    "roleplay_quick",
    "roleplay_grounded",
    "roleplay_warm",
)
_FUN_FACTS_EXCLUDED_SUBSTRINGS = (
    "roleplay_dry",
    "roleplay_quick",
    "roleplay_grounded",
    "roleplay_warm",
)
_NARRATOR_EXCLUDED_SUBSTRINGS = ("roleplay_dry",)


def canonical_speaker_identity(path: Path, bank_entry: Optional[VoiceBankEntry] = None) -> str:
    """Returns a stable physical speaker identity (merging Kokoro alias filenames)."""
    if bank_entry is not None:
        return f"{bank_entry.language}:{bank_entry.gender}:{bank_entry.speaker_id}"
    name = path.name.lower()
    if "kokoro_golden" in name:
        for suffix, canon in KOKORO_ALIAS_CANONICAL_SPEAKER.items():
            if name.endswith(f"_{suffix}.wav"):
                return f"kokoro:{canon}"
    return path.stem.lower()


def _script_numeric_index(script_id: Optional[str]) -> int:
    if not script_id:
        return 0
    digits = re.findall(r"\d+", str(script_id))
    if digits:
        return int(digits[-1])
    digest = hashlib.sha256(str(script_id).encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def pick_weighted_accent(
    lang_profile: LanguageVoiceProfile,
    script_id: Optional[str] = None,
    dialect_hint: Optional[str] = None,
) -> Optional[str]:
    """Resolves a target neutral accent via dialect lock or deterministic weighted rotation."""
    if dialect_hint and dialect_hint in lang_profile.default_accent_weights:
        return dialect_hint
    weights = lang_profile.default_accent_weights or {}
    if not weights:
        return dialect_hint
    if len(weights) == 1:
        return next(iter(weights.keys()))

    # Build a crisp 20-slot weighted cycle (e.g. 15 es_latam_neutral + 5 es_spain_castilian for 75/25)
    cycle: List[str] = []
    for accent, w in sorted(weights.items(), key=lambda kv: -kv[1]):
        slots = max(1, int(round(float(w) * 20)))
        cycle.extend([accent] * slots)
    # Interleave deterministically via Bresenham-style slot distribution so any 2-accent ratio
    # (e.g. 60/40 or 75/25) is exact over each 10/20-script window without bunching.
    accents_ordered = sorted(weights.keys(), key=lambda a: -weights[a])
    if len(accents_ordered) == 2 and float(weights[accents_ordered[1]]) > 0:
        slots_total = 20
        minority_slots = max(1, min(slots_total - 1, int(round(float(weights[accents_ordered[1]]) * slots_total))))
        idx = _script_numeric_index(script_id)
        if script_id and ((idx * minority_slots) % slots_total) < minority_slots:
            return accents_ordered[1]
        return accents_ordered[0]

    idx = _script_numeric_index(script_id)
    return cycle[idx % len(cycle)]


class VoiceCastingEngine:
    """Selects distinct, expressive, anti-repetition reference voices per language, accent, and video type."""

    def __init__(self, max_history_per_key: int = 8, history_path: Optional[Path] = None):
        self.max_history = max(2, max_history_per_key)
        self.history_path: Optional[Path] = Path(history_path) if history_path else None
        self._recent_by_bucket: Dict[Tuple[str, str], List[str]] = {}
        self._load_history()

    def _load_history(self) -> None:
        if not self.history_path or not self.history_path.exists():
            return
        try:
            payload = json.loads(self.history_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(payload, dict):
            return
        for raw_key, items in payload.items():
            if not isinstance(raw_key, str) or ":" not in raw_key or not isinstance(items, list):
                continue
            lang, gend = raw_key.split(":", 1)
            clean_items = [str(x) for x in items if isinstance(x, str) and x.strip()]
            if clean_items:
                self._recent_by_bucket[(lang.lower(), gend.lower())] = clean_items[-self.max_history :]

    def _save_history(self) -> None:
        if not self.history_path:
            return
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            serialized = {
                f"{lang}:{gend}": list(items[-self.max_history :])
                for (lang, gend), items in sorted(self._recent_by_bucket.items())
                if items
            }
            self.history_path.write_text(
                json.dumps(serialized, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except Exception:
            pass

    def record_assignment(self, language: str, gender: str, speaker_identity: str) -> None:
        key = (language.lower(), gender.lower())
        hist = self._recent_by_bucket.setdefault(key, [])
        if speaker_identity in hist:
            hist.remove(speaker_identity)
        hist.append(speaker_identity)
        if len(hist) > self.max_history:
            del hist[0 : len(hist) - self.max_history]
        self._save_history()

    def _build_candidate_records(
        self,
        open_swara_dir: Path,
        lang: str,
        gender: str,
        all_paths: Sequence[Path],
        manifest: Optional[VoiceBankManifest],
        is_acceptable_fn,
    ) -> List[Tuple[Path, str, int, Optional[VoiceBankEntry]]]:
        """Builds `(path, canonical_speaker_id, tier_rank, bank_entry)` sorted by quality tier.
        Tier priority in `typed` mode:
          0: Curated VoiceDesign baseline clips from `voice_bank_manifest.json`
          1: Clean audited `open_swara` human clips
          2: `kokoro_golden` clips (demoted to fallback)
        """
        records: List[Tuple[Path, str, int, Optional[VoiceBankEntry]]] = []
        seen_paths: Set[str] = set()

        if manifest is not None:
            for ent in manifest.get_entries(lang, gender, energy_tier="baseline"):
                p = manifest.resolve_path(ent, open_swara_dir)
                if p.exists() and is_acceptable_fn(p, lang):
                    key = p.name.lower()
                    if key not in seen_paths:
                        seen_paths.add(key)
                        tier = 0 if ent.source == "voice_design" else 1
                        records.append((p, canonical_speaker_identity(p, ent), tier, ent))

        for p in sorted(all_paths, key=lambda x: x.name):
            key = p.name.lower()
            if key in seen_paths or not p.exists() or not is_acceptable_fn(p, lang):
                continue
            if key in LOW_QUALITY_OPEN_SWARA:
                continue
            ent = manifest.find_entry_by_audio(p.name) if manifest else None
            if "kokoro_golden" in key:
                tier = 2
            else:
                tier = 1
            seen_paths.add(key)
            records.append((p, canonical_speaker_identity(p, ent), tier, ent))

        return records

    def select_speaker_voice(
        self,
        *,
        open_swara_dir: Path,
        language: str,
        gender: str,
        role: str,
        video_type: str,
        all_paths: Sequence[Path],
        manifest: Optional[VoiceBankManifest],
        lang_profile: LanguageVoiceProfile,
        is_acceptable_fn,
        used_identities: Set[str],
        used_filenames: Set[str],
        script_id: Optional[str] = None,
        dialect_hint: Optional[str] = None,
        exclude_voices: Optional[Set[str]] = None,
    ) -> Optional[Path]:
        """Selects one non-repetitive, accent-aligned, role-suitable voice Path."""
        records = self._build_candidate_records(
            open_swara_dir=open_swara_dir,
            lang=language,
            gender=gender,
            all_paths=all_paths,
            manifest=manifest,
            is_acceptable_fn=is_acceptable_fn,
        )
        if not records:
            return None

        # 1. Exclude voices already taken by another speaker in THIS script or requested by modifier recast
        ex_low = {Path(v).name.lower() for v in (exclude_voices or set())}
        pool = [
            rec for rec in records
            if rec[1] not in used_identities
            and rec[0].name.lower() not in used_filenames
            and rec[0].name.lower() not in ex_low
        ]
        if not pool:
            # Relax external exclude_voices before ever violating same-script uniqueness
            pool = [
                rec for rec in records
                if rec[1] not in used_identities and rec[0].name.lower() not in used_filenames
            ]
        if not pool:
            pool = records

        # 2. Restrict to highest available quality tier (e.g. VoiceDesign + open_swara before Kokoro fallback)
        has_voice_design = any(r[2] == 0 for r in pool)
        has_human_open_swara = any(r[2] == 1 for r in pool)
        if has_voice_design and has_human_open_swara:
            # Blend VoiceDesign expressive clips + clean open_swara human clips
            tiered_pool = [r for r in pool if r[2] in (0, 1)]
        elif has_voice_design:
            tiered_pool = [r for r in pool if r[2] == 0]
        elif has_human_open_swara:
            tiered_pool = [r for r in pool if r[2] == 1]
        else:
            tiered_pool = pool

        # 3. Exclude reviewed fallback/actor-only speakers for Narrator BEFORE accent filtering
        #    so recasting in a small-accent bucket (e.g. en_uk_neutral) never forces a blacklisted voice.
        is_narrator = "narrator" in role.lower()
        vtype_low = (video_type or "expression").lower()
        if is_narrator:
            preferred_pool = [
                r for r in tiered_pool
                if r[3] is None or (
                    r[3].speaker_id not in _NARRATOR_FALLBACK_SPEAKERS
                    and not any(sub in r[3].speaker_id for sub in _NARRATOR_EXCLUDED_SUBSTRINGS)
                    and not (vtype_low == "game" and any(sub in r[3].speaker_id for sub in _GAME_EXCLUDED_SUBSTRINGS))
                    and not (vtype_low == "fun_facts" and any(sub in r[3].speaker_id for sub in _FUN_FACTS_EXCLUDED_SUBSTRINGS))
                )
            ]
            if preferred_pool:
                tiered_pool = preferred_pool

        # 4. Neutral accent matching when VoiceDesign bank has accent-tagged entries
        target_accent = pick_weighted_accent(lang_profile, script_id=script_id, dialect_hint=dialect_hint)
        if target_accent:
            accent_matched = [r for r in tiered_pool if r[3] is not None and r[3].accent == target_accent]
            if accent_matched:
                tiered_pool = accent_matched

        # 5. Choose the performance style before rotating among suitable voices.
        if is_narrator:
            if vtype_low == "game":
                archetype_groups = (
                    ("energetic_host",),
                    ("energetic_host", "warm_narrator"),
                )
            elif vtype_low == "fun_facts":
                archetype_groups = (
                    ("warm_narrator",),
                    ("warm_narrator", "energetic_host"),
                )
            else:
                archetype_groups = (
                    ("warm_narrator", "roleplay_actor"),
                    ("warm_narrator", "energetic_host", "roleplay_actor"),
                )
        else:
            archetype_groups = (("roleplay_actor", "expressive_actor"),)

        min_required = 2 if is_narrator else 1
        for archetypes in archetype_groups:
            matched = [
                r for r in tiered_pool
                if r[3] is not None and any(a in r[3].archetypes for a in archetypes)
            ]
            if len({r[1] for r in matched}) >= min_required:
                tiered_pool = matched
                break

        if not is_narrator and vtype_low == "roleplay" and manifest is not None and hasattr(manifest, "find_speaker_energy_variant"):
            _emo_tiers = ("surprised_urgent", "high_energy", "embarrassed", "frustrated", "reassuring")
            with_variants = [
                r for r in tiered_pool
                if any(
                    manifest.find_speaker_energy_variant(r[0].name, tier, open_swara_dir=open_swara_dir) is not None
                    for tier in _emo_tiers
                )
            ]
            if len({r[1] for r in with_variants}) >= 1:
                tiered_pool = with_variants

        # 5. Deduplicate Kokoro alias twins within candidate list so weights stay fair
        deduped: List[Tuple[Path, str, int, Optional[VoiceBankEntry]]] = []
        seen_ids: Set[str] = set()
        for rec in tiered_pool:
            if rec[1] not in seen_ids:
                seen_ids.add(rec[1])
                deduped.append(rec)

        # 6. Anti-repetition filter against recent history for this (language, gender)
        hist = self._recent_by_bucket.get((language.lower(), gender.lower()), [])
        if hist and len(deduped) > 1:
            non_recent = [r for r in deduped if r[1] not in hist]
            if not non_recent:
                # At minimum exclude the immediately preceding voice!
                last_used = hist[-1]
                non_recent = [r for r in deduped if r[1] != last_used]
            if non_recent:
                deduped = non_recent

        # 7. Deterministic script-ID rotation over remaining eligible speakers
        if script_id:
            role_digest = int(hashlib.sha256(role.lower().encode("utf-8")).hexdigest()[:8], 16)
            role_salt = 0 if is_narrator else (role_digest % len(deduped))
            idx = (_script_numeric_index(script_id) + role_salt) % len(deduped)
            chosen = deduped[idx]
        else:
            chosen = deduped[0]

        used_identities.add(chosen[1])
        used_filenames.add(chosen[0].name.lower())
        self.record_assignment(language, gender, chosen[1])
        return chosen[0]
