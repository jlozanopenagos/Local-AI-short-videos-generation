import os
import sys
import re
import csv
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import BASE_DIR

LANGUAGE_CODES = {
    "english": "E",
    "french": "F",
    "spanish": "S",
    "italian": "I",
    "en": "E",
    "fr": "F",
    "es": "S",
    "it": "I",
}

TYPE_CODES = {
    "EXPRESSION": "E",
    "GAME": "G",
    "ROLEPLAY": "R",
    "FUN_FACTS": "F",
    "FUNFACTS": "F",
    "FACTS": "F",
}

def get_language_code(language_str: str) -> str:
    """Returns 1-letter uppercase code for language (e.g. English -> 'E', French -> 'F', Spanish -> 'S')."""
    if not language_str:
        return "E"
    clean = str(language_str).split("|")[0].strip().lower()
    for k, v in LANGUAGE_CODES.items():
        if k in clean:
            return v
    return clean[:1].upper()

def get_type_code(video_type_str: str) -> str:
    """Returns 1-letter uppercase code for video type (EXPRESSION -> 'E', GAME -> 'G', ROLEPLAY -> 'R', FUN_FACTS -> 'F')."""
    if not video_type_str:
        return "E"
    clean = str(video_type_str).strip().upper()
    for k, v in TYPE_CODES.items():
        if k in clean:
            return v
    return clean[:1].upper()

def generate_script_id(language: str, video_type: str, index: int) -> str:
    """
    Generates structured script ID: <Lang_Code><Type_Code><Index:02d>
    e.g. 'FE01', 'FG02', 'ER01', 'SE03', 'EF01', 'FF01'
    """
    lang_code = get_language_code(language)
    type_code = get_type_code(video_type)
    return f"{lang_code}{type_code}{index:02d}"

def parse_script_id(script_id: str) -> Optional[Dict[str, str]]:
    """
    Parses a script ID like 'FE01' or 'EF01' into its components:
    {'lang_code': 'E', 'type_code': 'F', 'index': 1, 'language': 'english', 'video_type': 'FUN_FACTS'}
    """
    if not script_id:
        return None
    m = re.match(r"^([A-Z])([A-Z])(\d+)$", str(script_id).strip().upper())
    if not m:
        return None
    lang_c, type_c, num_s = m.groups()
    lang_map_rev = {"E": "english", "F": "french", "S": "spanish", "I": "italian"}
    type_map_rev = {"E": "EXPRESSION", "G": "GAME", "R": "ROLEPLAY", "F": "FUN_FACTS"}
    return {
        "lang_code": lang_c,
        "type_code": type_c,
        "index": int(num_s),
        "language": lang_map_rev.get(lang_c, "english"),
        "video_type": type_map_rev.get(type_c, "EXPRESSION"),
    }

