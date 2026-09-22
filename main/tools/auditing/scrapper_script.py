import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure shorts_automation directory is in sys.path (needed for embedded python and arbitrary CWDs)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import LANG_MAP, TYPE_MAP, resolve_lang_and_type
from config import SCRIPTS_TO_SEE_DIR

DEFAULT_LANGUAGES = ["english", "french", "italian", "spanish"]
DEFAULT_TYPES = ["expression", "game", "roleplay", "fun_facts"]

CANONICAL_SECTION_ORDER = [
    "hook",
    "context",
    "setup",
    "mystery",
    "clues",
    "content",
    "dialogue",
    "dialogue_part_1",
    "dialogue_part_2",
    "dialogue_part_3",
    "dialogue_part_4",
    "comparison_a",
    "comparison_b",
    "fact_1",
    "fact_2",
    "fact_3",
    "item_3",
    "item_2",
    "item_1",
    "challenge",
    "pressure",
    "thinking_time",
    "discovery",
    "example",
    "reveal",
    "answer",
    "surprise",
    "explanation",
    "core_learning",
    "emphasis",
    "interrupt",
    "payoff",
    "loop_trigger",
    "cta",
]


def clean_text(text: str) -> str:
    """Normalizes escape sequences, unicode entities, and typography artifacts."""
    if not text:
        return ""

    # 1. Unescape unicode hex escapes like \u2019 or \\u2019
    text = re.sub(
        r"\\+u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text
    )

    # 2. Normalize smart quotes and dashes to clean standard characters
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2014", " - ").replace("\u2013", "-")
    text = text.replace("\u2026", "...")

    # 3. Handle literal escaped characters
    text = text.replace("\\r\\n", "\n").replace("\\n", "\n")
    text = text.replace('\\"', '"').replace("\\'", "'")

    # 4. Collapse consecutive carriage returns / trailing whitespace
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def natural_sort_key(s: Any) -> List[Any]:
    """Splits string into numeric and non-numeric parts for natural alphanumeric sorting.
    e.g. 'EE09' -> ['ee', 9], 'EE10' -> ['ee', 10], 'EE99' -> ['ee', 99], 'EE100' -> ['ee', 100]
    """
    return [
        int(chunk) if chunk.isdigit() else chunk.lower()
        for chunk in re.split(r"(\d+)", str(s or ""))
        if chunk
    ]


def extract_expression_from_state(state: Dict[str, Any]) -> str:
    """Extracts the target expression or topic from state metadata with robust fallbacks."""
    content_meta = state.get("content_metadata") or {}
    prompt_params = state.get("prompt_params") or {}

    # 1. Direct target expression or topic
    expr = (
        content_meta.get("target_expression")
        or prompt_params.get("TOPIC")
        or prompt_params.get("EXPRESSION")
    )
    if expr and str(expr).strip() and str(expr).strip().upper() != "NONE":
        return str(expr).strip()

    # 2. Content topic (frequently used in Roleplay/Game)
    topic = content_meta.get("topic")
    if topic and str(topic).strip() and str(topic).strip().upper() != "NONE":
        return str(topic).strip()

    # 3. Quoted phrase inside roleplay scenario (e.g. 'friend says "Break a leg!"')
    scenario = prompt_params.get("ROLEPLAY_SCENARIO") or ""
    quoted = re.findall(r'["\']([^"\']{2,40})["\']', str(scenario))
    if quoted:
        return quoted[-1].strip("!?. ")

    # 4. Fallback to category / subject
    subject = (
        prompt_params.get("SUBJECT") or content_meta.get("category") or ""
    )
    return str(subject).strip()


