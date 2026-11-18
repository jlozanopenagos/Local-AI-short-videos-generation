"""
visual/common/environment.py — Anchor environment resolver, delegating language tables to visual/languages.
"""
from __future__ import annotations

import re

from ..languages import (
    ENGLISH_HETERONYM_DOMAINS,
    get_all_idiom_markers,
    get_all_idiom_environments,
)

HETERONYM_DOMAINS = dict(ENGLISH_HETERONYM_DOMAINS)

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

KEYWORD_DOMAINS = [
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


def is_figurative_idiom(
    topic: str = "",
    lexical_field: str = "",
    scenario: str = "",
    script_text: str = "",
) -> bool:
    """Detects if the script is about an idiom or figurative expression across languages."""
    combined = f"{topic} {lexical_field} {scenario} {script_text}".lower()
    return any(marker in combined for marker in get_all_idiom_markers())


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

    # 3. Check for figurative idioms across language profiles (allows creative graphic visual metaphors)
    if is_figurative_idiom(topic, lexical_field, scenario, script_text):
        for phrases, env_desc in get_all_idiom_environments():
            if any(w in combined_script for w in phrases):
                return env_desc
        return "vibrant modern creative studio and everyday living space (featuring: focus work area, collaborative lounge, demonstration bench, sunlit terrace)"

    # 4. Check for explicit keyword domains in script text and metadata
    for pattern, domain in KEYWORD_DOMAINS:
        if re.search(pattern, combined_script):
            return domain

    # 5. Authentic modern everyday setting fallback (NON-cafeteria, NON-classroom, NON-greenhouse)
    return "vibrant modern creative studio and cultural study lounge (featuring: collaborative work table, conversation lounge, reference bookshelf, architectural drafting desk, sunlit terrace window)"
