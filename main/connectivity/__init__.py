"""
connectivity package — Modular Google Sheets integration for shorts_automation.
"""

from connectivity.endpoints import (
    get_endpoint,
    register_endpoint,
    list_registered_endpoints,
    DEFAULT_FRENCH_EXPRESSION_URL,
)
from connectivity.sheets_fetcher import (
    fetch_sheet_data,
    save_connectivity_data,
    sync_sheet,
    resolve_connectivity_output_dir,
    TARGET_COLUMNS,
)

__all__ = [
    "get_endpoint",
    "register_endpoint",
    "list_registered_endpoints",
    "DEFAULT_FRENCH_EXPRESSION_URL",
    "fetch_sheet_data",
    "save_connectivity_data",
    "sync_sheet",
    "resolve_connectivity_output_dir",
    "TARGET_COLUMNS",
]
