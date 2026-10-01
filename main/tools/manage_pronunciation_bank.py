"""Pronunciation Bank Management & Quality Audit Tool.

CLI utility to inspect, audit, import, and validate verified heteronym studio clips.
Part of Option B Architecture (Phase 4: Curated Production Bank).

Usage:
  py main/tools/manage_pronunciation_bank.py --status
  py main/tools/manage_pronunciation_bank.py --audit
  py main/tools/manage_pronunciation_bank.py --import <file> --word <w> --role <noun|verb>
  py main/tools/manage_pronunciation_bank.py --export-json <output.json>
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console for IPA characters
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Setup search path
TOOL_DIR = Path(__file__).resolve().parent
MAIN_DIR = TOOL_DIR.parent
PROJECT_ROOT = MAIN_DIR.parent
for p in [str(PROJECT_ROOT), str(MAIN_DIR), str(MAIN_DIR / "core"), str(MAIN_DIR / "video_creation" / "_B_voice_generation")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import soundfile as sf
from video_creation._B_voice_generation.core.pronunciation_bank import (
    HETERONYM_REGISTRY,
    get_bank_directory,
    get_heteronym_data,
    get_pronunciation_clip,
    has_pronunciation_clip,
    list_available_clips,
    save_pronunciation_clip,
)
from video_creation._B_voice_generation.core.acoustic_evaluator import (
    evaluate_acoustic_prominence,
)


def print_status(bank_dir: Path = None) -> None:
    """Prints a clear tabular status of all heteronyms and their audio coverage."""
    storage = get_bank_directory(bank_dir)
    coverage = list_available_clips(storage)
    total_slots = len(HETERONYM_REGISTRY) * 2
    filled_slots = sum((1 if v["noun"] else 0) + (1 if v["verb"] else 0) for v in coverage.values())

    print("=" * 75)
    print(f"HETERONYM PRONUNCIATION BANK STATUS (Storage: {storage})")
    print("=" * 75)
    print(f"{'WORD':<14} | {'NOUN CLIP':<15} | {'VERB CLIP':<15} | {'IPA (NOUN / VERB)':<25}")
    print("-" * 75)

    for word, roles in sorted(coverage.items()):
        entry = HETERONYM_REGISTRY[word]
        noun_status = "[READY]" if roles["noun"] else "[MISSING]"
        verb_status = "[READY]" if roles["verb"] else "[MISSING]"
        ipa_display = f"{entry['noun']['ipa']} / {entry['verb']['ipa']}"
        print(f"{word:<14} | {noun_status:<15} | {verb_status:<15} | {ipa_display:<25}")

    pct = (filled_slots / total_slots) * 100
    print("=" * 75)
    print(f"Coverage: {filled_slots}/{total_slots} clips available ({pct:.1f}% complete)")
    print("=" * 75)


def audit_bank(bank_dir: Path = None) -> int:
    """Audits all existing clips in the bank for acoustic contrast and duration."""
    storage = get_bank_directory(bank_dir)
    print("=" * 75)
    print(f"AUDITING PRONUNCIATION BANK ACOUSTICS (Storage: {storage})")
    print("=" * 75)

    clips_found = 0
    passed_audit = 0

    for word, roles in sorted(HETERONYM_REGISTRY.items()):
        for role in ["noun", "verb"]:
            clip = get_pronunciation_clip(word, role, bank_dir=storage)
            if not clip:
                continue

            clips_found += 1
            meta = roles[role]
            expected_carrier = meta["carrier"]
            expected_cased = meta["cased"]

            try:
                data, sr = sf.read(str(clip))
                dur = len(data) / sr
                score, details = evaluate_acoustic_prominence(
                    audio_path=clip,
                    target_words=[word],
                    text_context=expected_carrier
                )

                occs = details.get("occurrences", [])
                ratio = occs[0]["ratio"] if occs else score
                ratio_label = f"Ratio={ratio:.2f}"

                # Quality threshold: ratio >= 1.0 (correct prominence direction)
                if score >= 1.0 or ratio >= 1.0:
                    status = "[PASS]"
                    passed_audit += 1
                else:
                    status = "[WARN]"

                print(f"{status} {word:<10} ({role:<4}): dur={dur:.2f}s | Score={score:.2f} | {ratio_label} | file={clip.name}")

            except Exception as exc:
                print(f"[FAIL] {word:<10} ({role:<4}): Error reading audio ({exc})")

    print("-" * 75)
    print(f"Audit Summary: {passed_audit}/{clips_found} verified clips passed acoustic quality checks.")
    print("=" * 75)
    return 0 if (clips_found == 0 or passed_audit == clips_found) else 1


def import_clip_cli(file_path: str, word: str, role: str, bank_dir: Path = None, force: bool = False) -> int:
    """Imports and validates an external audio file into the bank."""
    src = Path(file_path)
    if not src.exists():
        print(f"Error: Source file {src} does not exist.", file=sys.stderr)
        return 1

    clean_word = word.strip().lower()
    clean_role = role.strip().lower()

    if clean_word not in HETERONYM_REGISTRY:
        print(f"Error: Word '{clean_word}' is not in the registered heteronym list.", file=sys.stderr)
        return 1

    if clean_role not in ["noun", "verb"]:
        print(f"Error: Role must be 'noun' or 'verb', got '{clean_role}'.", file=sys.stderr)
        return 1

    # Validate audio with acoustic evaluator
    meta = HETERONYM_REGISTRY[clean_word][clean_role]
    score, details = evaluate_acoustic_prominence(src, [clean_word], meta["carrier"])

    if score < 0.8 and not force:
        print(f"Quality Warning: Audio scored low ({score:.2f} < 0.80). Use --force to import anyway.", file=sys.stderr)
        return 1

    dest = save_pronunciation_clip(clean_word, clean_role, src, bank_dir=bank_dir, overwrite=True)
    print(f"Successfully imported and verified '{clean_word}' ({clean_role}) -> {dest} (Score: {score:.2f})")
    return 0


def export_json_cli(output_file: str, bank_dir: Path = None) -> int:
    """Exports registry metadata and clip availability to a structured JSON file."""
    storage = get_bank_directory(bank_dir)
    coverage = list_available_clips(storage)

    export_data = {}
    for word, meta in HETERONYM_REGISTRY.items():
        export_data[word] = {
            "metadata": meta,
            "clips": {
                "noun": {
                    "available": coverage[word]["noun"],
                    "path": str(get_pronunciation_clip(word, "noun", storage)) if coverage[word]["noun"] else None
                },
                "verb": {
                    "available": coverage[word]["verb"],
                    "path": str(get_pronunciation_clip(word, "verb", storage)) if coverage[word]["verb"] else None
                }
            }
        }

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2)

    print(f"Successfully exported heteronym bank metadata to {out_path}")
    return 0


def populate_with_kokoro(bank_dir: Path = None, voice: str = "af_bella", force: bool = False) -> int:
    """Uses Kokoro-82M ONNX precision engine to synthesize any missing heteronym clips."""
    try:
        from video_creation._B_voice_generation.core.kokoro_engine import get_kokoro_engine
    except (ImportError, ModuleNotFoundError):
        from core.kokoro_engine import get_kokoro_engine

    engine = get_kokoro_engine()
    if not engine.is_ready:
        print("Error: Kokoro-82M engine is not available or model files missing.", file=sys.stderr)
        return 1

    storage = get_bank_directory(bank_dir)
    print(f"Populating Heteronym Bank at {storage} using Kokoro-82M (Voice: {voice})...")

    generated_count = 0
    skipped_count = 0

    for word, data in sorted(HETERONYM_REGISTRY.items()):
        for role in ["noun", "verb"]:
            already_has = has_pronunciation_clip(word, role, storage)
            if already_has and not force:
                skipped_count += 1
                continue

            target_path = storage / f"{word}_{role}.wav"
            res = engine.generate_heteronym_demonstration(word, role, target_path, voice=voice)
            if res and res.exists():
                generated_count += 1
                print(f"  [+] Generated {word:<12} ({role:<4}) -> {target_path.name}")
            else:
                print(f"  [-] Failed to generate {word} ({role})")

    print(f"\nPopulation complete! Generated {generated_count} clip(s), skipped {skipped_count} existing clip(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LingoVerse Pronunciation Bank Tool")
    parser.add_argument("--status", action="store_true", help="Display coverage status of heteronym audio clips")
    parser.add_argument("--audit", action="store_true", help="Run acoustic quality audit on all existing clips")
    parser.add_argument("--populate-kokoro", action="store_true", help="Batch-synthesize all missing clips using Kokoro-82M")
    parser.add_argument("--voice", type=str, default="af_bella", help="Voice ID for Kokoro generation (default: af_bella)")
    parser.add_argument("--import-clip", type=str, default=None, help="Path to audio file to import into bank")
    parser.add_argument("--word", type=str, default=None, help="Target heteronym word for import")
    parser.add_argument("--role", type=str, choices=["noun", "verb"], default=None, help="Grammatical role for import")
    parser.add_argument("--force", action="store_true", help="Force overwrite or import even if existing/low score")
    parser.add_argument("--export-json", type=str, default=None, help="Path to export metadata JSON")
    parser.add_argument("--bank-dir", type=str, default=None, help="Custom bank storage directory")
    args = parser.parse_args()

    bank_dir = Path(args.bank_dir) if args.bank_dir else None

    if args.status:
        print_status(bank_dir)
        return 0

    if args.audit:
        return audit_bank(bank_dir)

    if args.populate_kokoro:
        return populate_with_kokoro(bank_dir, voice=args.voice, force=args.force)

    if args.import_clip:
        if not args.word or not args.role:
            print("Error: --word and --role are required when using --import-clip", file=sys.stderr)
            return 1
        return import_clip_cli(args.import_clip, args.word, args.role, bank_dir, args.force)

    if args.export_json:
        return export_json_cli(args.export_json, bank_dir)

    # Default action if no flags provided
    print_status(bank_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

