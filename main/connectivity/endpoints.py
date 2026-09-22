"""
endpoints.py — Modular Registry for Google Sheets Apps Script Web App Endpoints.

Allows seamless switching between endpoints across all 4 languages (English, French, Spanish, Italian)
and 4 video formats (Expression, Roleplay, Game, Fun Facts).
"""

from __future__ import annotations

import os
from typing import Dict, Tuple, Optional, List

# Primary registry of Google Sheets endpoints: (language_lower, video_type_lower) -> Web App URL
# The provided French sheet URL is configured as default / french expression.
DEFAULT_ENGLISH_EXPRESSION_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_ENGLISH_EXPRESSION_SHEET_ID/edit?gid=1253474145#gid=1253474145"
)

DEFAULT_FRENCH_EXPRESSION_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_FRENCH_EXPRESSION_SHEET_ID/edit?gid=388718205#gid=388718205"
)
DEFAULT_SPANISH_EXPRESSION_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_SPANISH_EXPRESSION_SHEET_ID/edit?gid=938942305#gid=938942305"
)

DEFAULT_ITALIAN_EXPRESSION_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_ITALIAN_EXPRESSION_SHEET_ID/edit?gid=1798445539#gid=1798445539"
)
DEFAULT_ENGLISH_GAME_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_ENGLISH_GAME_SHEET_ID/edit?gid=797764761#gid=797764761"
)

DEFAULT_FRENCH_GAME_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_FRENCH_GAME_SHEET_ID/edit?gid=1568557660#gid=1568557660"
)
DEFAULT_SPANISH_GAME_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_SPANISH_GAME_SHEET_ID/edit?gid=619858333#gid=619858333"
)

DEFAULT_ITALIAN_GAME_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_ITALIAN_GAME_SHEET_ID/edit?gid=2016972632#gid=2016972632"
)

DEFAULT_ENGLISH_ROLEPLAY_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_ENGLISH_ROLEPLAY_SHEET_ID/edit?gid=1652307005#gid=1652307005"
)

DEFAULT_FRENCH_ROLEPLAY_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_FRENCH_ROLEPLAY_SHEET_ID/edit?gid=320241190#gid=320241190"
)

DEFAULT_SPANISH_ROLEPLAY_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_SPANISH_ROLEPLAY_SHEET_ID/edit?gid=453429196#gid=453429196"
)

DEFAULT_ITALIAN_ROLEPLAY_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_ITALIAN_ROLEPLAY_SHEET_ID/edit?gid=1330624165#gid=1330624165"
)

DEFAULT_ENGLISH_FUN_FACTS_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_ENGLISH_FUN_FACTS_SHEET_ID/edit?gid=1018300388#gid=1018300388"
)

DEFAULT_FRENCH_FUN_FACTS_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_FRENCH_FUN_FACTS_SHEET_ID/edit?gid=326424538#gid=326424538"
)

DEFAULT_SPANISH_FUN_FACTS_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_SPANISH_FUN_FACTS_SHEET_ID/edit?gid=1653121820#gid=1653121820"
)

DEFAULT_ITALIAN_FUN_FACTS_URL = (
    "https://docs.google.com/spreadsheets/d/YOUR_ITALIAN_FUN_FACTS_SHEET_ID/edit?gid=1565936975#gid=1565936975"
)

# The central deployed Google Apps Script Web App URL for Option A dynamic sheet routing
MASTER_WEBAPP_URL = os.getenv(
    "SHEETS_MASTER_WEBAPP_URL",
    "https://script.google.com/macros/s/YOUR_APPS_SCRIPT_WEBAPP_ID/exec"
)

