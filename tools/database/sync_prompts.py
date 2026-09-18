"""
sync_prompts.py
Unified maintenance tool to validate, align, and sync all prompt queues across:
- EXPRESSION, GAME, and ROLEPLAY CSVs
- FUN_FACTS CSVs
- Central SQLite database (expressions.db)
"""

import csv
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.expression_db import get_expression_db

BASE_DIR = PROJECT_ROOT
LANGUAGES = [("english", "E"), ("french", "F"), ("spanish", "S"), ("italian", "I")]

def check_and_sync_language(lang: str, code: str) -> dict:
    d = BASE_DIR / "input" / "csv" / lang / "expressions_list"
    expr_p = d / f"{lang.upper()}_READY_PROMPTS_EXPRESSION.csv"
    game_p = d / f"{lang.upper()}_READY_PROMPTS_GAME.csv"
    role_p = d / f"{lang.upper()}_READY_PROMPTS_ROLEPLAY.csv"
    fun_p = d / f"{lang.upper()}_READY_PROMPTS_FUN_FACTS.csv"

    stats = {
        "lang": lang.capitalize(),
        "expression_count": 0,
        "game_count": 0,
        "roleplay_count": 0,
        "fun_facts_count": 0,
        "in_sync": True,
        "warnings": []
    }

    if not expr_p.exists():
        stats["warnings"].append(f"Missing {expr_p.name}")
        stats["in_sync"] = False
        return stats

    with open(expr_p, encoding="utf-8-sig") as f:
        expr_rows = list(csv.DictReader(f))
    stats["expression_count"] = len(expr_rows)

    # Check GAME
    game_rows = []
    if game_p.exists():
        with open(game_p, encoding="utf-8-sig") as f:
            game_rows = list(csv.DictReader(f))
    stats["game_count"] = len(game_rows)

    # Check ROLEPLAY
    role_rows = []
    if role_p.exists():
        with open(role_p, encoding="utf-8-sig") as f:
            role_rows = list(csv.DictReader(f))
    stats["roleplay_count"] = len(role_rows)

    # Check FUN_FACTS
    fun_rows = []
    if fun_p.exists():
        with open(fun_p, encoding="utf-8-sig") as f:
            fun_rows = list(csv.DictReader(f))
    stats["fun_facts_count"] = len(fun_rows)

    # Alignment check
    if not (len(expr_rows) == len(game_rows) == len(role_rows)):
        stats["in_sync"] = False
        stats["warnings"].append(
            f"Count mismatch: EXPRESSION={len(expr_rows)}, GAME={len(game_rows)}, ROLEPLAY={len(role_rows)}"
        )

    # Missing fields check in EXPRESSION
    for i, r in enumerate(expr_rows, start=1):
        if not r.get("ID"):
            stats["warnings"].append(f"Row {i} in {expr_p.name} has empty ID")
            stats["in_sync"] = False
        if not r.get("EXPRESSION"):
            stats["warnings"].append(f"Row {i} in {expr_p.name} has empty EXPRESSION")
            stats["in_sync"] = False

    return stats

def main():
    print("=" * 64)
    print("      SHORTS AUTOMATION - PROMPT & DATABASE SYNCHRONIZER")
    print("=" * 64)

    all_in_sync = True
    results = []

    for lang, code in LANGUAGES:
        res = check_and_sync_language(lang, code)
        results.append(res)
        if not res["in_sync"]:
            all_in_sync = False

    # Display table
    print(f"{'Language':<12} | {'EXPRESSION':<10} | {'GAME':<6} | {'ROLEPLAY':<8} | {'FUN_FACTS':<9} | {'Status'}")
    print("-" * 64)
    for r in results:
        status_str = "[OK] Aligned" if r["in_sync"] else "[!] Mismatch"
        print(f"{r['lang']:<12} | {r['expression_count']:<10} | {r['game_count']:<6} | {r['roleplay_count']:<8} | {r['fun_facts_count']:<9} | {status_str}")

    print("-" * 64)

    for r in results:
        if r["warnings"]:
            print(f"[{r['lang']}] Warnings:")
            for w in r["warnings"]:
                print(f"  - {w}")

    # Synchronize database
    print("\nSynchronizing expressions database (SQLite & master CSVs)...")
    try:
        db = get_expression_db()
        db.sync()
        seeded = db.seed_from_input_csvs()
        db.export_to_csv()
        stats = db.get_stats()
        print(f"[OK] Database in sync! Total prompts in DB: {stats['total']} (PENDING: {stats['pending']}, DONE: {stats['done']})")
    except Exception as e:
        print(f"Error syncing database: {e}")
        return 1

    if all_in_sync:
        print("\nAll 4 languages and all formats are 100% aligned and ready for video generation!\n")
    else:
        print("\nPlease resolve any reported mismatches above.\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
