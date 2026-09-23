"""
connectivity package — Modular Google Sheets integration for shorts_automation.

Modules:
- core: Endpoint registries, URL building, and raw HTTP client.
- sheet_sync: Syncs Google Sheets (columns A, B, C) to D:\\AI\\output\\connectivity.
- corrected_scripts: Pulls corrected scripts (Column D) into main/input/csv/script_to_change.
"""

import sys
from connectivity.core import endpoints
from connectivity.sheet_sync import sync_service

# Backward-compatibility aliases for legacy module paths
sys.modules.setdefault("connectivity.endpoints", endpoints)
sys.modules.setdefault("connectivity.sheets_fetcher", sync_service)
sys.modules.setdefault("main.connectivity.endpoints", endpoints)
sys.modules.setdefault("main.connectivity.sheets_fetcher", sync_service)

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
)
from connectivity.sheet_sync.sync_service import (
    fetch_sheet_data,
    save_connectivity_data,
    sync_sheet,
    sync_all_sheets,
    resolve_connectivity_output_dir,
    TARGET_COLUMNS as SYNC_TARGET_COLUMNS,
    FOUR_COLUMNS as SYNC_FOUR_COLUMNS,
)
from connectivity.corrected_scripts.fetcher import (
    fetch_raw_corrected_records,
    filter_corrected_records,
    save_corrected_scripts_csv,
    fetch_and_save_corrected_scripts,
    fetch_all_sheets_corrected_scripts,
    load_ids_from_csv,
)
from connectivity.post_scripts.poster import (
    DEFAULT_SCRIPTS_TO_SEE_DIR,
    DEFAULT_SCRIPTS_TO_POST_DIR,
    get_source_csv_path,
    load_source_scripts_csv,
    parse_range_spec,
    filter_scripts,
    post_single_sheet,
    post_all_sheets,
)
from connectivity.reconcile.service import (
    DEFAULT_CONNECTIVITY_DIR,
    load_csv_records,
    reconcile_all_sheets,
    reconcile_sheet_data,
    reconcile_single_sheet,
    save_reconciled_csv,
)

TARGET_COLUMNS = SYNC_TARGET_COLUMNS
FOUR_COLUMNS = SYNC_FOUR_COLUMNS

__all__ = [
    # Core
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
    # Sheet Sync (Feature 1)
    "fetch_sheet_data",
    "save_connectivity_data",
    "sync_sheet",
    "sync_all_sheets",
    "resolve_connectivity_output_dir",
    "TARGET_COLUMNS",
    "FOUR_COLUMNS",
    # Corrected Scripts (Feature 2)
    "fetch_raw_corrected_records",
    "filter_corrected_records",
    "save_corrected_scripts_csv",
    "fetch_and_save_corrected_scripts",
    "fetch_all_sheets_corrected_scripts",
    "load_ids_from_csv",
    # Post Scripts (Feature 3)
    "DEFAULT_SCRIPTS_TO_SEE_DIR",
    "DEFAULT_SCRIPTS_TO_POST_DIR",
    "get_source_csv_path",
    "load_source_scripts_csv",
    "parse_range_spec",
    "filter_scripts",
    "post_single_sheet",
    "post_all_sheets",
    # Reconcile & Reorganize (Feature 4)
    "DEFAULT_CONNECTIVITY_DIR",
    "load_csv_records",
    "reconcile_sheet_data",
    "reconcile_single_sheet",
    "reconcile_all_sheets",
    "save_reconciled_csv",
]

