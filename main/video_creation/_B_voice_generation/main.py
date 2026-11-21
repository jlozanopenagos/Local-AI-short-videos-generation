import argparse
import re
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Optional

# Add project root, video_creation, core, and module directory to path
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
for p in [str(PROJECT_ROOT), str(CORE_DIR), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# pyrefly: ignore [missing-import]
import config
# pyrefly: ignore [missing-import]
from config import (
    BASE_DIR,
    COMFY_API_URL, COMFY_OUTPUT_DIR, COMFY_INPUT_DIR,
    VOICE_WORKFLOW_PATH, OPEN_SWARA_DIR, STATIC_NARRATOR_PERSONALITY,
    require_services, get_script_output_dir
)

try:
    # pyrefly: ignore [missing-import]
    from core.state_manager import StateManager, resolve_lang_and_type
except (ImportError, ModuleNotFoundError):
    # pyrefly: ignore [missing-import]
    from state_manager import StateManager, resolve_lang_and_type

try:
    from video_creation._B_voice_generation.voice.common.orchestrator import (
        EMOTION_TRANSLATION_MAP,
        infer_dialogue_emotion,
        is_stress_pronunciation_vital,
        map_emotion_to_energy,
        synthesize_script_voice,
    )
    from video_creation._B_voice_generation.core.comfy_client import ComfyClient
    from video_creation._B_voice_generation.core.voice_manager import VoiceManager
except (ImportError, ModuleNotFoundError):
    try:
        from voice.common.orchestrator import (  # type: ignore[no-redef]
            EMOTION_TRANSLATION_MAP,
            infer_dialogue_emotion,
            is_stress_pronunciation_vital,
            map_emotion_to_energy,
            synthesize_script_voice,
        )
        from core.comfy_client import ComfyClient  # type: ignore[no-redef]
        from core.voice_manager import VoiceManager  # type: ignore[no-redef]
    except (ImportError, ModuleNotFoundError):
        # pyrefly: ignore [missing-import]
        from _B_voice_generation.voice.common.orchestrator import (
            EMOTION_TRANSLATION_MAP,
            infer_dialogue_emotion,
            is_stress_pronunciation_vital,
            map_emotion_to_energy,
            synthesize_script_voice,
        )
        # pyrefly: ignore [missing-import]
        from _B_voice_generation.core.comfy_client import ComfyClient
        # pyrefly: ignore [missing-import]
        from _B_voice_generation.core.voice_manager import VoiceManager


def process_script(
    script_data: dict,
    state_manager: StateManager,
    comfy_client: Optional[ComfyClient],
    voice_manager: VoiceManager,
    force: bool,
    base_dir: Path,
    candidates: Optional[int] = None,
    explicit_accent: Optional[str] = None,
    engine_mode: Optional[str] = None,
) -> bool:
    """Entrypoint facade delegating Stage B synthesis to `voice.common.orchestrator`."""
    return synthesize_script_voice(
        script_data=script_data,
        state_manager=state_manager,
        comfy_client=comfy_client,
        voice_manager=voice_manager,
        force=force,
        base_dir=base_dir,
        candidates=candidates,
        explicit_accent=explicit_accent,
        engine_mode=engine_mode,
    )

def main() -> int:
    parser = argparse.ArgumentParser(description="LingoVerse Shorts Voice Generator (Qwen3-TTS)")
    parser.add_argument("--script-id", type=str, default=None, help="Target specific script ID(s) (e.g. EE01, FG02 or comma-separated)")
    parser.add_argument("--force", action="store_true", help="Force regeneration even if voice is already generated")
    parser.add_argument("--auto", action="store_true", help="Auto-generate without interactive terminal prompts")
    parser.add_argument(
        "--fun-facts",
        "--fun-facts-only",
        dest="fun_facts_only",
        action="store_true",
        help="Only voice Fun Facts scripts (e.g. EF01, FF01, SF01, IF01)"
    )
    parser.add_argument(
        "--video-type",
        type=str,
        default=None,
        choices=["expression", "game", "roleplay", "fun_facts", "all"],
        help="Filter generation to specific video type"
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        choices=["all", "english", "french", "spanish", "italian"],
        help="Filter generation to specific language"
    )
    parser.add_argument(
        "--from-csv",
        "--csv-list",
        dest="csv_list",
        nargs="?",
        const="",
        default=None,
        help="Target scripts listed in CSV (default checks input/csv/voice_to_change/)"
    )
    parser.add_argument(
        "--from-ready-scripts",
        "--ready-scripts",
        dest="ready_scripts_csv",
        nargs="?",
        const="",
        default=None,
        help="Target scripts from <date>_ready_scripts.csv (default checks <OUTPUT_DIR>/connectivity/ready_scripts/)"
    )
    parser.add_argument(
        "--from-mass-ready-scripts",
        "--mass-ready-scripts",
        dest="mass_ready_scripts_csv",
        nargs="?",
        const="",
        default=None,
        help="Target scripts in mass from multiple/all ready_scripts CSVs (comma-separated file paths or empty for all)"
    )
    parser.add_argument(
        "--candidates",
        type=int,
        default=None,
        help="Number of candidate takes to sample for stress-vital segments (default: 2 for stress-vital, 1 for standard)"
    )
    parser.add_argument(
        "--accent",
        type=str,
        default=None,
        help="Optional neutral accent override (e.g. es_latam_neutral, es_spain_castilian, en_us_neutral, en_uk_neutral)"
    )
    parser.add_argument(
        "--engine",
        type=str,
        default=None,
        choices=["typed", "legacy"],
        help="Voice engine mode override ('typed' or 'legacy')"
    )
    args = parser.parse_args()
    
    base_dir = BASE_DIR
    state_manager = StateManager(base_dir)
    
    workflow_template_path = VOICE_WORKFLOW_PATH
    if not workflow_template_path.exists():
        print(f"Error: Could not locate template {workflow_template_path}", file=sys.stderr)
        return 1

    try:
        # pyrefly: ignore[missing-import]
        from core.llama_manager import ensure_llama_stopped
        ensure_llama_stopped()
    except Exception:
        pass

    try:
        require_services(comfy=True)
        comfy_client = ComfyClient(COMFY_API_URL, workflow_template_path, COMFY_OUTPUT_DIR)
        print("AI services connection (ComfyUI) verified.")
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    try:
        # pyrefly: ignore [missing-import]
        from core.cli_prompt import (
            prompt_production_mode,
            prompt_group_range,
            prompt_fun_facts_mode,
            prompt_ready_scripts_mode,
            prompt_mass_ready_scripts_mode,
        )
    except (ImportError, ModuleNotFoundError):
        # pyrefly: ignore [missing-import]
        from cli_prompt import (
            prompt_production_mode,
            prompt_group_range,
            prompt_fun_facts_mode,
            prompt_ready_scripts_mode,
            prompt_mass_ready_scripts_mode,
        )

    is_cli_fun_facts = args.fun_facts_only or (args.video_type and args.video_type.lower() == "fun_facts")

    if is_cli_fun_facts and not args.script_id and args.csv_list is None and args.ready_scripts_csv is None and args.mass_ready_scripts_csv is None:
        print("\n[CLI Option] Fun Facts mode active: targeting Fun Facts scripts only.")
        target_script_ids = None
        selected_mode = "fun_facts"
    else:
        target_script_ids, selected_mode = prompt_production_mode(
            stage_title="Part B: Voice Generation",
            asset_name="voiceovers / audio files",
            timeout=10.0,
            script_id_arg=args.script_id,
            auto=args.auto,
            require_existing_state=True,
            base_dir=base_dir,
            return_mode=True,
            allow_fun_facts_mode=True,
            allow_csv_list_mode=True,
            csv_folder_name="voice_to_change",
            csv_path_arg=args.csv_list,
            allow_ready_scripts_mode=True,
            ready_scripts_path_arg=args.ready_scripts_csv,
            allow_mass_ready_scripts_mode=True,
            mass_ready_scripts_path_arg=args.mass_ready_scripts_csv,
        )
        if is_cli_fun_facts:
            selected_mode = "fun_facts"

    voice_manager = VoiceManager(OPEN_SWARA_DIR, COMFY_INPUT_DIR)

    while True:
        target_video_type = None
        if selected_mode == "fun_facts" or args.fun_facts_only:
            target_video_type = "fun_facts"
        elif args.video_type and args.video_type.lower() != "all":
            target_video_type = args.video_type.lower()

        target_language = args.language if args.language and args.language.lower() != "all" else None

        try:
            try:
                # pyrefly: ignore [missing-import]
                from core.status_tracker import get_status_tracker
            except (ImportError, ModuleNotFoundError):
                # pyrefly: ignore [missing-import]
                from status_tracker import get_status_tracker
            tracker = get_status_tracker(base_dir)
            pending_rows = tracker.get_pending_scripts(
                "voice_generation",
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
                if status.get("script_generation") == "done":
                    if args.force or status.get("voice_generation") != "done":
                        pending.append(script)

        if not pending:
            scope_label = f" ({target_video_type.upper()})" if target_video_type else ""
            if target_script_ids:
                print(f"None of the target script(s) are pending for voice generation (already voiced or missing state). Use --force to regenerate.")
            else:
                print(f"No pending video scripts for voice generation{scope_label}.")

            if selected_mode in ("group_range", "fun_facts", "ready_scripts", "mass_ready_scripts") and not args.auto:
                try:
                    create_more = input("\nDo you want to select another group or scope of scripts? [y/N]: ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    return 0
                if create_more in ("y", "yes"):
                    if selected_mode == "fun_facts":
                        target_script_ids = prompt_fun_facts_mode(require_existing_state=True, base_dir=base_dir)
                    elif selected_mode == "ready_scripts":
                        target_script_ids = prompt_ready_scripts_mode(require_existing_state=True, base_dir=base_dir)
                    elif selected_mode == "mass_ready_scripts":
                        target_script_ids = prompt_mass_ready_scripts_mode(require_existing_state=True, base_dir=base_dir)
                    else:
                        target_script_ids = prompt_group_range(require_existing_state=True, base_dir=base_dir)
                    if target_script_ids:
                        continue
            return 0
            
        print(f"\nFound {len(pending)} pending script(s) for voice generation:")
        print(f"Target IDs: {', '.join([s['id'] for s in pending[:12]])}{'...' if len(pending) > 12 else ''}\n")
        
        success_count = 0
        for i, script in enumerate(pending, start=1):
            try:
                print(f"[{i}/{len(pending)}] Processing Script ID: {script['id']} for Voice...")
                if process_script(
                    script,
                    state_manager,
                    comfy_client,
                    voice_manager,
                    args.force,
                    base_dir,
                    candidates=args.candidates,
                    explicit_accent=args.accent,
                    engine_mode=args.engine,
                ):
                    success_count += 1
                    time.sleep(0.3)
                else:
                    print(f"Failed to generate voice for script ID {script['id']}.", file=sys.stderr)
                    return 1
            except Exception as exc:
                print(f"Unexpected error processing script ID {script['id']}: {exc}", file=sys.stderr)
                traceback.print_exc()
                return 1
                
        print(f"\n[Completed] Process complete. Successfully voiced {success_count} script(s).")

        if selected_mode in ("group_range", "fun_facts", "ready_scripts", "mass_ready_scripts") and not args.auto:
            try:
                create_more = input("\nDo you want to voice more scripts? [y/N]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\nFinished voice generation session.")
                break

            if create_more in ("y", "yes"):
                if selected_mode == "fun_facts":
                    target_script_ids = prompt_fun_facts_mode(require_existing_state=True, base_dir=base_dir)
                elif selected_mode == "ready_scripts":
                    target_script_ids = prompt_ready_scripts_mode(require_existing_state=True, base_dir=base_dir)
                elif selected_mode == "mass_ready_scripts":
                    target_script_ids = prompt_mass_ready_scripts_mode(require_existing_state=True, base_dir=base_dir)
                else:
                    target_script_ids = prompt_group_range(require_existing_state=True, base_dir=base_dir)
                if target_script_ids:
                    continue
                else:
                    break
            else:
                print("\nFinished voice generation session.")
                break
        else:
            break

    return 0

if __name__ == "__main__":
    sys.exit(main())
