#!/usr/bin/env python3
"""
CLI entrypoint for Script Modifier.
Interactively ingests plain text scripts (singly or in groups) to update video state JSON
while strictly preserving the script text verbatim.
"""
import sys
from pathlib import Path

# Add project root and video_creation to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
video_creation_dir = PROJECT_ROOT / "video_creation"
for p in [str(PROJECT_ROOT), str(video_creation_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from video_creation._A_video_scripts.script_modifier import interactive_main

if __name__ == "__main__":
    sys.exit(interactive_main())
