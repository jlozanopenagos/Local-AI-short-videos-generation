"""
core/expression_db.py — Hybrid SQLite + Per-Language Auto-Synced CSV Database.

Key Rules:
1. Per-language CSVs in database/ (<lang>_expressions.csv): english, french, spanish, italian.
2. Columns: ID, EXPRESSION, CONTEXT, VIDEO_TYPE, STATUS (LANGUAGE column omitted as ID and filename define it).
3. Default STATUS is PENDING. Automatically populated from input/csv/.
4. SCRIPTS NEVER WRITE 'DONE'. Only the user sets STATUS to 'DONE' (via CSV or CLI).
5. Universal Gate: is_done(script_id) returns True if STATUS == 'DONE'.
6. Two-way sync: edits to any <lang>_expressions.csv are automatically detected and synced into SQLite.
"""
import os
import re
import csv
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from config import (
    BASE_DIR,
    DATABASE_DIR,
    DB_PATH,
    INPUT_CSV_DIR,
)
from core.state_manager import resolve_lang_and_type, LANG_MAP

SUPPORTED_LANGUAGES = ["english", "french", "spanish", "italian"]


class ExpressionDB:
    """Manages the expressions database with SQLite backend and per-language auto-synced CSV files."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        database_dir: Optional[Path] = None,
        auto_sync: bool = True,
    ):
        self.db_path = Path(db_path or DB_PATH)
        self.database_dir = Path(database_dir or DATABASE_DIR)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.database_dir.mkdir(parents=True, exist_ok=True)

        self._init_db()
        if auto_sync:
            self.sync()

    def get_csv_path(self, language: str) -> Path:
        """Returns the CSV path for a specific language (e.g. database/english_expressions.csv)."""
        return self.database_dir / f"{language.lower()}_expressions.csv"

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Creates tables and indexes if they do not exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS expressions (
                    id TEXT PRIMARY KEY,
                    expression TEXT NOT NULL,
                    context TEXT,
                    language TEXT,
                    video_type TEXT,
                    status TEXT DEFAULT 'PENDING',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expr_status ON expressions(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expr_lang ON expressions(language);")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)
            conn.commit()

    def _get_meta(self, key: str) -> Optional[str]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else None

    def _set_meta(self, key: str, value: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            conn.commit()

    def sync(self) -> None:
        """
        Bidirectional sync across all language CSVs.
        If a CSV was edited by user, syncs changes into SQLite.
        If any language CSV is missing, exports it from SQLite.
        """
        for lang in SUPPORTED_LANGUAGES:
            csv_file = self.get_csv_path(lang)
            if not csv_file.exists():
                self.export_to_csv(lang)
                continue

            current_mtime = str(os.path.getmtime(csv_file))
            last_mtime = self._get_meta(f"csv_mtime_{lang}")

            if current_mtime != last_mtime:
                self._import_from_csv(lang)
                self._set_meta(f"csv_mtime_{lang}", str(os.path.getmtime(csv_file)))

    def _import_from_csv(self, language: str) -> None:
        """Reads a specific language CSV and updates SQLite records (status, context, etc.)."""
        csv_file = self.get_csv_path(language)
        if not csv_file.exists():
            return

        with open(csv_file, mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            with self._get_connection() as conn:
                for row in reader:
                    sid = (row.get("ID") or "").strip().upper()
                    if not sid:
                        continue

                    expr = (row.get("EXPRESSION") or "").strip()
                    ctx = (row.get("CONTEXT") or "").strip()
                    vtype = (row.get("VIDEO_TYPE") or "").strip().lower()
                    status = (row.get("STATUS") or "PENDING").strip().upper()

                    # Fallback language / video_type resolution from ID if missing
                    resolved_lang, resolved_type = resolve_lang_and_type(sid)
                    lang = language.lower() or resolved_lang
                    vtype = vtype or resolved_type

                    existing = conn.execute("SELECT status FROM expressions WHERE id = ?", (sid,)).fetchone()
                    if existing:
                        if existing["status"].strip().upper() != status:
                            conn.execute(
                                "UPDATE expressions SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                (status, sid),
                            )
                    else:
                        conn.execute(
                            """
                            INSERT INTO expressions (id, expression, context, language, video_type, status, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                            """,
                            (sid, expr, ctx, lang, vtype, status),
                        )
                conn.commit()

    def export_to_csv(self, language: Optional[str] = None) -> None:
        """
        Exports expressions from SQLite to language-specific CSV files in natural sorted order.
        Columns: ID, EXPRESSION, CONTEXT, VIDEO_TYPE, STATUS (LANGUAGE column omitted).
        """
        langs = [language.lower()] if language else SUPPORTED_LANGUAGES

        # Natural sort helper by language/type prefix and numeric index (e.g. EE01, EE02, ..., EE99, EE100)
        def natural_sort_key(r):
            parts = re.split(r"(\d+)", r["id"])
            return [int(p) if p.isdigit() else p.lower() for p in parts]

        fieldnames = ["ID", "EXPRESSION", "CONTEXT", "VIDEO_TYPE", "STATUS"]

        with self._get_connection() as conn:
            for lang in langs:
                rows = conn.execute(
                    "SELECT id, expression, context, video_type, status FROM expressions WHERE LOWER(language) = ?",
                    (lang,),
                ).fetchall()

                sorted_rows = sorted(rows, key=natural_sort_key)
                csv_file = self.get_csv_path(lang)

                with open(csv_file, mode="w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for r in sorted_rows:
                        writer.writerow({
                            "ID": r["id"],
                            "EXPRESSION": r["expression"],
                            "CONTEXT": r["context"] or "",
                            "VIDEO_TYPE": r["video_type"] or "",
                            "STATUS": (r["status"] or "PENDING").upper(),
                        })

                self._set_meta(f"csv_mtime_{lang}", str(os.path.getmtime(csv_file)))

    def seed_from_input_csvs(self, input_dir: Optional[Path] = None) -> int:
        """
        Automatically scans all ready prompts CSVs in input/csv/ and populates SQLite.
        IMPORTANT: Uses INSERT OR IGNORE so existing rows and your user-defined STATUS are strictly preserved!
        You NEVER have to write down records manually!
        """
        if input_dir is None:
            input_dir = INPUT_CSV_DIR

        if not input_dir.exists():
            return 0

        csv_files = []
        for lang_dir in sorted(input_dir.iterdir()):
            if lang_dir.is_dir():
                expr_dir = lang_dir / "expressions_list"
                if expr_dir.exists():
                    csv_files.extend(sorted(expr_dir.glob("*READY_PROMPTS_*.csv")))

        new_count = 0
        with self._get_connection() as conn:
            for csv_file in csv_files:
                inferred_lang = csv_file.parent.parent.name.lower()
                stem = csv_file.stem.upper()
                if "GAME" in stem:
                    inferred_type = "game"
                elif "ROLEPLAY" in stem:
                    inferred_type = "roleplay"
                elif "FUN_FACTS" in stem or "FUNFACTS" in stem or "FACTS" in stem:
                    inferred_type = "fun_facts"
                else:
                    inferred_type = "expression"

                with open(csv_file, mode="r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        sid = (row.get("ID") or "").strip().upper()
                        if not sid:
                            continue

                        expr = (
                            row.get("TOPIC")
                            or row.get("EXPRESSION")
                            or row.get("ROLEPLAY_SCENARIO")
                            or row.get("SUBJECT")
                            or ""
                        ).strip()
                        ctx = (
                            row.get("FACT_DETAILS")
                            or row.get("HOOK_ANGLE")
                            or row.get("CONTEXT")
                            or row.get("SUBJECT")
                            or row.get("ANGLE")
                            or ""
                        ).strip()

                        lang = (row.get("TARGET_LANGUAGE") or inferred_lang).lower()
                        vtype = (row.get("VIDEO_TYPE") or inferred_type).lower()

                        cursor = conn.execute(
                            """
                            INSERT OR IGNORE INTO expressions (id, expression, context, language, video_type, status, updated_at)
                            VALUES (?, ?, ?, ?, ?, 'PENDING', CURRENT_TIMESTAMP)
                            """,
                            (sid, expr, ctx, lang, vtype),
                        )
                        if cursor.rowcount > 0:
                            new_count += 1
            conn.commit()

        # Export all language CSVs
        self.export_to_csv()
        return new_count

    def is_done(self, script_id: str) -> bool:
        """
        Universal check: returns True if script is marked DONE (case-insensitive) in database.
        Checks for recent CSV edits first so any manual user edits take effect immediately.
        """
        if not script_id:
            return False

        self.sync()
        sid = str(script_id).strip().upper()

        with self._get_connection() as conn:
            row = conn.execute("SELECT status FROM expressions WHERE id = ?", (sid,)).fetchone()
            if row and row["status"]:
                return row["status"].strip().upper() == "DONE"

        return False

    def get_status(self, script_id: str) -> Optional[str]:
        """Returns current status of an expression ('DONE', 'PENDING') or None."""
        self.sync()
        sid = str(script_id).strip().upper()
        with self._get_connection() as conn:
            row = conn.execute("SELECT status FROM expressions WHERE id = ?", (sid,)).fetchone()
            return row["status"].strip().upper() if row and row["status"] else None

    def set_status(self, script_id: str, status: str) -> bool:
        """Updates the STATUS of an expression and syncs to its respective language CSV."""
        sid = str(script_id).strip().upper()
        clean_status = str(status).strip().upper()

        with self._get_connection() as conn:
            row = conn.execute("SELECT language FROM expressions WHERE id = ?", (sid,)).fetchone()
            if not row:
                return False
            lang = row["language"]

            cursor = conn.execute(
                "UPDATE expressions SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (clean_status, sid),
            )
            conn.commit()
            if cursor.rowcount > 0:
                self.export_to_csv(lang)
                return True
        return False

    def get_expression(self, script_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves full expression record as a dict."""
        self.sync()
        sid = str(script_id).strip().upper()
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM expressions WHERE id = ?", (sid,)).fetchone()
            return dict(row) if row else None

    def list_expressions(
        self,
        status: Optional[str] = None,
        language: Optional[str] = None,
        video_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Queries and returns expressions filtered by status, language, or video_type."""
        self.sync()
        query = "SELECT * FROM expressions WHERE 1=1"
        params = []

        if status:
            query += " AND UPPER(status) = ?"
            params.append(status.strip().upper())
        if language:
            query += " AND LOWER(language) = ?"
            params.append(language.strip().lower())
        if video_type:
            query += " AND LOWER(video_type) = ?"
            params.append(video_type.strip().lower())

        query += " ORDER BY id ASC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> Dict[str, Any]:
        """Returns summary counts of expressions (total, pending, done)."""
        self.sync()
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM expressions").fetchone()["c"]
            done = conn.execute("SELECT COUNT(*) as c FROM expressions WHERE UPPER(status) = 'DONE'").fetchone()["c"]
            pending = conn.execute("SELECT COUNT(*) as c FROM expressions WHERE UPPER(status) != 'DONE'").fetchone()["c"]

            by_lang = {}
            for r in conn.execute(
                "SELECT language, UPPER(status) as st, COUNT(*) as c FROM expressions GROUP BY language, st"
            ).fetchall():
                lang = r["language"] or "unknown"
                st = r["st"]
                if lang not in by_lang:
                    by_lang[lang] = {"total": 0, "DONE": 0, "PENDING": 0}
                by_lang[lang]["total"] += r["c"]
                if st == "DONE":
                    by_lang[lang]["DONE"] += r["c"]
                else:
                    by_lang[lang]["PENDING"] += r["c"]

        return {
            "total": total,
            "done": done,
            "pending": pending,
            "by_language": by_lang,
        }


# Singleton accessor
_DEFAULT_DB: Optional[ExpressionDB] = None

def get_expression_db() -> ExpressionDB:
    global _DEFAULT_DB
    if _DEFAULT_DB is None:
        _DEFAULT_DB = ExpressionDB()
    return _DEFAULT_DB

def is_expression_done(script_id: str) -> bool:
    """Convenience helper: checks if an expression is marked DONE."""
    return get_expression_db().is_done(script_id)
