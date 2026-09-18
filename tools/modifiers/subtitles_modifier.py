#!/usr/bin/env python3
"""
CLI entrypoint for Subtitle Modifier and Video Re-assembler.
Inspect/edit subtitles (.ass), find/replace words, and re-assemble video without destructive Whisper overwrites.
"""
import sys
from pathlib import Path

# Add project root and video_creation to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
video_creation_dir = PROJECT_ROOT / "video_creation"
for p in [str(PROJECT_ROOT), str(video_creation_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from video_creation._G_video_assembly.subtitles_modifier import main

if __name__ == "__main__":
    sys.exit(main())
