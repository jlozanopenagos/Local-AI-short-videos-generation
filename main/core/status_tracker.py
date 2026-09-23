import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from config import BASE_DIR
except (ImportError, ModuleNotFoundError):
    BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from core.state_manager import LANG_MAP, TYPE_MAP, resolve_lang_and_type
except (ImportError, ModuleNotFoundError):
    LANG_MAP = {"E": "english", "F": "french", "S": "spanish", "I": "italian"}
    TYPE_MAP = {"E": "expression", "G": "game", "R": "roleplay", "F": "fun_facts"}
    def resolve_lang_and_type(sid: str, st=None):
        sid = str(sid).strip().upper()
        l = LANG_MAP.get(sid[0]) if len(sid) >= 2 else "english"
        t = TYPE_MAP.get(sid[1]) if len(sid) >= 2 else "expression"
        return l, t

try:
    from core.expression_db import get_expression_db, is_expression_done
except (ImportError, ModuleNotFoundError):
    def is_expression_done(sid: str) -> bool:
        return False
    def get_expression_db():
        return None

CSV_COLUMNS = [
    "ID",
    "EXPRESSION",
    "LANGUAGE",
    "VIDEO_TYPE",
    "script_generation_status",
    "voice_generation_status",
    "image_generation_status",
    "thumbnail_generation_status",
    "video_assembly_status",
    "db_status"
]

STAGE_STATUS_KEYS = [
    ("script_generation", "script_generation_status"),
    ("voice_generation", "voice_generation_status"),
    ("image_generation", "image_generation_status"),
    ("thumbnail_generation", "thumbnail_generation_status"),
    ("video_assembly", "video_assembly_status")
]

