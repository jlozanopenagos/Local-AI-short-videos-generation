#!/usr/bin/env python3
"""
CLI entrypoint forwarding to canonical reset_stage_status in tools.database.
Allows resetting pipeline stage status (e.g. voice_generation, image_generation, video_assembly)
to 'pending' across state files and synchronizing state/pipeline_status.csv.
"""
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
MAIN_DIR = TOOL_DIR.parent
PROJECT_ROOT = MAIN_DIR.parent

for p in [str(PROJECT_ROOT), str(MAIN_DIR), str(TOOL_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from tools.database.reset_stage_status import main, reset_stage_status

if __name__ == "__main__":
    sys.exit(main())
