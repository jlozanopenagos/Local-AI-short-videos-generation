#!/usr/bin/env python3
"""
little_short_creation.py — Instant Little Short / Teaser Clip Generator.

Takes a Script ID and a seconds lapse (e.g. 10-16 or 4-10), extracts that segment
from the produced video, wraps it with the brand Opening card (2s),
and saves the result directly to the script's output directory.

Usage:
    # Interactive CLI (prompts for ID and lapse):
    py main/video_creation/_G_video_assembly/little_short_creation.py

    # Non-interactive / Scripted CLI:
    py main/video_creation/_G_video_assembly/little_short_creation.py --id EE01 --lapse 10-16
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# Ensure project directories are in sys.path
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = MODULE_DIR.parent.resolve()
PROJECT_ROOT = VIDEO_CREATION_DIR.parent.resolve()
CORE_DIR = PROJECT_ROOT / "core"

for p in [str(PROJECT_ROOT), str(CORE_DIR), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# pyrefly: ignore[missing-import]
import ffmpeg
from config.settings import (
    BASE_DIR,
    get_script_output_dir,
    resolve_opening_closure_paths,
    resolve_script_language,
    resolve_script_video_type,
)
# pyrefly: ignore[missing-import]
from state_manager import StateManager


def get_ffmpeg_tools() -> Tuple[str, str]:
    """Resolve ffmpeg and ffprobe paths (prefer bundled binary in _G_video_assembly)."""
    ffmpeg_local = MODULE_DIR / "ffmpeg.exe"
    ffprobe_local = MODULE_DIR / "ffprobe.exe"

    ffmpeg_cmd = ffmpeg_local.as_posix() if ffmpeg_local.exists() else "ffmpeg"
    ffprobe_cmd = ffprobe_local.as_posix() if ffprobe_local.exists() else "ffprobe"
    return ffmpeg_cmd, ffprobe_cmd


def parse_timestamp_value(val_str: str) -> float:
    """
    Parse a single timestamp string (seconds float or MM:SS format) into float seconds.
    Examples:
        "10" -> 10.0
        "10.5" -> 10.5
        "0:10" -> 10.0
        "01:23.5" -> 83.5
    """
    val_str = val_str.strip()
    if ":" in val_str:
        parts = val_str.split(":")
        if len(parts) == 2:
            minutes = float(parts[0])
            seconds = float(parts[1])
            return minutes * 60.0 + seconds
        elif len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600.0 + minutes * 60.0 + seconds
        else:
            raise ValueError(f"Invalid timestamp format: '{val_str}'")
    return float(val_str)


def parse_lapse(lapse_str: str) -> Tuple[float, float]:
    """
    Parse a seconds lapse range into (start_sec, end_sec).
    Supports formats:
        "10-16", "10 - 16", "4.5-10.2", "0:04-0:10", "10,16", "10 to 16", "10:16" (when separated by colon)
    """
    cleaned = lapse_str.strip().lower()
    if not cleaned:
        raise ValueError("Lapse range cannot be empty.")

    # Check for "to" separator
    if " to " in cleaned:
        start_part, end_part = cleaned.split(" to ", 1)
    elif "," in cleaned:
        start_part, end_part = cleaned.split(",", 1)
    elif "-" in cleaned:
        parts = cleaned.split("-")
        if len(parts) == 2:
            start_part, end_part = parts[0], parts[1]
        else:
            raise ValueError(f"Ambiguous or invalid lapse range: '{lapse_str}'")
    else:
        # Fallback regex for two numbers
        match = re.search(r"(\d+(?:\.\d+)?)\s*[:\s]\s*(\d+(?:\.\d+)?)", cleaned)
        if match:
            start_part, end_part = match.group(1), match.group(2)
        else:
            raise ValueError(f"Could not parse lapse range from: '{lapse_str}'. Use format like '10-16' or '4-10'.")

    start_sec = parse_timestamp_value(start_part)
    end_sec = parse_timestamp_value(end_part)

    if start_sec < 0:
        raise ValueError(f"Start time cannot be negative ({start_sec}s).")
    if end_sec <= start_sec:
        raise ValueError(f"End time ({end_sec}s) must be greater than start time ({start_sec}s).")

    return round(start_sec, 3), round(end_sec, 3)


def format_seconds_tag(sec: float) -> str:
    """Format seconds for clean, filename-friendly tagging (e.g. 10.0 -> '10', 10.5 -> '10.5')."""
    if sec == int(sec):
        return str(int(sec))
    return f"{sec:.3f}".rstrip("0").rstrip(".")


def get_video_duration(video_path: Path, ffprobe_cmd: str) -> float:
    """Probe video file duration in seconds."""
    probe = ffmpeg.probe(video_path.as_posix(), cmd=ffprobe_cmd)
    return float(probe["format"]["duration"])


def create_little_short(
    script_id: str,
    start_sec: float,
    end_sec: float,
    base_dir: Path = BASE_DIR,
    state_manager: Optional[StateManager] = None,
    output_path_override: Optional[Path] = None,
) -> Optional[Path]:
    """
    Creates a 'little short' by slicing [start_sec, end_sec] from the script's final video,
    prepending the opening card (2s).

    Returns the Path of the generated little short MP4, or None on failure.
    """
    if state_manager is None:
        state_manager = StateManager(base_dir)

    script_data = state_manager.get_script_state(script_id)
    if not script_data:
        print(f"[{script_id}] Error: Script state not found.")
        return None

    label = script_data.get("metadata", {}).get("LABEL") or script_data.get("prompt_params", {}).get("TARGET_LANGUAGE", "english")
    script_output_dir = get_script_output_dir(script_id, label, base_dir)

    # 1. Locate final video
    assets = script_data.get("assets", {})
    final_video_str = assets.get("final_video")
    final_video_path = Path(final_video_str) if final_video_str else (script_output_dir / f"script_{script_id}_final.mp4")

    if not final_video_path.exists():
        print(f"[{script_id}] Error: Final video does not exist at {final_video_path}.")
        print(f"[{script_id}] Please run video assembly (Stage G) for {script_id} first.")
        return None

    ffmpeg_cmd, ffprobe_cmd = get_ffmpeg_tools()

    # 2. Check duration
    try:
        total_duration = get_video_duration(final_video_path, ffprobe_cmd)
    except Exception as e:
        print(f"[{script_id}] Warning: Could not probe video duration ({e}). Proceeding...")
        total_duration = None

    if total_duration is not None:
        if start_sec >= total_duration:
            print(f"[{script_id}] Error: Start time ({start_sec}s) is beyond total video duration ({total_duration:.2f}s).")
            return None
        if end_sec > total_duration:
            print(f"[{script_id}] Notice: End time ({end_sec}s) exceeds duration ({total_duration:.2f}s). Capping to video end.")
            end_sec = round(total_duration, 3)

    clip_duration = end_sec - start_sec
    if clip_duration < 0.2:
        print(f"[{script_id}] Error: Clip duration ({clip_duration}s) is too short.")
        return None

    # 3. Resolve Opening card (Closure card is deliberately excluded from little shorts)
    opening_path_str = assets.get("opening_card")
    opening_path = Path(opening_path_str) if opening_path_str and Path(opening_path_str).exists() else None

    if not opening_path:
        res_open, _ = resolve_opening_closure_paths(script_data, base_dir=base_dir)
        if res_open and res_open.exists():
            opening_path = res_open

    # 4. Determine output path
    start_tag = format_seconds_tag(start_sec)
    end_tag = format_seconds_tag(end_sec)
    default_filename = f"script_{script_id}_little_{start_tag}-{end_tag}.mp4"

    if output_path_override:
        output_path = Path(output_path_override)
    else:
        output_path = script_output_dir / default_filename

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("-" * 60)
    print(f"Assembling Little Short for {script_id}")
    print(f"  Lapse Range:  {start_sec}s -> {end_sec}s (Duration: {clip_duration:.2f}s)")
    print(f"  Opening Card: {opening_path.name if opening_path else 'None'}")
    print(f"  Output Path:  {output_path.resolve()}")
    print("-" * 60)

    # 5. Build FFmpeg Filter Graph
    video_streams = []
    audio_streams = []

    # Stream A: Opening card (2.0s)
    if opening_path and opening_path.exists():
        v_open = (
            ffmpeg.input(opening_path.as_posix(), loop=1, framerate=25, t=2)
            .filter("scale", "576x1024", force_original_aspect_ratio="decrease")
            .filter("pad", "576", "1024", "(ow-iw)/2", "(oh-ih)/2")
            .filter("setsar", "1")
            .filter("format", "yuv420p")
        )
        a_open = ffmpeg.input("anullsrc=channel_layout=mono:sample_rate=32000", f="lavfi", t=2)
        video_streams.append(v_open)
        audio_streams.append(a_open)

    # Stream B: Sliced Lapse Clip
    clip = ffmpeg.input(final_video_path.as_posix(), ss=start_sec, t=clip_duration)
    v_clip = clip.video.filter("setsar", "1").filter("format", "yuv420p")
    # Apply audio formatting and 50ms anti-pop micro-fades at start/end
    fade_out_start = max(0.0, clip_duration - 0.05)
    a_clip = (
        clip.audio
        .filter("aformat", sample_rates="32000", channel_layouts="mono")
        .filter("afade", t="in", ss=0, d=0.05)
        .filter("afade", t="out", st=fade_out_start, d=0.05)
    )
    video_streams.append(v_clip)
    audio_streams.append(a_clip)

    concat_video = ffmpeg.concat(*video_streams, v=1, a=0)
    concat_audio = ffmpeg.concat(*audio_streams, v=0, a=1)

    try:
        (
            ffmpeg.output(
                concat_video,
                concat_audio,
                output_path.as_posix(),
                vcodec="libx264",
                pix_fmt="yuv420p",
                acodec="aac",
                shortest=None,
            )
            .overwrite_output()
            .run(cmd=ffmpeg_cmd, capture_stdout=True, capture_stderr=True)
        )
        print(f"[SUCCESS] Little short successfully assembled at: {output_path}")

        # Record in state JSON for persistence and tracking
        script_data.setdefault("assets", {}).setdefault("little_shorts", {})[f"{start_tag}-{end_tag}"] = str(output_path)
        state_manager.save_script_state(script_id, script_data)

        return output_path
    except ffmpeg.Error as exc:
        err_msg = exc.stderr.decode("utf-8") if exc.stderr else str(exc)
        print(f"[ERROR] FFmpeg failed assembling little short: {err_msg}")
        return None
    except Exception as exc:
        print(f"[ERROR] Unexpected error: {exc}")
        traceback.print_exc()
        return None


def display_script_info(script_id: str, script_data: dict, base_dir: Path) -> Optional[float]:
    """Display script metadata, timeline landmarks, and total video duration."""
    meta = script_data.get("metadata", {})
    prompt_params = script_data.get("prompt_params", {})
    title = script_data.get("title") or meta.get("TITLE") or "Untitled"
    lang = resolve_script_language(script_data).capitalize()
    vtype = resolve_script_video_type(script_data).upper()

    label = meta.get("LABEL") or prompt_params.get("TARGET_LANGUAGE", "english")
    script_output_dir = get_script_output_dir(script_id, label, base_dir)
    final_video_path = script_output_dir / f"script_{script_id}_final.mp4"

    print("\n" + "=" * 64)
    print(f"  SCRIPT FOUND: [{script_id}] {title}")
    print(f"  Category: {lang} | {vtype}")
    print(f"  Folder:   {script_output_dir}")

    total_dur = None
    if final_video_path.exists():
        _, ffprobe_cmd = get_ffmpeg_tools()
        try:
            total_dur = get_video_duration(final_video_path, ffprobe_cmd)
            print(f"  Master Video: {final_video_path.name} (Total Duration: {total_dur:.2f}s)")
        except Exception:
            print(f"  Master Video: {final_video_path.name}")
    else:
        print(f"  Master Video: NOT FOUND (Must assemble Stage G first)")

    # Read timings.json for helpful section landmark guidance
    timings_path = script_output_dir / "timings.json"
    if timings_path.exists():
        try:
            with timings_path.open("r", encoding="utf-8") as tf:
                timings_data = json.load(tf)
            sorted_sec = sorted(timings_data.items(), key=lambda x: x[1].get("start", 0))
            print("\n  Scene Landmark Timings (Master Audio):")
            print("    [Opening Card]  0.0s -> 2.0s")
            for sec_name, t_info in sorted_sec:
                st = t_info.get("start", 0.0)
                en = t_info.get("end", 0.0)
                # In final video, content starts after opening card (2.0s)
                v_st = st + 2.0
                v_en = en + 2.0
                print(f"    - {sec_name:16}: Audio {st:4.1f}s-{en:4.1f}s | Video {v_st:4.1f}s-{v_en:4.1f}s")
        except Exception:
            pass

    print("=" * 64 + "\n")
    return total_dur


def interactive_loop(base_dir: Path = BASE_DIR) -> None:
    """Run interactive terminal prompt to ask for ID and lapse."""
    state_manager = StateManager(base_dir)

    print("\n" + "#" * 64)
    print("      LITTLE SHORT CREATION TOOL (Stage G Snippet Assembler)")
    print("#" * 64)

    while True:
        try:
            script_id_input = input("\nEnter Script ID (e.g. EE01, FG12, EF03) [or 'q' to quit]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if not script_id_input or script_id_input.lower() in ("q", "quit", "exit"):
            print("Goodbye!")
            break

        script_id = script_id_input.upper()
        script_data = state_manager.get_script_state(script_id)

        if not script_data:
            print(f"Error: Script ID '{script_id}' does not exist in state manager.")
            continue

        label = script_data.get("metadata", {}).get("LABEL") or script_data.get("prompt_params", {}).get("TARGET_LANGUAGE", "english")
        script_output_dir = get_script_output_dir(script_id, label, base_dir)
        final_video_path = script_output_dir / f"script_{script_id}_final.mp4"

        if not final_video_path.exists():
            print(f"\n[Warning] Final video does not exist yet at: {final_video_path}")
            # Check if voice and images are ready to offer auto-assembly
            status = script_data.get("status", {})
            if status.get("voice_generation") == "done" and status.get("image_generation") == "done":
                try:
                    assemble_choice = input("Voice and images are ready. Assemble master video now? (y/n) [y]: ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    break
                if assemble_choice in ("", "y", "yes"):
                    try:
                        from _G_video_assembly.main import process_script
                    except (ImportError, ModuleNotFoundError):
                        # pyrefly: ignore [missing-import]
                        from main import process_script
                    print(f"[{script_id}] Launching video assembly...")
                    ok = process_script(script_data, state_manager, base_dir=base_dir, auto=True)
                    if not ok or not final_video_path.exists():
                        print(f"[{script_id}] Failed to assemble master video.")
                        continue
                else:
                    continue
            else:
                print(f"[{script_id}] Cannot assemble: voice/images not completed. Please run earlier stages first.")
                continue

        total_dur = display_script_info(script_id, script_data, base_dir)

        # Prompt for lapse
        while True:
            try:
                prompt_text = "Enter seconds lapse time (e.g. 10-16 or 4-10) [or 'b' to change ID]: "
                lapse_input = input(prompt_text).strip()
            except (KeyboardInterrupt, EOFError):
                return

            if lapse_input.lower() in ("b", "back", "q"):
                break

            try:
                start_sec, end_sec = parse_lapse(lapse_input)
            except ValueError as val_err:
                print(f"Invalid input: {val_err}. Please try again.")
                continue

            if total_dur and start_sec >= total_dur:
                print(f"Start time ({start_sec}s) is greater than total duration ({total_dur:.2f}s). Try again.")
                continue

            res_path = create_little_short(
                script_id=script_id,
                start_sec=start_sec,
                end_sec=end_sec,
                base_dir=base_dir,
                state_manager=state_manager,
            )

            if res_path:
                print(f"\nCreated successfully! Path: {res_path}")
            break

        try:
            another = input("\nCreate another little short? (y/n) [n]: ").strip().lower()
            if another not in ("y", "yes"):
                print("Done. Goodbye!")
                break
        except (KeyboardInterrupt, EOFError):
            break


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract a seconds lapse from a video, wrap with Opening card, and save as a Little Short."
    )
    parser.add_argument("--id", "--script-id", dest="script_id", type=str, default=None, help="Target Script ID (e.g. EE01)")
    parser.add_argument("--lapse", type=str, default=None, help="Seconds lapse range (e.g. '10-16', '4-10')")
    parser.add_argument("--output", type=str, default=None, help="Optional custom output path for the video")

    args = parser.parse_args()

    # If ID and lapse are provided as CLI arguments, run non-interactively
    if args.script_id and args.lapse:
        script_id = args.script_id.upper().strip()
        try:
            start_sec, end_sec = parse_lapse(args.lapse)
        except ValueError as exc:
            print(f"Error parsing --lapse argument: {exc}", file=sys.stderr)
            return 1

        output_override = Path(args.output) if args.output else None
        res = create_little_short(
            script_id=script_id,
            start_sec=start_sec,
            end_sec=end_sec,
            base_dir=BASE_DIR,
            output_path_override=output_override,
        )
        return 0 if res else 1

    # Otherwise run the interactive terminal workflow
    interactive_loop(base_dir=BASE_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