# In-memory endpoint dictionary mapping (language, video_type) -> Google Sheet URL or ID
ENDPOINT_REGISTRY: Dict[Tuple[str, str], str] = {
    # French
    ("french", "expression"): os.getenv("SHEETS_ENDPOINT_FRENCH_EXPRESSION", DEFAULT_FRENCH_EXPRESSION_URL),
    ("french", "roleplay"): os.getenv("SHEETS_ENDPOINT_FRENCH_ROLEPLAY", DEFAULT_FRENCH_ROLEPLAY_URL),
    ("french", "game"): os.getenv("SHEETS_ENDPOINT_FRENCH_GAME", DEFAULT_FRENCH_GAME_URL),
    ("french", "fun_facts"): os.getenv("SHEETS_ENDPOINT_FRENCH_FUN_FACTS", DEFAULT_FRENCH_FUN_FACTS_URL),

    # English
    ("english", "expression"): os.getenv("SHEETS_ENDPOINT_ENGLISH_EXPRESSION", DEFAULT_ENGLISH_EXPRESSION_URL),
    ("english", "roleplay"): os.getenv("SHEETS_ENDPOINT_ENGLISH_ROLEPLAY", DEFAULT_ENGLISH_ROLEPLAY_URL),
    ("english", "game"): os.getenv("SHEETS_ENDPOINT_ENGLISH_GAME", DEFAULT_ENGLISH_GAME_URL),
    ("english", "fun_facts"): os.getenv("SHEETS_ENDPOINT_ENGLISH_FUN_FACTS", DEFAULT_ENGLISH_FUN_FACTS_URL),

    # Spanish
    ("spanish", "expression"): os.getenv("SHEETS_ENDPOINT_SPANISH_EXPRESSION", DEFAULT_SPANISH_EXPRESSION_URL),
    ("spanish", "roleplay"): os.getenv("SHEETS_ENDPOINT_SPANISH_ROLEPLAY", DEFAULT_SPANISH_ROLEPLAY_URL),
    ("spanish", "game"): os.getenv("SHEETS_ENDPOINT_SPANISH_GAME", DEFAULT_SPANISH_GAME_URL),
    ("spanish", "fun_facts"): os.getenv("SHEETS_ENDPOINT_SPANISH_FUN_FACTS", DEFAULT_SPANISH_FUN_FACTS_URL),

    # Italian
    ("italian", "expression"): os.getenv("SHEETS_ENDPOINT_ITALIAN_EXPRESSION", DEFAULT_ITALIAN_EXPRESSION_URL),
    ("italian", "roleplay"): os.getenv("SHEETS_ENDPOINT_ITALIAN_ROLEPLAY", DEFAULT_ITALIAN_ROLEPLAY_URL),
    ("italian", "game"): os.getenv("SHEETS_ENDPOINT_ITALIAN_GAME", DEFAULT_ITALIAN_GAME_URL),
    ("italian", "fun_facts"): os.getenv("SHEETS_ENDPOINT_ITALIAN_FUN_FACTS", DEFAULT_ITALIAN_FUN_FACTS_URL),
}

# Comprehensive alias shortcuts (e.g. 'french', 'fe', 'fr_game', 'english_roleplay')
ALIAS_MAP: Dict[str, Tuple[str, str]] = {
    # French
    "french": ("french", "expression"),
    "fe": ("french", "expression"),
    "fr": ("french", "expression"),
    "french_expression": ("french", "expression"),
    "french_roleplay": ("french", "roleplay"),
    "fr_roleplay": ("french", "roleplay"),
    "french_game": ("french", "game"),
    "fr_game": ("french", "game"),
    "french_fun_facts": ("french", "fun_facts"),
    "fr_fun_facts": ("french", "fun_facts"),

    # English
    "english": ("english", "expression"),
    "ee": ("english", "expression"),
    "en": ("english", "expression"),
    "english_expression": ("english", "expression"),
    "english_roleplay": ("english", "roleplay"),
    "en_roleplay": ("english", "roleplay"),
    "english_game": ("english", "game"),
    "en_game": ("english", "game"),
    "english_fun_facts": ("english", "fun_facts"),
    "en_fun_facts": ("english", "fun_facts"),

    # Spanish
    "spanish": ("spanish", "expression"),
    "se": ("spanish", "expression"),
    "es": ("spanish", "expression"),
    "spanish_expression": ("spanish", "expression"),
    "spanish_roleplay": ("spanish", "roleplay"),
    "es_roleplay": ("spanish", "roleplay"),
    "spanish_game": ("spanish", "game"),
    "es_game": ("spanish", "game"),
    "spanish_fun_facts": ("spanish", "fun_facts"),
    "es_fun_facts": ("spanish", "fun_facts"),

    # Italian
    "italian": ("italian", "expression"),
    "ie": ("italian", "expression"),
    "it": ("italian", "expression"),
    "italian_expression": ("italian", "expression"),
    "italian_roleplay": ("italian", "roleplay"),
    "it_roleplay": ("italian", "roleplay"),
    "italian_game": ("italian", "game"),
    "it_game": ("italian", "game"),
    "italian_fun_facts": ("italian", "fun_facts"),
    "it_fun_facts": ("italian", "fun_facts"),
}

