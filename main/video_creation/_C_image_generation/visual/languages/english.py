"""
visual/languages/english.py — English visual palette, heteronyms, and idiom markers.
"""
from __future__ import annotations

from .base import LanguageVisualProfile

ENGLISH_HETERONYM_DOMAINS = {
    "record": "acoustic music recording studio and audio production facility (featuring: sound control board, vocal tracking booth, live acoustic instrument room, vinyl listening lounge)",
    "permit": "metropolitan transit center and security checkpoint (featuring: vehicle entry barrier, administrative security desk, transit concourse, credential booth)",
    "project": "modern creative design and architectural innovation agency (featuring: drafting workstation, collaborative conference lounge, fabrication workbench, luminous presentation space)",
    "present": "festive celebration banquet hall or elegant reception venue (featuring: banquet dining table, presentation stage, gift alcove, outdoor terrace)",
    "object": "curiosity archives and historical appraisal chamber (featuring: specimen display cabinets, study desk, appraisal reference library, gallery room)",
    "contract": "executive law library or dynamic sports management facility (featuring: consultation desk, document archive, client lounge, athletic training arena)",
    "conduct": "symphony concert hall or scientific physics laboratory (featuring: orchestra podium, acoustic seating, research workstation, demonstration table)",
    "desert": "golden sand dune expedition camp (featuring: canvas safari tent, navigational map table, shaded campfire circle, desert overlook)",
    "increase": "bustling commercial logistics center or tech analytics trading office (featuring: dispatch floor, analytics whiteboard, trading station, logistics overview deck)",
    "decrease": "energy conservation laboratory or quiet evening study (featuring: efficiency monitoring workstation, resource optimization desk, quiet reading area)",
    "import": "international cargo shipping port and freight terminal (featuring: harbor viewing deck, customs office desk, container loading dock, logistics lounge)",
    "export": "international cargo shipping port and freight terminal (featuring: logistics dispatch desk, maritime harbor overlook, cargo staging area, freight gate)",
    "protest": "historic civic community hall or public city plaza (featuring: assembly stage, creative banner workshop, public steps, town hall courtyard)",
    "refuse": "sustainable design workshop and upcycling studio (featuring: material sorting station, fabrication bench, upcycled product gallery, design desk)",
    "rebel": "vintage printmaking atelier or underground creative studio (featuring: mechanical printing press, paper drafting table, typeset drawer wall, studio lounge)",
    "address": "formal conference auditorium or classic epistolary study (featuring: podium stage, library writing desk, correspondence cabinet, reading alcove)",
}

ENGLISH_PROFILE = LanguageVisualProfile(
    language="english",
    lang_code="E",
    aliases=("en", "eng", "american", "british"),
    palette_mood=(
        "BRAND PALETTE MOOD (ENGLISH): Warm, vibrant, natural, cinematic.\n"
        "Key Accent Colors: Forest Green, Warm Ochre, Rich Amber, Slate Blue, Cream.\n"
    ),
    idiom_markers=(
        "idiom", "saying", "figurative", "slang", "proverb", "idiomatic expression",
        "piece of cake", "break a leg", "bite the bullet", "spill the beans",
        "under the weather", "cost an arm and a leg", "burn the midnight oil",
        "hit the nail on the head", "once in a blue moon", "barking up the wrong tree",
        "cold feet", "see eye to eye", "ball is in your court", "cross that bridge",
        "call it a day", "cut corners", "easy as pie", "drop in the ocean",
        "rule of thumb", "through the grapevine", "pull someone's leg",
        "actions speak louder", "beat around the bush", "blessing in disguise",
    ),
    idiom_environments=(
        (("piece of cake", "easy as pie"), "chic modern social dining salon or studio lounge (featuring: central display table showcasing an elaborate towering multi-tier cake with a single slice removed, stylish seating lounge, sunlit terrace)"),
        (("break a leg",), "historic theater and performing arts center (featuring: dressing room with mirror, backstage wings with velvet curtains, rehearsal stage, grand auditorium)"),
        (("spill the beans",), "vibrant artisan kitchen and social pantry lounge (featuring: open prep counter with oversized ceramic bean jars, cozy banquette table, sunlit courtyard)"),
        (("under the weather",), "cozy sunlit living room and wellness study (featuring: comfortable sofa with warm knitted throw, warm ceramic tea mugs on a low wooden table, soft reading window, warm fireplace mantle)"),
        (("burn the midnight oil",), "quiet late-night home study and creative library (featuring: vintage wooden desk with brass lamp, tall bookshelves, armchair, evening city skyline window)"),
        (("cost an arm and a leg",), "chic metropolitan haute-couture boutique and promenade (featuring: extravagant luxury mannequin displays, marble counter, elegant shopping boulevard)"),
    ),
    heteronym_domains=ENGLISH_HETERONYM_DOMAINS,
    cultural_cue="English-speaking everyday urban, academic, and creative studio environments",
)
