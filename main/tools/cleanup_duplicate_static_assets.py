"""
Cleanup utility to safely purge redundant static asset copies (such as duplicate Tito waiting images)
from script output folders, reclaiming disk space now that VideoAssembler resolves them dynamically.
"""

import os
import sys
from pathlib import Path

# Add project root and core to sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import VIDEO_ASSETS_DIR, GAME_IMAGES_DIR, resolve_static_scene_path


def cleanup_redundant_game_pressure_images(dry_run: bool = False) -> int:
    """
    Finds and deletes redundant script_<id>_pressure.png files from Game video asset directories.
    These files are duplicates of the centralized Tito waiting images in input/images/game_images/.
    """
    if not VIDEO_ASSETS_DIR.exists():
        print(f"Directory {VIDEO_ASSETS_DIR} not found.")
        return 0

    deleted_count = 0
    reclaimed_bytes = 0

    print(f"Scanning for redundant static assets in {VIDEO_ASSETS_DIR}...")
    for root, dirs, files in os.walk(VIDEO_ASSETS_DIR):
        for fname in files:
            fname_lower = fname.lower()
            if fname_lower.endswith("_pressure.png") and fname_lower.startswith("script_"):
                file_path = Path(root) / fname
                size = file_path.stat().st_size

                # Verify that the central static image exists before deleting
                # Path format: .../video_assets/<language>/game/<script_id>/images/script_<id>_pressure.png
                parts = file_path.parts
                lang = "english"
                for p in parts:
                    plow = p.lower()
                    if plow in ("english", "french", "spanish", "italian"):
                        lang = plow
                        break

                central_img = resolve_static_scene_path(
                    section_name="pressure",
                    language=lang,
                    video_type="GAME",
                )

                if central_img and central_img.exists():
                    if dry_run:
                        print(f"  [DRY RUN] Would delete: {file_path.name} ({size / 1024:.1f} KB) -> Central: {central_img.name}")
                    else:
                        try:
                            file_path.unlink()
                            print(f"  [DELETED] {file_path.name} ({size / 1024:.1f} KB) -> Verified central: {central_img.name}")
                            deleted_count += 1
                            reclaimed_bytes += size
                        except Exception as e:
                            print(f"  [ERROR] Could not delete {file_path}: {e}")
                else:
                    print(f"  [SKIPPED] Central static asset not verified for {file_path}")

    mb_freed = reclaimed_bytes / (1024 * 1024)
    if dry_run:
        print(f"\nDry run complete. Would purge {deleted_count} duplicate files ({mb_freed:.2f} MB).")
    else:
        print(f"\nCleanup complete. Purged {deleted_count} duplicate files, reclaiming {mb_freed:.2f} MB of disk space.")
    return deleted_count


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    cleanup_redundant_game_pressure_images(dry_run=dry_run)
