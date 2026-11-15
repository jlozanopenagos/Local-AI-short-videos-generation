#!/usr/bin/env python3
"""
clear_stale_image_prompts.py — Clear stale cached image prompts across state JSONs.

Wipes assets.image_prompts = {} across all state files where legacy prompts exist,
so that the pipeline generates brand-new scene prompts using the Archetype Visual Grammar,
camera angle rules, and character continuity anchors.
Also resets image_generation status to 'pending' for any scripts previously marked 'done',
and synchronizes pipeline_status.csv.
"""

import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.status_tracker import get_status_tracker

STATE_DIR = BASE_DIR / "state"


def clear_stale_image_prompts() -> None:
    total_scanned = 0
    prompts_cleared_count = 0
    status_reset_count = 0

    for path in sorted(STATE_DIR.rglob("script_*.json")):
        if path.name == "script_state.sample.json":
            continue
        total_scanned += 1

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
        except Exception as exc:
            print(f"[ERROR] Could not read {path}: {exc}", file=sys.stderr)
            continue

        if not isinstance(data, dict):
            continue

        modified = False
        assets = data.setdefault("assets", {})
        status = data.setdefault("status", {})

        # 1. Clear stale image_prompts
        if assets.get("image_prompts") and isinstance(assets["image_prompts"], dict) and len(assets["image_prompts"]) > 0:
            assets["image_prompts"] = {}
            modified = True
            prompts_cleared_count += 1

        # 2. Clear stale rendered image references
        if assets.get("images") and isinstance(assets["images"], dict) and len(assets["images"]) > 0:
            assets["images"] = {}
            modified = True

        # 3. Reset image_generation status if it was marked 'done'
        if status.get("image_generation") == "done":
            status["image_generation"] = "pending"
            status_reset_count += 1
            modified = True

        # 4. Reset video_assembly if it was marked 'done' without fresh images
        if status.get("video_assembly") == "done":
            status["video_assembly"] = "pending"
            modified = True

        if modified:
            path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Scanned {total_scanned} state files.")
    print(f"Cleared stale image prompts in {prompts_cleared_count} state files.")
    print(f"Reset image_generation status from 'done' to 'pending' in {status_reset_count} state files.")

    # Synchronize pipeline_status.csv
    tracker = get_status_tracker()
    tracker.scrape_and_save()
    print("Synchronized pipeline_status.csv.")


if __name__ == "__main__":
    clear_stale_image_prompts()
