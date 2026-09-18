#!/usr/bin/env python3
"""
tools/migrate_remove_music_state.py

Migrates all 1,184 script state JSON files across state/ to remove:
1. data['status']['music_generation']
2. data['assets']['bgm_path'] (if present)

This transitions the codebase to the Standing Music Bank architecture,
where background music is resolved dynamically during assembly based on
emotional triggers rather than tracking per-script music generation.
"""

import json
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parents[2]
    state_dir = base_dir / "state"

    state_files = sorted(state_dir.rglob("script_*.json"))
    print(f"Found {len(state_files)} state JSON files in {state_dir}")

    modified_count = 0
    total_cleaned_status = 0
    total_cleaned_assets = 0

    for file_path in state_files:
        try:
            with file_path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)

            changed = False
            status = data.get("status")
            if isinstance(status, dict) and "music_generation" in status:
                del status["music_generation"]
                total_cleaned_status += 1
                changed = True

            assets = data.get("assets")
            if isinstance(assets, dict) and "bgm_path" in assets:
                del assets["bgm_path"]
                total_cleaned_assets += 1
                changed = True

            if changed:
                with file_path.open("w", encoding="utf-8") as fp:
                    json.dump(data, fp, indent=4, ensure_ascii=False)
                modified_count += 1
        except Exception as exc:
            print(f"Error processing {file_path.name}: {exc}")

    print("=" * 60)
    print(f"Migration Complete:")
    print(f"  Total state files inspected : {len(state_files)}")
    print(f"  Files modified              : {modified_count}")
    print(f"  'music_generation' removed  : {total_cleaned_status}")
    print(f"  'bgm_path' removed          : {total_cleaned_assets}")
    print("=" * 60)

if __name__ == "__main__":
    main()
