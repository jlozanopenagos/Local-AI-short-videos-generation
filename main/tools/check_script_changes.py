#!/usr/bin/env python3
"""
check_script_changes.py — Audit & Synchronize Script Changes from CSV to State JSON.

Scans CSV files in main/input/csv/script_to_change/, compares NEW_SCRIPT against
the current state JSONs across all languages and video types, reports exact differences,
and prompts (or allows CLI flag) to update the JSON state files for changed IDs.

Usage:
  # Interactive audit & update prompt:
  py main/tools/check_script_changes.py

  # Check only without modifying:
  py main/tools/check_script_changes.py --check-only

  # Automatically apply all detected changes:
  py main/tools/check_script_changes.py --apply

  # Audit/apply a specific script ID:
  py main/tools/check_script_changes.py --script-id EE06
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Add project root and main/ to path
MAIN_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = MAIN_DIR.parent
for p in [str(PROJECT_ROOT), str(MAIN_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Reconfigure streams to avoid Windows charmap encoding issues
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

from config import BASE_DIR, INPUT_CSV_DIR
from core.state_manager import StateManager
from video_creation._A_video_scripts.script_modifier import modify_video_script


def extract_spoken_text_from_state(state: Dict[str, Any]) -> str:
    """Extracts all spoken sections from state JSON, excluding the title."""
    if not isinstance(state, dict):
        return ""

    content_meta = state.get("content_metadata", {})
    script_obj = content_meta.get("script", {})

    if not isinstance(script_obj, dict):
        st_raw = state.get("script_text", "")
        if isinstance(st_raw, str) and st_raw.strip().startswith("{"):
            try:
                script_obj = json.loads(st_raw)
            except Exception:
                pass

    if isinstance(script_obj, dict):
        spoken_parts = [
            str(v).strip()
            for k, v in script_obj.items()
            if k.lower() != "title" and isinstance(v, str) and str(v).strip()
        ]
        return "\n\n".join(spoken_parts).strip()

    return ""


def normalize_text_for_comparison(text: str, video_type: str = "") -> str:
    """Normalizes whitespace, quotes, narrator prefixes, line breaks, and GAME option syntax for comparison."""
    if not text:
        return ""
    # Strip speaker prefixes like 'Narrator:' that are stripped during JSON state storage
    lines = []
    for l in text.splitlines():
        l_clean = re.sub(r"^(?:narrator|narrateur|narratore|narrador)\s*:\s*", "", l.strip(), flags=re.IGNORECASE)
        lines.append(l_clean)
    t = " ".join(lines)
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    # Strip quotes so expressions wrapped in quotes match unquoted state keys
    t = t.replace("'", "").replace('"', "").replace("«", "").replace("»", "")

    if video_type.upper() == "GAME":
        # Strip option connectors: or, ou, oppure, o, and, y, e
        t = re.sub(r"\b(?:or|ou|oppure|and|y|e)\s+([B-D]\s*:)", r"\1", t, flags=re.IGNORECASE)
        # Lowercase uppercase stress words (e.g. record, present, project)
        t = re.sub(r"\b[a-zA-Z]*[A-Z]{2,}[a-zA-Z-]*\b", lambda m: m.group(0).lower() if m.group(0) not in ("A", "B", "C", "D") else m.group(0), t)
        # Strip articles 'a', 'to' when attached right after A: or B: for single words
        t = re.sub(r"([A-D]\s*:\s*)(?:a\s+|an\s+|to\s+|un\s+|une\s+|uno\s+|una\s+)", r"\1", t, flags=re.IGNORECASE)
        # Strip punctuation at end of options/challenge (? vs .)
        t = re.sub(r"[?!.,;:]+", " ", t)

    return " ".join(re.findall(r"\S+", t)).strip()


def compute_preview_diff(old_text: str, new_text: str, max_lines: int = 4) -> str:
    """Generates a concise unified diff snippet between old and new text."""
    old_lines = old_text.strip().splitlines()
    new_lines = new_text.strip().splitlines()
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))
    # Filter header lines
    diff_content = [line for line in diff if line.startswith(("+", "-")) and not line.startswith(("---", "+++"))]
    if not diff_content:
        return "Content whitespace/formatting adjusted"
    snippet = "\n    ".join(diff_content[:max_lines])
    if len(diff_content) > max_lines:
        snippet += f"\n    ... (+{len(diff_content) - max_lines} more lines)"
    return snippet


def audit_script_changes(
    base_dir: Path,
    target_csv: Optional[str] = None,
    target_script_id: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """
    Scans script_to_change directory, compares each CSV row against state JSON.
    Returns: (changed_records, identical_records, missing_state_ids)
    """
    state_mgr = StateManager(base_dir)
    csv_dir = base_dir / "input" / "csv" / "script_to_change"

    if not csv_dir.exists():
        print(f"Directory not found: {csv_dir}", file=sys.stderr)
        return [], [], []

    if target_csv:
        csv_p = Path(target_csv)
        if not csv_p.is_file():
            csv_p = csv_dir / target_csv
        if not csv_p.is_file():
            print(f"Error: CSV file not found: {target_csv}", file=sys.stderr)
            return [], [], []
        candidate_files = [csv_p]
    else:
        candidate_files = sorted(csv_dir.glob("*.csv"))
        candidate_files = [f for f in candidate_files if not f.name.startswith("model_")]

    changed_records: List[Dict[str, Any]] = []
    identical_records: List[Dict[str, Any]] = []
    missing_ids: List[str] = []

    for cf in candidate_files:
        try:
            raw_text = cf.read_text(encoding="utf-8-sig", errors="replace")
        except Exception:
            try:
                raw_text = cf.read_text(encoding="latin-1", errors="replace")
            except Exception as e:
                print(f"Warning: Failed to read {cf.name}: {e}", file=sys.stderr)
                continue

        import io
        reader = csv.DictReader(io.StringIO(raw_text))
        fieldnames = reader.fieldnames or []

        id_col = next((c for c in fieldnames if c.strip().upper() == "ID"), None)
        script_col = next(
            (c for c in fieldnames if c.strip().upper() in ("NEW_SCRIPT", "SCRIPT", "NEW_SCRIPT_TEXT", "SCRIPT_CHANGE", "SCRIPT_CHANGED")),
            None,
        )

        if not id_col or not script_col:
            continue

        for row in reader:
            sid = str(row.get(id_col, "")).strip().upper()
            new_script = str(row.get(script_col, "")).strip()

            if not sid:
                continue
            if target_script_id and sid != target_script_id.strip().upper():
                continue
            if not new_script:
                continue

            if not state_mgr.script_exists(sid):
                missing_ids.append(sid)
                continue

            state = state_mgr.get_script_state(sid)
            vtype = (
                state.get("prompt_params", {}).get("VIDEO_TYPE")
                or state.get("content_metadata", {}).get("video_type", "")
            )
            if not vtype:
                try:
                    from core.state_manager import resolve_lang_and_type
                    _, vtype = resolve_lang_and_type(sid)
                except Exception:
                    vtype = ""

            curr_spoken = extract_spoken_text_from_state(state)

            norm_new = normalize_text_for_comparison(new_script, video_type=vtype)
            norm_curr = normalize_text_for_comparison(curr_spoken, video_type=vtype)

            record_info = {
                "id": sid,
                "file": cf.name,
                "new_script": new_script,
                "current_spoken": curr_spoken,
                "words_current": len(curr_spoken.split()),
                "words_new": len(new_script.split()),
            }

            if norm_new != norm_curr:
                # Check if words are identical regardless of section schema ordering or minor punctuation
                words_new = re.findall(r"\w+", norm_new.lower())
                words_curr = re.findall(r"\w+", norm_curr.lower())
                if sorted(words_new) == sorted(words_curr):
                    identical_records.append(record_info)
                elif vtype.upper() == "GAME":
                    # For GAME, check if the remaining differences are only minor particles/connectors
                    diff_words_new = set(words_new) - set(words_curr)
                    diff_words_curr = set(words_curr) - set(words_new)
                    ignorable_game_diffs = {
                        "a", "an", "to", "or", "ou", "o", "oppure", "and", "y", "e",
                        "which", "one", "is", "it", "tu", "ton", "il", "la", "le"
                    }
                    if diff_words_new.issubset(ignorable_game_diffs) and diff_words_curr.issubset(ignorable_game_diffs):
                        identical_records.append(record_info)
                    else:
                        record_info["diff_preview"] = compute_preview_diff(curr_spoken, new_script)
                        changed_records.append(record_info)
                else:
                    record_info["diff_preview"] = compute_preview_diff(curr_spoken, new_script)
                    changed_records.append(record_info)
            else:
                identical_records.append(record_info)

    return changed_records, identical_records, missing_ids


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check and apply script changes from input/csv/script_to_change/ to local State JSONs."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Target specific CSV file in script_to_change/",
    )
    parser.add_argument(
        "--script-id",
        type=str,
        default=None,
        help="Check or apply changes for a specific script ID (e.g. EE06, EG01)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only display detected changes; do not prompt or modify state JSONs.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Automatically apply all detected changes without interactive confirmation.",
    )
    parser.add_argument(
        "--reset-downstream",
        action="store_true",
        default=True,
        help="Reset voice, image, and video assembly stages to 'pending' (default: True).",
    )
    args = parser.parse_args()

    base_dir = BASE_DIR
    print("\n" + "=" * 70)
    print("🔍 SCRIPT CHANGE AUDITOR: CSV (Column D) vs State JSON")
    print("=" * 70)

    changed, identical, missing = audit_script_changes(
        base_dir=base_dir,
        target_csv=args.csv,
        target_script_id=args.script_id,
    )

    total_checked = len(changed) + len(identical) + len(missing)
    print(f"• Total Scripts Checked: {total_checked}")
    print(f"• Already Up-to-Date:    {len(identical)}")
    print(f"• Differences Detected:  {len(changed)}")
    if missing:
        print(f"• Missing State Files:   {len(missing)} ({', '.join(missing[:8])})")
    print("-" * 70)

    if not changed:
        print("\n✨ All checked scripts are already 100% synchronized with local State JSONs!")
        return 0

    print(f"\nFound {len(changed)} script(s) with pending modifications:\n")
    for idx, item in enumerate(changed, start=1):
        delta = item["words_new"] - item["words_current"]
        delta_str = f"+{delta}w" if delta >= 0 else f"{delta}w"
        print(f"[{idx:2d}] {item['id']:6} ({item['file']})")
        print(f"     Word count: {item['words_current']}w -> {item['words_new']}w ({delta_str})")
        print(f"     Diff preview:")
        print(f"    {item['diff_preview']}\n")

    if args.check_only:
        print("(--check-only specified. Exiting without modifications.)")
        return 0

    to_apply: List[Dict[str, Any]] = []

    if args.apply:
        to_apply = changed
    else:
        # Interactive prompt
        print("=" * 70)
        print("Options:")
        print("  [A] Apply ALL changes to State JSONs (Recommended)")
        print("  [S] Select specific IDs (e.g. 'EE06, EE07' or range '1-5')")
        print("  [N] Cancel and exit without changing anything")
        print("=" * 70)

        try:
            choice = input("Select an option [A/s/N]: ").strip().upper()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return 0

        if choice in ("A", "ALL", ""):
            to_apply = changed
        elif choice in ("N", "NO"):
            print("Cancelled by user. No state files were modified.")
            return 0
        else:
            # Parse custom selection
            selection_raw = choice if choice not in ("S", "SELECT") else input("Enter IDs or numbers (e.g. EE06, EE07 or 1,2,3): ").strip()
            selected_ids: Set[str] = set()
            for part in re.split(r"[\s,]+", selection_raw):
                part = part.strip().upper()
                if not part:
                    continue
                if part.isdigit():
                    num = int(part)
                    if 1 <= num <= len(changed):
                        selected_ids.add(changed[num - 1]["id"])
                else:
                    selected_ids.add(part)

            to_apply = [item for item in changed if item["id"] in selected_ids]

            if not to_apply:
                print("No matching scripts selected. Exiting.")
                return 0

    print(f"\n🚀 Applying updates to {len(to_apply)} script state(s)...")
    successful = 0
    failed = 0

    for item in to_apply:
        sid = item["id"]
        raw_text = item["new_script"]
        print(f"\nUpdating {sid}...")
        try:
            ok = modify_video_script(
                script_id=sid,
                raw_script_text=raw_text,
                reset_downstream=args.reset_downstream,
                base_dir=base_dir,
            )
            if ok:
                successful += 1
            else:
                failed += 1
        except Exception as err:
            print(f"❌ Error updating {sid}: {err}", file=sys.stderr)
            failed += 1

    print("\n" + "=" * 70)
    print("BATCH SYNCHRONIZATION COMPLETE")
    print(f"• Successfully updated: {successful} script(s)")
    if failed:
        print(f"• Failed:               {failed} script(s)")
    print("• Downstream stages (voice, images, assembly) reset to 'pending'.")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

