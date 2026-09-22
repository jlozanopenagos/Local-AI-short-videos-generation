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
DEFAULT_FRENCH_EXPRESSION_URL = (
    "https://script.google.com/macros/s/YOUR_APPS_SCRIPT_WEBAPP_ID/exec"
)

DEFAULT_ENGLISH_EXPRESSION_URL = (
    "https://script.google.com/macros/s/YOUR_APPS_SCRIPT_WEBAPP_ID/exec"
)

# In-memory endpoint dictionary
ENDPOINT_REGISTRY: Dict[Tuple[str, str], str] = {
    ("french", "expression"): os.getenv("SHEETS_ENDPOINT_FRENCH_EXPRESSION", DEFAULT_FRENCH_EXPRESSION_URL),
    ("french", "roleplay"): os.getenv("SHEETS_ENDPOINT_FRENCH_ROLEPLAY", ""),
    ("french", "game"): os.getenv("SHEETS_ENDPOINT_FRENCH_GAME", ""),
    ("french", "fun_facts"): os.getenv("SHEETS_ENDPOINT_FRENCH_FUN_FACTS", ""),

    ("english", "expression"): os.getenv("SHEETS_ENDPOINT_ENGLISH_EXPRESSION", DEFAULT_ENGLISH_EXPRESSION_URL),
    ("english", "roleplay"): os.getenv("SHEETS_ENDPOINT_ENGLISH_ROLEPLAY", ""),
    ("english", "game"): os.getenv("SHEETS_ENDPOINT_ENGLISH_GAME", ""),
    ("english", "fun_facts"): os.getenv("SHEETS_ENDPOINT_ENGLISH_FUN_FACTS", ""),

    ("spanish", "expression"): os.getenv("SHEETS_ENDPOINT_SPANISH_EXPRESSION", ""),
    ("spanish", "roleplay"): os.getenv("SHEETS_ENDPOINT_SPANISH_ROLEPLAY", ""),
    ("spanish", "game"): os.getenv("SHEETS_ENDPOINT_SPANISH_GAME", ""),
    ("spanish", "fun_facts"): os.getenv("SHEETS_ENDPOINT_SPANISH_FUN_FACTS", ""),

    ("italian", "expression"): os.getenv("SHEETS_ENDPOINT_ITALIAN_EXPRESSION", ""),
    ("italian", "roleplay"): os.getenv("SHEETS_ENDPOINT_ITALIAN_ROLEPLAY", ""),
    ("italian", "game"): os.getenv("SHEETS_ENDPOINT_ITALIAN_GAME", ""),
    ("italian", "fun_facts"): os.getenv("SHEETS_ENDPOINT_ITALIAN_FUN_FACTS", ""),
}

# Alias shortcuts (e.g. 'french', 'fe', 'fr_expression')
ALIAS_MAP: Dict[str, Tuple[str, str]] = {
    "french": ("french", "expression"),
    "fe": ("french", "expression"),
    "fr": ("french", "expression"),
    "french_expression": ("french", "expression"),
    "french_roleplay": ("french", "roleplay"),
    "french_game": ("french", "game"),
    "french_fun_facts": ("french", "fun_facts"),

    "english": ("english", "expression"),
    "ee": ("english", "expression"),
    "en": ("english", "expression"),

    "spanish": ("spanish", "expression"),
    "se": ("spanish", "expression"),
    "es": ("spanish", "expression"),

    "italian": ("italian", "expression"),
    "ie": ("italian", "expression"),
    "it": ("italian", "expression"),
}


MASTER_WEBAPP_URL = DEFAULT_FRENCH_EXPRESSION_URL

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
