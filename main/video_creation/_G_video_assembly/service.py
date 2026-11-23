import traceback
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from config import (
    BASE_DIR, BANK_MUSIC_DIR, GAME_IMAGES_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, WATERMARK_DIR,
    get_script_output_dir, resolve_opening_closure_paths, resolve_script_language, resolve_script_video_type,
)
from core.state_manager import StateManager
from video_creation._G_video_assembly.assembly.types import get_assembly_profile
from video_creation._G_video_assembly.core.subtitle_builder import SubtitleBuilder
from video_creation._G_video_assembly.core.transcriber import Transcriber
from video_creation._G_video_assembly.core.video_assembler import VideoAssembler


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



    print(f"[{script_id}] Notice: No background music found in bank ({lang}/{vtype}). Assembling video without BGM.")
    return None

def resolve_assembly_prerequisites(
    script_data: dict,
    base_dir: Path = BASE_DIR,
) -> tuple[bool, bool, Optional[Path], Optional[Path]]:
    """Checks whether voice and image assets exist via state status OR actual files on disk."""
    script_id = script_data["id"]
    label = (
        script_data.get("metadata", {}).get("LABEL")
        or script_data.get("prompt_params", {}).get("TARGET_LANGUAGE", "english")
    )
    script_output_dir = get_script_output_dir(script_id, label, base_dir)
    status = script_data.get("status", {}) or {}
    assets = script_data.get("assets", {}) or {}

    audio_path: Optional[Path] = None
    audio_path_str = assets.get("audio_path")
    if audio_path_str:
        cand = Path(audio_path_str)
        if cand.is_file():
            audio_path = cand
    if audio_path is None:
        cand_audio = script_output_dir / f"script_{script_id}_master.wav"
        if cand_audio.is_file():
            audio_path = cand_audio

    image_dir: Optional[Path] = None
    image_dir_str = assets.get("image_dir")
    if image_dir_str:
        cand = Path(image_dir_str)
        if cand.is_dir():
            image_dir = cand
    if image_dir is None:
        cand_images = script_output_dir / "images"
        if cand_images.is_dir():
            image_dir = cand_images

    has_voice_files = bool(
        audio_path is not None
        and audio_path.is_file()
        and (audio_path.parent / "timings.json").is_file()
    )
    has_image_files = bool(
        image_dir is not None
        and image_dir.is_dir()
        and (
            any(image_dir.glob(f"script_{script_id}_*.png"))
            or any(image_dir.glob("*.png"))
        )
    )

    has_voice = (status.get("voice_generation") == "done") or has_voice_files
    has_images = (status.get("image_generation") == "done") or has_image_files
    return has_voice, has_images, audio_path, image_dir


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

    # Verify prerequisites (status 'done' OR actual assets present on disk)
    status = script_data.get("status", {}) or {}
    has_voice, has_images, resolved_audio, resolved_images = resolve_assembly_prerequisites(
        script_data, base_dir=base_dir
    )
    if not has_voice:
        print(f"Error: Voice generation for {script_id} is not marked as done and audio/timings are missing on disk.")
        return False
    if not has_images:
        print(f"Error: Image generation for {script_id} is not marked as done and scene images are missing on disk.")
        return False

    if status.get("voice_generation") != "done":
        print(f"[{script_id}] Notice: voice_generation is '{status.get('voice_generation', 'missing')}' in state, but audio/timings exist on disk — proceeding.")
    if status.get("image_generation") != "done":
        print(f"[{script_id}] Notice: image_generation is '{status.get('image_generation', 'missing')}' in state, but scene images exist on disk — proceeding.")

    assets = script_data.setdefault("assets", {})
    if resolved_audio is None:
        print(f"Error: Missing master audio for script {script_id}")
        return False
    if not assets.get("audio_path") or not Path(assets["audio_path"]).is_file():
        assets["audio_path"] = str(resolved_audio)

    if resolved_images is None:
        print(f"Error: Missing image directory for script {script_id}")
        return False
    if not assets.get("image_dir") or not Path(assets["image_dir"]).is_dir():
        assets["image_dir"] = str(resolved_images)

    audio_path = resolved_audio
    image_dir = resolved_images

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
        try:
            rel_open = str(Path(opening_path).resolve().relative_to(Path(base_dir).resolve())).replace("\\", "/")
        except ValueError:
            rel_open = str(opening_path)
        script_data.setdefault("assets", {})["opening_card"] = rel_open
    if closure_path:
        try:
            rel_close = str(Path(closure_path).resolve().relative_to(Path(base_dir).resolve())).replace("\\", "/")
        except ValueError:
            rel_close = str(closure_path)
        script_data.setdefault("assets", {})["closure_card"] = rel_close
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

                target_expr = (
                    script_data.get("prompt_params", {}).get("target_expression")
                    or script_data.get("content_metadata", {}).get("target_expression")
                    or script_data.get("prompt_params", {}).get("EXPRESSION")
                    or script_data.get("content_metadata", {}).get("topic")
                )
                if target_expr and isinstance(target_expr, str) and len(target_expr) < 60:
                    initial_prompt = target_expr.strip()
                else:
                    initial_prompt = None

            words = transcriber.transcribe(audio_path, language=whisper_lang, initial_prompt=initial_prompt)

            # 2. Build Subtitles
            suppress_windows = []
            resolved_lang = resolve_script_language(script_data)
            vtype = resolve_script_video_type(script_data)
            assembly_profile = get_assembly_profile(vtype or script_id)
            suppressed_secs = (
                assembly_profile.get_suppress_subtitle_sections()
                if assembly_profile is not None
                else ({"challenge"} if vtype == "game" else set())
            )

            timings_data = None
            if timings_path.exists():
                import json
                try:
                    with timings_path.open("r", encoding="utf-8") as tf:
                        timings_data = json.load(tf)
                except Exception as e:
                    print(f"[{script_id}] Warning reading timings map: {e}")

            if suppressed_secs and timings_data:
                for sec_name in sorted(suppressed_secs):
                    if sec_name in timings_data:
                        ch_start = timings_data[sec_name].get("start", 0.0)
                        ch_end = timings_data[sec_name].get("end", 0.0)
                        suppress_windows.append((ch_start, ch_end))
                        print(f"[{script_id}] Subtitles suppressed during {sec_name.upper()} section ({ch_start}s - {ch_end}s)")

            builder.build_ass(
                words,
                ass_path,
                VIDEO_WIDTH,
                VIDEO_HEIGHT,
                suppress_windows=suppress_windows,
                script_data=script_data,
                timings_data=timings_data,
                video_type=vtype,
                language=resolved_lang,
            )
            print(f"Generated subtitles at {ass_path.name}")

        # 3. Assemble Video
        if resolve_script_video_type(script_data) == "game":
            try:
                from _C_image_generation.core.chalkboard_renderer import render_chalkboard_image
                content_meta = script_data.get("content_metadata", {})
                nested_meta = (
                    content_meta.get("content_metadata", {})
                    if isinstance(content_meta.get("content_metadata"), dict)
                    else {}
                )
                exercise_text = (
                    nested_meta.get("chalkboard_exercise")
                    or content_meta.get("chalkboard_exercise")
                    or content_meta.get("script", {}).get("challenge", "")
                )
                game_images = GAME_IMAGES_DIR if base_dir == BASE_DIR else base_dir / "input" / "images" / "game_images"
                chalkboard_model = game_images / "empty_chalkboard.png"
                if exercise_text and chalkboard_model.exists():
                    challenge_img_path = image_dir / f"script_{script_id}_challenge.png"
                    render_chalkboard_image(
                        empty_chalkboard_path=chalkboard_model,
                        exercise_text=exercise_text,
                        dest_path=challenge_img_path,
                        target_size=(VIDEO_WIDTH, VIDEO_HEIGHT),
                    )
                    print(f"[{script_id}] Synced chalkboard image from state: {challenge_img_path.name}")
            except Exception as cb_exc:
                print(f"[{script_id}] Warning syncing chalkboard image: {cb_exc}")

        if assembler is None:
            assembler = VideoAssembler()

        resolved_lang = resolve_script_language(script_data)
        vtype = resolve_script_video_type(script_data)
        final_video_path = script_output_dir / f"script_{script_id}_final.mp4"

        with TemporaryDirectory(prefix=".assembly-", dir=script_output_dir) as staging_dir:
            staged_video = Path(staging_dir) / final_video_path.name
            success = assembler.assemble(
                script_id, timings_path, image_dir, audio_path, ass_path, staged_video,
                bgm_path=bgm_path, watermark_path=watermark_path,
                opening_path=opening_path, closure_path=closure_path,
                video_type=vtype,
                script_data=script_data,
                language=resolved_lang,
            )
            if success:
                if not staged_video.is_file() or staged_video.stat().st_size == 0:
                    raise OSError(f"Assembler did not produce a video: {staged_video}")
                staged_video.replace(final_video_path)

        if success:
            script_data["assets"]["final_video"] = str(final_video_path)
            script_data["status"]["video_assembly"] = "done"
            state_manager.save_script_state(script_id, script_data)

        return success
    except Exception as exc:
        print(f"Error processing script {script_id}: {exc}")
        traceback.print_exc()
        return False
