"""
visual/common/environment.py — 4-Tier Cultural World Atlas Resolver & Anchor Environment Resolver.

Escapes generic studio/lounge/workshop fallbacks by routing scripts through:
  Tier 1: Multilingual Explicit Setting Match (localized per target language)
  Tier 2: Heteronym & Culturally Upgraded Idiom Visual Metaphors
  Tier 3: Multilingual Semantic Vibe Match within the language's CulturalWorld Atlas
  Tier 4: Seeded Anti-Repetition Atlas Permutation filtered by video_type (Triplet-safe)
"""
from __future__ import annotations

import hashlib
import random
import re
from typing import Dict, Iterable, List, Optional, Tuple

from ..languages import (
    CulturalWorld,
    ENGLISH_HETERONYM_DOMAINS,
    LanguageVisualProfile,
    get_all_idiom_environments,
    get_all_idiom_markers,
    get_language_profile,
)

HETERONYM_DOMAINS = dict(ENGLISH_HETERONYM_DOMAINS)

# Specialized literal domains when the script/scenario explicitly demands a specific non-Atlas facility
EXPLICIT_SCENARIO_DOMAINS: List[Tuple[str, str]] = [
    (
        r'\b(animation studio|animator|animation desk|storyboard room)\b',
        "atmospheric 2D animation production room at night (featuring: wooden animator drawing tables with illuminated lightboxes, character model sheets pinned to corkboards, glowing monitors with colorful timeline bars, warm green-shaded desk lamps)",
    ),
    (
        r'\b(rooftop cinema|cinema shoot|film shoot|movie set|film set)\b',
        "architectural rooftop cinema shoot at dusk (featuring: director clapperboards without text, brass megaphone, camera tripods, rolled storyboard reels, warm amber string lights, twilight skyline)",
    ),
    (
        r'\b(hospital|doctor|clinic|medical|patient|nurse|consultation|ospedale|dottore|médico|médecin|hôpital|clinica)\b',
        "bright sunlit neighborhood wellness clinic and classic apothecary hall (featuring: polished timber apothecary cabinets lined with ceramic jars, sunlit tall paned windows, brass balance scales, cushioned wooden examination chair)",
    ),
    (
        r'\b(airport|flight|plane|airplane|boarding|luggage|aeroporto|aeropuerto|volo|vuelo|aéroport|avion)\b',
        "sunlit modern international airport terminal concourse (featuring: sweeping curved glass tarmac overlook with docked airliners, wheeled leather suitcases, curved skylight trusses, warm terrazzo floor)",
    ),
    (
        r'\b(theater|theatre|teatro|théâtre|stage|acting|backstage|curtain|rehearsal)\b',
        "historic grand theater and performing arts stagehouse (featuring: gilded backstage dressing mirror framed by glowing vanity bulbs, crimson velvet curtains, painted scenery flats, carved wooden proscenium auditorium)",
    ),
    (
        r'\b(gym|workout|fitness|athletic|exercise|dumbbells|palestra|gimnasio)\b',
        "sunlit historic athletic club and outdoor track court (featuring: gleaming maple court planks, wooden pommel horse, kettlebells, striped locker benches, sunlit arched windows opening onto running track)",
    ),
]

# High-precision explicit venue keywords in scenario/topic (checked BEFORE falling back to SPECIAL_LOCKED)
_STRONG_SPECIAL_IN_TEXT_RE = re.compile(
    r'\b(animation studio|rooftop cinema|film shoot|movie set|film set|hospital|clinic|ospedale|hôpital|airport|aeroporto|aeropuerto|aéroport|theater|theatre|teatro|théâtre|backstage|rehearsal|gym|dumbbells)\b',
    re.IGNORECASE,
)

