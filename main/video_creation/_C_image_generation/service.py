from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Optional

from config import (
    BASE_DIR, GAME_IMAGES_DIR, IMAGE_DEFAULT_STEPS, IMAGE_DEFAULT_WIDTH,
    IMAGE_DEFAULT_HEIGHT, IMAGE_STALL_TIMEOUT, get_script_output_dir, resolve_static_scene_path,
)
from core.llama_manager import ensure_llama_running, ensure_llama_stopped
from core.state_manager import StateManager, resolve_lang_and_type
from video_creation._B_voice_generation.core.script_parser import parse_sections
from video_creation._C_image_generation.core.chalkboard_renderer import render_chalkboard_image
from video_creation._C_image_generation.core.comfy_client import ImageComfyClient
from video_creation._C_image_generation.core.prompt_builder import (
    VisualPromptBuilder,
    resolve_anchor_environment,
    resolve_cultural_world,
    sanitize_and_style_prompt,
    get_speaker_gender_safe,
    resolve_default_speakers_gender,
    persist_character_anchors_in_state,
)

logger = logging.getLogger(__name__)


def ensure_image_prompts_for_script(
    script_data: dict,
    state_manager: StateManager,
    prompt_builder: VisualPromptBuilder,
    force: bool = False,
    base_dir: Optional[Path] = None,
    preserve_general_prompt: bool = False,
) -> bool:
    """Pre-generates and persists general_prompt and storyboard image_prompts in state if missing or forced.

    When ``preserve_general_prompt=True`` and a non-empty ``general_prompt`` already exists in state,
    that saved general prompt is kept intact while scene-specific storyboard prompts are regenerated
    from it (and character anchors are refreshed from it).
    """
    script_id = script_data["id"]
    script_text = script_data.get("script_text", "")
    metadata = script_data.get("metadata", {})
    resolved_lang, resolved_type = resolve_lang_and_type(script_id, script_data)
    label = metadata.get("LABEL") or resolved_lang
    video_type = (
        script_data.get("content_metadata", {}).get("video_type")
        or script_data.get("prompt_params", {}).get("VIDEO_TYPE")
        or metadata.get("VIDEO_TYPE")
        or resolved_type
        or "EXPRESSION"
    ).upper()

    # Establish character genders without interactive timer delay
    speakers_gender = script_data.get("content_metadata", {}).get("speakers_gender", {})
    if not isinstance(speakers_gender, dict):
        speakers_gender = {}

    if video_type == "ROLEPLAY":
        speakers_gender = resolve_default_speakers_gender(speakers_gender, video_type="ROLEPLAY")
        if "content_metadata" not in script_data or not isinstance(script_data["content_metadata"], dict):
            script_data["content_metadata"] = {}
        script_data["content_metadata"]["speakers_gender"] = speakers_gender
        state_manager.save_script_state(script_id, script_data)

    sections = parse_sections(script_text)
    if not sections:
        logger.warning("[%s] No sections found in script.", script_id)
        return False

    # For GAME shorts, LLM storyboard prompts are generated for 'hook', 'answer', and 'explanation'.
    # 'challenge' is rendered as native chalkboard, 'pressure' is static Tito waiting.
    # 'explanation' has its own unique cultural immersion prompt to guarantee zero duplicate images.
    VALID_PROMPT_GAME_SECTIONS = {"hook", "answer", "explanation"}
    VALID_ROLEPLAY_SECTIONS = {"hook", "dialogue_part_1", "dialogue_part_2", "dialogue_part_3", "dialogue_part_4", "payoff"}
    METADATA_IGNORE_KEYS = {
        "title", "difficulty", "emotion", "game_type", "related_content",
        "category", "subcategory", "topic", "learning_objective",
        "chalkboard_exercise", "target_expression", "roleplay_scenario"
    }

    valid_active_sections = {
        k.strip().lower() for k, v in sections.items()
        if k.strip().lower() not in METADATA_IGNORE_KEYS
        and (video_type != "GAME" or k.strip().lower() in VALID_PROMPT_GAME_SECTIONS)
        and (video_type != "ROLEPLAY" or k.strip().lower() in VALID_ROLEPLAY_SECTIONS)
        and v.strip()
    }

    content_meta = script_data.get("content_metadata", {})
    prompt_params = script_data.get("prompt_params", {})
    character_personalities = content_meta.get("character_personalities", None)

    topic = (
        prompt_params.get("EXPRESSION")
        or prompt_params.get("ROLEPLAY_SCENARIO")
        or prompt_params.get("TOPIC")
        or content_meta.get("topic")
        or content_meta.get("target_expression")
        or ""
    )
    scenario = (
        content_meta.get("roleplay_scenario")
        or prompt_params.get("ROLEPLAY_SCENARIO")
        or prompt_params.get("CONTEXT")
        or content_meta.get("learning_objective")
        or ""
    )
    lexical_field = (
        prompt_params.get("LEXICAL_FIELD")
        or content_meta.get("subcategory")
        or content_meta.get("category")
        or ""
    )

    general_prompt = (script_data.get("assets", {}).get("general_prompt") or "").strip()
    reuse_existing_gp = bool(general_prompt) and (preserve_general_prompt or not force)

    if force:
        if isinstance(script_data.get("assets"), dict):
            script_data["assets"].pop("character_anchors", None)
            if not reuse_existing_gp:
                script_data["assets"].pop("anchor_world_id", None)
                script_data["assets"].pop("anchor_world_title", None)
        if isinstance(content_meta, dict):
            content_meta.pop("character_anchors", None)
            if not reuse_existing_gp:
                content_meta.pop("anchor_environment", None)

    if reuse_existing_gp:
        anchor_environment = general_prompt
    else:
        ensure_llama_running()
        cultural_world = resolve_cultural_world(
            script_text=script_text,
            topic=topic,
            scenario=scenario,
            lexical_field=lexical_field,
            label=label,
            video_type=video_type,
            language=resolved_lang or label,
            script_id=script_id,
        )
        anchor_environment = resolve_anchor_environment(
            script_text=script_text,
            topic=topic,
            scenario=scenario,
            lexical_field=lexical_field,
            label=label,
            video_type=video_type,
            language=resolved_lang or label,
            script_id=script_id,
        )
        try:
            general_prompt = prompt_builder.build_general_prompt(
                script_text=script_text,
                label=label,
                script_id=script_id,
                speakers_gender=speakers_gender,
                video_type=video_type,
                character_personalities=character_personalities,
                topic=topic,
                scenario=scenario,
                lexical_field=lexical_field,
                anchor_environment=anchor_environment,
            )
            if "assets" not in script_data or not isinstance(script_data["assets"], dict):
                script_data["assets"] = {}
            script_data["assets"]["general_prompt"] = general_prompt
            if cultural_world is not None:
                script_data["assets"]["anchor_world_id"] = cultural_world.id
                script_data["assets"]["anchor_world_title"] = cultural_world.title
            if "content_metadata" not in script_data or not isinstance(script_data["content_metadata"], dict):
                script_data["content_metadata"] = {}
            script_data["content_metadata"]["anchor_environment"] = general_prompt
            state_manager.save_script_state(script_id, script_data)
        except Exception as exc:
            logger.warning("[%s] Failed to build general prompt: %s; falling back to anchor_environment", script_id, exc)
            general_prompt = anchor_environment
        anchor_environment = general_prompt

    if "content_metadata" not in script_data or not isinstance(script_data["content_metadata"], dict):
        script_data["content_metadata"] = {}
    script_data["content_metadata"]["anchor_environment"] = general_prompt
    persist_character_anchors_in_state(
        script_data=script_data,
        general_prompt=general_prompt,
        speakers_gender=speakers_gender,
        video_type=video_type,
    )

    existing_prompts = script_data.get("assets", {}).get("image_prompts", {})
    all_scenes_have_prompts = (
        isinstance(existing_prompts, dict)
        and all(
            sec.strip().lower() in existing_prompts and existing_prompts[sec.strip().lower()]
            for sec in valid_active_sections
        )
    )

    if all_scenes_have_prompts and not force:
        return True

    sections_for_storyboard = {
        k: v for k, v in sections.items()
        if k.strip().lower() in valid_active_sections
    }

    cast_meta = script_data.get("cast", {}) if isinstance(script_data.get("cast"), dict) else {}
    character_anchors = (
        content_meta.get("character_anchors")
        or cast_meta.get("character_anchors")
        or (script_data.get("assets", {}).get("character_anchors") if isinstance(script_data.get("assets"), dict) else None)
        or prompt_params.get("CHARACTER_ANCHORS")
    )
    ensure_llama_running()
    storyboard_prompts = prompt_builder.build_storyboard_prompts(
        script_text=script_text,
        label=label,
        sections=sections_for_storyboard,
        script_id=script_id,
        speakers_gender=speakers_gender,
        video_type=video_type,
        character_personalities=character_personalities,
        topic=topic,
        scenario=scenario,
        lexical_field=lexical_field,
        anchor_environment=anchor_environment,
        general_prompt=general_prompt,
        character_anchors=character_anchors,
    )
    if not storyboard_prompts:
        raise ValueError(f"[{script_id}] LLM failed to produce storyboard visual prompts.")
    if "assets" not in script_data or not isinstance(script_data["assets"], dict):
        script_data["assets"] = {}
    script_data["assets"]["image_prompts"] = storyboard_prompts
    state_manager.save_script_state(script_id, script_data)
    return True


