#!/usr/bin/env python3
"""
LingoVerse Stage Status Reset Utility.
Allows resetting pipeline stage status (e.g. voice_generation, image_generation, video_assembly)
to 'pending' (or another status) across all state files or filtered by language, video type, or script ID.
Automatically synchronizes state/pipeline_status.csv upon completion.

Usage examples:
  # Reset voice_generation to 'pending' across all 1224 state files
  py tools/reset_stage_status.py --stage voice_generation --yes

  # Reset image_generation for all French expressions
  py tools/reset_stage_status.py --stage image_generation -l french -t expression --yes

  # Reset specific scripts
  py tools/reset_stage_status.py --stage voice_generation -id EE01,EE02,FE01 --yes

  # Dry run preview without making changes
  py tools/reset_stage_status.py --stage voice_generation --dry-run
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure paths are configured
TOOL_DIR = Path(__file__).resolve().parent
MAIN_DIR = TOOL_DIR.parent if TOOL_DIR.name in ("database", "modifiers", "auditing", "prompt_builders") else TOOL_DIR
PROJECT_ROOT = MAIN_DIR.parent

for p in [str(PROJECT_ROOT), str(MAIN_DIR), str(MAIN_DIR / "core")]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from config import BASE_DIR
except (ImportError, ModuleNotFoundError):
    BASE_DIR = MAIN_DIR

from core.state_manager import StateManager, resolve_lang_and_type
from core.status_tracker import PipelineStatusTracker, get_status_tracker

VALID_STAGES = [
    "script_generation",
    "voice_generation",
    "image_generation",
    "thumbnail_generation",
    "video_assembly",
    "all",
]

STAGE_ASSET_KEYS = {
    "voice_generation": ["audio_path"],
    "image_generation": ["image_dir", "image_prompts", "general_prompt"],
    "video_assembly": ["final_video"],
}


def reset_stage_status(
    stage: str = "voice_generation",
    target_status: str = "pending",
    language: Optional[str] = "all",
    video_type: Optional[str] = "all",
    script_ids: Optional[Sequence[str]] = None,
    base_dir: Optional[Path] = None,
    clear_assets: bool = False,
    dry_run: bool = False,
    sync_manifest: bool = True,
) -> Dict[str, Any]:
    """
    Resets status for the given stage across matching state JSON files.
    Returns a dictionary summarizing modified and matching script counts.
    """
    stage_lower = stage.strip().lower()
    if stage_lower not in VALID_STAGES:
        raise ValueError(f"Invalid stage '{stage}'. Must be one of: {', '.join(VALID_STAGES)}")

    stages_to_update = (
        ["script_generation", "voice_generation", "image_generation", "thumbnail_generation", "video_assembly"]
        if stage_lower == "all"
        else [stage_lower]
    )

    app_base = Path(base_dir or BASE_DIR).resolve()
    state_dir = app_base / "state"

    if not state_dir.exists():
        return {
            "total_scanned": 0,
            "total_matched": 0,
            "total_modified": 0,
            "modified_ids": [],
            "by_language": {},
            "by_type": {},
        }

    lang_filter = language.strip().lower() if language and language.strip().lower() != "all" else None
    type_filter = video_type.strip().lower() if video_type and video_type.strip().lower() != "all" else None
    id_set: Optional[Set[str]] = (
        {s.strip().upper() for s in script_ids if s.strip()} if script_ids else None
    )

    all_state_files = sorted(state_dir.rglob("script_*.json"))
    candidate_files = [
        f for f in all_state_files
        if ".sample" not in f.name.lower() and "sample" not in f.name.lower()
    ]

    total_matched = 0
    total_modified = 0
    modified_ids: List[str] = []
    by_lang: Dict[str, int] = {}
    by_type: Dict[str, int] = {}

    for s_file in candidate_files:
        sid = s_file.stem.replace("script_", "").strip().upper()
        if id_set and sid not in id_set:
            continue

        try:
            with s_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        lang, vtype = resolve_lang_and_type(sid, data)
        if lang_filter and lang.lower() != lang_filter:
            continue
        if type_filter and vtype.lower() != type_filter:
            continue

        total_matched += 1
        status_dict = data.setdefault("status", {})
        assets_dict = data.setdefault("assets", {})

        needs_save = False
        for stg in stages_to_update:
            current_val = str(status_dict.get(stg, "")).strip().lower()
            if current_val != target_status.lower():
                status_dict[stg] = target_status.lower()
                needs_save = True

            if clear_assets and stg in STAGE_ASSET_KEYS:
                for asset_k in STAGE_ASSET_KEYS[stg]:
                    if asset_k in assets_dict:
                        assets_dict.pop(asset_k, None)
                        needs_save = True

        if needs_save:
            total_modified += 1
            modified_ids.append(sid)
            by_lang[lang] = by_lang.get(lang, 0) + 1
            by_type[vtype] = by_type.get(vtype, 0) + 1

            if not dry_run:
                with s_file.open("w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

    if not dry_run and sync_manifest and total_modified > 0:
        try:
            tracker = get_status_tracker(app_base)
            tracker.scrape_and_save()
        except Exception as exc:
            print(f"[Warning] Failed to synchronize pipeline_status.csv: {exc}", file=sys.stderr)

    return {
        "total_scanned": len(candidate_files),
        "total_matched": total_matched,
        "total_modified": total_modified,
        "modified_ids": modified_ids,
        "by_language": by_lang,
        "by_type": by_type,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset pipeline stage status across LingoVerse state files."
    )
    parser.add_argument(
        "--stage",
        type=str,
        default="voice_generation",
        choices=VALID_STAGES,
        help="Stage to reset (default: voice_generation). Use 'all' for all pipeline stages.",
    )
    parser.add_argument(
        "--status",
        type=str,
        default="pending",
        help="Target status value to apply (default: pending).",
    )
    parser.add_argument(
        "-l", "--language",
        type=str,
        default="all",
        choices=["all", "english", "french", "spanish", "italian"],
        help="Filter by language (default: all).",
    )
    parser.add_argument(
        "-t", "--type",
        type=str,
        default="all",
        choices=["all", "expression", "game", "roleplay", "fun_facts"],
        help="Filter by video type (default: all).",
    )
    parser.add_argument(
        "-id", "--script-id",
        type=str,
        default=None,
        help="Specific script ID or comma-separated list of IDs (e.g. EE01,EE02,FR05).",
    )
    parser.add_argument(
        "--clear-assets",
        action="store_true",
        help="Also remove output asset paths corresponding to the reset stage(s).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to state files or manifest.",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Automatically proceed without confirmation prompt.",
    )

    args = parser.parse_args()

    script_ids = None
    if args.script_id:
        script_ids = [s.strip().upper() for s in args.script_id.split(",") if s.strip()]

    print("\n" + "=" * 76)
    print("           LINGOVERSE PIPELINE STAGE STATUS RESET TOOL")
    print("=" * 76)
    print(f"Target Stage         : {args.stage}")
    print(f"Target Status        : {args.status}")
    print(f"Language Filter      : {args.language}")
    print(f"Video Type Filter    : {args.type}")
    print(f"Script IDs Filter    : {', '.join(script_ids) if script_ids else 'ALL'}")
    print(f"Clear Stage Assets   : {args.clear_assets}")
    print(f"Dry Run Mode         : {args.dry_run}")
    print("-" * 76)

    # Pre-scan in dry-run mode to report counts
    pre_scan = reset_stage_status(
        stage=args.stage,
        target_status=args.status,
        language=args.language,
        video_type=args.type,
        script_ids=script_ids,
        clear_assets=args.clear_assets,
        dry_run=True,
        sync_manifest=False,
    )

    print(f"State files scanned : {pre_scan['total_scanned']}")
    print(f"Matching criteria   : {pre_scan['total_matched']}")
    print(f"Requiring update    : {pre_scan['total_modified']}")
    if pre_scan["total_modified"] > 0:
        print("Breakdown by language:")
        for lk, count in sorted(pre_scan["by_language"].items()):
            print(f"  • {lk:<12}: {count}")
        print("Breakdown by video type:")
        for tk, count in sorted(pre_scan["by_type"].items()):
            print(f"  • {tk:<12}: {count}")
    print("-" * 76)

    if pre_scan["total_modified"] == 0:
        print("No state files require updates. All matching scripts already have the desired status.")
        print("=" * 76 + "\n")
        return 0

    if args.dry_run:
        print("[DRY RUN] No files were modified.")
        print("=" * 76 + "\n")
        return 0

    if not args.yes:
        try:
            confirm = input(f"Are you sure you want to update {pre_scan['total_modified']} state file(s)? [y/N]: ").strip().lower()
            if confirm not in ("y", "yes"):
                print("Aborted by user.")
                return 0
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return 0

    # Execute actual update
    result = reset_stage_status(
        stage=args.stage,
        target_status=args.status,
        language=args.language,
        video_type=args.type,
        script_ids=script_ids,
        clear_assets=args.clear_assets,
        dry_run=False,
        sync_manifest=True,
    )

    print(f"\n✓ Successfully updated {result['total_modified']} state file(s)!")
    print(f"✓ Synchronized state/pipeline_status.csv master manifest.")
    print("=" * 76 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