# Multilingual vibe clusters used by Tier 3 to match abstract/dialogue scripts to CulturalWorld.vibe_tags
_MULTILINGUAL_VIBE_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("food", (
        "food", "eat", "eating", "cook", "dish", "meal", "bread", "cake", "pastry", "ice cream", "gelato",
        "pizza", "pasta", "restaurant", "breakfast", "lunch", "dinner", "fruit", "orange", "sweet",
        "cibo", "mangiare", "cucina", "dolce", "colazione", "pranzo", "cena", "gelato",
        "comida", "comer", "desayuno", "almuerzo", "fruta", "pan", "tapa", "chocolate", "churro",
        "nourriture", "manger", "repas", "déjeuner", "dîner", "pâtisserie", "pain", "fromage", "crêpe",
    )),
    ("coffee", (
        "coffee", "cafe", "café", "espresso", "cappuccino", "latte", "tea", "thé", "té", "caffè", "horchata",
    )),
    ("shopping", (
        "shop", "shopping", "store", "buy", "bought", "price", "market", "boutique", "thrift", "jacket", "clothes",
        "negozio", "mercato", "comprare", "prezzo", "vestiti", "regalo",
        "tienda", "mercado", "comprar", "precio", "ropa", "barato", "caro", "regalo",
        "magasin", "marché", "acheter", "prix", "vêtements", "friperie",
    )),
    ("money", (
        "money", "pay", "cost", "expensive", "cheap", "coin", "cash", "bill", "wallet", "euro", "dollar",
        "soldi", "pagare", "costare", "caro", "conto", "portafoglio",
        "dinero", "pagar", "costar", "cuenta", "moneda", "cartera",
        "argent", "payer", "coûter", "addition", "portefeuille",
    )),
    ("travel", (
        "travel", "trip", "vacation", "holiday", "train", "station", "metro", "subway", "tram", "ticket", "suitcase", "ferry",
        "viaggio", "viaggiare", "vacanza", "treno", "stazione", "biglietto", "valigia",
        "viaje", "viajar", "vacaciones", "tren", "estación", "billete", "maleta",
        "voyage", "voyager", "vacances", "gare", "valise", "billet", "métro",
    )),
    ("music", (
        "music", "song", "sing", "band", "concert", "guitar", "piano", "vinyl", "record", "jazz", "opera", "dance",
        "musica", "canzone", "cantare", "concerto", "chitarra", "ballo",
        "música", "canción", "cantar", "concierto", "guitarra", "baile", "tango", "salsa",
        "musique", "chanson", "chanter", "vinyle", "disquaire", "opéra",
    )),
    ("books", (
        "book", "books", "read", "reading", "library", "bookshop", "bookstore", "novel", "story", "poem", "study", "exam", "school",
        "libro", "libri", "leggere", "biblioteca", "libreria", "storia", "scuola", "esame", "studiare",
        "lectura", "leer", "librería", "novela", "escuela", "examen", "estudiar",
        "livre", "livres", "lire", "librairie", "bibliothèque", "école", "étudier", "bande dessinée",
    )),
    ("coastal", (
        "beach", "sea", "ocean", "coast", "coastal", "island", "harbor", "harbour", "pier", "boat", "sail", "wave", "surf", "summer",
        "mare", "spiaggia", "costa", "isola", "porto", "barca", "estate", "sole",
        "playa", "mar", "costa", "isla", "puerto", "barco", "verano", "ola",
        "plage", "mer", "côte", "île", "port", "bateau", "été", "vague",
    )),
    ("sports", (
        "sport", "soccer", "football", "basketball", "skate", "swim", "run", "running", "race", "match", "cycling", "bicycle", "hike",
        "calcio", "partita", "pallone", "correre", "bici",
        "fútbol", "partido", "correr", "bici", "nadar",
        "vélo", "courir", "match", "ski",
    )),
    ("history", (
        "history", "ancient", "century", "medieval", "museum", "palace", "castle", "tower", "roman", "arch", "monument", "tradition",
        "storia", "antico", "secolo", "museo", "palazzo", "torre", "romano", "monumento",
        "historia", "antiguo", "siglo", "museo", "palacio", "castillo", "torre", "inca", "maya", "ruinas",
        "histoire", "ancien", "siècle", "musée", "palais", "château", "romain",
    )),
    ("celebration", (
        "party", "celebrate", "celebration", "festival", "birthday", "wedding", "cheer", "gift", "present", "holiday",
        "festa", "festeggiare", "compleanno", "carnevale", "auguri",
        "fiesta", "celebrar", "cumpleaños", "regalo", "alegría",
        "fête", "célébrer", "anniversaire", "cadeau",
    )),
)

