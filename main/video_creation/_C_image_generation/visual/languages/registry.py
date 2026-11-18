"""
visual/languages/registry.py — Central registry for language visual profiles and multilingual domain tables.
Unifies language palettes, idiom markers, and semantic domain detection across `environment.py` and `gemini_auditor.py`.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .base import LanguageVisualProfile
from .english import ENGLISH_PROFILE, ENGLISH_HETERONYM_DOMAINS
from .french import FRENCH_PROFILE
from .spanish import SPANISH_PROFILE
from .italian import ITALIAN_PROFILE

ALL_LANGUAGE_PROFILES: Tuple[LanguageVisualProfile, ...] = (
    ENGLISH_PROFILE,
    FRENCH_PROFILE,
    SPANISH_PROFILE,
    ITALIAN_PROFILE,
)

# Unified multilingual semantic domain rules (used by gemini_auditor.detect_script_domain)
MULTILINGUAL_SEMANTIC_DOMAINS: List[Tuple[str, List[str], str]] = [
    (
        "Family, Home & Holiday Gatherings",
        [
            "parenti", "genitori", "family", "famiglia", "familia", "famille",
            "parents", "relatives", "cugini", "cousin", "nonni", "grandparents",
            "casa", "home", "house", "dinner", "cena", "pranzo", "natale", "christmas",
            "holiday", "festa", "fratello", "sorella", "brother", "sister",
            "mamma", "papà", "mom", "dad", "living room", "kitchen", "cucina",
            "tablecloth", "sofa", "porch", "patio", "ancestor", "heritage"
        ],
        "Ground this visual world in an authentic {lang} domestic or family setting "
        "(e.g. a warm holiday dining room with festive table setting, a lively family kitchen, "
        "an intimate living room gathering, or an outdoor courtyard porch) directly reflecting family life and shared meals."
    ),
    (
        "Food, Culinary & Dining",
        [
            "food", "cibo", "comida", "nourriture", "eat", "eating", "mangiare",
            "comer", "manger", "restaurant", "ristorante", "restaurante", "cafe",
            "café", "trattoria", "pizza", "pasta", "cooking", "cuoco", "chef",
            "recipe", "ricetta", "breakfast", "colazione", "desayuno", "lunch",
            "dish", "beverage", "espresso", "cappuccino", "tasting", "pastry", "wine"
        ],
        "Ground this visual world in a vibrant culinary or dining setting in {lang} culture "
        "(e.g. a neighborhood trattoria dining table, an open kitchen pass, an outdoor cafe terrace, "
        "a lively food hall, or a coffee counter)."
    ),
    (
        "Travel, Transit & Commute",
        [
            "travel", "viaggio", "viaje", "voyage", "train", "treno", "tren",
            "airport", "aeroporto", "aeropuerto", "gare", "stazione", "estación",
            "station", "ticket", "biglietto", "billete", "bus", "autobus", "subway",
            "metro", "tram", "hotel", "albergo", "suitcase", "valigia", "maleta",
            "baggage", "flight", "volo", "vuelo", "trip", "tourism", "turista",
            "luggage", "platform", "backpack", "ferry"
        ],
        "Ground this visual world in an authentic travel or transit hub "
        "(e.g. a railway station platform with vintage departures board, a tramway interchange, "
        "an airport check-in concourse, or a scenic transit stop)."
    ),
    (
        "Academic, School & Study Life",
        [
            "school", "scuola", "escuela", "école", "class", "classe", "aula",
            "exam", "esame", "examen", "test", "study", "studiare", "estudiar",
            "étudier", "teacher", "professore", "profesor", "prof", "student",
            "studente", "homework", "compiti", "tarea", "devoirs", "library",
            "biblioteca", "bibliothèque", "grade", "voto", "nota", "university",
            "università", "campus", "blackboard", "chalkboard", "desk"
        ],
        "Ground this visual world in an authentic student academic environment "
        "(e.g. a university library research carrel with green-shaded brass lamps, a campus project table, "
        "an architectural student drafting atelier, or a student common room lounge)."
    ),
    (
        "Workplace & Professional Life",
        [
            "work", "lavoro", "trabajo", "travail", "office", "ufficio", "oficina",
            "bureau", "boss", "capo", "jefe", "colleague", "collega", "colega",
            "meeting", "riunione", "reunión", "job", "interview", "colloquio",
            "entrevista", "company", "azienda", "empresa", "email", "client", "career"
        ],
        "Ground this visual world in a realistic professional or vocational workspace "
        "(e.g. a shared creative studio, a municipal client counter, an architectural drafting atelier, "
        "or an open-plan office discussion nook)."
    ),
    (
        "Shopping, Markets & Commerce",
        [
            "shop", "negozio", "tienda", "magasin", "store", "buy", "comprare",
            "comprar", "acheter", "price", "prezzo", "precio", "prix", "clothes",
            "vestiti", "ropa", "vêtements", "market", "mercato", "mercado", "marché",
            "supermarket", "cashier", "cassa", "caja", "boutique", "receipt", "shopping"
        ],
        "Ground this visual world in a lively commercial or market space "
        "(e.g. a bustling neighborhood open-air market, a vintage storefront counter, "
        "or a specialty goods boutique)."
    ),
    (
        "Sports, Outdoor & Fitness",
        [
            "sport", "calcio", "football", "soccer", "gym", "palestra", "gimnasio",
            "fitness", "run", "correre", "correr", "courir", "match", "partita",
            "partido", "coach", "allenatore", "entrenador", "court", "field", "stadium",
            "basketball", "tennis", "skate", "cycling"
        ],
        "Ground this visual world in an active sports or recreation environment "
        "(e.g. a community sports club bleacher, an outdoor court sideline, a skate park perimeter, "
        "or a lakeside athletic path)."
    ),
    (
        "Arts, Music & Culture",
        [
            "music", "musica", "musique", "song", "canzone", "canción", "chanson",
            "art", "arte", "cinema", "film", "movie", "theatre", "teatro", "théâtre",
            "concert", "concerto", "dance", "ballo", "danza", "danse", "instrument",
            "guitar", "piano", "museum", "museo", "gallery", "exhibition"
        ],
        "Ground this visual world in an expressive creative or cultural space "
        "(e.g. an intimate music practice studio, a cinema lobby, an art gallery corridor, "
        "or a theater backstage)."
    ),
    (
        "Healthcare & Wellbeing",
        [
            "doctor", "dottore", "médico", "médecin", "hospital", "ospedale", "hopital",
            "pharmacy", "farmacia", "pharmacie", "sick", "malato", "enfermo", "malade",
            "pain", "dolore", "dolor", "douleur", "medicine", "medicina", "médicament",
            "health", "salute", "salud", "santé", "dentist", "dentista"
        ],
        "Ground this visual world in a healthcare or wellness setting "
        "(e.g. an authentic neighborhood pharmacy counter, a clinic waiting room with paned windows, "
        "or an apothecary consultation nook)."
    ),
]


def get_language_profile(identifier: str = "english") -> LanguageVisualProfile:
    """
    Resolves a LanguageVisualProfile from:
    1. Language name or alias ('english', 'french', 'français', 'spanish', 'español', 'italian', 'italiano')
    2. LABEL string ('French | work | ...')
    3. 1-letter code ('E', 'F', 'S', 'I') or Canonical Script ID ('FE01', 'SR01', 'IG02')
    """
    if not identifier:
        return ENGLISH_PROFILE

    clean = str(identifier).split("|")[0].strip()
    lower = clean.lower()

    if "french" in lower or "français" in lower or "francais" in lower:
        return FRENCH_PROFILE
    if "spanish" in lower or "español" in lower or "espanol" in lower:
        return SPANISH_PROFILE
    if "italian" in lower or "italiano" in lower:
        return ITALIAN_PROFILE
    if "english" in lower:
        return ENGLISH_PROFILE

    upper = clean.upper()
    m = re.match(r"^([EFSI])_?[EFGR]\d{2,}$", upper)
    if m:
        upper = m.group(1)

    for prof in ALL_LANGUAGE_PROFILES:
        if upper == prof.lang_code or lower in prof.aliases:
            return prof

    return ENGLISH_PROFILE


def get_all_idiom_markers() -> Tuple[str, ...]:
    markers: List[str] = []
    for prof in ALL_LANGUAGE_PROFILES:
        markers.extend(prof.idiom_markers)
    return tuple(markers)


def get_all_idiom_environments() -> List[Tuple[Tuple[str, ...], str]]:
    envs: List[Tuple[Tuple[str, ...], str]] = []
    for prof in ALL_LANGUAGE_PROFILES:
        envs.extend(prof.idiom_environments)
    return envs


def get_all_heteronym_domains() -> Dict[str, str]:
    merged: Dict[str, str] = {}
    for prof in ALL_LANGUAGE_PROFILES:
        merged.update(prof.heteronym_domains)
    return merged
