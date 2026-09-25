#!/usr/bin/env python3
"""
CLI entrypoint forwarding to the canonical image modifier in video_creation._C_image_generation.
Allows interactive scene recreation, prompt steering, and chalkboard editing.
"""
import sys
from pathlib import Path

# Ensure shorts_automation directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from video_creation._C_image_generation.image_modifier import main

if __name__ == "__main__":
    sys.exit(main())
