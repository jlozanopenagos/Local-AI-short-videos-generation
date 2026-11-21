"""
voice/common/bank_manifest.py — Curated VoiceDesign bank manifest loader, open_swara cleaner, and variant lookup.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import config

from .models import VoiceBankEntry

# Known Kokoro alias files on disk that are acoustically duplicates of another golden clip
KOKORO_ALIAS_CANONICAL_SPEAKER = {
    "baritone": "kokoro_g1",
    "char1": "kokoro_g1",
    "alto": "kokoro_g1",
    "bass": "kokoro_g2",
    "char2": "kokoro_g2",
    "mezzo": "kokoro_g2",
    "narrator": "kokoro_narrator",
    "tenor": "kokoro_tenor",
    "soprano": "kokoro_soprano",
}

# Known corrupted / low-SNR / English-bleed Open-Swara clips to avoid in typed mode
LOW_QUALITY_OPEN_SWARA = {
    "french_male_open_swara_001.wav",  # 6.3% clipping in reference_audit.csv
    "french_male_open_swara_019.wav",  # low SNR (18.9 dB)
    "italian_male_open_swara_004.wav",  # lower score (73) / low lang_prob (0.88)
}

# Canonical calibration sentences read by non-English Open-Swara clips to repair Whisper ASR typos
_CLEAN_CALIBRATION_TRANSCRIPTS = {
    "french": "La chaleur du soleil matinale apporte un sentiment de calme et de clarté pour la journée à venir.",
    "spanish": "La calidez del sol de la mañana trae una sensación de calma y claridad para el día que viene.",
    "italian": "Il calore del sole mattutino porta un senso di calma e chiarezza per la giornata a venire.",
}

_FRENCH_TYPO_TRIGGERS = ("achelleur", "mattinale", "clarter", "clartis", "sherlock", "quartet", "chale en", "l'ajourner", "calmer de")
_SPANISH_TYPO_TRIGGERS = ("la calidad del sol", "del sod", "calme y claridad", "calme claridad", "trabe una", "calidez es el sol")
_ITALIAN_TYPO_TRIGGERS = ("chiaretta", "porto un senso", "calme che ha", "che ha rezza", "eretza", "desso le")


def sanitize_ref_transcript(text: str, language: str = "", audio_name: str = "") -> str:
    """Repairs known Whisper transcription typos on Open-Swara calibration clips without altering custom transcripts."""
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", str(text)).strip()
    low = cleaned.lower()
    lang_low = (language or "").lower()
    name_low = (audio_name or "").lower()

    if "open_swara" in name_low or any(t in low for t in _FRENCH_TYPO_TRIGGERS + _SPANISH_TYPO_TRIGGERS + _ITALIAN_TYPO_TRIGGERS):
        if lang_low == "french" or name_low.startswith("french_") or "chaleur" in low or "achelleur" in low or "soleil matinal" in low:
            if any(t in low for t in _FRENCH_TYPO_TRIGGERS) or "matinale apportent" in low or "avez-vous" in low or "zip" in low:
                return _CLEAN_CALIBRATION_TRANSCRIPTS["french"]
        if lang_low == "spanish" or name_low.startswith("spanish_") or "sol de la mañana" in low or "del sod" in low:
            if any(t in low for t in _SPANISH_TYPO_TRIGGERS):
                return _CLEAN_CALIBRATION_TRANSCRIPTS["spanish"]
        if lang_low == "italian" or name_low.startswith("italian_") or "sole mattutino" in low or "desso le" in low:
            if any(t in low for t in _ITALIAN_TYPO_TRIGGERS):
                return _CLEAN_CALIBRATION_TRANSCRIPTS["italian"]
    return cleaned


def resolve_bank_manifest_path(open_swara_dir: Optional[Path] = None) -> Optional[Path]:
    """Resolves `voice_bank_manifest.json` from env override, open_swara sibling bank, or config."""
    env_bank = os.getenv("VOICE_BANK_DIR")
    if env_bank and env_bank.strip():
        cand = Path(env_bank.strip()) / "voice_bank_manifest.json"
        if cand.exists():
            return cand
    if open_swara_dir:
        for cand in (
            Path(open_swara_dir) / "voice_design_bank" / "voice_bank_manifest.json",
            Path(open_swara_dir) / "voice_bank_manifest.json",
        ):
            if cand.exists():
                return cand
    cfg_manifest = getattr(config, "VOICE_BANK_MANIFEST_PATH", None)
    if cfg_manifest and Path(cfg_manifest).exists():
        return Path(cfg_manifest)
    return None


def _entry_from_dict(raw: Dict) -> Optional[VoiceBankEntry]:
    try:
        archetypes_raw = raw.get("archetypes") or ("warm_narrator",)
        if isinstance(archetypes_raw, str):
            archetypes_raw = [archetypes_raw]
        return VoiceBankEntry(
            voice_id=str(raw["voice_id"]),
            speaker_id=str(raw.get("speaker_id") or raw["voice_id"]),
            language=str(raw["language"]).strip().lower(),
            gender=str(raw["gender"]).strip().lower(),
            accent=str(raw.get("accent") or "neutral").strip().lower(),
            energy_tier=str(raw.get("energy_tier") or "baseline").strip().lower(),
            archetypes=tuple(str(a).strip().lower() for a in archetypes_raw if a),
            rel_path=str(raw["rel_path"]),
            ref_text=str(raw.get("ref_text") or "").strip(),
            source=str(raw.get("source") or "voice_design"),
            f0_mean=float(raw.get("f0_mean", 0.0)),
            f0_var=float(raw.get("f0_var", 0.0)),
            snr_db=float(raw.get("snr_db", 0.0)),
            lang_prob=float(raw.get("lang_prob", 1.0)),
            active=bool(raw.get("active", True)),
        )
    except Exception:
        return None


class VoiceBankManifest:
    """Loads, queries, and matches curated Voice Bank entries and same-speaker energy variants."""

    def __init__(self, entries: List[VoiceBankEntry], root_dir: Path):
        self.entries = entries
        self.root_dir = root_dir
        self._by_path: Dict[str, VoiceBankEntry] = {}
        self._by_name: Dict[str, VoiceBankEntry] = {}
        self._by_speaker_tier: Dict[tuple, VoiceBankEntry] = {}
        for entry in entries:
            if not entry.active:
                continue
            self._by_path[entry.rel_path.replace("\\", "/")] = entry
            self._by_name[Path(entry.rel_path).name.lower()] = entry
            self._by_speaker_tier[(entry.language, entry.speaker_id, entry.energy_tier)] = entry

    @classmethod
    def load(cls, open_swara_dir: Optional[Path] = None) -> Optional["VoiceBankManifest"]:
        manifest_path = resolve_bank_manifest_path(open_swara_dir)
        if not manifest_path or not manifest_path.exists():
            return None
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        raw_entries = payload.get("voices", []) if isinstance(payload, dict) else []
        entries: List[VoiceBankEntry] = []
        root_dir = manifest_path.parent
        for item in raw_entries:
            ent = _entry_from_dict(item)
            if not ent or not ent.active:
                continue
            if ent.lang_prob < 0.90:
                continue
            cand_file = cls._resolve_entry_file(ent, root_dir, open_swara_dir)
            if cand_file and cand_file.exists():
                entries.append(ent)
        return cls(entries, root_dir=root_dir)

    @staticmethod
    def _resolve_entry_file(entry: VoiceBankEntry, manifest_root: Path, open_swara_dir: Optional[Path]) -> Optional[Path]:
        p_raw = Path(entry.rel_path)
        if p_raw.is_absolute() and p_raw.exists():
            return p_raw
        for base in (manifest_root, open_swara_dir):
            if base:
                cand = Path(base) / entry.rel_path
                if cand.exists():
                    return cand
        return manifest_root / entry.rel_path

    def resolve_path(self, entry: VoiceBankEntry, open_swara_dir: Optional[Path] = None) -> Path:
        return self._resolve_entry_file(entry, self.root_dir, open_swara_dir) or (self.root_dir / entry.rel_path)

    def get_entries(
        self,
        language: str,
        gender: str,
        energy_tier: str = "baseline",
        accent: Optional[str] = None,
    ) -> List[VoiceBankEntry]:
        lang_low = (language or "").strip().lower()
        gend_low = (gender or "").strip().lower()
        tier_low = (energy_tier or "baseline").strip().lower()
        out = []
        for e in self.entries:
            if e.language == lang_low and e.gender == gend_low and e.energy_tier == tier_low:
                if accent and e.accent != accent:
                    continue
                out.append(e)
        return out

    def find_entry_by_audio(self, audio_path_or_name: str) -> Optional[VoiceBankEntry]:
        if not audio_path_or_name:
            return None
        norm = str(audio_path_or_name).replace("\\", "/")
        return self._by_path.get(norm) or self._by_name.get(Path(norm).name.lower())

    def find_speaker_energy_variant(
        self,
        base_audio_name: str,
        energy_tier: str,
        open_swara_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        """Finds a different energy take (`high_energy` / `surprised_urgent`) for the SAME speaker_id."""
        ent = self.find_entry_by_audio(base_audio_name)
        if not ent:
            return None
        tier_low = (energy_tier or "baseline").strip().lower()
        if ent.energy_tier == tier_low:
            p = self.resolve_path(ent, open_swara_dir)
            return p if p.exists() else None
        variant = self._by_speaker_tier.get((ent.language, ent.speaker_id, tier_low))
        if variant:
            p = self.resolve_path(variant, open_swara_dir)
            if p.exists():
                return p
        return None

    def lookup_ref_text(self, audio_path_or_name: str) -> str:
        ent = self.find_entry_by_audio(audio_path_or_name)
        return ent.ref_text if ent else ""
