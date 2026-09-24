import argparse
import sys
import traceback
from pathlib import Path

# Add project root, video_creation, and module directory to path
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
for p in [str(PROJECT_ROOT), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
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
    from core.state_manager import StateManager
except (ImportError, ModuleNotFoundError):
    # pyrefly: ignore [missing-import]
    from state_manager import StateManager

try:
    from video_creation._B_voice_generation.core.script_parser import get_script_segments
    from video_creation._B_voice_generation.core.comfy_client import ComfyClient
    from video_creation._B_voice_generation.core.voice_manager import VoiceManager
    from video_creation._B_voice_generation.core.audio_processor import concatenate_audios
except (ImportError, ModuleNotFoundError):
    try:
        from core.script_parser import get_script_segments
        from core.comfy_client import ComfyClient
        from core.voice_manager import VoiceManager
        from core.audio_processor import concatenate_audios
    except (ImportError, ModuleNotFoundError):
        # pyrefly: ignore [missing-import]
        from _B_voice_generation.core.script_parser import get_script_segments
        # pyrefly: ignore [missing-import]
        from _B_voice_generation.core.comfy_client import ComfyClient
        # pyrefly: ignore [missing-import]
        from _B_voice_generation.core.voice_manager import VoiceManager
        # pyrefly: ignore [missing-import]
        from _B_voice_generation.core.audio_processor import concatenate_audios

def infer_dialogue_emotion(speaker: str, text: str, explicit_emotion: str = None, section: str = None, is_game: bool = False) -> str:
    """Infers rich acting emotions from dialogue text, section role, and punctuation."""
    if explicit_emotion and explicit_emotion.lower() not in ["neutral", "none", "", "normal"]:
        return explicit_emotion
        
    t = text.lower()
    spk = speaker.lower()
    sec = (section or "").lower()
    
    if is_game:
        if "hook" in sec:
            return "vibrant, enthusiastic, and electrifying trivia host bursting with excitement and game-show spirit"
        elif "challenge" in sec:
            return "clear, articulate, and engaging quizmaster presenting a puzzle"
        elif "pressure" in sec:
            return "tense, dramatic game-show suspense and countdown anticipation"
        elif "answer" in sec:
            return "triumphant, celebratory, and excited game-show answer reveal"
        elif "explanation" in sec:
            return "charismatic, warm, and highly encouraging language mentor"

    if "narrator" in spk:
        if "hook" in sec or any(w in t for w in ["panic", "crazy", "stop", "secret", "hack", "danger", "attention", "incroyable", "cuidado", "racing", "weird", "terrified", "hear", "attenzione", "incredibile"]):
            return "dramatic, intriguing, and suspenseful"
        if sec in ["mystery", "clues", "setup"]:
            return "intriguing, playful, and mysterious language detective"
        if sec in ["discovery", "reveal", "surprise"]:
            return "fascinated, delighted, and wonderfully surprised"
        if sec in ["example", "explanation"]:
            return "natural, conversational, and lively, demonstrating a real-life situation"
        if sec in ["fact_1", "fact_2", "fact_3", "item_1", "item_2", "item_3", "comparison_a", "comparison_b"]:
            return "engaging, punchy, and lively storyteller sharing a curious discovery"
        if sec in ["thinking_time"]:
            return "playful, suspenseful countdown with high curiosity"
        if "payoff" in sec or "cta" in sec or any(w in t for w in ["remember", "next time", "follow", "try it", "learn", "ricorda", "tocca a te"]):
            return "charismatic, warm, and highly encouraging"
        return "confident, energetic, and engaging"
        
    # Dialogue characters (Person One, Person Two, roleplay characters)
    # 1. Nervousness, anxiety, stage fright
    if any(w in t for w in ["shaking", "panic", "can't believe", "nervous", "stage fright", "scared", "afraid", "tremble", "peur", "miedo", "nervioso", "angoisse", "paura", "ansia", "agitato", "tremando"]):
        return "anxious, nervous, and trembling with stage fright"
        
    # 2. Confusion, suspicion, disbelief, questioning
    if any(w in t for w in ["what does that even mean", "bad luck", "what?", "quoi", "qué", "comment", "really?", "de verdad", "cosa?", "davvero?", "sul serio?"]):
        return "confused, bewildered, and questioning"
        
    # 3. Reassurance, comfort, soothing
    if any(w in t for w in ["calm down", "remember this", "don't worry", "relax", "t'inquiète", "tranquilo", "respira", "calme-toi", "calmati", "non ti preoccupare", "rilassati"]):
        return "warm, reassuring, and comforting"
        
    # 4. Encouragement, inspiration, cheering
    if any(w in t for w in ["shine", "got this", "do a great job", "no!", "good luck", "bonne chance", "buena suerte", "briller", "tu peux le faire", "buona fortuna", "in bocca al lupo", "ce la puoi fare", "forza"]):
        return "cheerful, enthusiastic, and highly encouraging"
        
    # 5. Relief, discovery, gratitude
    if any(w in t for w in ["oh!", "get it now", "thanks", "feel a lot better", "relieved", "merci", "compris", "soulagé", "gracias", "alivio", "grazie", "meno male", "sollevato"]):
        return "relieved, thankful, and genuinely happy"
        
    # 6. High excitement, cheering, celebration
    if any(w in t for w in ["superstar", "go get 'em", "go get them", "awesome", "crush it", "vas-y", "génial", "vamos", "campeón", "fantastico", "bravissimo", "campione", "grandioso"]):
        return "excited, cheering, and hyped up"
        
    # Punctuation heuristics
    if "?" in text:
        return "curious, engaged, and questioning"
    if "!" in text:
        return "expressive, spirited, and energetic"
        
    return "natural, expressive, and lively"

def map_emotion_to_energy(emotion: str) -> str:
    if not emotion:
        return "high"
    emo_lower = emotion.lower()
    if any(k in emo_lower for k in ["superstar", "go get", "furious", "screaming", "hyped", "crier", "shouting", "electrifying", "bursting", "trivia host"]):
        return "very high"
    elif any(k in emo_lower for k in ["whisper", "sad", "hesitant", "chuchot", "quizmaster"]):
        return "medium"
    return "high"

def process_script(
    script_data: dict,
    state_manager: StateManager,
    comfy_client: ComfyClient,
    voice_manager: VoiceManager,
    force: bool,
    base_dir: Path
) -> bool:
    script_id = script_data["id"]
    script_text = script_data.get("script_text", "")
    metadata = script_data.get("metadata", {})
    label = metadata.get("LABEL", "english")
    
    script_output_dir = get_script_output_dir(script_id, label, base_dir)
    script_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean up old audio files to prevent reusing stale segments if script changed
    for old_file in script_output_dir.glob("*.flac"):
        try:
            old_file.unlink()
        except Exception:
            pass
    for old_file in script_output_dir.glob("*.wav"):
        try:
            old_file.unlink()
        except Exception:
            pass
    
    print("=" * 60)
    print(f"Processing Script ID: {script_id}")
    print(f"Label: {label}")
    print("=" * 60)
    
    segments = get_script_segments(script_id, script_text, label)
    if not segments:
        print(f"Error: Script {script_id} has no valid segments.")
        return False
        
    print(f"Found {len(segments)} segments to synthesize.")
    
    unique_speakers = list(set(seg["speaker"] for seg in segments))
    voice_manager.assign_voices_for_script(unique_speakers, label)
    
    # Save the assigned genders into the script state for image generation
    speakers_gender = {}
    for spk in unique_speakers:
        gender, _, _ = voice_manager.get_speaker_voice(spk, label)
        speakers_gender[spk] = gender
        
    if "content_metadata" not in script_data:
        script_data["content_metadata"] = {}
    script_data["content_metadata"]["speakers_gender"] = speakers_gender
    state_manager.save_script_state(script_id, script_data)
    
    video_type = (
        script_data.get("content_metadata", {}).get("video_type")
        or script_data.get("prompt_params", {}).get("VIDEO_TYPE")
        or ""
    ).upper()
    is_game = video_type == "GAME" or any(s.get("section") in ["challenge", "pressure"] for s in segments)

    segments_to_concat = []
    
    for seg in segments:
        idx = seg["index"]
        speaker = seg["speaker"]
        text = seg["text"]
        emotion = seg["emotion"]
        language = seg["language"]
        is_dialogue = seg["is_dialogue"]
        sec_name = (seg.get("section") or "").lower()
        
        print(f"\n--- Segment {idx}/{len(segments)} [{speaker}] ({language}) ---")
        
        gender, ref_voice_path, seed = voice_manager.get_speaker_voice(speaker, language)
        ref_filename = voice_manager.prepare_voice_in_comfy(ref_voice_path)
        
        if is_game and "narrator" in speaker.lower():
            if "hook" in sec_name:
                context = f"Vibrant, charismatic TV trivia show host presenting an educational quiz in {language}"
                style = "electrifying game show host delivery, bold dynamic vocal projection, energetic high-spirited broadcast cadence, punchy and enthusiastic, magnetic trivia spirit, charismatic and inviting"
            elif "challenge" in sec_name:
                context = f"Articulate quizmaster presenting a multiple-choice question clearly to viewers in {language}"
                style = "deliberate articulate broadcast pacing, clear and steady cadence, distinct pauses between options, engaging quizmaster delivery, never rushed"
            elif "pressure" in sec_name:
                context = f"Suspenseful game show host leading an intense countdown in {language}"
                style = "deliberate dramatic suspense cadence, steady countdown urgency, gripping anticipation, building intense pressure, dramatic and measured delivery, not rushed"
            elif "answer" in sec_name:
                context = f"Enthusiastic game show host revealing the correct answer in {language}"
                style = "triumphant celebratory delivery, joyful game show reveal cadence, energetic and punchy intonation"
            else:
                context = f"Charismatic language coach explaining the answer in {language}"
                style = "crisp energetic delivery, upbeat broadcast cadence, charismatic and encouraging, clear dynamic intonation"
        else:
            char_personalities = script_data.get("content_metadata", {}).get("character_personalities", {})
            speaker_personality = char_personalities.get(speaker, "")
            if not speaker_personality and "narrator" in speaker.lower():
                speaker_personality = STATIC_NARRATOR_PERSONALITY

            context = (
                f"Character '{speaker}' ({speaker_personality}) in a {language} conversational dialogue"
                if (is_dialogue and speaker_personality)
                else (f"Narrator ({speaker_personality}) presenting in {language}" if speaker_personality
                      else (f"Character '{speaker}' participating in a {language} conversational dialogue" if is_dialogue
                            else f"Narrator introducing a language learning topic in {language}"))
            )
            # Upbeat, fast-paced conversational style to avoid sleepy audiobook reading
            style = (
                "crisp energetic delivery, upbeat broadcast cadence, lively conversational tempo, fast and engaging, clear dynamic intonation, natural and punchy"
                if not is_dialogue
                else "lively, fast-paced authentic dialogue, upbeat and spontaneous conversational tempo, quick natural cadence, expressive human intonation, energetic roleplay"
            )

        emotion = infer_dialogue_emotion(speaker, text, emotion, section=seg.get("section"), is_game=is_game)
        energy = map_emotion_to_energy(emotion)
        pers_log = f" | Persona: '{context}'" if context else ""
        print(f"[{speaker}] Acting tone: '{emotion}' | Energy: '{energy}'{pers_log}")
        
        output_prefix = f"audio/script_{script_id}_{idx:02d}_{speaker.replace(' ', '_')}"
        dest_filename = f"segment_{idx:02d}_{speaker.replace(' ', '_')}.flac"
        dest_path = script_output_dir / dest_filename
        
        if dest_path.exists() and not force:
            print(f"Audio segment already exists at {dest_path.name}. Skipping API call.")
        else:
            try:
                comfy_client.generate_voice_segment(
                    ref_audio_name=ref_filename,
                    target_text=text,
                    language=language,
                    gender=gender,
                    context=context,
                    emotion=emotion,
                    energy=energy,
                    style=style,
                    output_prefix=output_prefix,
                    dest_path=dest_path,
                    seed=seed
                )
            except Exception as exc:
                print(f"API Error on segment {idx}: {exc}", file=sys.stderr)
                return False
                
        segments_to_concat.append({
            "path": dest_path,
            "section": seg["section"],
            "speaker": speaker
        })
        
    print(f"\nSyntheses complete. Merging {len(segments_to_concat)} segments...")
    master_path = script_output_dir / f"script_{script_id}_master.wav"
    
    try:
        merged_file = concatenate_audios(
            segments_metadata=segments_to_concat,
            output_path=master_path
        )
        if merged_file:
            print(f"Successfully generated master audio: {merged_file}")
            # Update state manager
            script_data["assets"]["audio_path"] = str(merged_file)
            script_data["status"]["voice_generation"] = "done"
            state_manager.save_script_state(script_id, script_data)
            
            # Cleanup intermediate segment files
            for seg in segments_to_concat:
                try:
                    if seg["path"].exists():
                        seg["path"].unlink()
                except Exception:
                    pass
            
            # Cleanup ComfyUI input references
            voice_manager.cleanup_comfy_input()
            
            return True
    except Exception as exc:
        print(f"Error during audio merge: {exc}", file=sys.stderr)
        
    return False

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
        help="Target scripts from <date>_ready_scripts.csv (default checks D:\\AI\\output\\connectivity\\ready_scripts/)"
    )
    args = parser.parse_args()
    
    base_dir = BASE_DIR
    state_manager = StateManager(base_dir)
    
    workflow_template_path = VOICE_WORKFLOW_PATH
    if not workflow_template_path.exists():
        print(f"Error: Could not locate template {workflow_template_path}", file=sys.stderr)
        return 1
            
    comfy_client = ComfyClient(COMFY_API_URL, workflow_template_path, COMFY_OUTPUT_DIR)
    try:
        print("Checking AI services connection (ComfyUI & LLM)...")
        require_services(comfy=True, llm=True)
        print("AI services connection verified.")
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Production Mode Selection: Mass-produce (default in 10s), Specific ID, Group Range, Fun Facts, CSV List, or Ready Scripts CSV
    # pyrefly: ignore [missing-import]
    from core.cli_prompt import (
        prompt_production_mode,
        prompt_group_range,
        prompt_fun_facts_mode,
        prompt_ready_scripts_mode,
    )

    is_cli_fun_facts = args.fun_facts_only or (args.video_type and args.video_type.lower() == "fun_facts")

    if is_cli_fun_facts and not args.script_id and args.csv_list is None and args.ready_scripts_csv is None:
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
        )
        if is_cli_fun_facts:
            selected_mode = "fun_facts"

    voice_manager = VoiceManager(OPEN_SWARA_DIR, COMFY_INPUT_DIR)

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
            # pyrefly: ignore [missing-import]
            from core.status_tracker import get_status_tracker
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
                    
                # pyrefly: ignore [missing-import]
                from core.expression_db import is_expression_done
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

            if selected_mode in ("group_range", "fun_facts") and not args.auto:
                try:
                    create_more = input("\nDo you want to select another group or scope of scripts? [y/N]: ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    return 0
                if create_more in ("y", "yes"):
                    if selected_mode == "fun_facts":
                        target_script_ids = prompt_fun_facts_mode(require_existing_state=True, base_dir=base_dir)
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
                if process_script(script, state_manager, comfy_client, voice_manager, args.force, base_dir):
                    success_count += 1
                else:
                    print(f"Failed to generate voice for script ID {script['id']}.", file=sys.stderr)
                    return 1
            except Exception as exc:
                print(f"Unexpected error processing script ID {script['id']}: {exc}", file=sys.stderr)
                traceback.print_exc()
                return 1
                
        print(f"\n[Completed] Process complete. Successfully voiced {success_count} script(s).")

        # If in group_range or fun_facts mode, prompt whether to process more
        if selected_mode in ("group_range", "fun_facts") and not args.auto:
            try:
                create_more = input("\nDo you want to voice more scripts? [y/N]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\nFinished voice generation session.")
                break

            if create_more in ("y", "yes"):
                if selected_mode == "fun_facts":
                    target_script_ids = prompt_fun_facts_mode(require_existing_state=True, base_dir=base_dir)
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