_TYPE_PREFERRED_STAGING = {
    "FUN_FACTS": "monumental",
    "ROLEPLAY": "threshold",
    "GAME": "tactile_props",
    "EXPRESSION": "layered_depth",
}

_TYPE_INDEX_OFFSETS = {
    "EXPRESSION": 0,
    "GAME": 7,
    "ROLEPLAY": 13,
    "FUN_FACTS": 5,
}

_TRIPLET_LANE = {
    "EXPRESSION": 0,
    "GAME": 1,
    "ROLEPLAY": 2,
}

# Precompile regexes once at import time so batch and test runs execute cleanly without re-cache thrashing
_COMPILED_EXPLICIT_SCENARIO_DOMAINS: Tuple[Tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern, re.IGNORECASE), domain)
    for pattern, domain in EXPLICIT_SCENARIO_DOMAINS
)
_COMPILED_HETERONYM_PATTERNS: Tuple[Tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(r"\b" + re.escape(word_key) + r"\b", re.IGNORECASE), domain)
    for word_key, domain in HETERONYM_DOMAINS.items()
)
_COMPILED_VIBE_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = tuple(
    (vibe_name, re.compile(r"\b(?:" + "|".join(re.escape(kw) for kw in kw_tuple) + r")\b"))
    for vibe_name, kw_tuple in _MULTILINGUAL_VIBE_KEYWORDS
)
_WORLD_KW_PATTERN_CACHE: Dict[str, Tuple[re.Pattern[str], ...]] = {}
_POOL_ORDER_CACHE: Dict[Tuple[str, str], Tuple[CulturalWorld, ...]] = {}


def _get_world_kw_patterns(world: CulturalWorld) -> Tuple[re.Pattern[str], ...]:
    pats = _WORLD_KW_PATTERN_CACHE.get(world.id)
    if pats is None:
        pats = tuple(re.compile(r"\b" + re.escape(kw.lower()) + r"\b") for kw in world.explicit_keywords)
        _WORLD_KW_PATTERN_CACHE[world.id] = pats
    return pats


def _normalize_video_type(video_type: str = "EXPRESSION") -> str:
    vt = (video_type or "EXPRESSION").strip().upper()
    if vt == "QUIZ":
        return "GAME"
    if vt in ("FUNFACTS", "FUNFACT", "FACTS"):
        return "FUN_FACTS"
    if vt in _TYPE_PREFERRED_STAGING:
        return vt
    return "EXPRESSION"