import re

def extract_spreadsheet_id(val: str) -> Optional[str]:
    """
    Extracts the Google Spreadsheet ID from either:
    - A full Google Sheets URL: https://docs.google.com/spreadsheets/d/<ID>/edit...
    - A direct alphanumeric ID string.
    Returns None if it is a Google Apps Script Web App URL or empty.
    """
    if not val or not val.strip():
        return None
    val_clean = val.strip()

    # If it's a script.google.com URL, it's not a spreadsheet ID
    if "script.google.com" in val_clean:
        return None

    # Check for standard docs.google.com URL pattern
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", val_clean)
    if match:
        return match.group(1)

    # If it looks like a raw ID (no slashes, length > 15)
    if "/" not in val_clean and len(val_clean) >= 15:
        return val_clean

    return None


def build_fetch_url(target: str, tab: Optional[str] = None) -> str:
    """
    Builds the final HTTP GET URL.
    - If target is already a Google Apps Script Web App URL, appends ?sheet=tab if tab is provided.
    - If target is a Spreadsheet ID or docs.google.com URL, routes through MASTER_WEBAPP_URL with ?id=<ID>.
    """
    if not target or not target.strip():
        base = MASTER_WEBAPP_URL
    else:
        target_clean = target.strip()
        sheet_id = extract_spreadsheet_id(target_clean)
        if sheet_id:
            sep = "&" if "?" in MASTER_WEBAPP_URL else "?"
            base = f"{MASTER_WEBAPP_URL}{sep}id={sheet_id}"
        else:
            base = target_clean

    if tab and tab.strip():
        sep = "&" if "?" in base else "?"
        base = f"{base}{sep}sheet={tab.strip()}"

    return base


def register_endpoint(language: str, video_type: str, target: str) -> None:
    """
    Registers a Google Sheets target for a language & video type.
    Target can be:
    - A Google Spreadsheet ID (e.g. '1AbCdEfGhIjKl...')
    - A full Google Sheet URL ('https://docs.google.com/spreadsheets/d/1AbCd.../edit')
    - A dedicated Google Apps Script Web App URL ('https://script.google.com/.../exec')
    """
    lang = language.strip().lower()
    vtype = video_type.strip().lower()
    ENDPOINT_REGISTRY[(lang, vtype)] = target.strip()


def get_endpoint(
    language: Optional[str] = None,
    video_type: Optional[str] = None,
    alias: Optional[str] = None,
    custom_url: Optional[str] = None,
    sheet_id: Optional[str] = None,
    tab: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Resolves the target endpoint URL, returning (language, video_type, final_fetch_url).

    Resolution precedence:
    1. Direct sheet_id (routed via MASTER_WEBAPP_URL).
    2. Direct custom_url if provided.
    3. Alias string (e.g. 'french', 'fe').
    4. (language, video_type) pair.
    5. Fallback to default French Expression endpoint.
    """
    lang = (language or "french").strip().lower()
    vtype = (video_type or "expression").strip().lower()

    if sheet_id and sheet_id.strip():
        url = build_fetch_url(sheet_id.strip(), tab=tab)
        return lang, vtype, url

    if custom_url and custom_url.strip():
        url = build_fetch_url(custom_url.strip(), tab=tab)
        return lang, vtype, url

    if alias and alias.strip().lower() in ALIAS_MAP:
        key = ALIAS_MAP[alias.strip().lower()]
        target = ENDPOINT_REGISTRY.get(key, "")
        if target:
            return key[0], key[1], build_fetch_url(target, tab=tab)

    key = (lang, vtype)
    target = ENDPOINT_REGISTRY.get(key, "")
    if not target:
        # Default fallback
        target = DEFAULT_FRENCH_EXPRESSION_URL
        lang = "french"
        vtype = "expression"

    url = build_fetch_url(target, tab=tab)
    return lang, vtype, url


def list_registered_endpoints() -> List[Dict[str, str]]:
    """Returns a list of all non-empty configured endpoints."""
    results = []
    for (lang, vtype), target in sorted(ENDPOINT_REGISTRY.items()):
        if target:
            results.append({
                "language": lang,
                "video_type": vtype,
                "target": target,
                "resolved_url": build_fetch_url(target),
            })
    return results
