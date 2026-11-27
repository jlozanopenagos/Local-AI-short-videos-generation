"""
voice/types/roleplay/emotion.py — Multilingual Roleplay turn emotion classifier & same-speaker energy-tier resolver.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

from ...common.bank_manifest import VoiceBankManifest

MAX_VARIANT_PITCH_DRIFT_SEMITONES = 4.5

_ACTING_REFERENCE_CUES = {
    "embarrassed": ("embarrass", "fluster", "gêné", "gene", "avergonz", "imbarazz"),
    "frustrated": ("frustr", "exasp", "annoy", "angry", "furious", "agacé", "agace",
                   "énerv", "enerv", "molest", "enoj", "enfad", "arrabbi", "infastid"),
    "reassuring": ("reassur", "rassur", "calm", "tranquil", "rilassat", "encourag"),
}

_SURPRISED_URGENT_KEYWORDS = (
    # English
    "surpris", "shock", "incredul", "baffl", "panick", "anxious", "urgenc", "terrified",
    "scared", "nervous", "worried", "frustrat", "exasperat", "angry", "furious", "embarrass",
    "skeptic", "disbelief", "what?", "wait", "no way",
    # French
    "surpris", "choqu", "inquiet", "stress", "paniqu", "frustr", "exasp", "énerv", "enerv",
    "embarrass", "incrédule", "sceptiqu", "vraiment", "comment",
    # Spanish
    "sorprend", "asombr", "preocup", "nervios", "frustrad", "enojad", "enfadad", "furios",
    "avergonz", "incrédul", "escéptic", "urgencia", "qué?", "espera", "en serio",
    # Italian
    "sorpres", "scioccat", "preoccup", "ansia", "ansios", "frustrat", "arrabbiat", "incredul",
    "imbarazz", "scettic", "urgenza", "davvero", "sul serio", "ma come",
)

_HIGH_ENERGY_KEYWORDS = (
    # English
    "hyped", "excit", "enthusiast", "celebrat", "cheerful", "triumph", "playful", "teas",
    "amused", "laugh", "proud", "delighted", "superstar", "relieved", "bright", "eager",
    # French
    "enthousias", "excit", "joyeux", "amus", "moqu", "taquin", "fier", "ravi", "soulag",
    "génial", "super", "bravo",
    # Spanish
    "entusias", "emoci", "alegre", "divert", "burl", "orgull", "feliz", "alivi",
    "genial", "vamos", "campeón", "celebr",
    # Italian
    "entusias", "eccitat", "allegr", "divert", "scherz", "orgogli", "felice", "sollev",
    "fantastico", "grandioso", "bravissim", "evviva",
)

EXTENDED_ROLEPLAY_EMOTIONS = {
    # Multilingual parenthetical tags -> vivid English acting directives
    "teasing": "playful, teasing, and lighthearted conversational banter",
    "embarrassed": "flustered, embarrassed, and stammering with humorous discomfort",
    "skeptical": "skeptical, doubtful, and questioning with raised eyebrow energy",
    "annoyed": "mildly annoyed, sharp, and impatiently expressive",
    "excited": "genuinely excited, upbeat, and bursting with lively enthusiasm",
    "relieved": "relieved, bright, and exhaling with happy gratitude",
    "taquin": "playful, teasing, and lighthearted conversational banter",
    "gêné": "flustered, embarrassed, and stammering with humorous discomfort",
    "gene": "flustered, embarrassed, and stammering with humorous discomfort",
    "sceptique": "skeptical, doubtful, and questioning with raised eyebrow energy",
    "agacé": "mildly annoyed, sharp, and impatiently expressive",
    "agace": "mildly annoyed, sharp, and impatiently expressive",
    "burlón": "playful, teasing, and lighthearted conversational banter",
    "avergonzado": "flustered, embarrassed, and stammering with humorous discomfort",
    "escéptico": "skeptical, doubtful, and questioning with raised eyebrow energy",
    "molesto": "mildly annoyed, sharp, and impatiently expressive",
    "emocionado": "genuinely excited, upbeat, and bursting with lively enthusiasm",
    "imbarazzato": "flustered, embarrassed, and stammering with humorous discomfort",
    "scettico": "skeptical, doubtful, and questioning with raised eyebrow energy",
    "infastidito": "mildly annoyed, sharp, and impatiently expressive",
    "emozionato": "genuinely excited, upbeat, and bursting with lively enthusiasm",
    "entusiasta": "genuinely excited, upbeat, and bursting with lively enthusiasm",
}


def classify_roleplay_energy_tier(emotion: str, text: str, section: str = "") -> str:
    """Maps a dialogue turn's acting emotion & text cues to one of 3 Voice Bank energy tiers:
    Acting-specific references take precedence over punctuation and energy cues.
    """
    emo_low = (emotion or "").lower()
    txt_low = (text or "").lower()
    for tier, cues in _ACTING_REFERENCE_CUES.items():
        if any(cue in emo_low for cue in cues):
            return tier

    if any(k in emo_low for k in _SURPRISED_URGENT_KEYWORDS) or ("?!" in text) or ("!?" in text):
        return "surprised_urgent"
    if any(k in emo_low for k in _HIGH_ENERGY_KEYWORDS):
        return "high_energy"
    if "?" in text and any(k in txt_low for k in ("what", "quoi", "comment", "qué", "cómo", "cosa", "come", "davvero", "really", "seriously", "serio")):
        return "surprised_urgent"
    if "!" in text:
        return "high_energy"
    if any(k in txt_low for k in ("panic", "stress", "anxious", "nervous", "worried", "peur", "miedo", "paura")):
        return "surprised_urgent"
    return "baseline"


_ACTING_TIER_FALLBACKS = {
    "frustrated": ("surprised_urgent", "high_energy"),
    "embarrassed": ("surprised_urgent", "high_energy"),
    "reassuring": ("baseline",),
    "surprised_urgent": ("high_energy",),
    "high_energy": ("surprised_urgent",),
}


def _is_variant_pitch_aligned(
    manifest: Optional[VoiceBankManifest],
    base_voice_path: Path,
    variant_path: Path,
    max_semitones: float = MAX_VARIANT_PITCH_DRIFT_SEMITONES,
) -> bool:
    """Rejects same-speaker variants whose manifest median F0 drifts beyond `max_semitones` from baseline."""
    lookup_fn = getattr(manifest, "find_entry_by_audio", None)
    if not callable(lookup_fn):
        return True
    base_ent = lookup_fn(base_voice_path.name)
    var_ent = lookup_fn(variant_path.name)
    base_f0 = getattr(base_ent, "f0_mean", None)
    var_f0 = getattr(var_ent, "f0_mean", None)
    if (
        isinstance(base_f0, (int, float))
        and isinstance(var_f0, (int, float))
        and not isinstance(base_f0, bool)
        and not isinstance(var_f0, bool)
        and base_f0 > 0
        and var_f0 > 0
    ):
        semitones = abs(12.0 * math.log2(float(var_f0) / float(base_f0)))
        return semitones <= max_semitones
    return True


def resolve_roleplay_turn_reference(
    base_voice_path: Path,
    emotion: str,
    text: str,
    section: str,
    manifest: Optional[VoiceBankManifest],
    open_swara_dir: Optional[Path] = None,
) -> Path:
    """Use a matching emotional reference for the cast speaker when one exists,
    falling back from fine-grained acting cues to available `surprised_urgent` / `high_energy` tiers.
    """
    if manifest is None or base_voice_path is None:
        return base_voice_path
    tier = classify_roleplay_energy_tier(emotion, text, section)
    if tier == "baseline":
        return base_voice_path
    variant = manifest.find_speaker_energy_variant(base_voice_path.name, tier, open_swara_dir=open_swara_dir)
    if variant and variant.exists() and _is_variant_pitch_aligned(manifest, base_voice_path, variant):
        return variant
    for fallback_tier in _ACTING_TIER_FALLBACKS.get(tier, ()):
        if fallback_tier == "baseline":
            return base_voice_path
        fb = manifest.find_speaker_energy_variant(base_voice_path.name, fallback_tier, open_swara_dir=open_swara_dir)
        if fb and fb.exists() and fb != base_voice_path and _is_variant_pitch_aligned(manifest, base_voice_path, fb):
            return fb
    return base_voice_path
