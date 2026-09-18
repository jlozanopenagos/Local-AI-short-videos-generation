import argparse
import sys
import traceback
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# Add project root, video_creation, and module directory to path
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
for p in [str(PROJECT_ROOT), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import (
    BASE_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, WATERMARK_DIR, OPENING_CLOSURE_DIR,
    get_script_output_dir, require_services, resolve_opening_closure_paths,
    BANK_MUSIC_DIR, resolve_script_language, resolve_script_video_type
)
# pyrefly: ignore [missing-import]
from state_manager import StateManager
try:
    # pyrefly: ignore [missing-import]
    from core.transcriber import Transcriber
    # pyrefly: ignore [missing-import]
    from core.subtitle_builder import SubtitleBuilder
    # pyrefly: ignore [missing-import]
    from core.video_assembler import VideoAssembler
except ImportError:
    from _G_video_assembly.core.transcriber import Transcriber
    from _G_video_assembly.core.subtitle_builder import SubtitleBuilder
    from _G_video_assembly.core.video_assembler import VideoAssembler


def resolve_bank_music(script_data: dict, script_output_dir: Path, base_dir: Path = BASE_DIR) -> Optional[Path]:
    """
    Selects a background music track for the script from the Standing Music Bank (BANK_MUSIC_DIR)
    based on the script's emotional triggers and language/video_type category.
    Falls back to legacy per-script bgm if present, or None if no bank tracks are available.
    """
    script_id = script_data.get("id", "UNKNOWN")
    lang = resolve_script_language(script_data)
    vtype = resolve_script_video_type(script_data)

    cat_dir = Path(BANK_MUSIC_DIR) / lang / vtype
    if cat_dir.exists():
        catalog_path = cat_dir / "bank_catalog.json"
        if catalog_path.exists():
            try:
                import json
                with catalog_path.open("r", encoding="utf-8") as f:
                    cat_data = json.load(f)
                tracks = cat_data.get("tracks", [])
                available_tracks = [t for t in tracks if (cat_dir / t["filename"]).exists()]

                if available_tracks:
                    prompt_params = script_data.get("prompt_params", {})
                    content_metadata = script_data.get("content_metadata", {})

                    trigger_text = " ".join([
                        str(prompt_params.get("EMOTIONAL_TRIGGER", "")),
                        str(content_metadata.get("emotional_trigger", "")),
                        str(content_metadata.get("emotion", "")),
                        str(content_metadata.get("game_type", "")),
                    ]).lower()

                    matching_tracks = []
                    for t in available_tracks:
                        slug = t.get("emotion_slug", "").lower()
                        match_emotions = [m.lower() for m in t.get("matching_emotions", [])]
                        if slug in trigger_text or any(m in trigger_text for m in match_emotions):
                            matching_tracks.append(t)

                    candidate_pool = matching_tracks if matching_tracks else available_tracks
                    selected_track = candidate_pool[abs(hash(script_id)) % len(candidate_pool)]
                    selected_path = cat_dir / selected_track["filename"]
                    print(f"[{script_id}] Music Bank assigned: '{selected_track.get('name')}' ({selected_track.get('filename')}) [matched: {bool(matching_tracks)}]")
                    return selected_path
            except Exception as e:
                print(f"[{script_id}] Warning reading bank catalog: {e}")

        # Fallback to any existing .wav in the category directory
        wav_files = sorted(list(cat_dir.glob("*.wav")))
        if wav_files:
            selected_wav = wav_files[abs(hash(script_id)) % len(wav_files)]
            print(f"[{script_id}] Music Bank assigned: {selected_wav.name} (from category wavs)")
            return selected_wav

    # Fallback to legacy per-script BGM if it exists
    legacy_bgm = script_output_dir / f"script_{script_id}_bgm.wav"
    if legacy_bgm.exists():
        print(f"[{script_id}] Using legacy per-script BGM: {legacy_bgm.name}")
        return legacy_bgm

    print(f"[{script_id}] Notice: No background music found in bank ({lang}/{vtype}). Assembling video without BGM.")
    return None

def process_script(
    script_data: dict,
    state_manager: StateManager,
    transcriber: Transcriber = None,
    builder: SubtitleBuilder = None,
    assembler: VideoAssembler = None,
    base_dir: Path = BASE_DIR,
    regenerate_subtitles: bool = True,
    ass_path: Path = None
) -> bool:
    script_id = script_data["id"]
    print("=" * 60)
    print(f"Processing Script ID: {script_id} for Video Assembly")
    print("=" * 60)
    
    label = script_data.get("metadata", {}).get("LABEL") or script_data.get("prompt_params", {}).get("TARGET_LANGUAGE", "english")
    script_output_dir = get_script_output_dir(script_id, label, base_dir)
    script_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Verify prerequisites
    status = script_data.get("status", {})
    if status.get("voice_generation") != "done":
        print(f"Error: Voice generation for {script_id} is not marked as done.")
        return False
    if status.get("image_generation") != "done":
        print(f"Error: Image generation for {script_id} is not marked as done.")
        return False
        
    assets = script_data.get("assets", {})
    audio_path_str = assets.get("audio_path")
    image_dir_str = assets.get("image_dir")
    
    # Fallback to canonical script_output_dir if path was moved or relocated
    if not audio_path_str or not Path(audio_path_str).exists():
        candidate_audio = script_output_dir / f"script_{script_id}_master.wav"
        if candidate_audio.exists():
            audio_path_str = str(candidate_audio)
            assets["audio_path"] = audio_path_str
        else:
            print(f"Error: Missing master audio for script {script_id}")
            return False
    
    if not image_dir_str or not Path(image_dir_str).exists():
        candidate_images = script_output_dir / "images"
        if candidate_images.exists():
            image_dir_str = str(candidate_images)
            assets["image_dir"] = image_dir_str
        else:
            print(f"Error: Missing image directory for script {script_id}")
            return False
        
    audio_path = Path(audio_path_str)
    image_dir = Path(image_dir_str)

    # Dynamic BGM selection from Standing Music Bank
    bgm_path = resolve_bank_music(script_data, script_output_dir, base_dir=base_dir)
    watermark_path = WATERMARK_DIR / "watermark.png"
    
    metadata = script_data.get("metadata", {})
    opening_path, closure_path = resolve_opening_closure_paths(script_data, base_dir=base_dir)
    print(f"[{script_id}] Opening card: {opening_path.name if opening_path else 'None (skipped)'}")
    print(f"[{script_id}] Closure card: {closure_path.name if closure_path else 'None (skipped)'}")
    
    # the timing map is created by Voice Manager inside audio_path's parent directory generally, or during merge.
    # We'll just assume it's next to the master audio
    timings_path = audio_path.parent / "timings.json" 
    
    if not timings_path.exists():
        print(f"Error: Missing timings map {timings_path}.")
        return False
        
    try:
        if ass_path is None:
            ass_path = script_output_dir / f"script_{script_id}_subtitles.ass"

        if not regenerate_subtitles and ass_path.exists():
            print(f"Using existing subtitles at {ass_path.name} (skipping Whisper transcription)")
        else:
            if transcriber is None:
                transcriber = Transcriber()
            if builder is None:
                builder = SubtitleBuilder()

            # 1. Transcribe
            words = transcriber.transcribe(audio_path)
            
            # 2. Build Subtitles
            suppress_windows = []
            video_type = (
                script_data.get("content_metadata", {}).get("video_type")
                or script_data.get("prompt_params", {}).get("VIDEO_TYPE")
                or metadata.get("VIDEO_TYPE", "")
            ).upper()

            if video_type == "GAME":
                import json
                try:
                    with timings_path.open("r", encoding="utf-8") as tf:
                        timings_data = json.load(tf)
                    if "challenge" in timings_data:
                        ch_start = timings_data["challenge"].get("start", 0.0)
                        ch_end = timings_data["challenge"].get("end", 0.0)
                        suppress_windows.append((ch_start, ch_end))
                        print(f"[{script_id}] Subtitles suppressed during CHALLENGE section ({ch_start}s - {ch_end}s)")
                except Exception as e:
                    print(f"[{script_id}] Warning checking timings for subtitle suppression: {e}")

            builder.build_ass(words, ass_path, VIDEO_WIDTH, VIDEO_HEIGHT, suppress_windows=suppress_windows)
            print(f"Generated subtitles at {ass_path.name}")
        
        # 3. Assemble Video
        if assembler is None:
            assembler = VideoAssembler()

        final_video_path = script_output_dir / f"script_{script_id}_final.mp4"
        success = assembler.assemble(
            script_id, timings_path, image_dir, audio_path, ass_path, final_video_path, 
            bgm_path=bgm_path, watermark_path=watermark_path,
            opening_path=opening_path, closure_path=closure_path
        )
        
        if success:
            script_data["assets"]["final_video"] = str(final_video_path)
            script_data["status"]["video_assembly"] = "done"
            state_manager.save_script_state(script_id, script_data)
            
        return success
    except Exception as exc:
        print(f"Error processing script {script_id}: {exc}")
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script-id", type=str, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--keep-subtitles", "--skip-transcribe", dest="keep_subtitles", action="store_true", help="Reuse existing .ass subtitles if available")
    args = parser.parse_args()
    
    base_dir = BASE_DIR
    state_manager = StateManager(base_dir)
    
    # Pre-flight service check
    print("\n" + "=" * 60)
    print("Pre-flight Connection Checks:")
    try:
        require_services(llm=False, comfy=False)
    except ConnectionError as exc:
        print(f"\n{exc}\n")
        return 1
    print("=" * 60 + "\n")

    # Production Mode Selection: Mass-produce (default in 10s) or Specific Script ID
    from core.cli_prompt import prompt_production_mode
    target_script_ids = prompt_production_mode(
        stage_title="Part G: Video Assembly",
        asset_name="final short videos",
        timeout=10.0,
        script_id_arg=args.script_id,
        require_existing_state=True,
        base_dir=base_dir,
    )
    
    # Query pending scripts via Pipeline Status Tracker
    try:
        from core.status_tracker import get_status_tracker
        tracker = get_status_tracker(base_dir)
        pending_rows = tracker.get_pending_scripts("video_assembly", script_id=target_script_ids, force=args.force)
        pending = [state_manager.get_script_state(r["ID"]) for r in pending_rows]
        if target_script_ids:
            pending.sort(key=lambda s: target_script_ids.index(s.get("id", "")) if s.get("id", "") in target_script_ids else 9999)
    except Exception:
        all_scripts = state_manager.get_all_scripts()
        pending = []
        for script in all_scripts:
            script_id = script.get("id")
            if target_script_ids and script_id not in target_script_ids:
                continue
                
            from core.expression_db import is_expression_done
            if is_expression_done(script_id):
                continue

            status = script.get("status", {})
            if status.get("voice_generation") == "done" and status.get("image_generation") == "done":
                if args.force or status.get("video_assembly") != "done":
                    pending.append(script)
                    
    if not pending:
        print("No pending scripts for video assembly.")
        return 0
        
    print(f"Found {len(pending)} pending script(s) for video assembly.")
    
    transcriber = None if args.keep_subtitles else Transcriber()
    builder = SubtitleBuilder()
    assembler = VideoAssembler()
    
    success_count = 0
    for script in pending:
        if process_script(
            script,
            state_manager,
            transcriber=transcriber,
            builder=builder,
            assembler=assembler,
            base_dir=base_dir,
            regenerate_subtitles=not args.keep_subtitles
        ):
            success_count += 1
        else:
            print(f"Failed to assemble video for {script['id']}", file=sys.stderr)
            
    print(f"Process complete. Successfully assembled {success_count} video(s).")
    return 0 if success_count == len(pending) else 1

if __name__ == "__main__":
    sys.exit(main())
