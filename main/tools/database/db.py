#!/usr/bin/env python3
"""
tools/db.py — CLI management utility for the Expression Database.

Usage examples:
  py tools/db.py stats
  py tools/db.py list --status PENDING
  py tools/db.py list --lang english --status DONE
  py tools/db.py status EE01
  py tools/db.py set-status EE01 DONE
  py tools/db.py set-status EE01 PENDING
  py tools/db.py sync
"""
import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.expression_db import get_expression_db


def cmd_stats(db, args):
    stats = db.get_stats()
    print("\n" + "=" * 55)
    print("         EXPRESSION DATABASE OVERVIEW")
    print("=" * 55)
    print(f"Total Expressions : {stats['total']}")
    print(f"  - DONE          : {stats['done']}")
    print(f"  - PENDING       : {stats['pending']}")
    print("-" * 55)
    print("Breakdown by Language:")
    for lang, counts in sorted(stats["by_language"].items()):
        print(f"  {lang.capitalize():<10} : Total: {counts['total']:<4} | DONE: {counts['DONE']:<4} | PENDING: {counts['PENDING']}")
    print("=" * 55)
    print(f"Database Directory: {db.database_dir}")
    print(f"SQLite DB File    : {db.db_path}\n")


def cmd_list(db, args):
    expressions = db.list_expressions(
        status=args.status,
        language=args.language,
        video_type=args.type,
    )
    if not expressions:
        print(f"No expressions found matching criteria (status={args.status}, lang={args.language}).")
        return

    print(f"\nFound {len(expressions)} expression(s):")
    print("-" * 80)
    print(f"{'ID':<6} {'STATUS':<9} {'LANG':<8} {'TYPE':<12} {'EXPRESSION'}")
    print("-" * 80)
    for r in expressions:
        expr = r["expression"]
        if len(expr) > 42:
            expr = expr[:39] + "..."
        print(f"{r['id']:<6} {r['status']:<9} {r['language']:<8} {r['video_type']:<12} {expr}")
    print("-" * 80 + "\n")


def cmd_status(db, args):
    rec = db.get_expression(args.id)
    if not rec:
        print(f"Expression ID '{args.id}' not found in database.", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 50)
    print(f"Expression Record: {rec['id']}")
    print("=" * 50)
    print(f"  Status     : {rec['status']}")
    print(f"  Expression : {rec['expression']}")
    print(f"  Context    : {rec['context']}")
    print(f"  Language   : {rec['language']}")
    print(f"  Video Type : {rec['video_type']}")
    print(f"  Updated At : {rec['updated_at']}")
    print("=" * 50 + "\n")


def cmd_set_status(db, args):
    new_status = args.status.strip().upper()
    if new_status not in ("DONE", "PENDING"):
        print(f"Warning: Unusual status '{new_status}'. Standard values are 'DONE' or 'PENDING'.")

    rec = db.get_expression(args.id)
    if not rec:
        print(f"Error: Expression ID '{args.id}' not found in database.", file=sys.stderr)
        sys.exit(1)

    old_status = rec["status"]
    if db.set_status(args.id, new_status):
        print(f"[OK] Updated {args.id.upper()} status: {old_status} -> {new_status}")
        print(f"Auto-synced to: {db.get_csv_path(rec['language'])}")
    else:
        print(f"Failed to update status for {args.id}.", file=sys.stderr)
        sys.exit(1)


def cmd_sync(db, args):
    print("Syncing database with language CSVs and scanning input queues...")
    db.sync()
    seeded = db.seed_from_input_csvs()
    db.export_to_csv()
    stats = db.get_stats()
    print(f"[OK] Sync complete. Newly seeded expressions: {seeded}")
    print(f"Total in Database: {stats['total']} (DONE: {stats['done']}, PENDING: {stats['pending']})")
    print(f"Editable CSVs: {db.database_dir}/*_expressions.csv")


def main():
    parser = argparse.ArgumentParser(description="Expression Database CLI Management Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # stats
    sub_stats = subparsers.add_parser("stats", help="Show database overview and counts")
    sub_stats.set_defaults(func=cmd_stats)

    # list
    sub_list = subparsers.add_parser("list", help="List expressions with optional filters")
    sub_list.add_argument("--status", choices=["DONE", "PENDING", "done", "pending"], help="Filter by status")
    sub_list.add_argument("--lang", "--language", dest="language", help="Filter by language (e.g. english, french)")
    sub_list.add_argument("--type", choices=["expression", "game", "roleplay", "fun_facts"], help="Filter by video type")
    sub_list.set_defaults(func=cmd_list)

    # status
    sub_status = subparsers.add_parser("status", help="Get details and status for a single expression ID")
    sub_status.add_argument("id", help="Expression ID (e.g. EE01, FR02)")
    sub_status.set_defaults(func=cmd_status)

    # set-status
    sub_set = subparsers.add_parser("set-status", help="Change status of an expression (e.g. set-status EE01 DONE)")
    sub_set.add_argument("id", help="Expression ID (e.g. EE01, FR02)")
    sub_set.add_argument("status", help="New status (DONE or PENDING)")
    sub_set.set_defaults(func=cmd_set_status)

    # sync
    sub_sync = subparsers.add_parser("sync", help="Force two-way sync between CSV and SQLite, seeding any new prompts")
    sub_sync.set_defaults(func=cmd_sync)

    args = parser.parse_args()
    db = get_expression_db()

    if not args.command:
        # Default behavior if no subcommand given: show stats
        cmd_stats(db, args)
    else:
        args.func(db, args)


if __name__ == "__main__":
    main()
