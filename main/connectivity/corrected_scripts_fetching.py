#!/usr/bin/env python3
"""
corrected_scripts_fetching.py — Backward-compatibility forwarder for connectivity.fetch_corrected_scripts.
Delegates execution to fetch_corrected_scripts.main().
"""

import sys
from pathlib import Path

# Add project root and main/ to path
MAIN_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = MAIN_DIR.parent
for p in [str(PROJECT_ROOT), str(MAIN_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from connectivity.fetch_corrected_scripts import main

if __name__ == "__main__":
    sys.exit(main())
