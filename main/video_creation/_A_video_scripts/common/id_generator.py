"""
id_generator.py — Re-exports ID parsing and generation tools into common.
"""

from __future__ import annotations

import sys
from pathlib import Path

#pyrefly: ignore[missing-import]
from ..id_generator import (
    LANGUAGE_CODES,
    TYPE_CODES,
    get_language_code,
    get_type_code,
    extract_components_from_id,
    generate_canonical_id,
    find_next_index_for_type,
)

__all__ = [
    "LANGUAGE_CODES",
    "TYPE_CODES",
    "get_language_code",
    "get_type_code",
    "extract_components_from_id",
    "generate_canonical_id",
    "find_next_index_for_type",
]

