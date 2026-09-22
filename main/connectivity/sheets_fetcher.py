"""
sheets_fetcher.py — Root forwarder for connectivity.sheet_sync.sync_service.
Maintains backward compatibility with all imports of `from connectivity.sheets_fetcher import ...`.
"""

from connectivity.sheet_sync.sync_service import (
    fetch_sheet_data,
    save_connectivity_data,
    sync_sheet,
    sync_all_sheets,
    resolve_connectivity_output_dir,
    TARGET_COLUMNS,
)

__all__ = [
    "fetch_sheet_data",
    "save_connectivity_data",
    "sync_sheet",
    "sync_all_sheets",
    "resolve_connectivity_output_dir",
    "TARGET_COLUMNS",
]
