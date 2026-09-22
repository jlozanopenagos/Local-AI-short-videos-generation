"""
core — Core endpoints registry, URL building, and HTTP client for Google Sheets.
"""

from connectivity.core.endpoints import (
    get_endpoint,
    register_endpoint,
    list_registered_endpoints,
    extract_spreadsheet_id,
    build_fetch_url,
    MASTER_WEBAPP_URL,
    DEFAULT_FRENCH_EXPRESSION_URL,
    DEFAULT_ENGLISH_EXPRESSION_URL,
    ENDPOINT_REGISTRY,
    ALIAS_MAP,
)
from connectivity.core.client import (
    fetch_raw_sheet_rows,
    normalize_sheet_rows,
    post_sheet_rows,
)

__all__ = [
    "get_endpoint",
    "register_endpoint",
    "list_registered_endpoints",
    "extract_spreadsheet_id",
    "build_fetch_url",
    "MASTER_WEBAPP_URL",
    "DEFAULT_FRENCH_EXPRESSION_URL",
    "DEFAULT_ENGLISH_EXPRESSION_URL",
    "ENDPOINT_REGISTRY",
    "ALIAS_MAP",
    "fetch_raw_sheet_rows",
    "normalize_sheet_rows",
    "post_sheet_rows",
]

