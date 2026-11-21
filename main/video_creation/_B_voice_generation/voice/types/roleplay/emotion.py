"""
voice/types/roleplay/emotion.py — Multilingual Roleplay turn emotion classifier & same-speaker energy-tier resolver.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ...common.bank_manifest import VoiceBankManifest

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
    `'baseline'`, `'high_energy'`, or `'surprised_urgent'`.
    """
    emo_low = (emotion or "").lower()
    txt_low = (text or "").lower()
    combined = f"{emo_low} {txt_low}"

    if any(k in emo_low for k in _SURPRISED_URGENT_KEYWORDS) or ("?!" in text) or ("!?" in text):
        return "surprised_urgent"
    if any(k in emo_low for k in _HIGH_ENERGY_KEYWORDS):
        return "high_energy"
    if "?" in text and any(k in txt_low for k in ("what", "quoi", "comment", "qué", "cómo", "cosa", "come", "davvero", "really", "seriously", "serio")):
        return "surprised_urgent"
    if "!" in text:
        return "high_energy"
    if any(k in combined for k in ("frustrat", "panic", "stress", "anxious", "nervous", "worried", "peur", "miedo", "paura")):
        return "surprised_urgent"
    return "baseline"


def resolve_roleplay_turn_reference(
    base_voice_path: Path,
    emotion: str,
    text: str,
    section: str,
    manifest: Optional[VoiceBankManifest],
    open_swara_dir: Optional[Path] = None,
) -> Path:
    """Switches to the SAME speaker's `high_energy` or `surprised_urgent` take when available.

    Guarantees 100% speaker timbre continuity across turns while letting `1.7B-Base` ICL
    deliver genuine emotional dynamics. Falls back safely to `base_voice_path` if no variant exists.
    """
    if manifest is None or base_voice_path is None:
        return base_voice_path
    tier = classify_roleplay_energy_tier(emotion, text, section)
    if tier == "baseline":
        return base_voice_path
    variant = manifest.find_speaker_energy_variant(base_voice_path.name, tier, open_swara_dir=open_swara_dir)
    if variant and variant.exists():
        return variant
    return base_voice_path
