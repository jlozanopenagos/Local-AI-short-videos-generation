#!/usr/bin/env python3
"""
CLI entrypoint forwarding to the canonical script modifier in video_creation._A_video_scripts.
Supports Single Script, Mass Script Changes, and Ready Scripts CSV modes.
"""
import sys
from pathlib import Path

# Ensure shorts_automation directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from video_creation._A_video_scripts.script_modifier import interactive_main, modify_video_script

if __name__ == "__main__":
    sys.exit(interactive_main())
