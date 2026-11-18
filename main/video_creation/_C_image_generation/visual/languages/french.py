"""
visual/languages/french.py — French visual palette and idiom markers.
"""
from __future__ import annotations

from .base import LanguageVisualProfile

FRENCH_PROFILE = LanguageVisualProfile(
    language="french",
    lang_code="F",
    aliases=("fr", "français", "francais"),
    palette_mood=(
        "BRAND PALETTE MOOD (FRENCH): Elegant, warm, cultured, friendly.\n"
        "Key Accent Colors: French Blue, Deep Teal, and restrained Red.\n"
    ),
    idiom_markers=(
        "expression idiomatique",
        "poser un lapin", "yeux de la tête", "coup de foudre", "dans les pommes", "du gâteau",
    ),
    idiom_environments=(
        (("du gâteau",), "chic modern social dining salon or studio lounge (featuring: central display table showcasing an elaborate towering multi-tier cake with a single slice removed, stylish seating lounge, sunlit terrace)"),
        (("dans les pommes",), "cozy sunlit living room and wellness study (featuring: comfortable sofa with warm knitted throw, warm ceramic tea mugs on a low wooden table, soft reading window, warm fireplace mantle)"),
        (("yeux de la tête",), "chic metropolitan haute-couture boutique and promenade (featuring: extravagant luxury mannequin displays, marble counter, elegant shopping boulevard)"),
        (("poser un lapin",), "charming historic bistro exterior and clock tower plaza (featuring: outdoor cafe table with an untouched cup, historic clock face showing late time, cobblestone promenade)"),
    ),
    cultural_cue="French everyday cultural, Parisian/provincial architectural, and social settings",
)
