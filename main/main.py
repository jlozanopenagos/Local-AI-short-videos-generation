import subprocess
import os
import sys

def run_script(script_path, cwd, description):
    print(f"\n{'='*50}")
    print(f"Starting: {description}")
    print(f"Script: {script_path}")
    print(f"{'='*50}\n")
    
    try:
        # Run the script in its respective directory and wait for it to finish
        result = subprocess.run([sys.executable, script_path], cwd=cwd, check=True)
        print(f"\n[{description}] completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Failed to run {description}. Exit code: {e.returncode}")
        print("Stopping execution.")
        sys.exit(e.returncode)

def main():
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
    
    # 1. Part A: Video Scripts
    dir_a = os.path.join(base_dir, "video_creation", "_A_video_scripts")
    script_a = os.path.join(dir_a, "main.py")
    if os.path.exists(script_a):
        run_script(script_a, dir_a, "Part A: Video Scripts")
    else:
        print(f"[WARNING] Could not find {script_a}")

    # Interactive Review Checkpoint: allow user to inspect/edit state JSON before generating audio & timings
    print("\n" + "="*50)
    print("CHECKPOINT: Script & Metadata generation complete.")
    print("The script state JSON is ready in the 'state/' directory.")
    print("="*50)
    
    try:
        user_choice = input("\nDo you want to proceed with Voice Generation (audio & timings.json)? [Y/n]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\nExecution cancelled by user.")
        return

    if user_choice not in ("", "y", "yes"):
        print("\nExecution paused by user.")
        print("You can review or edit the script in 'state/', and run main.py again when ready.")
        return

    # 2. Part B: Voice Generation
    dir_b = os.path.join(base_dir, "video_creation", "_B_voice_generation")
    script_b = os.path.join(dir_b, "main.py")
    if os.path.exists(script_b):
        run_script(script_b, dir_b, "Part B: Voice Generation")
    else:
        print(f"[WARNING] Could not find {script_b}")
        
    print("\n" + "="*50)
    print("SUCCESS: Pipeline execution finished.")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