def parse_raw_script(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Retrieves script dictionary from content_metadata.script or parses script_text JSON."""
    content_meta = state.get("content_metadata") or {}
    script_obj = content_meta.get("script")

    if isinstance(script_obj, dict) and script_obj:
        return script_obj

    script_text = state.get("script_text")
    if not script_text:
        return None

    st = str(script_text).strip()
    if st.startswith("```json"):
        st = st[7:]
    if st.startswith("```"):
        st = st[3:]
    if st.endswith("```"):
        st = st[:-3]
    st = st.strip()

    try:
        parsed = json.loads(st)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # Fallback: treat raw string as a single body
    return {"body": st}


def format_script_content(
    script_dict: Dict[str, Any],
    include_tags: bool = False,
    include_title: bool = False,
) -> str:
    """Formats and cleans script sections into readable continuous text or tagged dialogue."""
    if not script_dict:
        return ""

    title = clean_text(str(script_dict.get("title", "")))

    # Order keys according to canonical shorts sequence, keeping custom keys at end
    lower_map = {k.lower(): (k, v) for k, v in script_dict.items()}

    ordered_keys = []
    for k in CANONICAL_SECTION_ORDER:
        if k in lower_map:
            ordered_keys.append(lower_map[k][0])

    for k in script_dict:
        if k.lower() not in CANONICAL_SECTION_ORDER and k.lower() != "title":
            if k not in ordered_keys:
                ordered_keys.append(k)

    sections_text = []

    if include_title and title:
        sections_text.append(f"Title: {title}" if include_tags else title)

    for key in ordered_keys:
        val = script_dict[key]
        cleaned_val = clean_text(str(val))
        if not cleaned_val:
            continue

        if include_tags:
            tag_name = key.replace("_", " ").upper()
            sections_text.append(f"[{tag_name}]\n{cleaned_val}")
        else:
            sections_text.append(cleaned_val)

    return "\n\n".join(sections_text)


def process_scripts(
    base_dir: Path,
    output_dir: Optional[Path] = None,
    target_languages: Optional[List[str]] = None,
    target_types: Optional[List[str]] = None,
    include_tags: bool = False,
    include_title: bool = False,
) -> Dict[str, int]:
    """Scrapes state files and generates structured CSVs partitioned by language and kind."""
    state_dir = base_dir / "state"
    out_base = (
        output_dir if output_dir else (SCRIPTS_TO_SEE_DIR if base_dir == PROJECT_ROOT else base_dir / "output" / "scripts_to_see")
    )

    languages = [l.lower() for l in (target_languages or DEFAULT_LANGUAGES)]
    types = [t.lower() for t in (target_types or DEFAULT_TYPES)]

    # Pre-create all folders for requested languages and video types
    for lang in languages:
        for vtype in types:
            (out_base / lang / vtype).mkdir(parents=True, exist_ok=True)

    # Collect and group scripts by (language, video_type)
    collected: Dict[Tuple[str, str], List[Dict[str, str]]] = {
        (l, t): [] for l in languages for t in types
    }
    seen_ids: Dict[Tuple[str, str], set] = {
        (l, t): set() for l in languages for t in types
    }

    if state_dir.exists():
        for state_file in sorted(state_dir.rglob("script_*.json")):
            # Ignore non-files and sample templates (e.g. script_state.sample.json)
            if not state_file.is_file() or ".sample" in state_file.name:
                continue

            try:
                with state_file.open("r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception as e:
                print(f"[Warning] Failed to read {state_file.name}: {e}")
                continue

            script_id = state.get("id") or state_file.stem.replace(
                "script_", ""
            )
            lang, vtype = resolve_lang_and_type(script_id, state)
            lang = lang.lower()
            vtype = vtype.lower()

            # Filter if specific languages or types were requested
            if lang not in languages or vtype not in types:
                continue

            key = (lang, vtype)
            if key not in collected:
                collected[key] = []
                seen_ids[key] = set()

            # Deduplicate by script_id per category
            if script_id in seen_ids[key]:
                continue
            seen_ids[key].add(script_id)

            expression = extract_expression_from_state(state)
            script_dict = parse_raw_script(state)
            formatted_script = (
                format_script_content(
                    script_dict,
                    include_tags=include_tags,
                    include_title=include_title,
                )
                if script_dict
                else ""
            )

            collected[key].append(
                {
                    "ID": script_id,
                    "expression": expression,
                    "script": formatted_script,
                }
            )


    stats = {}
    print("=" * 65)
    print("Shorts Automation - Script Scraper")
    print("=" * 65)
    print(f"State Root  : {state_dir}")
    print(f"Output Root : {out_base}")
    print(f"Options     : include_tags={include_tags}, include_title={include_title}")
    print("-" * 65)

    for (lang, vtype), rows in collected.items():
        dest_folder = out_base / lang / vtype
        dest_csv = dest_folder / f"{lang}_{vtype}_scripts.csv"

        # Sort rows naturally by script ID (e.g. EE01, EE02 ... EE99, EE100)
        rows_sorted = sorted(rows, key=lambda r: natural_sort_key(r["ID"]))

        with dest_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["ID", "expression", "script"],
                quoting=csv.QUOTE_MINIMAL,
            )
            writer.writeheader()
            for row in rows_sorted:
                writer.writerow(row)

        stats[f"{lang}/{vtype}"] = len(rows_sorted)
        status_msg = (
            f"Saved {len(rows_sorted)} script(s)"
            if rows_sorted
            else "Created empty CSV (0 scripts found)"
        )
        try:
            rel_path = dest_csv.relative_to(base_dir)
        except ValueError:
            rel_path = dest_csv
        print(f"[{lang.capitalize()}/{vtype.upper():<10}] -> {rel_path} ({status_msg})")

    total_scraped = sum(stats.values())
    print("=" * 65)
    print(
        f"Completed: Processed {total_scraped} script(s) across {len(collected)} category folders."
    )
    print("=" * 65)

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrapes and cleans generated video scripts into review CSVs partitioned by language and kind."
    )
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        nargs="+",
        choices=DEFAULT_LANGUAGES,
        help="Filter by language(s) (english, french, italian, spanish). Default: all.",
    )
    parser.add_argument(
        "--type",
        "-t",
        type=str,
        nargs="+",
        choices=DEFAULT_TYPES,
        help="Filter by video type(s) (expression, game, roleplay). Default: all.",
    )
    parser.add_argument(
        "--include-tags",
        action="store_true",
        help="Include audio section headers (e.g. [HOOK], [CHALLENGE]) instead of continuous clean text.",
    )
    parser.add_argument(
        "--include-title",
        action="store_true",
        help="Prepend the script title at the top of the script cell.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory. Default: output/scripts_to_see.",
    )

    args = parser.parse_args()
    base_dir = PROJECT_ROOT
    out_dir = Path(args.output_dir).resolve() if args.output_dir else None

    process_scripts(
        base_dir=base_dir,
        output_dir=out_dir,
        target_languages=args.language,
        target_types=args.type,
        include_tags=args.include_tags,
        include_title=args.include_title,
    )
    return 0


if __name__ == "__main__":
    main()
