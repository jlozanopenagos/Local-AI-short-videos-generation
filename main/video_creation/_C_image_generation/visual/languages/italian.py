"""
visual/languages/italian.py — Italian visual palette and idiom markers.
"""
from __future__ import annotations

from .base import LanguageVisualProfile

ITALIAN_PROFILE = LanguageVisualProfile(
    language="italian",
    lang_code="I",
    aliases=("it", "italiano"),
    palette_mood=(
        "BRAND PALETTE MOOD (ITALIAN): Warm, passionate, stylish, vibrant.\n"
        "Key Accent Colors: Mediterranean Blue, Olive Green, Warm Terracotta, and Sunlit Gold.\n"
    ),
    idiom_markers=(
        "in bocca al lupo", "occhio della testa", "mani bucate", "lucciole per lanterne",
    ),
    idiom_environments=(
        (("in bocca al lupo",), "historic theater and performing arts center (featuring: dressing room with mirror, backstage wings with velvet curtains, rehearsal stage, grand auditorium)"),
        (("occhio della testa",), "chic metropolitan haute-couture boutique and promenade (featuring: extravagant luxury mannequin displays, marble counter, elegant shopping boulevard)"),
    ),
    cultural_cue="Italian Mediterranean piazza, trattoria, atelier, and domestic settings",
)