def process_csv_files(base_dir: Path = None, dry_run: bool = False, force_reindex: bool = False) -> Tuple[List[Dict], Dict[str, str]]:
    """
    Scans all ready prompts CSV files across input/<lang>/expressions_list/,
    assigns structured IDs (<Lang><Type><02d>) per language and video type,
    and writes them back to disk.

    - Preserves existing valid structured IDs (e.g. FE01, FE02) without re-numbering.
    - If new rows are added without an ID, assigns the next available unique index (e.g. FE03).
    - If force_reindex=True, strictly re-numbers all rows sequentially from 01.

    Returns:
      - list of assigned row summary records
      - mapping of old_id -> new_id
    """
    if base_dir is None:
        base_dir = BASE_DIR

    input_dir = base_dir / "input"
    state_dir = base_dir / "state"
    if not input_dir.exists():
        print(f"[ERROR] Input directory not found: {input_dir}")
        return [], {}

    # Find all CSV files in input/csv/<lang>/expressions_list/*READY_PROMPTS_*.csv
    csv_files = []
    input_csv_dir = input_dir / "csv"
    if input_csv_dir.exists():
        for lang_dir in sorted(input_csv_dir.iterdir()):
            if lang_dir.is_dir():
                expr_dir = lang_dir / "expressions_list"
                if expr_dir.exists():
                    csv_files.extend(sorted(expr_dir.glob("*READY_PROMPTS_*.csv")))

    # Fallback to input/<lang>/expressions_list/ if not found
    if not csv_files:
        for lang_dir in sorted(input_dir.iterdir()):
            if lang_dir.is_dir() and lang_dir.name not in ("csv", "images"):
                expr_dir = lang_dir / "expressions_list"
                if expr_dir.exists():
                    csv_files.extend(sorted(expr_dir.glob("*READY_PROMPTS_*.csv")))

    # Fallback to flat input/ if none found
    if not csv_files:
        csv_files.extend(sorted(input_dir.glob("*READY_PROMPTS_*.csv")))

    # Step 1: Pre-scan existing IDs across state/ and CSVs to find highest index per (lang, type)
    max_indices: Dict[Tuple[str, str], int] = {}
    used_ids: set = set()

    if not force_reindex:
        # Check existing state files
        if state_dir.exists():
            for sf in state_dir.rglob("script_*.json"):
                parsed = parse_script_id(sf.stem.replace("script_", ""))
                if parsed:
                    k = (parsed["lang_code"], parsed["type_code"])
                    max_indices[k] = max(max_indices.get(k, 0), parsed["index"])
                    used_ids.add(f"{parsed['lang_code']}{parsed['type_code']}{parsed['index']:02d}")

        # Check existing CSV entries
        for csv_path in csv_files:
            with csv_path.open("r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    cid = str(r.get("ID", "")).strip().upper()
                    parsed = parse_script_id(cid)
                    if parsed:
                        k = (parsed["lang_code"], parsed["type_code"])
                        max_indices[k] = max(max_indices.get(k, 0), parsed["index"])

    old_to_new_mapping: Dict[str, str] = {}
    assignments: List[Dict] = []
    assigned_in_run: set = set()

    for csv_path in csv_files:
        rows = []
        fieldnames = []
        with csv_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for row in reader:
                rows.append(row)

        if not rows:
            continue

        file_modified = False

        # Infer language from file path if possible
        path_parts = [p.lower() for p in csv_path.parts]
        inferred_lang = "english"
        for lk in ["french", "spanish", "italian", "english"]:
            if lk in path_parts:
                inferred_lang = lk
                break

        # Infer video type from file name if possible
        fname_upper = csv_path.name.upper()
        inferred_type = "EXPRESSION"
        if "GAME" in fname_upper:
            inferred_type = "GAME"
        elif "ROLEPLAY" in fname_upper:
            inferred_type = "ROLEPLAY"
        elif "FUN_FACTS" in fname_upper or "FUNFACTS" in fname_upper or "FACTS" in fname_upper:
            inferred_type = "FUN_FACTS"
        elif "EXPRESSION" in fname_upper:
            inferred_type = "EXPRESSION"

        for row in rows:
            lang = row.get("TARGET_LANGUAGE") or inferred_lang
            vtype = row.get("VIDEO_TYPE") or inferred_type
            old_id = str(row.get("ID", "")).strip()

            lang_c = get_language_code(lang)
            type_c = get_type_code(vtype)
            key = (lang_c, type_c)

            new_id = None

            # If not forcing reindex, preserve already valid and non-colliding structured IDs
            if not force_reindex and old_id:
                parsed = parse_script_id(old_id)
                if parsed and parsed["lang_code"] == lang_c and parsed["type_code"] == type_c:
                    if old_id not in assigned_in_run:
                        new_id = old_id
                        assigned_in_run.add(new_id)

            # Otherwise, assign the next available unique index
            if not new_id:
                current_idx = max_indices.get(key, 0) + 1
                while True:
                    candidate = generate_script_id(lang, vtype, current_idx)
                    if candidate not in assigned_in_run and (force_reindex or candidate not in used_ids):
                        new_id = candidate
                        break
                    current_idx += 1
                max_indices[key] = current_idx
                assigned_in_run.add(new_id)
                used_ids.add(new_id)

            if old_id and old_id != new_id:
                old_to_new_mapping[old_id] = new_id

            if row.get("ID") != new_id:
                row["ID"] = new_id
                file_modified = True

            assignments.append({
                "file": csv_path.name,
                "language": lang,
                "type": vtype,
                "old_id": old_id,
                "new_id": new_id,
                "expression": row.get("EXPRESSION") or (row.get("ROLEPLAY_SCENARIO", "")[:40] + "..."),
            })

        if file_modified and not dry_run:
            with csv_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

    return assignments, old_to_new_mapping

def migrate_state_and_outputs(base_dir: Path, id_mapping: Dict[str, str], dry_run: bool = False) -> List[str]:
    """
    Migrates state/<old>.json -> state/<new>.json and output/<lang>/script_<old> -> output/<lang>/script_<new>
    based on the id_mapping.
    """
    state_dir = base_dir / "state"
    output_dirs = [base_dir / "output"]
    try:
        from config import OUTPUT_DIR
        if OUTPUT_DIR not in output_dirs and OUTPUT_DIR.exists():
            output_dirs.append(OUTPUT_DIR)
    except Exception:
        pass
    actions = []

    for old_id, new_id in id_mapping.items():
        if old_id == new_id:
            continue

        # 1. State file migration
        old_state_path = state_dir / f"script_{old_id}.json"
        new_state_path = state_dir / f"script_{new_id}.json"

        if old_state_path.exists():
            import json
            try:
                with old_state_path.open("r", encoding="utf-8") as f:
                    state_data = json.load(f)

                # Update ID in state
                state_data["id"] = new_id
                if "prompt_params" in state_data and isinstance(state_data["prompt_params"], dict):
                    state_data["prompt_params"]["ID"] = new_id

                # Update assets paths inside state
                assets = state_data.get("assets", {})
                for k, v in list(assets.items()):
                    if isinstance(v, str):
                        # Replace script_<old_id> with script_<new_id>
                        updated_v = re.sub(
                            rf"script_{re.escape(old_id)}([_\\]|$)",
                            rf"script_{new_id}\1",
                            v
                        )
                        assets[k] = updated_v

                if not dry_run:
                    with new_state_path.open("w", encoding="utf-8") as f:
                        json.dump(state_data, f, indent=4)
                    # Keep backup of old state or remove old state
                    old_state_path.unlink()
                actions.append(f"State: script_{old_id}.json -> script_{new_id}.json")
            except Exception as e:
                actions.append(f"[ERROR] Migrating state for {old_id}: {e}")

        # 2. Output directory migration across all configured output directories
        for output_dir in output_dirs:
            if not output_dir.exists():
                continue
            for old_out_dir in list(output_dir.rglob(f"script_{old_id}")):
                if not old_out_dir.is_dir():
                    continue
                new_out_dir = old_out_dir.parent / f"script_{new_id}"

                if old_out_dir.exists():
                    if not dry_run:
                        if new_out_dir.exists():
                            shutil.rmtree(new_out_dir)
                        old_out_dir.rename(new_out_dir)

                        # Rename any files inside new_out_dir matching script_<old_id>_* (including in subdirs like images/)
                        for asset_file in list(new_out_dir.rglob(f"script_{old_id}_*")):
                            if asset_file.is_file():
                                new_asset_name = asset_file.name.replace(f"script_{old_id}_", f"script_{new_id}_")
                                asset_file.rename(asset_file.parent / new_asset_name)

                    try:
                        old_rel = old_out_dir.relative_to(base_dir)
                        new_rel = new_out_dir.relative_to(base_dir)
                    except ValueError:
                        old_rel = old_out_dir
                        new_rel = new_out_dir
                    actions.append(f"Output: {old_rel} -> {new_rel}")

    return actions

def main():
    parser = argparse.ArgumentParser(description="Generate and standardize script IDs in CSVs (e.g. FE01, FG01, ER01).")
    parser.add_argument("--dry-run", action="store_true", help="Preview ID assignments without modifying files.")
    parser.add_argument("--force-reindex", action="store_true", help="Force renumbering all rows from 01 sequentially.")
    parser.add_argument("--migrate", action="store_true", default=True, help="Migrate existing state files and output folders matching old IDs.")
    parser.add_argument("--no-migrate", dest="migrate", action="store_false", help="Do not migrate existing state/output folders.")
    args = parser.parse_args()

    base_dir = BASE_DIR
    print("=" * 70)
    print(" SHORTS AUTOMATION - STRUCTURED SCRIPT ID GENERATOR")
    print(" Format: <Language_Code><Type_Code><Index:02d> (e.g. FE01, EG01, SR02)")
    print("=" * 70)

    assignments, id_mapping = process_csv_files(base_dir, dry_run=args.dry_run, force_reindex=args.force_reindex)

    if not assignments:
        print("No CSV prompt entries found.")
        return

    print(f"\nFound {len(assignments)} prompts across input CSVs:\n")
    print(f"{'NEW ID':<8} {'OLD ID':<8} {'LANG':<10} {'TYPE':<12} {'CSV FILE':<35} {'EXPRESSION'}")
    print("-" * 105)
    for a in assignments:
        print(f"{a['new_id']:<8} {a['old_id']:<8} {a['language']:<10} {a['type']:<12} {a['file']:<35} {a['expression']}")

    if args.dry_run:
        print("\n[DRY RUN] No files were modified.")
        return

    print("\n[SUCCESS] All CSV files have been updated with standardized IDs.")

    if args.migrate and id_mapping:
        print("\nMigrating existing state and output artifacts...")
        actions = migrate_state_and_outputs(base_dir, id_mapping, dry_run=False)
        for act in actions:
            print(f"  [OK] {act}")
        print("[SUCCESS] State and output migration completed.")

    print("\nDone!")

if __name__ == "__main__":
    main()