def _extract_numeric_seed(script_id: str, fallback_text: str) -> int:
    m = re.search(r"(\d+)", script_id or "")
    if m:
        return int(m.group(1))
    digest = hashlib.sha1(fallback_text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _deterministic_pool_order(
    worlds: Tuple[CulturalWorld, ...],
    language: str,
    video_type: str,
) -> List[CulturalWorld]:
    cache_key = (language, video_type)
    base_order = _POOL_ORDER_CACHE.get(cache_key)
    if base_order is None:
        profile = get_language_profile(language)
        full = list(profile.cultural_worlds or worlds)
        rng = random.Random(f"cultural_atlas_v1:{language}:{video_type}")
        rng.shuffle(full)
        base_order = tuple(full)
        _POOL_ORDER_CACHE[cache_key] = base_order

    allowed_ids = {w.id for w in worlds}
    ordered = [w for w in base_order if w.id in allowed_ids]
    if len(ordered) == len(allowed_ids):
        return ordered
    extras = [w for w in worlds if w.id not in {o.id for o in ordered}]
    return ordered + extras


def format_cultural_world_anchor(world: CulturalWorld) -> str:
    """Format a CulturalWorld into a concise, vivid anchor_environment string."""
    props_str = ", ".join(world.focal_props[:4])
    return (
        f"{world.title} in {world.region} ({world.setting_prompt}; "
        f"featuring natural props: {props_str})"
    )


def infer_world_ids_from_text(text: str, language: str = "") -> List[str]:
    """
    Infers which CulturalWorld ID(s) a free-form prompt already uses so Gemini Audit
    rerolls can strictly exclude the prior draft's venue even if anchor_world_id wasn't saved.
    """
    if not text or not isinstance(text, str):
        return []
    low = text.lower()
    profile = get_language_profile(language or "english")
    candidate_profiles: Tuple[LanguageVisualProfile, ...] = (
        (profile,)
        if language
        else (
            get_language_profile("english"),
            get_language_profile("french"),
            get_language_profile("spanish"),
            get_language_profile("italian"),
        )
    )
    found: List[str] = []
    for prof in candidate_profiles:
        for world in prof.cultural_worlds:
            title_low = world.title.lower()
            if title_low in low:
                found.append(world.id)
                continue
            sig_words = [
                w for w in re.findall(r"[a-zA-ZÀ-ÿ]{5,}", title_low)
                if w not in {"market", "street", "plaza", "corner", "bridge", "vintage", "historic", "golden", "coastal", "classic", "modern", "grand"}
            ]
            hits = sum(1 for w in sig_words if re.search(r"\b" + re.escape(w) + r"\b", low))
            if (len(sig_words) >= 2 and hits >= 2) or (len(sig_words) == 1 and hits == 1):
                found.append(world.id)
    return list(dict.fromkeys(found))


def is_figurative_idiom(
    topic: str = "",
    lexical_field: str = "",
    scenario: str = "",
    script_text: str = "",
) -> bool:
    """Detects if the script is about an idiom or figurative expression across languages."""
    combined = f"{topic} {lexical_field} {scenario} {script_text}".lower()
    return any(marker in combined for marker in get_all_idiom_markers())


def match_special_locked_domain(topic: str, scenario: str, script_text: str) -> Optional[str]:
    """Returns a locked non-Atlas facility description only for explicit hospital/airport/theater/gym/film-set scripts."""
    scen_low = (scenario or "").lower()
    topic_low = (topic or "").lower()
    for pat, domain in _COMPILED_EXPLICIT_SCENARIO_DOMAINS:
        if scen_low and pat.search(scen_low):
            return domain
        if topic_low and pat.search(topic_low):
            return domain
    text_low = (script_text or "").lower()
    if text_low and _STRONG_SPECIAL_IN_TEXT_RE.search(text_low):
        for pat, domain in _COMPILED_EXPLICIT_SCENARIO_DOMAINS:
            if pat.search(text_low):
                return domain
    return None


def _pick_from_world_pool(
    candidates: List[CulturalWorld],
    script_id: str,
    vt: str,
    profile: LanguageVisualProfile,
    fallback_seed_text: str,
    exclude_set: set[str],
    last_excluded: Optional[str] = None,
) -> Optional[CulturalWorld]:
    if not candidates:
        return None
    available = [w for w in candidates if w.id not in exclude_set]
    if not available:
        available = [w for w in candidates if w.id != last_excluded] or list(candidates)

    num_seed = _extract_numeric_seed(script_id, fallback_seed_text)
    if vt in _TRIPLET_LANE and len(available) >= 3:
        rank_map = {w.id: idx for idx, w in enumerate(profile.cultural_worlds)}
        lane = _TRIPLET_LANE[vt]
        lane_filtered = [w for w in available if (rank_map.get(w.id, 0) + num_seed) % 3 == lane]
        if lane_filtered:
            available = lane_filtered

    ordered = _deterministic_pool_order(tuple(available), profile.language, vt)
    offset = _TYPE_INDEX_OFFSETS.get(vt, 0)
    return ordered[(num_seed + offset) % len(ordered)]


def _resolve_cultural_world_core(
    *,
    script_text: str,
    topic: str,
    scenario: str,
    lexical_field: str,
    label: str,
    vt: str,
    profile: LanguageVisualProfile,
    script_id: str,
    exclude_set: set[str],
    last_excluded: Optional[str],
) -> Optional[CulturalWorld]:
    worlds = profile.cultural_worlds
    if not worlds:
        return None

    preferred_tag = _TYPE_PREFERRED_STAGING.get(vt, "layered_depth")
    meta_text = f"{scenario} {topic}".lower()
    combined_text = f"{topic} {scenario} {lexical_field} {label} {script_text}".lower()

    # For FUN_FACTS, restrict primary pool to monumental wonders/landmarks; keep landmarks distinct from E/G/R
    if vt == "FUN_FACTS":
        landmark_only = [w for w in worlds if w.category == "landmark"]
        primary_pool = landmark_only or [w for w in worlds if "monumental" in w.staging_tags] or list(worlds)
    else:
        non_landmark = [w for w in worlds if w.category != "landmark"] or list(worlds)
        primary_pool = [w for w in non_landmark if preferred_tag in w.staging_tags] or non_landmark

    # Tier 1b: Explicit CulturalWorld keyword matches (scenario/topic first, then full script text)
    for source_text in (meta_text, (script_text or "").lower()):
        if not source_text or not source_text.strip():
            continue
        kw_matches: List[Tuple[int, CulturalWorld]] = []
        search_pool = primary_pool if vt == "FUN_FACTS" else non_landmark
        for w in search_pool:
            if w.id in exclude_set:
                continue
            hits = sum(1 for pat in _get_world_kw_patterns(w) if pat.search(source_text))
            if hits > 0:
                score = hits * 10 + (3 if preferred_tag in w.staging_tags else 0)
                kw_matches.append((score, w))
        if kw_matches:
            max_score = max(s for s, _ in kw_matches)
            top_matches = [w for s, w in kw_matches if s == max_score]
            return _pick_from_world_pool(
                top_matches, script_id, vt, profile, combined_text, exclude_set, last_excluded
            )

    # Tier 3: Multilingual Semantic Vibe Match inside language Atlas
    matched_vibes: List[str] = [
        vibe_name
        for vibe_name, pat in _COMPILED_VIBE_PATTERNS
        if pat.search(combined_text)
    ]

    if matched_vibes:
        vibe_scores: List[Tuple[int, CulturalWorld]] = []
        for w in primary_pool:
            if w.id in exclude_set:
                continue
            overlap = sum(1 for v in matched_vibes[:3] if v in w.vibe_tags)
            if overlap > 0:
                vibe_scores.append((overlap, w))
        if not vibe_scores and vt != "FUN_FACTS":
            # Widen across non-landmark worlds if staging subset had zero vibe hits
            for w in non_landmark:
                if w.id in exclude_set:
                    continue
                overlap = sum(1 for v in matched_vibes[:3] if v in w.vibe_tags)
                if overlap > 0:
                    vibe_scores.append((overlap, w))
        if vibe_scores:
            top_vibe_worlds = [w for _, w in vibe_scores]
            return _pick_from_world_pool(
                top_vibe_worlds, script_id, vt, profile, combined_text, exclude_set, last_excluded
            )

    # Tier 4: Seeded Anti-Repetition Atlas Permutation (escapes CSV abstract grammar/phonetics trap)
    return _pick_from_world_pool(
        primary_pool, script_id, vt, profile, combined_text, exclude_set, last_excluded
    )


def resolve_cultural_world(
    script_text: str,
    topic: str = "",
    scenario: str = "",
    lexical_field: str = "",
    label: str = "",
    video_type: str = "EXPRESSION",
    language: str = "",
    script_id: str = "",
    exclude_world_ids: Iterable[str] = (),
) -> Optional[CulturalWorld]:
    """
    Resolves a distinct, 100% text-free CulturalWorld from the target language's Atlas.
    Enforces automatic Triplet Collision Guard so sibling E/G/R/F scripts never collide.
    """
    lang_hint = language or label or script_id or "english"
    profile = get_language_profile(lang_hint)
    if not profile.cultural_worlds:
        return None

    vt = _normalize_video_type(video_type)
    exclude_list = [str(wid).strip() for wid in (exclude_world_ids or ()) if str(wid).strip()]
    exclude_set = set(exclude_list)
    last_excluded = exclude_list[-1] if exclude_list else None

    # Triplet Collision Guard: ensure E/G/R/F sharing the same topic index pick distinct worlds
    triplet_match = re.match(r"^([EFSI])([EGRF])(\d+)$", (script_id or "").strip().upper())
    if triplet_match and vt != "EXPRESSION":
        lang_char, _type_char, num_str = triplet_match.groups()
        prior_types: List[str] = ["EXPRESSION"]
        if vt in ("ROLEPLAY", "FUN_FACTS"):
            prior_types.append("GAME")
        if vt == "FUN_FACTS":
            prior_types.append("ROLEPLAY")
        type_to_code = {"EXPRESSION": "E", "GAME": "G", "ROLEPLAY": "R"}
        for p_vt in prior_types:
            p_sid = f"{lang_char}{type_to_code[p_vt]}{num_str}"
            sib = _resolve_cultural_world_core(
                script_text=script_text,
                topic=topic,
                scenario=scenario,
                lexical_field=lexical_field,
                label=label,
                vt=p_vt,
                profile=profile,
                script_id=p_sid,
                exclude_set=set(exclude_set),
                last_excluded=last_excluded,
            )
            if sib is not None:
                exclude_set.add(sib.id)

    return _resolve_cultural_world_core(
        script_text=script_text,
        topic=topic,
        scenario=scenario,
        lexical_field=lexical_field,
        label=label,
        vt=vt,
        profile=profile,
        script_id=script_id,
        exclude_set=exclude_set,
        last_excluded=last_excluded,
    )


def resolve_anchor_environment(
    script_text: str,
    topic: str = "",
    scenario: str = "",
    lexical_field: str = "",
    label: str = "",
    video_type: str = "EXPRESSION",
    language: str = "",
    script_id: str = "",
    exclude_world_ids: Iterable[str] = (),
) -> str:
    """
    4-Tier Cultural Anchor Environment Resolver:
      Tier 1: Multilingual Explicit Setting Match (specialized locked facility OR language-local venue)
      Tier 2: English Heteronyms & Upgraded Figurative Idiom Visual Metaphors
      Tier 3: Multilingual Semantic Vibe Match inside language CulturalWorld Atlas
      Tier 4: Seeded Anti-Repetition CulturalWorld Atlas Permutation (0% studio/lounge fallbacks)
    """
    profile = get_language_profile(language or label or script_id or "english")
    exclude_list = [str(wid).strip() for wid in (exclude_world_ids or ()) if str(wid).strip()]

    # Tier 1a: Locked explicit facilities (hospital, airport, theater, gym, film set, animation desk)
    special_domain = match_special_locked_domain(topic=topic, scenario=scenario, script_text=script_text)
    if special_domain:
        return special_domain

    # If exclude_world_ids is non-empty (e.g. Gemini Auditor reroll), explore a fresh CulturalWorld
    # instead of re-returning the exact same static idiom string over and over.
    if not exclude_list:
        # Tier 2a: Known heteronym / word-stress domain mappings
        topic_low = (topic or "").lower()
        for pat, domain in _COMPILED_HETERONYM_PATTERNS:
            if topic_low and pat.search(topic_low):
                return domain

        # Tier 2b: Upgraded figurative idiom visual metaphors
        combined_script = f"{topic} {scenario} {lexical_field} {label} {script_text}".lower()
        if is_figurative_idiom(topic, lexical_field, scenario, script_text):
            for phrases, env_desc in profile.idiom_environments:
                if any(w in combined_script for w in phrases):
                    return env_desc
            for phrases, env_desc in get_all_idiom_environments():
                if any(w in combined_script for w in phrases):
                    return env_desc

    # Tiers 1b, 3 & 4: Resolve rich CulturalWorld from target language's Atlas
    world = resolve_cultural_world(
        script_text=script_text,
        topic=topic,
        scenario=scenario,
        lexical_field=lexical_field,
        label=label,
        video_type=video_type,
        language=language,
        script_id=script_id,
        exclude_world_ids=exclude_list,
    )
    if world is not None:
        return format_cultural_world_anchor(world)

    return (
        "sunlit historic city pedestrian square with patterned cobblestones, local artisan storefront arches, "
        "wrought-iron balconies, and warm amber afternoon sunlight (0% text, zero signage)"
    )
