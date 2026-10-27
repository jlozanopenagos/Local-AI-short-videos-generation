import argparse
import sys
import traceback
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# Add project root, video_creation, core, and module directory to path
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
for p in [str(PROJECT_ROOT), str(CORE_DIR), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
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
    from _G_video_assembly.core.transcriber import Transcriber
    # pyrefly: ignore [missing-import]
    from _G_video_assembly.core.subtitle_builder import SubtitleBuilder
    # pyrefly: ignore [missing-import]
    from _G_video_assembly.core.video_assembler import VideoAssembler
except (ImportError, ModuleNotFoundError):
    # pyrefly: ignore [missing-import]
    from core.transcriber import Transcriber
    # pyrefly: ignore [missing-import]
    from core.subtitle_builder import SubtitleBuilder
    # pyrefly: ignore [missing-import]
    from core.video_assembler import VideoAssembler


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
    ass_path: Path = None,
    opening_path: Path = None,
    closure_path: Path = None,
    dialect: str = None,
    auto: bool = False,
    remembered_dialects: dict = None,
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

    # Interactive dialect/variant prompt exclusively for Fun Facts (English: US vs UK, Spanish: LatAm vs Spain)
    if dialect is None and (opening_path is None or closure_path is None):
        try:
            try:
                from core.cli_prompt import prompt_fun_facts_cards_variant
            except (ImportError, ModuleNotFoundError):
                # pyrefly: ignore[missing-import]
                from cli_prompt import prompt_fun_facts_cards_variant
            dialect = prompt_fun_facts_cards_variant(
                script_data,
                auto=auto,
                remembered_dialects=remembered_dialects,
            )
        except Exception as e:
            print(f"[{script_id}] Warning checking card variant: {e}")

    res_open, res_close = resolve_opening_closure_paths(script_data, base_dir=base_dir, dialect=dialect)
    if opening_path is None:
        opening_path = res_open
    if closure_path is None:
        closure_path = res_close

    if opening_path:
        script_data.setdefault("assets", {})["opening_card"] = str(opening_path)
    if closure_path:
        script_data.setdefault("assets", {})["closure_card"] = str(closure_path)
    if dialect:
        script_data.setdefault("assets", {})["opening_closure_dialect"] = dialect

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

            # 1. Transcribe with language & prompt hints from script_data
            whisper_lang = None
            initial_prompt = None
            if script_data:
                target_lang = (
                    script_data.get("content_metadata", {}).get("language")
                    or script_data.get("prompt_params", {}).get("TARGET_LANGUAGE")
                    or metadata.get("LABEL")
                    or ""
                ).lower()
                lang_map = {
                    "french": "fr", "fr": "fr",
                    "italian": "it", "it": "it",
                    "spanish": "es", "es": "es",
                    "english": "en", "en": "en"
                }
                for k, v in lang_map.items():
                    if k in target_lang:
                        whisper_lang = v
                        break

                script_dict = script_data.get("content_metadata", {}).get("script", {})
                if script_dict and isinstance(script_dict, dict):
                    full_p = " ".join(str(v) for k, v in script_dict.items() if k.lower() != "title")
                    initial_prompt = full_p[:800]

            words = transcriber.transcribe(audio_path, language=whisper_lang, initial_prompt=initial_prompt)
            
            # 2. Build Subtitles
            suppress_windows = []
            video_type = (
                script_data.get("content_metadata", {}).get("video_type")
                or script_data.get("prompt_params", {}).get("VIDEO_TYPE")
                or metadata.get("VIDEO_TYPE", "")
            ).upper()

            timings_data = None
            if timings_path.exists():
                import json
                try:
                    with timings_path.open("r", encoding="utf-8") as tf:
                        timings_data = json.load(tf)
                except Exception as e:
                    print(f"[{script_id}] Warning reading timings map: {e}")

            if video_type == "GAME" and timings_data and "challenge" in timings_data:
                ch_start = timings_data["challenge"].get("start", 0.0)
                ch_end = timings_data["challenge"].get("end", 0.0)
                suppress_windows.append((ch_start, ch_end))
                print(f"[{script_id}] Subtitles suppressed during CHALLENGE section ({ch_start}s - {ch_end}s)")

            builder.build_ass(
                words, 
                ass_path, 
                VIDEO_WIDTH, 
                VIDEO_HEIGHT, 
                suppress_windows=suppress_windows, 
                script_data=script_data,
                timings_data=timings_data
            )
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
    parser.add_argument("--auto", action="store_true", help="Auto-assemble without interactive terminal prompts")
    parser.add_argument("--keep-subtitles", "--skip-transcribe", dest="keep_subtitles", action="store_true", help="Reuse existing .ass subtitles if available")
    parser.add_argument(
        "--fun-facts",
        "--fun-facts-only",
        dest="fun_facts_only",
        action="store_true",
        help="Only assemble Fun Facts scripts (e.g. EF01, FF01, SF01, IF01)"
    )
    parser.add_argument(
        "--video-type",
        type=str,
        default=None,
        choices=["expression", "game", "roleplay", "fun_facts", "all"],
        help="Filter assembly to specific video type"
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        choices=["all", "english", "french", "spanish", "italian"],
        help="Filter assembly to specific language"
    )
    parser.add_argument(
        "--from-ready-scripts",
        "--ready-scripts",
        "--from-csv",
        dest="ready_scripts_csv",
        nargs="?",
        const="",
        default=None,
        help="Target scripts from <date>_ready_scripts.csv (default checks D:\\AI\\output\\connectivity\\ready_scripts/)"
    )
    parser.add_argument(
        "--dialect",
        "--variant",
        dest="dialect",
        type=str,
        default=None,
        choices=["american", "british", "latin_american", "spain"],
        help="Force specific opening/closure card dialect for Fun Facts (skips interactive prompt)"
    )
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

    # Production Mode Selection: Mass-produce (default in 10s), Specific ID, Group Range, Fun Facts, or Ready Scripts CSV
    # pyrefly: ignore [missing-import]
    try:
        # pyrefly: ignore [missing-import]
        from core.cli_prompt import (
            prompt_production_mode,
            prompt_group_range,
            prompt_fun_facts_mode,
            prompt_ready_scripts_mode,
        )
    except (ImportError, ModuleNotFoundError):
        # pyrefly: ignore [missing-import]
        from cli_prompt import (
            prompt_production_mode,
            prompt_group_range,
            prompt_fun_facts_mode,
            prompt_ready_scripts_mode,
        )

    is_cli_fun_facts = args.fun_facts_only or (args.video_type and args.video_type.lower() == "fun_facts")

    if is_cli_fun_facts and not args.script_id and args.ready_scripts_csv is None:
        print("\n[CLI Option] Fun Facts mode active: targeting Fun Facts scripts only.")
        target_script_ids = None
        selected_mode = "fun_facts"
    else:
        target_script_ids, selected_mode = prompt_production_mode(
            stage_title="Part G: Video Assembly",
            asset_name="final short videos",
            timeout=10.0,
            script_id_arg=args.script_id,
            auto=args.auto,
            require_existing_state=True,
            base_dir=base_dir,
            return_mode=True,
            allow_fun_facts_mode=True,
            allow_ready_scripts_mode=True,
            ready_scripts_path_arg=args.ready_scripts_csv,
        )
        if is_cli_fun_facts:
            selected_mode = "fun_facts"

    transcriber = None if args.keep_subtitles else Transcriber()
    builder = SubtitleBuilder()
    assembler = VideoAssembler()

    while True:
        # Determine target video type filter
        target_video_type = None
        if selected_mode == "fun_facts" or args.fun_facts_only:
            target_video_type = "fun_facts"
        elif args.video_type and args.video_type.lower() != "all":
            target_video_type = args.video_type.lower()

        target_language = args.language if args.language and args.language.lower() != "all" else None

        # Query pending scripts via Pipeline Status Tracker
        try:
            try:
                # pyrefly: ignore [missing-import]
                from core.status_tracker import get_status_tracker
            except (ImportError, ModuleNotFoundError):
                # pyrefly: ignore [missing-import]
                from status_tracker import get_status_tracker
            tracker = get_status_tracker(base_dir)
            pending_rows = tracker.get_pending_scripts(
                "video_assembly",
                script_id=target_script_ids,
                language=target_language,
                video_type=target_video_type,
                force=args.force
            )
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
                if target_language:
                    slang = (script.get("content_metadata", {}).get("language") or "").lower()
                    if slang != target_language.lower():
                        continue
                if target_video_type:
                    svtype = (script.get("content_metadata", {}).get("video_type") or "").lower()
                    if target_video_type == "fun_facts" and svtype not in ("fun_facts", "funfacts"):
                        continue
                    elif target_video_type != "fun_facts" and svtype != target_video_type:
                        continue

                try:
                    # pyrefly: ignore [missing-import]
                    from core.expression_db import is_expression_done
                except (ImportError, ModuleNotFoundError):
                    # pyrefly: ignore [missing-import]
                    from expression_db import is_expression_done
                if is_expression_done(script_id):
                    continue

                status = script.get("status", {})
                if status.get("voice_generation") == "done" and status.get("image_generation") == "done":
                    if args.force or status.get("video_assembly") != "done":
                        pending.append(script)

        if not pending:
            scope_label = f" ({target_video_type.upper()})" if target_video_type else ""
            if target_script_ids:
                print(f"None of the target script(s) are pending for video assembly (already assembled or missing prerequisites). Use --force to regenerate.")
            else:
                print(f"No pending scripts for video assembly{scope_label}.")

            if selected_mode in ("group_range", "fun_facts", "ready_scripts") and not args.auto:
                try:
                    create_more = input("\nDo you want to select another group or scope of scripts? [y/N]: ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    return 0
                if create_more in ("y", "yes"):
                    if selected_mode == "fun_facts":
                        target_script_ids = prompt_fun_facts_mode(require_existing_state=True, base_dir=base_dir)
                    elif selected_mode == "ready_scripts":
                        target_script_ids = prompt_ready_scripts_mode(require_existing_state=True, base_dir=base_dir)
                    else:
                        target_script_ids = prompt_group_range(require_existing_state=True, base_dir=base_dir)
                    if target_script_ids:
                        continue
            return 0

        print(f"\nFound {len(pending)} pending script(s) for video assembly:")
        print(f"Target IDs: {', '.join([s['id'] for s in pending[:12]])}{'...' if len(pending) > 12 else ''}\n")

        remembered_dialects = {}
        if args.dialect:
            remembered_dialects["english"] = args.dialect
            remembered_dialects["spanish"] = args.dialect

        success_count = 0
        for i, script in enumerate(pending, start=1):
            try:
                print(f"[{i}/{len(pending)}] Assembling Script ID: {script['id']}...")
                if process_script(
                    script,
                    state_manager,
                    transcriber=transcriber,
                    builder=builder,
                    assembler=assembler,
                    base_dir=base_dir,
                    regenerate_subtitles=not args.keep_subtitles,
                    auto=args.auto,
                    dialect=args.dialect,
                    remembered_dialects=remembered_dialects,
                ):
                    success_count += 1
                else:
                    print(f"Failed to assemble video for {script['id']}", file=sys.stderr)
            except Exception as exc:
                print(f"Unexpected error assembling script ID {script['id']}: {exc}", file=sys.stderr)
                traceback.print_exc()

        print(f"\n[Completed] Process complete. Successfully assembled {success_count} video(s).")

        # If in group_range, fun_facts, or ready_scripts mode, prompt whether to process more
        if selected_mode in ("group_range", "fun_facts", "ready_scripts") and not args.auto:
            try:
                create_more = input("\nDo you want to assemble more scripts? [y/N]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\nFinished video assembly session.")
                break

            if create_more in ("y", "yes"):
                if selected_mode == "fun_facts":
                    target_script_ids = prompt_fun_facts_mode(require_existing_state=True, base_dir=base_dir)
                elif selected_mode == "ready_scripts":
                    target_script_ids = prompt_ready_scripts_mode(require_existing_state=True, base_dir=base_dir)
                else:
                    target_script_ids = prompt_group_range(require_existing_state=True, base_dir=base_dir)
                if target_script_ids:
                    continue
                else:
                    break
            else:
                print("\nFinished video assembly session.")
                break
        else:
            break

    return 0 if success_count == len(pending) else 1


if __name__ == "__main__":
    sys.exit(main())
