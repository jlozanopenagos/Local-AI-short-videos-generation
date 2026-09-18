#!/usr/bin/env python3
"""
video_creation/_D_music_generation/main.py

Standing Music Bank Generator for LingoVerse Shorts Automation.
Produces and manages a rich library of distinct, loopable 30s background jams
in D:\\AI\\output\\bank_music/<language>/<video_type>/ tailored to the emotional triggers
of each video format and target language.
"""

import argparse
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root and video_creation directory to path
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
for p in [str(PROJECT_ROOT), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import (
    BASE_DIR,
    OUTPUT_DIR,
    BANK_MUSIC_DIR,
    require_services
)

from prompts_catalog import (
    MUSIC_BANK_CATALOG,
    get_bank_categories,
    get_prompts_for_category
)

# Optional heavy model imports inside loader function
def load_musicgen_model(device_str: str = "cuda"):
    """Loads MusicGen model and processor."""
    # pyrefly: ignore [missing-import]
    import torch
    # pyrefly: ignore [missing-import]
    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    if device_str == "cuda" and not torch.cuda.is_available():
        device_str = "cpu"

    device = torch.device(device_str)
    print(f"\n[MusicGen] Loading 'facebook/musicgen-small' on {device}...")
    processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
    model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small").to(device)
    print("[MusicGen] Model successfully loaded!\n")
    return processor, model, device


def generate_audio_clip(processor, model, device, prompt_text: str, output_path: Path, max_tokens: int = 1500):
    """
    Generates a ~30-second audio clip using MusicGen-small and writes to output_path.
    max_tokens=1500 corresponds to ~30 seconds (maximum positional embedding).
    """
    # pyrefly: ignore [missing-import]
    import scipy.io.wavfile as wavfile
    # pyrefly: ignore [missing-import]
    import torch

    inputs = processor(
        text=[prompt_text],
        padding=True,
        return_tensors="pt",
    ).to(device)

    with torch.no_grad():
        audio_values = model.generate(**inputs, max_new_tokens=max_tokens)

    sampling_rate = model.config.audio_encoder.sampling_rate
    audio_data = audio_values[0, 0].cpu().numpy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(output_path), sampling_rate, audio_data)
    print(f"  [SAVED] -> {output_path.name}")


def ensure_bank_directories_and_catalogs(base_bank_dir: Path) -> Dict[str, Dict[str, Path]]:
    """
    Creates all 16 category subdirectories:
    <base_bank_dir>/<language>/<video_type>/
    and writes/updates bank_catalog.json in each directory.
    """
    base_bank_dir.mkdir(parents=True, exist_ok=True)
    folder_map: Dict[str, Dict[str, Path]] = {}

    for lang, vtype in get_bank_categories():
        target_dir = base_bank_dir / lang / vtype
        target_dir.mkdir(parents=True, exist_ok=True)

        folder_map.setdefault(lang, {})[vtype] = target_dir

        # Build catalog metadata for this category
        prompts = get_prompts_for_category(lang, vtype)
        catalog_file = target_dir / "bank_catalog.json"

        catalog_entries = []
        for p in prompts:
            audio_path = target_dir / p["filename"]
            entry = {
                "id": p["id"],
                "filename": p["filename"],
                "name": p["name"],
                "emotion_slug": p["emotion_slug"],
                "matching_emotions": p["matching_emotions"],
                "bpm": p["bpm"],
                "style": p["style"],
                "instrumentation": p["instrumentation"],
                "prompt": p["prompt"],
                "exists_on_disk": audio_path.exists(),
                "file_path": str(audio_path) if audio_path.exists() else ""
            }
            catalog_entries.append(entry)

        with catalog_file.open("w", encoding="utf-8") as f:
            json.dump({
                "language": lang,
                "video_type": vtype,
                "total_tracks": len(catalog_entries),
                "tracks": catalog_entries
            }, f, indent=4, ensure_ascii=False)

    return folder_map


