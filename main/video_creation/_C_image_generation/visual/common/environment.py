"""
visual/common/environment.py — Anchor environment resolver, heteronym domains, and idiom detection.
"""
from __future__ import annotations

import re

HETERONYM_DOMAINS = {
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

EXPLICIT_SCENARIO_DOMAINS = [
    (r'\b(animation studio|animator|animation desk|storyboard room)\b', "creative modern animation studio at night (featuring: animator drawing desks with digital pen displays, animation lightboxes, pencil sketches pinned to corkboards, glowing monitors with timeline tracks, comfortable studio chairs, warm desk lamps against dark ambient room)"),
    (r'\b(rooftop cinema|cinema shoot|film shoot|movie set|film set)\b', "architectural rooftop cinema shoot at dusk (featuring: director clapperboards, brass megaphone, camera tripods, blueprint rolls, warm amber string lights, twilight skyline)"),
    (r'\b(bakery|bake|baker|pastry)\b', "warm artisan culinary bakery (featuring: rustic wooden prep counter, baker oven alcove, flour dusting on table, cooling racks)"),
    (r'\b(theater|theatre|stage|acting|backstage|curtain|actor|show|rehearsal)\b', "historic theater and performing arts center (featuring: backstage wings, rehearsal stage, dressing room with mirror, grand auditorium)"),
    (r'\b(kitchen|cook|chef|dessert|ingredient|dish|oven)\b', "warm artisan culinary kitchen (featuring: rustic wooden prep counter, cookware rack, dining table, pantry alcove)"),
    (r'\b(library|exam|study|student|homework|grade|assignment|textbook)\b', "university academic library (featuring: individual study carrel, collaborative reference desk, book stacks, reading lounge)"),
    (r'\b(airport|flight|plane|airplane|travel|suitcase|boarding|luggage)\b', "modern international airport terminal (featuring: panoramic tarmac lounge, check-in concourse, boarding gate, baggage reclaim)"),
    (r'\b(train|station|subway|metro|platform|railway)\b', "scenic railway station (featuring: passenger platform, ticketing hall, waiting concourse, vintage trackside bench)"),
    (r'\b(hospital|doctor|clinic|medical|patient|nurse|consultation)\b', "bright modern wellness and medical consultation clinic (featuring: examination room, consultation desk, waiting lounge)"),
    (r'\b(street|city|avenue|plaza|sidewalk|urban|crosswalk|boulevard)\b', "bustling historic city avenue (featuring: pedestrian sidewalk, brick storefronts, street corner plaza, park bench)"),
    (r'\b(park|garden|nature|tree|bench|flower|outdoor|trail)\b', "sunlit municipal park promenade (featuring: walking promenade, historic stone balustrade, shaded wooden bench, open lawn)"),
    (r'\b(gym|workout|fitness|sport|athletic|exercise|dumbbells)\b', "dynamic modern athletic training gym (featuring: fitness floor, weights zone, training track, recovery lounge)"),
    (r'\b(market|store|boutique|seller|bazaar|craft)\b', "neighborhood artisan market boutique (featuring: craft display table, checkout counter, goods shelf, street awning)"),
    (r'\b(beach|sea|ocean|coastal|boat|sand|shore)\b', "sunlit coastal seaside promenade (featuring: ocean overlook deck, sand dunes path, beach pavilion)"),
    (r'\b(cafe|coffee|barista|latte|espresso)\b', "charming artisanal coffee bar (featuring: espresso counter, window high-top bar, cozy seating corner)"),
]


def is_figurative_idiom(
    topic: str = "",
    lexical_field: str = "",
    scenario: str = "",
    script_text: str = "",
) -> bool:
    """Detects if the script is about an idiom or figurative expression across languages."""
    combined = f"{topic} {lexical_field} {scenario} {script_text}".lower()
    idiom_markers = [
        "idiom", "saying", "figurative", "slang", "proverb",
        "dicho", "modismo", "idiotismo", "refrán", "locución idiomática",
        "idiomatic expression", "expression idiomatique", "expresión idiomática",
        "piece of cake", "break a leg", "bite the bullet", "spill the beans",
        "under the weather", "cost an arm and a leg", "burn the midnight oil",
        "hit the nail on the head", "once in a blue moon", "barking up the wrong tree",
        "cold feet", "see eye to eye", "ball is in your court", "cross that bridge",
        "call it a day", "cut corners", "easy as pie", "drop in the ocean",
        "rule of thumb", "through the grapevine", "pull someone's leg",
        "actions speak louder", "beat around the bush", "blessing in disguise",
        # Multilingual Idioms
        "poser un lapin", "yeux de la tête", "coup de foudre", "dans les pommes", "du gâteau",
        "costar un ojo", "ojo de la cara", "tomar el pelo", "en las nubes", "pan comido",
        "in bocca al lupo", "occhio della testa", "mani bucate", "lucciole per lanterne",
    ]
    return any(marker in combined for marker in idiom_markers)


def resolve_anchor_environment(
    script_text: str,
    topic: str = "",
    scenario: str = "",
    lexical_field: str = "",
    label: str = "",
    video_type: str = "EXPRESSION"
) -> str:
    """
    Deduces a vivid, concrete, and consistent physical anchor environment for the script.
    Prevents the LLM from falling back to generic cafeterias or flipping locations between scenes.
    """
    combined_meta = f"{topic} {scenario} {lexical_field} {label}".lower()
    combined_script = f"{combined_meta} {script_text}".lower()

    # 1. Check explicit scenario / setting keywords first (highest priority)
    for pattern, domain in EXPLICIT_SCENARIO_DOMAINS:
        if scenario and re.search(pattern, scenario.lower()):
            return domain
        if topic and re.search(pattern, topic.lower()):
            return domain

    # 2. Check known heteronym / word stress domain mappings (only if topic is specifically that heteronym)
    for word_key, domain in HETERONYM_DOMAINS.items():
        if re.search(r'\b' + re.escape(word_key) + r'\b', topic.lower()):
            return domain

    # 2. Check for figurative idioms (Allows creative graphic visual metaphors)
    if is_figurative_idiom(topic, lexical_field, scenario, script_text):
        if any(w in combined_script for w in ("piece of cake", "easy as pie", "pan comido", "du gâteau")):
            return "chic modern social dining salon or studio lounge (featuring: central display table showcasing an elaborate towering multi-tier cake with a single slice removed, stylish seating lounge, sunlit terrace)"
        elif any(w in combined_script for w in ("break a leg", "in bocca al lupo")):
            return "historic theater and performing arts center (featuring: dressing room with mirror, backstage wings with velvet curtains, rehearsal stage, grand auditorium)"
        elif "spill the beans" in combined_script:
            return "vibrant artisan kitchen and social pantry lounge (featuring: open prep counter with oversized ceramic bean jars, cozy banquette table, sunlit courtyard)"
        elif any(w in combined_script for w in ("under the weather", "dans les pommes")):
            return "cozy sunlit living room and wellness study (featuring: comfortable sofa with warm knitted throw, warm ceramic tea mugs on a low wooden table, soft reading window, warm fireplace mantle)"
        elif "burn the midnight oil" in combined_script:
            return "quiet late-night home study and creative library (featuring: vintage wooden desk with brass lamp, tall bookshelves, armchair, evening city skyline window)"
        elif any(w in combined_script for w in ("cost an arm and a leg", "ojo de la cara", "yeux de la tête", "occhio della testa")):
            return "chic metropolitan haute-couture boutique and promenade (featuring: extravagant luxury mannequin displays, marble counter, elegant shopping boulevard)"
        elif "poser un lapin" in combined_script:
            return "charming historic bistro exterior and clock tower plaza (featuring: outdoor cafe table with an untouched cup, historic clock face showing late time, cobblestone promenade)"
        return "vibrant modern creative studio and everyday living space (featuring: focus work area, collaborative lounge, demonstration bench, sunlit terrace)"

    # 3. Check for explicit keyword domains in script text and metadata
    keyword_domains = [
        (r'\b(theater|theatre|stage|acting|backstage|curtain|actor|show|rehearsal)\b', "historic theater and performing arts center (featuring: backstage wings, rehearsal stage, dressing room, auditorium)"),
        (r'\b(kitchen|cook|bake|recipe|chef|dessert|ingredient|dish|oven)\b', "warm artisan culinary kitchen (featuring: rustic wooden prep counter, cookware rack, dining table, pantry alcove)"),
        (r'\b(library|exam|study|student|homework|grade|assignment|textbook)\b', "university academic library (featuring: individual study carrel, collaborative reference desk, book stacks, reading lounge)"),
        (r'\b(office|workplace|colleague|coworker|meeting|boss|presentation|company|corporate)\b', "modern corporate creative studio (featuring: brainstorming desk, glass conference room, presentation hall, office lounge)"),
        (r'\b(airport|flight|plane|airplane|travel|suitcase|boarding|luggage)\b', "modern international airport terminal (featuring: panoramic tarmac lounge, check-in concourse, boarding gate, baggage reclaim)"),
        (r'\b(train|station|subway|metro|platform|railway)\b', "scenic railway station (featuring: passenger platform, ticketing hall, waiting concourse, vintage trackside bench)"),
        (r'\b(hospital|doctor|clinic|medical|patient|nurse|consultation)\b', "bright modern wellness and medical consultation clinic (featuring: examination room, consultation desk, waiting lounge)"),
        (r'\b(street|city|avenue|plaza|sidewalk|urban|crosswalk|boulevard)\b', "bustling historic city avenue (featuring: pedestrian sidewalk, brick storefronts, street corner plaza, park bench)"),
        (r'\b(park|garden|nature|tree|bench|flower|outdoor|trail)\b', "sunlit municipal park promenade (featuring: walking promenade, historic stone balustrade, shaded wooden bench, open lawn)"),
        (r'\b(gym|workout|fitness|sport|athletic|exercise|dumbbells)\b', "dynamic modern athletic training gym (featuring: fitness floor, weights zone, training track, recovery lounge)"),
        (r'\b(market|store|boutique|seller|bazaar|craft)\b', "neighborhood artisan market boutique (featuring: craft display table, checkout counter, goods shelf, street awning)"),
        (r'\b(beach|sea|ocean|coastal|boat|sand|shore)\b', "sunlit coastal seaside promenade (featuring: ocean overlook deck, sand dunes path, beach pavilion)"),
        (r'\b(cafe|coffee|barista|latte|espresso)\b', "charming artisanal coffee bar (featuring: espresso counter, window high-top bar, cozy seating corner)"),
    ]

    for pattern, domain in keyword_domains:
        if re.search(pattern, combined_script):
            return domain

    # 4. Authentic modern everyday setting fallback (NON-cafeteria, NON-classroom, NON-greenhouse)
    return "vibrant modern creative studio and cultural study lounge (featuring: collaborative work table, conversation lounge, reference bookshelf, architectural drafting desk, sunlit terrace window)"
