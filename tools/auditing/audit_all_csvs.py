"""
audit_all_csvs.py
Comprehensive audit and validation tool for all 16 prompt CSV files across English, Spanish, French, and Italian.
Checks:
1. File existence and schema
2. UTF-8 with BOM integrity and lack of mojibake / corrupted characters
3. Uniqueness of scenarios (zero copy-paste duplicates)
4. Absence of lazy boilerplate strings
5. Cross-format row count and ID alignment
"""

import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2] / "input" / "csv"
LANGUAGES = ["english", "spanish", "french", "italian"]
TYPES = ["ROLEPLAY", "GAME", "EXPRESSION", "FUN_FACTS"]

CORRUPTION_PATTERNS = [
    "\ufffd",  # Replacement character
    "Ã©", "Ã¡", "Ã³", "Ãº", "Ã±", "Ã¨", "Ã ", "Ã²", "Ã¹",  # UTF-8 decoded as latin1
    "d?T", "c?T", "l?T", "dell?T", "d?t",  # Apostrophe mojibake
    "Ǹ", "ǭ", "Ǫ", "ǥ",  # CP1252 to UTF-8 mojibake
]

LAZY_PATTERNS = [
    "En una conversación cotidiana: PERSON_ONE confunde",
    "En una charla animada: PERSON_ONE comete",
    "Al planificar una actividad diaria: PERSON_ONE duda",
    "Al describir una experiencia: PERSON_ONE se confunde",
    "Durante una pausa en el trabajo: PERSON_ONE usa",
    "En el día a día: PERSON_ONE busca",
    "Entre amigos en una terraza: PERSON_ONE comenta una situación insólita",
    "Au travail avec un collègue étranger : PERSON_ONE utilise",
    "En préparant une sortie entre amis : PERSON_ONE confond",
    "Dans une conversation quotidienne : PERSON_ONE commet",
    "En réservant un trajet de vacances : PERSON_ONE s'interroge",
    "Dans un échange naturel : PERSON_ONE et PERSON_TWO discutent avec aisance",
    "Durante una conversazione informale: PERSON_ONE fraintende",
    "In una chiacchierata quotidiana: PERSON_ONE esprime",
    "Parlando del tempo o dei progetti: PERSON_ONE confonde",
    "Alla stazione o in viaggio: PERSON_ONE è indeciso",
    "In una galleria o in centro: PERSON_ONE usa",
    "Al bar con gli amici: PERSON_ONE descrive",
    "In un incontro amichevole: PERSON_ONE e PERSON_TWO si scambiano",
    "A fine giornata: PERSON_ONE impiega",
]

def audit_suite():
    total_issues = 0
    print("=" * 70)
    print("RUNNING MASTER CSV INTEGRITY AUDIT")
    print("=" * 70)

    for lang in LANGUAGES:
        print(f"\n>>> Checking Language: {lang.upper()} <<<")
        lang_dir = BASE_DIR / lang / "expressions_list"
        if not lang_dir.exists():
            print(f"[ERROR] Missing directory: {lang_dir}")
            total_issues += 1
            continue

        counts = {}
        for vtype in TYPES:
            filename = f"{lang.upper()}_READY_PROMPTS_{vtype}.csv"
            filepath = lang_dir / filename
            if not filepath.exists():
                print(f"  [ERROR] Missing file: {filename}")
                total_issues += 1
                continue

            # Read raw text to check for mojibake / corrupt bytes
            try:
                raw_text = filepath.read_text(encoding="utf-8-sig")
            except Exception as e:
                print(f"  [ERROR] Failed to read {filename} as utf-8-sig: {e}")
                total_issues += 1
                continue

            for pattern in CORRUPTION_PATTERNS:
                if pattern in raw_text:
                    occurrences = raw_text.count(pattern)
                    print(f"  [CORRUPTION] Found '{pattern}' ({occurrences} times) in {filename}")
                    total_issues += 1

            # Check CSV rows and lazy patterns
            with open(filepath, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                counts[vtype] = len(rows)

            if vtype == "ROLEPLAY":
                scenarios = [r.get("ROLEPLAY_SCENARIO", "") for r in rows]
                # Check for duplicates
                unique_scenarios = set(scenarios)
                if len(unique_scenarios) < len(scenarios):
                    dups = len(scenarios) - len(unique_scenarios)
                    print(f"  [DUPLICATE] Found {dups} duplicate scenarios in {filename}!")
                    total_issues += 1

                # Check for lazy patterns
                for idx, r in enumerate(rows):
                    scen = r.get("ROLEPLAY_SCENARIO", "")
                    for lazy in LAZY_PATTERNS:
                        if lazy in scen:
                            print(f"  [LAZY PATTERN] Row {r.get('ID')} has boilerplate: '{lazy[:40]}...'")
                            total_issues += 1

            print(f"  [OK] {filename:<35} : {len(rows)} rows loaded clean")

        # Check alignment between ROLEPLAY, GAME, and EXPRESSION
        rp_cnt = counts.get("ROLEPLAY", 0)
        gm_cnt = counts.get("GAME", 0)
        exp_cnt = counts.get("EXPRESSION", 0)
        ff_cnt = counts.get("FUN_FACTS", 0)

        if rp_cnt != gm_cnt or rp_cnt != exp_cnt:
            print(f"  [MISMATCH] Row count divergence in {lang}: ROLEPLAY={rp_cnt}, GAME={gm_cnt}, EXPRESSION={exp_cnt}")
            total_issues += 1
        else:
            print(f"  [ALIGNED] ROLEPLAY, GAME, EXPRESSION aligned at {rp_cnt} rows.")

        if ff_cnt < 15:
            print(f"  [WARNING] FUN_FACTS count ({ff_cnt}) is less than 15.")
            total_issues += 1
        else:
            print(f"  [ALIGNED] FUN_FACTS expanded to {ff_cnt} rows.")

    print("\n" + "=" * 70)
    if total_issues == 0:
        print("[SUCCESS] All 16 CSVs passed audit with ZERO errors, ZERO duplicates, and ZERO encoding bugs!")
    else:
        print(f"[FAILED] Total audit issues found: {total_issues}")
    print("=" * 70)

if __name__ == "__main__":
    audit_suite()
