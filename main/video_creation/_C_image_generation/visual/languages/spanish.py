"""
visual/languages/spanish.py — Spanish visual palette and idiom markers.
"""
from __future__ import annotations

from .base import LanguageVisualProfile

SPANISH_PROFILE = LanguageVisualProfile(
    language="spanish",
    lang_code="S",
    aliases=("es", "español", "espanol", "castellano", "latam"),
    palette_mood=(
        "BRAND PALETTE MOOD (SPANISH): Warm, energetic, expressive, welcoming.\n"
        "Key Accent Colors: Warm Cream, Orange, Terracotta, and Botanical Green.\n"
    ),
    idiom_markers=(
        "dicho", "modismo", "idiotismo", "refrán", "locución idiomática", "expresión idiomática",
        "costar un ojo", "ojo de la cara", "tomar el pelo", "en las nubes", "pan comido",
    ),
    idiom_environments=(
        (("pan comido",), "chic modern social dining salon or studio lounge (featuring: central display table showcasing an elaborate towering multi-tier cake with a single slice removed, stylish seating lounge, sunlit terrace)"),
        (("ojo de la cara",), "chic metropolitan haute-couture boutique and promenade (featuring: extravagant luxury mannequin displays, marble counter, elegant shopping boulevard)"),
    ),
    cultural_cue="Hispanic and Spanish-speaking everyday plaza, home, and creative settings",
)