def process_script(
    script_data: dict,
    state_manager: StateManager,
    comfy_client: ImageComfyClient,
    prompt_builder: VisualPromptBuilder,
    force: bool,
    seed: int,
    base_dir: Path,
    check_cancelled: Any | None = None,
) -> bool:
    script_id = script_data["id"]
    script_text = script_data.get("script_text", "")
    metadata = script_data.get("metadata", {})
    resolved_lang, resolved_type = resolve_lang_and_type(script_id, script_data)
    label = metadata.get("LABEL") or resolved_lang
    video_type = (
        script_data.get("content_metadata", {}).get("video_type")
        or script_data.get("prompt_params", {}).get("VIDEO_TYPE")
        or metadata.get("VIDEO_TYPE")
        or resolved_type
        or "EXPRESSION"
    ).upper()

    print("=" * 60)
    print(f"Processing Script ID: {script_id} for Images [{video_type}]")
    print(f"Label: {label}")
    print("=" * 60)

    # 1. Ensure visual prompts exist
    ensure_image_prompts_for_script(
        script_data=script_data,
        state_manager=state_manager,
        prompt_builder=prompt_builder,
        force=False,
        base_dir=base_dir,
    )

    # 2. Release LLM VRAM before batch generation in ComfyUI
    ensure_llama_stopped()

    # 3. Setup output directory and parse sections
    script_output_dir = get_script_output_dir(script_id, label, base_dir) / "images"
    script_output_dir.mkdir(parents=True, exist_ok=True)
    
    sections = parse_sections(script_text)
    if not sections:
        logger.warning("[%s] No sections found in script.", script_id)
        return False

    # For GAME shorts, 5 scenes make up the timeline:
    # ComfyUI produces 2 scenes ('hook' and 'answer').
    # 'challenge' is rendered as native chalkboard, 'pressure' is static Tito waiting,
    # and 'explanation' reuses the 'answer' image to maintain visual continuity.
    VALID_GAME_SECTIONS = {"hook", "challenge", "pressure", "answer", "explanation"}
    VALID_ROLEPLAY_SECTIONS = {"hook", "dialogue_part_1", "dialogue_part_2", "dialogue_part_3", "dialogue_part_4", "payoff"}
    METADATA_IGNORE_KEYS = {
        "title", "difficulty", "emotion", "game_type", "related_content",
        "category", "subcategory", "topic", "learning_objective",
        "chalkboard_exercise", "target_expression", "roleplay_scenario"
    }

    valid_active_sections = {
        k.strip().lower() for k, v in sections.items()
        if k.strip().lower() not in METADATA_IGNORE_KEYS
        and (video_type != "GAME" or k.strip().lower() in VALID_GAME_SECTIONS)
        and (video_type != "ROLEPLAY" or k.strip().lower() in VALID_ROLEPLAY_SECTIONS)
        and v.strip()
    }

    # Clean up any stale/orphaned images from obsolete schemas
    for old_img in script_output_dir.glob(f"script_{script_id}_*.png"):
        sec_name = old_img.stem[len(f"script_{script_id}_"):].lower()
        if sec_name not in valid_active_sections:
            try:
                old_img.unlink()
                logger.info("[%s] Cleaned up obsolete legacy image: %s", script_id, old_img.name)
            except Exception:
                pass

    content_meta = script_data.get("content_metadata", {})
    prompt_params = script_data.get("prompt_params", {})
    storyboard_prompts = dict(script_data.get("assets", {}).get("image_prompts", {}))
    general_prompt = script_data.get("assets", {}).get("general_prompt", "")
    character_personalities = content_meta.get("character_personalities", None)
    speakers_gender = content_meta.get("speakers_gender", {})
    anchor_environment = content_meta.get("anchor_environment", "")

    topic = (
        prompt_params.get("EXPRESSION")
        or prompt_params.get("ROLEPLAY_SCENARIO")
        or prompt_params.get("TOPIC")
        or content_meta.get("topic")
        or content_meta.get("target_expression")
        or ""
    )
    scenario = (
        content_meta.get("roleplay_scenario")
        or prompt_params.get("ROLEPLAY_SCENARIO")
        or prompt_params.get("CONTEXT")
        or content_meta.get("learning_objective")
        or ""
    )
    lexical_field = (
        prompt_params.get("LEXICAL_FIELD")
        or content_meta.get("subcategory")
        or content_meta.get("category")
        or ""
    )

    success = True
    comfy_tasks = []

    for section_name, section_text in sections.items():
        sec_lower = section_name.strip().lower()
        if sec_lower in METADATA_IGNORE_KEYS:
            continue
        if video_type == "GAME" and sec_lower not in VALID_GAME_SECTIONS:
            continue
        if video_type == "ROLEPLAY" and sec_lower not in VALID_ROLEPLAY_SECTIONS:
            continue
        if not section_text.strip():
            continue
            
        scene_filename = f"script_{script_id}_{section_name}.png"
        dest_path = script_output_dir / scene_filename

        if dest_path.exists() and not force:
            logger.info("[%s] Image for %s already exists: %s â€” skipping.", script_id, section_name, dest_path.name)
            continue

        # Specialized handling for GAME: PRESSURE (Centralized static pre-made image â€” zero-copy)
        if video_type == "GAME" and section_name.lower() == "pressure":
            static_img = resolve_static_scene_path(
                section_name=section_name,
                script_data=script_data,
                language=label,
                video_type=video_type,
                base_dir=base_dir,
            )
            if static_img and static_img.exists():
                print(f"[OK] Section 'PRESSURE' resolved via centralized static asset: {static_img.name} (zero-copy skipped).")
                continue
            else:
                logger.warning(f"Could not find static waiting image for {script_id}, falling back to generation.")

        # Specialized handling for GAME: CHALLENGE (Native high-resolution chalk typography on empty_chalkboard.png)
        if video_type == "GAME" and section_name.lower() == "challenge":
            game_images = GAME_IMAGES_DIR if base_dir == BASE_DIR else base_dir / "input" / "images" / "game_images"
            chalkboard_model = game_images / "empty_chalkboard.png"
            if chalkboard_model.exists():
                exercise_text = content_meta.get("chalkboard_exercise", "")
                if not exercise_text:
                    exercise_text = section_text.strip()

                print(f"[Chalkboard Renderer] Generating high-resolution chalk challenge image...")
                print(f"Chalkboard Exercise Text:\n{exercise_text}")
                try:
                    render_chalkboard_image(
                        empty_chalkboard_path=chalkboard_model,
                        exercise_text=exercise_text,
                        dest_path=dest_path,
                        target_size=(IMAGE_DEFAULT_WIDTH, IMAGE_DEFAULT_HEIGHT)
                    )
                    print(f"[OK] Chalkboard challenge image saved: {dest_path.name}")
                    continue
                except Exception as exc:
                    logger.error("[%s] Native chalkboard rendering failed: %s. Falling back to Z-Image.", script_id, exc)

        visual_prompt = storyboard_prompts.get(sec_lower) or storyboard_prompts.get(section_name)
        if not visual_prompt:
            try:
                visual_prompt = prompt_builder.build_visual_prompt(
                    script_text=script_text,
                    label=label,
                    scene_name=section_name,
                    scene_text=section_text,
                    script_id=script_id,
                    speakers_gender=speakers_gender,
                    video_type=video_type,
                    character_personalities=character_personalities,
                    topic=topic,
                    scenario=scenario,
                    lexical_field=lexical_field,
                    anchor_environment=anchor_environment,
                    existing_scene_prompts=storyboard_prompts,
                    general_prompt=general_prompt,
                )
                storyboard_prompts[sec_lower] = visual_prompt
                script_data["assets"]["image_prompts"][sec_lower] = visual_prompt
                state_manager.save_script_state(script_id, script_data)
            except Exception as exc:
                logger.error("[%s] Failed to generate visual prompt for %s: %s", script_id, section_name, exc)
                success = False
                continue
        
        visual_prompt = sanitize_and_style_prompt(visual_prompt)
        print(f"\n[Visual Prompt - {section_name.upper()}]:\n\"{visual_prompt}\"\n")

        filename_prefix = f"Z-Image/script_{script_id}_{section_name}"
        comfy_tasks.append({
            "section_name": section_name,
            "prompt_text": visual_prompt,
            "filename_prefix": filename_prefix,
            "dest_path": dest_path,
            "seed": seed,
            "steps": IMAGE_DEFAULT_STEPS,
            "width": IMAGE_DEFAULT_WIDTH,
            "height": IMAGE_DEFAULT_HEIGHT,
        })

    # Batch execute all ComfyUI image tasks in a continuous FIFO queue
    if comfy_tasks and success:
        print(f"\n[ComfyUI Batch Pipeline] Enqueueing {len(comfy_tasks)} scene(s) for '{script_id}' into continuous FIFO queue...")
        for t in comfy_tasks:
            print(f"  â€¢ Enqueued scene: {t['section_name'].upper()}")

        def _on_batch_progress(sec_name: str, completed_cnt: int, total_cnt: int, dur: float) -> None:
            print(f"[OK] Scene {sec_name.upper()} rendered in {dur:.1f}s [{completed_cnt}/{total_cnt} completed] -> script_{script_id}_{sec_name}.png")
            state_manager.save_script_state(script_id, script_data)

        try:
            comfy_client.generate_images_batch(
                tasks=comfy_tasks,
                stall_timeout=IMAGE_STALL_TIMEOUT,
                progress_callback=_on_batch_progress,
                check_cancelled=check_cancelled,
            )
        except InterruptedError:
            print(f"[{script_id}] ComfyUI batch rendering cancelled.")
            return False
        except Exception as exc:
            logger.error("[%s] Unexpected batch generation error: %s", script_id, exc)
            success = False

    if success:
        script_data["assets"]["image_dir"] = str(script_output_dir)
        script_data["status"]["image_generation"] = "done"
        state_manager.save_script_state(script_id, script_data)
        
    return success
