import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.status_tracker import PipelineStatusTracker, get_status_tracker

def print_dashboard(tracker: PipelineStatusTracker, show_samples: bool = False):
    stats = tracker.get_summary_stats()
    rows = tracker.load_status_csv()

    print("\n" + "=" * 76)
    print("       LINGOVERSE SHORTS AUTOMATION - PIPELINE STATUS DASHBOARD")
    print("=" * 76)
    print(f"Total Video Prompts Tracked : {stats['total']}")
    print(f"Status CSV Location         : {tracker.status_csv_path}")
    print("-" * 76)
    print(f"{'Stage':<25} | {'Done':<10} | {'Pending':<10} | {'Completion %':<15}")
    print("-" * 76)
    
    stages = [
        ("Part A: Script Generation", stats["script_done"]),
        ("Part B: Voice Generation", stats["voice_done"]),
        ("Part C: Image Generation", stats["image_done"]),
        ("Part F: Thumbnail Gen", stats["thumbnail_done"]),
        ("Part G: Video Assembly", stats["video_assembly_done"]),
    ]
    
    total = stats["total"]
    for name, done_cnt in stages:
        pending_cnt = total - done_cnt
        pct = (done_cnt / total * 100) if total > 0 else 0
        print(f"{name:<25} | {done_cnt:<10} | {pending_cnt:<10} | {pct:>6.1f}%")
        
    print("-" * 76)
    try:
        from config import BANK_MUSIC_DIR
        bank_dir = Path(BANK_MUSIC_DIR)
        print(f"STANDING MUSIC BANK STATUS ({bank_dir}):")
        total_bank_tracks = len(list(bank_dir.rglob("*.wav"))) if bank_dir.exists() else 0
        print(f"Total Bank Audio Jams Ready: {total_bank_tracks}")
        if bank_dir.exists():
            for lang in ["english", "french", "spanish", "italian"]:
                lang_counts = []
                for vt in ["expression", "game", "roleplay", "fun_facts"]:
                    sub_dir = bank_dir / lang / vt
                    cnt = len(list(sub_dir.glob("*.wav"))) if sub_dir.exists() else 0
                    lang_counts.append(f"{vt[:4].upper()}: {cnt}")
                print(f"  {lang.capitalize():<10} | " + " | ".join(lang_counts))
    except Exception as exc:
        print(f"  Notice: Could not load music bank stats: {exc}")

    print("-" * 76)
    print("BREAKDOWN BY TARGET LANGUAGE:")
    print(f"{'Language':<12} | {'Total':<8} | {'Scripts':<10} | {'Voices':<10} | {'Videos':<10}")
    print("-" * 76)
    for lang, l_data in stats["by_language"].items():
        print(f"{lang.capitalize():<12} | {l_data['total']:<8} | {l_data['script_done']:<10} | {l_data['voice_done']:<10} | {l_data['video_done']:<10}")

    print("-" * 76)
    print("BREAKDOWN BY VIDEO TYPE:")
    print(f"{'Video Type':<12} | {'Total':<8} | {'Scripts':<10} | {'Voices':<10} | {'Videos':<10}")
    print("-" * 76)
    for vt, t_data in stats["by_type"].items():
        print(f"{vt.upper():<12} | {t_data['total']:<8} | {t_data['script_done']:<10} | {t_data['voice_done']:<10} | {t_data['video_done']:<10}")
    print("=" * 76)

    if show_samples:
        pending_scripts = [r for r in rows if r.get("script_generation_status") != "done"][:5]
        ready_for_voice = [r for r in rows if r.get("script_generation_status") == "done" and r.get("voice_generation_status") != "done"][:5]
        ready_for_assembly = [r for r in rows if r.get("voice_generation_status") == "done" and r.get("video_assembly_status") != "done"][:5]

        if pending_scripts:
            print(f"\nNext Script Prompts to Generate ({len(pending_scripts)} sample):")
            for r in pending_scripts:
                print(f"  [{r['ID']}] ({r['LANGUAGE'].capitalize()}/{r['VIDEO_TYPE'].upper()}) {r['EXPRESSION']}")

        if ready_for_voice:
            print(f"\nNext Scripts Ready for Voice Generation ({len(ready_for_voice)} sample):")
            for r in ready_for_voice:
                print(f"  [{r['ID']}] ({r['LANGUAGE'].capitalize()}/{r['VIDEO_TYPE'].upper()}) {r['EXPRESSION']}")

        if ready_for_assembly:
            print(f"\nNext Scripts Ready for Video Assembly ({len(ready_for_assembly)} sample):")
            for r in ready_for_assembly:
                print(f"  [{r['ID']}] ({r['LANGUAGE'].capitalize()}/{r['VIDEO_TYPE'].upper()}) {r['EXPRESSION']}")
        print()

def main() -> int:
    parser = argparse.ArgumentParser(description="Scrapes and updates pipeline_status.csv across all scripts.")
    parser.add_argument("--refresh", action="store_true", help="Force full re-scrape of all prompt CSVs and state JSONs")
    parser.add_argument("--samples", action="store_true", help="Display next pending video samples for upcoming stages")
    args = parser.parse_args()

    tracker = get_status_tracker(PROJECT_ROOT)
    print("Scraping and verifying video statuses across all queues and state files...")
    tracker.scrape_and_save()
    print_dashboard(tracker, show_samples=args.samples)
    return 0

if __name__ == "__main__":
    sys.exit(main())
