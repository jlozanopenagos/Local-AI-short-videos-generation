#!/usr/bin/env python3
"""
sync_drive.py — CLI tool for uploading finished videos and thumbnails to Google Drive.

Usage:
  # Upload single script
  py main/connectivity/sync_drive.py --script-id EE01

  # Upload all assembled scripts for a specific language
  py main/connectivity/sync_drive.py --language french --all

  # Upload all completed scripts across all languages
  py main/connectivity/sync_drive.py --all

  # Specify custom credentials or root folder
  py main/connectivity/sync_drive.py --script-id IG09 --credentials main/credentials/service_account.json
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root and main/ to path
MAIN_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = MAIN_DIR.parent
for p in [str(PROJECT_ROOT), str(MAIN_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from connectivity.drive_sync.drive_client import GoogleDriveClient, DEFAULT_ROOT_FOLDER_ID
from connectivity.drive_sync.sync_service import upload_script_to_drive, upload_completed_scripts_to_drive
# pyrefly: ignore[missing-import]
from state_manager import StateManager

# Reconfigure streams for Windows UTF-8 safety
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sync_drive")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upload assembled Shorts videos and thumbnails to Google Drive."
    )
    parser.add_argument(
        "--script-id",
        type=str,
        default=None,
        help="Target specific script ID (e.g. EE01, FR21, IG09)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Upload all completed/assembled scripts",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        choices=["english", "french", "italian", "spanish", "all"],
        help="Filter batch upload by language",
    )
    parser.add_argument(
        "--video-type",
        type=str,
        default=None,
        choices=["expression", "game", "roleplay", "fun_facts", "all"],
        help="Filter batch upload by video type",
    )
    parser.add_argument(
        "--credentials",
        type=str,
        default=None,
        help="Path to service_account.json (default: main/credentials/service_account.json)",
    )
    parser.add_argument(
        "--root-folder-id",
        type=str,
        default=DEFAULT_ROOT_FOLDER_ID,
        help=f"Target Google Drive root folder ID (default: {DEFAULT_ROOT_FOLDER_ID})",
    )

    args = parser.parse_args()

    if not args.script_id and not args.all:
        parser.print_help()
        print("\nError: Please specify either --script-id <ID> or --all.")
        return 1

    sm = StateManager()

    # Authenticate client
    try:
        client = GoogleDriveClient(
            credentials_path=args.credentials,
            root_folder_id=args.root_folder_id,
        )
        client.authenticate()
    except FileNotFoundError as fnf:
        print(f"\n[ERROR] Credentials missing: {fnf}")
        return 1
    except Exception as exc:
        print(f"\n[ERROR] Could not authenticate with Google Drive: {exc}")
        return 1

    if args.script_id:
        sid = args.script_id.upper().strip()
        print(f"\nUploading script {sid} to Google Drive...")
        try:
            res = upload_script_to_drive(
                script_id=sid,
                client=client,
                state_mgr=sm,
                root_folder_id=args.root_folder_id,
            )
            print(f"SUCCESS: Script {sid} uploaded!")
            print(f"  Drive Folder: {res['folder_url']}")
            if res.get("deleted_existing_count", 0) > 0:
                print(f"  Replaced:     {res['deleted_existing_count']} existing item(s) retired after upload")
            print(f"  Video:        {res['video']['name']} (ID: {res['video']['id']})")
            if res.get("thumbnail"):
                print(f"  Thumbnail:    {res['thumbnail']['name']} (ID: {res['thumbnail']['id']})")
            return 0
        except Exception as exc:
            logger.error("[%s] Upload failed: %s", sid, exc)
            return 1

    if args.all:
        lang_filter = None if args.language == "all" else args.language
        vtype_filter = None if args.video_type == "all" else args.video_type
        print(f"\nScanning assembled scripts to upload (Language: {lang_filter or 'ALL'}, Type: {vtype_filter or 'ALL'})...")
        results = upload_completed_scripts_to_drive(
            language=lang_filter,
            video_type=vtype_filter,
            client=client,
            state_mgr=sm,
        )
        successes = [r for r in results if "error" not in r]
        failures = [r for r in results if "error" in r]

        print(f"\nUpload Batch Complete: {len(successes)} succeeded, {len(failures)} failed.")
        for s in successes:
            print(f"  [OK] {s['script_id']}: {s['folder_url']}")
        for f in failures:
            print(f"  [FAIL] {f['script_id']}: {f['error']}")

        return 0 if not failures else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

