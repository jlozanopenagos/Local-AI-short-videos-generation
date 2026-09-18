#!/usr/bin/env python3
"""
CLI entrypoint to standardize and assign structured video IDs across input CSVs, state files, and output folders.
Format: <Language_Code><Type_Code><Index:02d> (e.g. FE01, EG01, SR02)
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from video_creation._A_video_scripts.id_generator import main

if __name__ == "__main__":
    main()