def print_bank_status(base_bank_dir: Path):
    """Prints a clear overview table of the Standing Music Bank."""
    print("\n" + "=" * 76)
    print(f"       STANDING MUSIC BANK OVERVIEW ({base_bank_dir})")
    print("=" * 76)
    print(f"{'Language':<12} | {'Expression':<12} | {'Roleplay':<12} | {'Game':<12} | {'Fun Facts':<12} | {'Total':<8}")
    print("-" * 76)

    grand_total = 0
    for lang in ["english", "french", "spanish", "italian"]:
        row_counts = []
        lang_total = 0
        for vt in ["expression", "roleplay", "game", "fun_facts"]:
            cat_dir = base_bank_dir / lang / vt
            count = len(list(cat_dir.glob("*.wav"))) if cat_dir.exists() else 0
            row_counts.append(f"{count}/10")
            lang_total += count
            grand_total += count
        print(f"{lang.capitalize():<12} | {row_counts[0]:<12} | {row_counts[1]:<12} | {row_counts[2]:<12} | {row_counts[3]:<12} | {lang_total:<8}")

    print("=" * 76)
    print(f"Grand Total Jams Ready in Bank: {grand_total} / 160\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and manage the Standing Music Bank for LingoVerse Shorts.")
    parser.add_argument(
        "--language",
        type=str,
        default="all",
        choices=["all", "english", "french", "spanish", "italian"],
        help="Target language (default: all)"
    )
    parser.add_argument(
        "--video-type",
        type=str,
        default="all",
        choices=["all", "expression", "roleplay", "game", "fun_facts"],
        help="Target video type (default: all)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum tracks to generate per category (default: 10)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate tracks even if audio file already exists on disk"
    )
    parser.add_argument(
        "--catalog-only",
        action="store_true",
        help="Only initialize folders and bank_catalog.json without running heavy AI audio synthesis"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="Inference device for MusicGen ('cuda' or 'cpu')"
    )
    args = parser.parse_args()

    base_bank_dir = Path(BANK_MUSIC_DIR)
    print(f"\n[Music Bank] Initializing Standing Music Bank at: {base_bank_dir}")

    # 1. Ensure all 16 category subdirectories and catalogs exist
    folder_map = ensure_bank_directories_and_catalogs(base_bank_dir)
    print(f"[Music Bank] Verified all 16 category subdirectories and bank_catalog.json files.")

    if args.catalog_only:
        print_bank_status(base_bank_dir)
        print("[Music Bank] Catalog-only initialization complete.")
        return 0

    # 2. Determine target categories to generate
    target_languages = [args.language] if args.language != "all" else ["english", "french", "spanish", "italian"]
    target_types = [args.video_type] if args.video_type != "all" else ["expression", "roleplay", "game", "fun_facts"]

    tasks_to_generate = []
    for lang in target_languages:
        for vt in target_types:
            cat_dir = base_bank_dir / lang / vt
            prompts = get_prompts_for_category(lang, vt)[:args.limit]
            for p in prompts:
                out_path = cat_dir / p["filename"]
                if args.force or not out_path.exists():
                    tasks_to_generate.append({
                        "language": lang,
                        "video_type": vt,
                        "prompt_data": p,
                        "output_path": out_path
                    })

    if not tasks_to_generate:
        print("\n[Music Bank] All requested jams are already generated and up to date!")
        print_bank_status(base_bank_dir)
        return 0

    print(f"\n[Music Bank] Identified {len(tasks_to_generate)} jam(s) to generate.")

    # 3. Load MusicGen model
    try:
        processor, model, device = load_musicgen_model(device_str=args.device)
    except Exception as exc:
        print(f"\n[ERROR] Failed to load MusicGen model: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

    # 4. Generate audio clips
    success_count = 0
    total_tasks = len(tasks_to_generate)
    for idx, task in enumerate(tasks_to_generate, 1):
        lang = task["language"]
        vt = task["video_type"]
        p = task["prompt_data"]
        out_path = task["output_path"]

        print(f"\n[{idx}/{total_tasks}] Generating: {lang.capitalize()}/{vt.upper()} -> {p['name']} ({p['bpm']} BPM, {p['style']})")
        print(f"  Prompt: \"{p['prompt'][:90]}...\"")
        try:
            generate_audio_clip(processor, model, device, p["prompt"], out_path)
            success_count += 1
        except Exception as exc:
            print(f"  [ERROR] Generation failed for {p['filename']}: {exc}", file=sys.stderr)

    # 5. Refresh catalogs with new disk states
    ensure_bank_directories_and_catalogs(base_bank_dir)
    print_bank_status(base_bank_dir)
    print(f"[Music Bank] Successfully generated {success_count} / {total_tasks} audio jams!")
    return 0 if success_count == total_tasks else 1


if __name__ == "__main__":
    sys.exit(main())
