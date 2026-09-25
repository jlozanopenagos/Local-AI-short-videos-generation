#!/usr/bin/env python3
"""
CLI entrypoint forwarding to the canonical voice modifier in video_creation._B_voice_generation.
Allows testing, manual voice casting, and audio re-synthesis per script.
"""
import sys
from pathlib import Path

# Ensure shorts_automation directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from video_creation._B_voice_generation.voice_modifier import main

if __name__ == "__main__":
    sys.exit(main())
