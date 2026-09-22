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

# In-memory endpoint dictionary
ENDPOINT_REGISTRY: Dict[Tuple[str, str], str] = {
    ("french", "expression"): os.getenv("SHEETS_ENDPOINT_FRENCH_EXPRESSION", DEFAULT_FRENCH_EXPRESSION_URL),
    ("french", "roleplay"): os.getenv("SHEETS_ENDPOINT_FRENCH_ROLEPLAY", ""),
    ("french", "game"): os.getenv("SHEETS_ENDPOINT_FRENCH_GAME", ""),
    ("french", "fun_facts"): os.getenv("SHEETS_ENDPOINT_FRENCH_FUN_FACTS", ""),

    ("english", "expression"): os.getenv("SHEETS_ENDPOINT_ENGLISH_EXPRESSION", ""),
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


def register_endpoint(language: str, video_type: str, url: str) -> None:
    """Registers or overrides a Google Sheets Web App URL for a language & video type."""
    lang = language.strip().lower()
    vtype = video_type.strip().lower()
    ENDPOINT_REGISTRY[(lang, vtype)] = url.strip()


def get_endpoint(
    language: Optional[str] = None,
    video_type: Optional[str] = None,
    alias: Optional[str] = None,
    custom_url: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Resolves the target endpoint URL, returning (language, video_type, url).

    Resolution precedence:
    1. Direct custom_url if provided.
    2. Alias string (e.g. 'french', 'fe').
    3. (language, video_type) pair.
    4. Fallback to default French Expression endpoint.
    """
    if custom_url and custom_url.strip():
        lang = language.strip().lower() if language else "french"
        vtype = video_type.strip().lower() if video_type else "expression"
        return lang, vtype, custom_url.strip()

    if alias and alias.strip().lower() in ALIAS_MAP:
        key = ALIAS_MAP[alias.strip().lower()]
        url = ENDPOINT_REGISTRY.get(key, "")
        if url:
            return key[0], key[1], url

    lang = (language or "french").strip().lower()
    vtype = (video_type or "expression").strip().lower()
    key = (lang, vtype)

    url = ENDPOINT_REGISTRY.get(key, "")
    if not url:
        # Default fallback
        url = DEFAULT_FRENCH_EXPRESSION_URL
        lang = "french"
        vtype = "expression"

    return lang, vtype, url


def list_registered_endpoints() -> List[Dict[str, str]]:
    """Returns a list of all non-empty configured endpoints."""
    results = []
    for (lang, vtype), url in sorted(ENDPOINT_REGISTRY.items()):
        if url:
            results.append({
                "language": lang,
                "video_type": vtype,
                "url": url,
            })
    return results