class PipelineStatusTracker:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir or BASE_DIR).resolve()
        self.state_dir = self.base_dir / "state"
        self.status_csv_path = self.state_dir / "pipeline_status.csv"

    def scrape_all(self) -> List[Dict[str, Any]]:
        """
        Scrapes all expressions across:
        1. All 16 input CSV queues (input/csv/<lang>/expressions_list/*_READY_PROMPTS_*.csv).
        2. All state JSON files in state/**/script_*.json.
        Returns a sorted list of row dicts conforming to CSV_COLUMNS.
        """
        all_records: Dict[str, Dict[str, Any]] = {}

        # 1. Harvest all planned prompts from input CSVs
        input_csv_dir = self.base_dir / "input" / "csv"
        if input_csv_dir.exists():
            for ready_csv in sorted(input_csv_dir.rglob("*READY_PROMPTS_*.csv")):
                path_parts = [p.lower() for p in ready_csv.parts]
                inferred_lang = "english"
                for lk in ["french", "spanish", "italian", "english"]:
                    if lk in path_parts:
                        inferred_lang = lk
                        break

                fname_upper = ready_csv.name.upper()
                inferred_type = "expression"
                if "GAME" in fname_upper:
                    inferred_type = "game"
                elif "ROLEPLAY" in fname_upper:
                    inferred_type = "roleplay"
                elif "FUN_FACTS" in fname_upper or "FUNFACTS" in fname_upper or "FACTS" in fname_upper:
                    inferred_type = "fun_facts"

                with ready_csv.open("r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        sid = str(row.get("ID", "")).strip().upper()
                        if not sid:
                            continue

                        expr = (
                            row.get("TOPIC")
                            or row.get("EXPRESSION")
                            or row.get("ROLEPLAY_SCENARIO")
                            or row.get("SUBJECT")
                            or ""
                        ).strip()

                        lang, vtype = resolve_lang_and_type(sid)
                        if not lang:
                            lang = inferred_lang
                        if not vtype:
                            vtype = inferred_type

                        all_records[sid] = {
                            "ID": sid,
                            "EXPRESSION": expr,
                            "LANGUAGE": lang,
                            "VIDEO_TYPE": vtype,
                            "script_generation_status": "pending",
                            "voice_generation_status": "pending",
                            "image_generation_status": "pending",
                            "thumbnail_generation_status": "pending",
                            "video_assembly_status": "pending",
                            "db_status": "DONE" if is_expression_done(sid) else "PENDING",
                        }

        # 2. Inspect all existing state JSON files
        if self.state_dir.exists():
            for state_file in sorted(self.state_dir.rglob("script_*.json")):
                if ".sample" in state_file.name.lower() or "sample" in state_file.name.lower():
                    continue
                sid = state_file.stem.replace("script_", "").strip().upper()
                if not sid:
                    continue

                try:
                    with state_file.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    continue

                lang, vtype = resolve_lang_and_type(sid, data)
                
                # Extract expression / topic
                expr = ""
                content_meta = data.get("content_metadata") or {}
                prompt_params = data.get("prompt_params") or {}
                metadata = data.get("metadata") or {}

                expr = (
                    content_meta.get("target_expression")
                    or prompt_params.get("TOPIC")
                    or prompt_params.get("EXPRESSION")
                    or prompt_params.get("ROLEPLAY_SCENARIO")
                    or prompt_params.get("SUBJECT")
                    or metadata.get("TOPIC")
                    or ""
                ).strip()

                if not expr and sid in all_records:
                    expr = all_records[sid]["EXPRESSION"]

                statuses = data.get("status", {})

                record = all_records.get(sid, {
                    "ID": sid,
                    "EXPRESSION": expr,
                    "LANGUAGE": lang,
                    "VIDEO_TYPE": vtype,
                    "db_status": "DONE" if is_expression_done(sid) else "PENDING",
                })

                if expr:
                    record["EXPRESSION"] = expr
                record["LANGUAGE"] = lang
                record["VIDEO_TYPE"] = vtype
                record["db_status"] = "DONE" if is_expression_done(sid) else "PENDING"

                for stage_key, col_key in STAGE_STATUS_KEYS:
                    val = str(statuses.get(stage_key, "pending")).strip().lower()
                    record[col_key] = val if val in ("done", "pending", "error") else "pending"

                all_records[sid] = record

        # 3. Sort records naturally (by language, type, index)
        def sort_key(row):
            sid = row["ID"]
            lang_code = sid[0] if len(sid) >= 1 else "Z"
            type_code = sid[1] if len(sid) >= 2 else "Z"
            num_part = sid[2:]
            try:
                num = int(num_part)
            except ValueError:
                num = 9999
            return (lang_code, type_code, num, sid)

        sorted_rows = sorted(all_records.values(), key=sort_key)
        return sorted_rows

    def save_status_csv(self, rows: Optional[List[Dict[str, Any]]] = None) -> Path:
        """Saves scraped or updated rows into state/pipeline_status.csv."""
        if rows is None:
            rows = self.scrape_all()

        self.state_dir.mkdir(parents=True, exist_ok=True)
        with self.status_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})

        return self.status_csv_path

    def load_status_csv(self, auto_scrape: bool = True, refresh: bool = False) -> List[Dict[str, Any]]:
        """Loads state/pipeline_status.csv. If missing or refresh=True, automatically scrapes and generates it."""
        if not self.status_csv_path.exists() or refresh:
            if auto_scrape or refresh:
                return self.scrape_and_save()
            return []

        rows = []
        with self.status_csv_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
        return rows

    def scrape_and_save(self) -> List[Dict[str, Any]]:
        """Full scrape + save in one call."""
        rows = self.scrape_all()
        self.save_status_csv(rows)
        return rows

    def update_script_stage_status(self, script_id: str, stage_name: str, status_value: str) -> None:
        """
        Updates a specific stage status for script_id directly inside state/pipeline_status.csv.
        """
        sid = str(script_id).strip().upper()
        col_key = f"{stage_name}_status" if not stage_name.endswith("_status") else stage_name
        if col_key not in CSV_COLUMNS:
            return

        rows = self.load_status_csv(auto_scrape=True)
        updated = False
        for row in rows:
            if row["ID"].upper() == sid:
                row[col_key] = status_value.lower()
                updated = True
                break

        if not updated:
            # Script wasn't in CSV yet, trigger full rescan
            self.scrape_and_save()
        else:
            with self.status_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                for row in rows:
                    writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})

    def get_pending_scripts(
        self,
        stage_name: str,
        script_id: Optional[Any] = None,
        language: Optional[str] = None,
        video_type: Optional[str] = None,
        force: bool = False,
        refresh: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Returns list of script entries pending for a given workflow stage:
        - 'script_generation': script_generation != 'done' and db_status != 'DONE'
        - 'voice_generation': script_generation == 'done' and (force or voice_generation != 'done') and db_status != 'DONE'
        - 'image_generation': script_generation == 'done' and (force or image_generation != 'done') and db_status != 'DONE'
        - 'music_generation': voice_generation == 'done' and (force or music_generation != 'done') and db_status != 'DONE'
        - 'thumbnail_generation': script_generation == 'done' and (force or thumbnail_generation != 'done') and db_status != 'DONE'
        - 'video_assembly': voice_generation == 'done' and image_generation == 'done' and (force or video_assembly != 'done') and db_status != 'DONE'
        """
        rows = self.load_status_csv(auto_scrape=True, refresh=refresh)
        pending = []

        target_ids = None
        if script_id:
            if isinstance(script_id, (list, set, tuple)):
                target_ids = {str(x).strip().upper() for x in script_id if str(x).strip()}
            elif "," in str(script_id):
                target_ids = {x.strip().upper() for x in str(script_id).split(",") if x.strip()}
            else:
                target_ids = {str(script_id).strip().upper()}

        for row in rows:
            sid = row["ID"]
            if target_ids and sid not in target_ids:
                continue
            if language and row["LANGUAGE"].lower() != language.strip().lower():
                continue
            if video_type and row["VIDEO_TYPE"].lower() != video_type.strip().lower():
                continue

            # DB gate: skip DONE expressions
            if row.get("db_status", "PENDING").upper() == "DONE":
                continue

            s_done = row.get("script_generation_status") == "done"
            v_done = row.get("voice_generation_status") == "done"
            i_done = row.get("image_generation_status") == "done"
            t_done = row.get("thumbnail_generation_status") == "done"
            a_done = row.get("video_assembly_status") == "done"

            if stage_name == "script_generation":
                if force or not s_done:
                    pending.append(row)
            elif stage_name == "voice_generation":
                if s_done and (force or not v_done):
                    pending.append(row)
            elif stage_name == "image_generation":
                if s_done and (force or not i_done):
                    pending.append(row)
            elif stage_name == "thumbnail_generation":
                if s_done and (force or not t_done):
                    pending.append(row)
            elif stage_name == "video_assembly":
                if v_done and i_done and (force or not a_done):
                    pending.append(row)

        return pending

    def get_summary_stats(self) -> Dict[str, Any]:
        """Returns aggregated totals and per-stage completion stats."""
        rows = self.load_status_csv(auto_scrape=True)
        total = len(rows)
        stats = {
            "total": total,
            "script_done": sum(1 for r in rows if r.get("script_generation_status") == "done"),
            "voice_done": sum(1 for r in rows if r.get("voice_generation_status") == "done"),
            "image_done": sum(1 for r in rows if r.get("image_generation_status") == "done"),
            "thumbnail_done": sum(1 for r in rows if r.get("thumbnail_generation_status") == "done"),
            "video_assembly_done": sum(1 for r in rows if r.get("video_assembly_status") == "done"),
            "by_language": {},
            "by_type": {}
        }

        for lang in ["english", "french", "spanish", "italian"]:
            l_rows = [r for r in rows if r.get("LANGUAGE") == lang]
            stats["by_language"][lang] = {
                "total": len(l_rows),
                "script_done": sum(1 for r in l_rows if r.get("script_generation_status") == "done"),
                "voice_done": sum(1 for r in l_rows if r.get("voice_generation_status") == "done"),
                "video_done": sum(1 for r in l_rows if r.get("video_assembly_status") == "done"),
            }

        for vt in ["expression", "game", "roleplay", "fun_facts"]:
            t_rows = [r for r in rows if r.get("VIDEO_TYPE") == vt]
            stats["by_type"][vt] = {
                "total": len(t_rows),
                "script_done": sum(1 for r in t_rows if r.get("script_generation_status") == "done"),
                "voice_done": sum(1 for r in t_rows if r.get("voice_generation_status") == "done"),
                "video_done": sum(1 for r in t_rows if r.get("video_assembly_status") == "done"),
            }

        return stats


def get_status_tracker(base_dir: Optional[Path] = None) -> PipelineStatusTracker:
    return PipelineStatusTracker(base_dir)
