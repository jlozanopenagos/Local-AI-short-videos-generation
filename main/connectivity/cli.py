#!/usr/bin/env python3
"""
cli.py — Backward-compatibility forwarder for connectivity.sync_sheets.
Delegates execution to sync_sheets.main().
"""

import sys
from pathlib import Path

# Add project root and main/ to path
MAIN_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = MAIN_DIR.parent
for p in [str(PROJECT_ROOT), str(MAIN_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from connectivity.sync_sheets import main, prompt_include_script_changed

if __name__ == "__main__":
    sys.exit(main())
