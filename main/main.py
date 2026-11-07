import argparse
import os
import subprocess
import sys
from typing import List, Optional


def run_script(script_path: str, cwd: str, description: str, extra_args: Optional[List[str]] = None) -> None:
    print(f"\n{'='*50}")
    print(f"Starting: {description}")
    print(f"Script: {script_path}")
    print(f"{'='*50}\n")

    cmd = [sys.executable, script_path]
    if extra_args:
        cmd.extend(extra_args)

    try:
        subprocess.run(cmd, cwd=cwd, check=True)
        print(f"\n[{description}] completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Failed to run {description}. Exit code: {e.returncode}")
        print("Stopping execution.")
        sys.exit(e.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="LingoVerse Shorts Automation Root Orchestrator")
    parser.add_argument("--language", type=str, help="Filter by language (english, french, spanish, italian)")
    parser.add_argument("--video-type", type=str, help="Filter by video type (expression, roleplay, game, fun_facts)")
    parser.add_argument("--id", type=str, help="Target a specific script ID (e.g. EE01, FR102)")
    parser.add_argument("--from-ready-scripts", action="store_true", help="Ingest from Ready Scripts in Stage A")
    parser.add_argument("--full-pipeline", action="store_true", help="Run all stages A -> B -> C -> F -> G sequentially")
    parser.add_argument("--no-prompt", action="store_true", help="Skip interactive confirmation checkpoints")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Pre-flight service health checks
    print("\n" + "=" * 50)
    print("Pre-flight AI Services Verification:")
    print("=" * 50)
    try:
        from config import check_all_services
        results = check_all_services()
        for name, info in results.items():
            status = "[ONLINE] " if info["online"] else "[OFFLINE]"
            print(f"  {status} {name}: {info['message']}")
    except Exception as exc:
        print(f"  [WARNING] Could not check service status: {exc}")

    # Expression Database status & auto-sync
    try:
        from core.expression_db import get_expression_db
        db = get_expression_db()
        db.sync()
        stats = db.get_stats()
        print(f"  [DATABASE] Expressions: {stats['total']} total | {stats['done']} DONE | {stats['pending']} PENDING")
    except Exception as exc:
        print(f"  [WARNING] Could not sync Expression Database: {exc}")

    # Output Storage Location
    try:
        from config import OUTPUT_DIR
        print(f"  [STORAGE]  Output Directory: {OUTPUT_DIR}")
    except Exception:
        pass

    # Pipeline Status Tracking & Manifest
    try:
        from core.status_tracker import get_status_tracker
        tracker = get_status_tracker(base_dir)
        p_stats = tracker.get_summary_stats()
        print(f"  [PIPELINE] Videos: {p_stats['total']} total | Scripts: {p_stats['script_done']} done | Voices: {p_stats['voice_done']} done | Videos: {p_stats['video_assembly_done']} done")
    except Exception as exc:
        print(f"  [WARNING] Could not load pipeline status: {exc}")

    print("=" * 50 + "\n")

    common_args: List[str] = []
    if args.language:
        common_args.extend(["--language", args.language])
    if args.video_type:
        common_args.extend(["--video-type", args.video_type])

    stage_a_args = list(common_args)
    if args.from_ready_scripts:
        stage_a_args.append("--from-ready-scripts")

    stage_filter_args = list(common_args)
    if args.id:
        stage_filter_args.extend(["--id", args.id])

    # 1. Stage A: Video Scripts
    dir_a = os.path.join(base_dir, "video_creation", "_A_video_scripts")
    script_a = os.path.join(dir_a, "main.py")
    if os.path.exists(script_a):
        run_script(script_a, dir_a, "Stage A: Video Scripts", stage_a_args)
    else:
        print(f"[WARNING] Could not find {script_a}")

    if not args.no_prompt:
        print("\n" + "=" * 50)
        print("CHECKPOINT: Script & Metadata generation complete.")
        print("The script state JSON is ready in 'video_creation/_A_video_scripts/video_scripts/'.")
        print("=" * 50)
        try:
            user_choice = input("\nDo you want to proceed with Stage B: Voice Generation (audio & timings.json)? [Y/n]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExecution cancelled by user.")
            return

        if user_choice not in ("", "y", "yes"):
            print("\nExecution paused by user.")
            print("You can review or edit the script state JSON, and run the next stage when ready.")
            return

    # 2. Stage B: Voice Generation
    dir_b = os.path.join(base_dir, "video_creation", "_B_voice_generation")
    script_b = os.path.join(dir_b, "main.py")
    if os.path.exists(script_b):
        run_script(script_b, dir_b, "Stage B: Voice Generation", stage_filter_args)
    else:
        print(f"[WARNING] Could not find {script_b}")

    if args.full_pipeline:
        for folder, label in [
            ("_C_image_generation", "Stage C: Image Generation"),
            ("_F_thumbnail_image_generation", "Stage F: Thumbnail Generation"),
            ("_G_video_assembly", "Stage G: Video Assembly"),
        ]:
            stage_dir = os.path.join(base_dir, "video_creation", folder)
            stage_script = os.path.join(stage_dir, "main.py")
            if os.path.exists(stage_script):
                run_script(stage_script, stage_dir, label, stage_filter_args)
            else:
                print(f"[WARNING] Could not find {stage_script}")

    print("\n" + "=" * 50)
    print("SUCCESS: Pipeline execution finished.")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
