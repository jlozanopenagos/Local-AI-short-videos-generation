"""
tools/upgrade_titles.py — Title & Metadata Singularity Auditor and Upgrader.

Eliminates repetitive 'Native Secret' / 'Il Segreto' clichés and emojis across
all state JSON files while establishing format-specific singularity across
EXPRESSION, GAME, ROLEPLAY, and FUN_FACTS.

Preserves existing rendered voice, image, and video assets (does not reset downstream statuses).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Reconfigure stdout for Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.state_manager import StateManager
from video_creation._A_video_scripts.core.metadata_builder import (
    strip_emojis,
    sanitize_title,
    BANNED_SUFFIX_PATTERNS,
)

_DB_CONN = None


def get_canonical_expression_from_db(sid: str) -> str:
    """Looks up clean target expression from database, mapping R/G back to E."""
    global _DB_CONN
    db_path = BASE_DIR / "database" / "expressions.db"
    if not db_path.exists():
        return ""
    try:
        if _DB_CONN is None:
            _DB_CONN = sqlite3.connect(str(db_path))
        c = _DB_CONN.cursor()

        # For Roleplay (R) or Game (G), map to Expression (E) to get clean expression
        target_id = sid
        if len(sid) >= 3 and sid[1] in ("R", "G"):
            target_id = f"{sid[0]}E{sid[2:]}"

        c.execute("SELECT expression FROM expressions WHERE id = ?", (target_id,))
        row = c.fetchone()
        if row and row[0]:
            return str(row[0]).strip()

        # Fallback to direct ID query
        c.execute("SELECT expression FROM expressions WHERE id = ?", (sid,))
        row = c.fetchone()
        if row and row[0]:
            val = str(row[0]).strip()
            # If it's a long scenario, skip it
            if len(val.split()) <= 8:
                return val
    except Exception:
        pass
    return ""


def has_cliche_or_emoji(script_title: str, yt_title: str) -> Tuple[bool, List[str]]:
    """Checks if either title contains banned clichés or emojis."""
    reasons = []

    # Check for emojis
    if strip_emojis(yt_title) != yt_title:
        reasons.append("Emojis in YouTube Title")
    if strip_emojis(script_title) != script_title:
        reasons.append("Emojis in Script Title")

    # Check for "secret" in either title
    comb = f"{script_title} {yt_title}".lower()
    for w in ("secret", "segreto", "secreto"):
        if re.search(rf"\b{w}\b", comb):
            reasons.append(f"Cliché word '{w}'")
            break

    # Check for banned suffix patterns
    for p in BANNED_SUFFIX_PATTERNS:
        if p.search(script_title):
            reasons.append("Banned suffix in Script Title")
            break
        if p.search(yt_title):
            reasons.append("Banned suffix in YouTube Title")
            break

    return (len(reasons) > 0, reasons)


def refine_and_upgrade_titles(
    sid: str,
    vtype: str,
    lang: str,
    expression: str,
    old_script_title: str,
    old_yt_title: str,
) -> Tuple[str, str]:
    """
    Refines and upgrades existing titles:
    1. Preserves custom, non-cliché script titles and YouTube titles.
    2. Strips all emojis from both titles.
    3. Replaces formulaic 'Native Secret' suffixes with format-differentiated descriptors.
    """
    vtype_upper = (vtype or "EXPRESSION").upper()
    lang_lower = (lang or "English").lower()

    # Resolve clean expression
    canonical_expr = get_canonical_expression_from_db(sid)
    if not canonical_expr:
        canonical_expr = expression

    expr_clean = re.sub(r"\s*\([^)]*\)", "", canonical_expr).strip() if canonical_expr else sid
    # If expression is a long sentence or prompt, shorten it
    if len(expr_clean.split()) > 7:
        expr_clean = expr_clean.split(":")[0].split("—")[0].strip()
        if len(expr_clean.split()) > 7:
            expr_clean = " ".join(expr_clean.split()[:5])

    # Strip existing format prefixes from expr_clean to prevent nesting
    clean_expr_base = re.sub(
        r"^(?:quiz|in action|en acci[óo]n|en action|in azione|origin|origen|origine)\s*[:：]\s*",
        "",
        expr_clean,
        flags=re.IGNORECASE,
    ).strip()

    # 1. Option B Chalkboard Script Title (Format Indicator + Clean Expression)
    if vtype_upper == "GAME":
        new_script_title = f"Quiz : {clean_expr_base}" if lang_lower == "french" else f"Quiz: {clean_expr_base}"
    elif vtype_upper == "ROLEPLAY":
        if lang_lower == "spanish":
            new_script_title = f"En Acción: {clean_expr_base}"
        elif lang_lower == "french":
            new_script_title = f"En Action : {clean_expr_base}"
        elif lang_lower == "italian":
            new_script_title = f"In Azione: {clean_expr_base}"
        else:
            new_script_title = f"In Action: {clean_expr_base}"
    elif vtype_upper == "FUN_FACTS":
        if lang_lower == "spanish":
            new_script_title = f"Origen: {clean_expr_base}"
        elif lang_lower == "french":
            new_script_title = f"Origine : {clean_expr_base}"
        elif lang_lower == "italian":
            new_script_title = f"Origine: {clean_expr_base}"
        else:
            new_script_title = f"Origin: {clean_expr_base}"
    else:  # EXPRESSION
        new_script_title = clean_expr_base

    # 2. Clean YouTube Title
    new_yt_title = strip_emojis(old_yt_title).strip()
    if not new_yt_title:
        new_yt_title = f"{expr_clean} - {new_script_title}"

    # Suffix replacements when at the end of string
    if lang_lower == "english":
        end_rep = "The Real Meaning" if vtype_upper == "EXPRESSION" else (
            "The Quick Ear Test" if vtype_upper == "GAME" else (
                "In Real Life" if vtype_upper == "ROLEPLAY" else "The Bizarre Truth"
            )
        )
    elif lang_lower == "spanish":
        end_rep = "El Significado Real" if vtype_upper == "EXPRESSION" else (
            "El Desafío Rápido" if vtype_upper == "GAME" else (
                "En la Vida Real" if vtype_upper == "ROLEPLAY" else "La Verdad Oculta"
            )
        )
    elif lang_lower == "french":
        end_rep = "Le Vrai Sens" if vtype_upper == "EXPRESSION" else (
            "Le Défi Express" if vtype_upper == "GAME" else (
                "En Situation Réelle" if vtype_upper == "ROLEPLAY" else "L'Histoire Insolite"
            )
        )
    elif lang_lower == "italian":
        end_rep = "Il Vero Significato" if vtype_upper == "EXPRESSION" else (
            "La Sfida Rapida" if vtype_upper == "GAME" else (
                "Nella Vita Reale" if vtype_upper == "ROLEPLAY" else "La Curiosità Nascosta"
            )
        )
    else:
        end_rep = "The Real Meaning"

    pattern_trailing = re.compile(
        r"[:\-–—]?\s*(?:the\s+)?native\s+secret\s*$|"
        r"[:\-–—]?\s*(?:le\s+)?secret\s+des\s+natifs\s*$|"
        r"[:\-–—]?\s*(?:el\s+)?secreto\s+de\s+los\s+nativos\s*$|"
        r"[:\-–—]?\s*(?:il\s+)?segreto\s+dei\s+nativi\s*$|"
        r"[:\-–—]?\s*(?:the\s+)?secret\s*$",
        re.IGNORECASE,
    )
    if pattern_trailing.search(new_yt_title):
        new_yt_title = pattern_trailing.sub(f" - {end_rep}", new_yt_title).strip()

    # In-sentence replacements
    new_yt_title = re.sub(r"\b(?:the\s+)?native\s+secret(?:\s+to|\s+for)?\b", "The Real Key To", new_yt_title, flags=re.IGNORECASE)
    new_yt_title = re.sub(r"\b(?:le\s+)?secret\s+des\s+natifs\b", "Le Vrai Sens", new_yt_title, flags=re.IGNORECASE)
    new_yt_title = re.sub(r"\b(?:il\s+)?segreto\s+dei\s+nativi\b", "Il Vero Significato", new_yt_title, flags=re.IGNORECASE)
    new_yt_title = re.sub(r"\b(?:el\s+)?secreto\s+de\s+los\s+nativos\b", "El Significado Real", new_yt_title, flags=re.IGNORECASE)
    new_yt_title = re.sub(r"\bsecret\b", "Truth", new_yt_title, flags=re.IGNORECASE)
    new_yt_title = re.sub(r"\bsegreto\b", "Mistero", new_yt_title, flags=re.IGNORECASE)
    new_yt_title = re.sub(r"\bsecreto\b", "Verdad", new_yt_title, flags=re.IGNORECASE)

    # Clean double spaces or orphaned separators
    new_yt_title = re.sub(r"\s+", " ", new_yt_title).strip()
    new_yt_title = re.sub(r"[\-–—:]\s*$", "", new_yt_title).strip()

    # Final sanitization pass
    new_script_title = sanitize_title(strip_emojis(new_script_title))
    new_yt_title = sanitize_title(strip_emojis(new_yt_title))

    return new_script_title, new_yt_title


def audit_and_upgrade_titles(
    base_dir: Path,
    apply_changes: bool = False,
    clean_emojis_only: bool = False,
    target_lang: Optional[str] = None,
    target_vtype: Optional[str] = None,
    target_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Audits all state JSON files for title clichés/emojis and optionally upgrades them.
    """
    state_files = sorted(glob.glob(str(base_dir / "state" / "**" / "*.json"), recursive=True))

    total_scanned = 0
    flagged_records = []
    upgraded_count = 0

    target_ids_set = {i.strip().upper() for i in target_ids} if target_ids else None

    for sf in state_files:
        if sf.endswith(".sample.json") or "pipeline_status" in sf:
            continue

        try:
            with open(sf, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            continue

        sid = state.get("id", "").strip().upper()
        if not sid:
            continue

        if target_ids_set and sid not in target_ids_set:
            continue

        content_meta = state.get("content_metadata") or {}
        prompt_params = state.get("prompt_params") or {}
        metadata = state.get("metadata") or {}

        vtype = (
            prompt_params.get("VIDEO_TYPE")
            or content_meta.get("video_type")
            or "EXPRESSION"
        ).upper()

        lang = (
            prompt_params.get("TARGET_LANGUAGE")
            or content_meta.get("language")
            or "English"
        ).title()

        if target_lang and lang.lower() != target_lang.lower().strip():
            continue
        if target_vtype and vtype.lower() != target_vtype.lower().strip():
            continue

        total_scanned += 1

        script_obj = content_meta.get("script") or {}
        if isinstance(script_obj, str):
            try:
                script_obj = json.loads(script_obj)
            except Exception:
                script_obj = {}

        curr_script_title = script_obj.get("title", "") if isinstance(script_obj, dict) else ""
        curr_yt_title = (metadata.get("TITLE") or metadata.get("title") or "")

        expression = (
            prompt_params.get("EXPRESSION")
            or prompt_params.get("TOPIC")
            or prompt_params.get("ROLEPLAY_SCENARIO")
            or content_meta.get("target_expression")
            or content_meta.get("topic")
            or sid
        )

        flagged, reasons = has_cliche_or_emoji(curr_script_title, curr_yt_title)

        if clean_emojis_only:
            new_script_title = sanitize_title(strip_emojis(curr_script_title))
            new_yt_title = sanitize_title(strip_emojis(curr_yt_title))
        else:
            new_script_title, new_yt_title = refine_and_upgrade_titles(
                sid, vtype, lang, expression, curr_script_title, curr_yt_title
            )

        if curr_script_title != new_script_title:
            flagged = True
            reasons.append("Chalkboard format alignment (Option B)")
        if curr_yt_title != new_yt_title and not any("YouTube" in r for r in reasons):
            flagged = True
            reasons.append("YouTube title alignment")

        if not flagged:
            continue

        record = {
            "id": sid,
            "vtype": vtype,
            "lang": lang,
            "expression": expression,
            "reasons": reasons,
            "old_script_title": curr_script_title,
            "old_yt_title": curr_yt_title,
            "file_path": sf,
        }

        record["new_script_title"] = new_script_title
        record["new_yt_title"] = new_yt_title
        flagged_records.append(record)

        if apply_changes:
            # Update state without touching status
            if isinstance(script_obj, dict):
                script_obj["title"] = new_script_title
                content_meta["script"] = script_obj
            state["content_metadata"] = content_meta

            metadata["TITLE"] = new_yt_title
            metadata["title"] = new_yt_title
            metadata["DESCRIPTION"] = strip_emojis(metadata.get("DESCRIPTION", ""))
            metadata["SHORT_DESCRIPTION"] = strip_emojis(metadata.get("SHORT_DESCRIPTION", ""))
            state["metadata"] = metadata

            # Preserve all statuses intact
            with open(sf, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            upgraded_count += 1

    return {
        "total_scanned": total_scanned,
        "flagged_count": len(flagged_records),
        "upgraded_count": upgraded_count,
        "flagged_records": flagged_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit and upgrade script and YouTube titles for singularity and zero emojis."
    )
    parser.add_argument("--apply", action="store_true", help="Apply title upgrades to state JSONs.")
    parser.add_argument("--check-only", action="store_true", help="Report flagged scripts without modifying files.")
    parser.add_argument("--clean-emojis-only", action="store_true", help="Strip emojis only without rewriting text.")
    parser.add_argument("-l", "--language", type=str, default=None, help="Target language (english, french, spanish, italian).")
    parser.add_argument("-t", "--video-type", type=str, default=None, help="Target video type (EXPRESSION, GAME, ROLEPLAY, FUN_FACTS).")
    parser.add_argument("-id", "--script-id", type=str, default=None, help="Target specific Script IDs (comma-separated).")
    args = parser.parse_args()

    target_ids = [s.strip().upper() for s in args.script_id.split(",")] if args.script_id else None
    apply_mode = args.apply and not args.check_only

    print("=" * 72)
    print("🎯 TITLE & METADATA SINGULARITY AUDITOR")
    print(f"• Mode: {'APPLY (Updating State Files)' if apply_mode else 'CHECK ONLY (Dry-Run)'}")
    print(f"• Clean Emojis Only: {args.clean_emojis_only}")
    print(f"• Target Language: {args.language or 'ALL'}")
    print(f"• Target Video Type: {args.video_type or 'ALL'}")
    print(f"• Target IDs: {', '.join(target_ids) if target_ids else 'ALL'}")
    print("=" * 72)

    results = audit_and_upgrade_titles(
        base_dir=BASE_DIR,
        apply_changes=apply_mode,
        clean_emojis_only=args.clean_emojis_only,
        target_lang=args.language,
        target_vtype=args.video_type,
        target_ids=target_ids,
    )

    print(f"\n📊 Results:")
    print(f"• Total State Files Scanned: {results['total_scanned']}")
    print(f"• Flagged (Clichés / Emojis): {results['flagged_count']}")
    if apply_mode:
        print(f"• Successfully Upgraded:     {results['upgraded_count']}")

    print("\nSample Preview (First 10 Flagged):")
    print("-" * 72)
    for idx, r in enumerate(results["flagged_records"][:10], start=1):
        print(f"[{idx:2d}] {r['id']} ({r['lang']} / {r['vtype']}) — {', '.join(r['reasons'])}")
        print(f"     Old Script Title: {repr(r['old_script_title'])}")
        print(f"     New Script Title: {repr(r['new_script_title'])}")
        print(f"     Old YT Title:     {repr(r['old_yt_title'])}")
        print(f"     New YT Title:     {repr(r['new_yt_title'])}\n")

    if not apply_mode and results["flagged_count"] > 0:
        print("💡 To apply these title upgrades cleanly to all state JSON files, run:")
        print("   py main/tools/upgrade_titles.py --apply")

    return 0


if __name__ == "__main__":
    sys.exit(main())
