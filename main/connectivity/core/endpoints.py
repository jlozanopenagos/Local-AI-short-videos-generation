"""
endpoints.py — Modular Registry for Google Sheets Apps Script Web App Endpoints.

Allows seamless switching between endpoints across all 4 languages (English, French, Spanish, Italian)
and 4 video formats (Expression, Roleplay, Game, Fun Facts).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Tuple, Optional, List, Any

# Ensure .env is loaded safely
try:
    # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv

    _main_env = Path(__file__).resolve().parent.parent.parent / ".env"
    if _main_env.exists():
        load_dotenv(_main_env)
    _root_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    if _root_env.exists():
        load_dotenv(_root_env)
    load_dotenv()
except Exception:
    pass

# The central deployed Google Apps Script Web App URL for Option A dynamic sheet routing
MASTER_WEBAPP_URL = os.getenv("SHEETS_MASTER_WEBAPP_URL", "")


def _get_env_endpoint(lang: str, vtype: str) -> str:
    """Retrieve Google Sheet URL or ID from environment variables."""
    return os.getenv(f"SHEETS_ENDPOINT_{lang.upper()}_{vtype.upper()}", "").strip()


# In-memory endpoint dictionary mapping (language, video_type) -> Google Sheet URL or ID
ENDPOINT_REGISTRY: Dict[Tuple[str, str], str] = {
    (lang, vtype): _get_env_endpoint(lang, vtype)
    for lang in ["french", "english", "spanish", "italian"]
    for vtype in ["expression", "roleplay", "game", "fun_facts"]
}

# Backward compatibility aliases
DEFAULT_FRENCH_EXPRESSION_URL = ENDPOINT_REGISTRY.get(("french", "expression"), "")
DEFAULT_ENGLISH_EXPRESSION_URL = ENDPOINT_REGISTRY.get(("english", "expression"), "")
DEFAULT_SPANISH_EXPRESSION_URL = ENDPOINT_REGISTRY.get(("spanish", "expression"), "")
DEFAULT_ITALIAN_EXPRESSION_URL = ENDPOINT_REGISTRY.get(("italian", "expression"), "")

# Comprehensive alias shortcuts
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


def extract_spreadsheet_id(val: Any) -> Optional[str]:
    """
    Extracts the Google Spreadsheet ID from either:
    - A full Google Sheets URL: https://docs.google.com/spreadsheets/d/<ID>/edit...
    - A URL with query param ?id=<ID> (e.g. Master Web App router URL)
    - A direct alphanumeric ID string.
    Returns None if no ID could be determined.
    """
    if not val:
        return None
    if isinstance(val, (tuple, list)) and len(val) > 0:
        val = val[-1]
    if not isinstance(val, str) or not val.strip():
        return None

    val_clean = val.strip()

    # Check query param ?id=... or &id=...
    param_match = re.search(r"[?&]id=([a-zA-Z0-9-_]+)", val_clean)
    if param_match:
        return param_match.group(1)

    if "script.google.com" in val_clean:
        return None

    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", val_clean)
    if match:
        return match.group(1)

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
    """Registers a Google Sheets target for a language & video type."""
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
    """Resolves target endpoint URL, returning (language, video_type, final_fetch_url)."""
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
