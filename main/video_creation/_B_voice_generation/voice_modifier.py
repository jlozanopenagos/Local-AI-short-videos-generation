import argparse
import random
import re
import shutil
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root, video_creation, core, and module directory to path
MODULE_DIR = Path(__file__).parent.resolve()
VIDEO_CREATION_DIR = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
for p in [str(PROJECT_ROOT), str(CORE_DIR), str(VIDEO_CREATION_DIR), str(MODULE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    # pyrefly: ignore [missing-import]
    from core.cli_prompt import timed_input
except (ImportError, ModuleNotFoundError):
    try:
        # pyrefly: ignore [missing-import]
        from cli_prompt import timed_input
    except (ImportError, ModuleNotFoundError):
        def timed_input(prompt: str, timeout: float = 10.0, default: str = "", default_msg: str = None) -> str:
            try:
                val = input(prompt).strip()
                return val if val else default
            except (KeyboardInterrupt, EOFError):
                return default

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
    from video_creation._B_voice_generation.core.script_parser import get_script_segments
    from video_creation._B_voice_generation.core.comfy_client import ComfyClient
    from video_creation._B_voice_generation.core.voice_manager import VoiceManager
    from video_creation._B_voice_generation.core.audio_processor import concatenate_audios
    from video_creation._B_voice_generation.core.stress_enhancer import (
        enhance_stress_text_for_tts,
        build_stress_style_directive,
        detect_intentional_stress_errors,
        normalize_multiple_choice_options_for_tts,
    )
    from video_creation._B_voice_generation.core.acoustic_evaluator import (
        select_best_voice_candidate,
        select_best_general_candidate,
        evaluate_voice_take
    )
    from video_creation._B_voice_generation.main import (
        is_stress_pronunciation_vital,
        EMOTION_TRANSLATION_MAP,
        infer_dialogue_emotion,
        map_emotion_to_energy,
    )
except (ImportError, ModuleNotFoundError):
    from core.script_parser import get_script_segments
    from core.comfy_client import ComfyClient
    from core.voice_manager import VoiceManager
    from core.audio_processor import concatenate_audios
    from core.stress_enhancer import (
        enhance_stress_text_for_tts,
        build_stress_style_directive,
        detect_intentional_stress_errors,
        normalize_multiple_choice_options_for_tts,
    )
    from core.acoustic_evaluator import (
        select_best_voice_candidate,
        select_best_general_candidate,
        evaluate_voice_take
    )
    from main import (
        is_stress_pronunciation_vital,
        EMOTION_TRANSLATION_MAP,
        infer_dialogue_emotion,
        map_emotion_to_energy,
    )


def resolve_user_script_id(raw_input: str, state_manager: StateManager) -> Optional[str]:
    """Resolves raw user input into a valid canonical Script ID (e.g. ER114, EE01, 114)."""
    cleaned = raw_input.strip().upper().replace("SCRIPT_", "").replace(".JSON", "")
    if not cleaned:
        return None

    if state_manager.script_exists(cleaned):
        return cleaned

    # Match numeric indices (e.g. '114' or '04')
    if cleaned.isdigit():
        padded = f"{int(cleaned):02d}"
        all_scripts = state_manager.get_all_scripts()
        matches = [
            s.get("id") for s in all_scripts
            if s.get("id") and s.get("id").endswith(padded)
        ]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            print(f"\nMultiple scripts match index '{cleaned}': {', '.join(matches[:8])}")
            print("Please enter the full canonical ID (e.g. ER114, EE04).")

    return None


def parse_gender_token(token: str, default: str = "male") -> str:
    """Normalizes raw input tokens ('m', 'f', 'male', 'female', etc.) to 'male' or 'female'."""
    t = str(token).strip().lower()
    if t in ("f", "female", "girl", "woman"):
        return "female"
    if t in ("m", "male", "boy", "man"):
        return "male"
    return default


def prompt_speaker_genders(
    unique_speakers: List[str],
    current_genders: Dict[str, str],
    video_type: str,
    cli_genders: Optional[str] = None
) -> Dict[str, str]:
    """Interactively prompts the user to select the gender ('genre') for each speaker.
    Users only choose genders; reference voices are automatically randomized from the pool.
    """
    # Separate characters from narrator for structured roleplay prompts
    characters = [s for s in unique_speakers if "narrator" not in s.lower()]
    narrators = [s for s in unique_speakers if "narrator" in s.lower()]
    ordered_speakers = characters + narrators

    # 1. Handle CLI override if supplied (e.g. --genders "male, female" or --genders "f")
    if cli_genders:
        tokens = [t.strip().lower() for t in cli_genders.split(",") if t.strip()]
        result = {}
        for idx, spk in enumerate(ordered_speakers):
            fallback = current_genders.get(spk, "female" if "two" in spk.lower() else "male")
            if idx < len(tokens):
                result[spk] = parse_gender_token(tokens[idx], fallback)
            else:
                result[spk] = fallback
        return result

    # 2. Interactive display and prompting
    print("\n" + "-" * 60)
    print("SPEAKER GENDER SELECTION (Voices will be randomly cast):")
    for idx, spk in enumerate(ordered_speakers, 1):
        curr = current_genders.get(spk, "female" if "two" in spk.lower() else "male").lower()
        role_label = " (Dialogue Character)" if "narrator" not in spk.lower() else " (Storyteller / Mentor)"
        print(f"  [{idx}] {spk:12s}: {curr.upper()}{role_label}")
    print("-" * 60)

    selected_genders = {}

    if video_type == "ROLEPLAY" and len(characters) >= 2:
        default_str = ", ".join(
            current_genders.get(s, "female" if "two" in s.lower() else "male").lower()
            for s in ordered_speakers
        )
        try:
            prompt_msg = (
                f"Enter genders for [{', '.join(ordered_speakers)}]\n"
                f"  (e.g. 'm, f, m' or 'male, female, female', Enter to keep [{default_str.upper()}]): "
            )
            raw_input = timed_input(prompt_msg, timeout=30.0, default="").strip()
            if raw_input:
                tokens = [t.strip().lower() for t in raw_input.split(",") if t.strip()]
                if len(tokens) == len(ordered_speakers):
                    for idx, spk in enumerate(ordered_speakers):
                        selected_genders[spk] = parse_gender_token(tokens[idx], current_genders.get(spk, "male"))
                    return selected_genders
        except (KeyboardInterrupt, EOFError):
            pass

    # Step-by-step fallback / confirmation per speaker
    for spk in ordered_speakers:
        curr = current_genders.get(spk, "female" if "two" in spk.lower() else "male").lower()
        prompt_msg = f"  Gender for '{spk}' [m = Male / f = Female, Enter to keep '{curr.upper()}']: "
        try:
            choice = timed_input(prompt_msg, timeout=20.0, default=curr).strip().lower()
            selected_genders[spk] = parse_gender_token(choice, curr)
        except (KeyboardInterrupt, EOFError):
            selected_genders[spk] = curr

    return selected_genders


def main():
    parser = argparse.ArgumentParser(description="Modify or regenerate voice for a specific script.")
    parser.add_argument("--script-id", type=str, default=None, help="Script ID to modify (e.g. ER114, EE04)")
    parser.add_argument("--genders", type=str, default=None, help="Comma-separated genders for speakers (e.g. 'male, female' or 'm, f, m')")
    parser.add_argument("--candidates", type=int, default=None, help="Number of candidate takes to generate for stress-vital segments (default: 2)")
    args = parser.parse_args()

    base_dir = BASE_DIR
    state_manager = StateManager(base_dir)

    print("\n" + "=" * 64)
    print("               VOICE MODIFIER & RANDOM RECASTER")
    print("=" * 64)

    # 1. Pre-flight Connection Checks (MUST run before any prompt)
    print("\n" + "=" * 64)
    print("Pre-flight Connection Checks:")
    comfy_client = None
    try:
        require_services(comfy=True)
        comfy_client = ComfyClient(COMFY_API_URL, VOICE_WORKFLOW_PATH, COMFY_OUTPUT_DIR)
        print("  [OK] Qwen3-TTS ComfyUI connected")
    except ConnectionError as e:
        print(f"  [ERROR] {e}")
        return
    print("=" * 64 + "\n")

    # 2. Resolve Script ID
    script_id = None
    if args.script_id:
        script_id = resolve_user_script_id(args.script_id, state_manager)
        if not script_id:
            print(f"Error: Script '{args.script_id}' not found.")
            return
    else:
        while not script_id:
            try:
                raw = input("Enter Video ID to modify (e.g. ER114, EE01, FG02) [or 'q' to quit]: ").strip()
            except (KeyboardInterrupt, EOFError):
                return
            if raw.lower() in ("q", "quit", "exit"):
                print("Exiting.")
                return
            script_id = resolve_user_script_id(raw, state_manager)
            if not script_id:
                print("Script not found. Please try again.")

    script_data = state_manager.get_script_state(script_id)
    if not script_data.get("script_text") and not script_data.get("content_metadata", {}).get("script"):
        print(f"Error: Script {script_id} not found or has no script_text.")
        return

    script_text = script_data.get("script_text", "")
    metadata = script_data.get("metadata", {})
    label = metadata.get("LABEL", "english")
    clean_language, _ = resolve_lang_and_type(script_id, script_data)
    if not clean_language or clean_language == "english":
        from video_creation._B_voice_generation.core.script_parser import extract_language_from_label
        extracted = extract_language_from_label(label)
        if extracted != "english":
            clean_language = extracted

    video_type = config.resolve_script_video_type(script_data).upper()
    topic = (
        script_data.get("prompt_params", {}).get("ROLEPLAY_SCENARIO")
        or script_data.get("prompt_params", {}).get("EXPRESSION")
        or script_data.get("content_metadata", {}).get("topic")
        or ""
    )

    script_output_dir = get_script_output_dir(script_id, clean_language, base_dir)
    script_output_dir.mkdir(parents=True, exist_ok=True)

    segments = get_script_segments(script_id, script_text, label)
    if not segments:
        # Fallback to structured content_metadata.script if script_text had formatting quirks
        script_dict = script_data.get("content_metadata", {}).get("script")
        if script_dict and isinstance(script_dict, dict):
            import json
            segments = get_script_segments(script_id, json.dumps(script_dict), label)
            if segments:
                script_data["script_text"] = json.dumps(script_dict, indent=2)
                state_manager.save_script_state(script_id, script_data)

    if not segments:
        print(f"Error: Script {script_id} has no valid segments.")
        return

    unique_speakers = list(set(seg["speaker"] for seg in segments))

    # Display Script Overview
    print("\n" + "=" * 64)
    print(f"🎬 SCRIPT [{script_id}] — {clean_language.upper()} / {video_type}")
    if topic:
        print(f"   Topic:    {topic[:70]}")
    print(f"   Speakers: {', '.join(unique_speakers)}")
    print("=" * 64)

    voice_manager = VoiceManager(OPEN_SWARA_DIR, COMFY_INPUT_DIR)

    # 2. Gender Selection (No manual file selection requested; user chooses genders)
    existing_genders = script_data.get("content_metadata", {}).get("speakers_gender", {})
    if not isinstance(existing_genders, dict):
        existing_genders = {}

    selected_genders = prompt_speaker_genders(
        unique_speakers=unique_speakers,
        current_genders=existing_genders,
        video_type=video_type,
        cli_genders=args.genders
    )

    print("\n-> Confirmed Genders:")
    for spk, g in selected_genders.items():
        print(f"     {spk:12s}: {g.upper()}")

    # 3. Automatic Random Voice Casting with Strict Roleplay Differentiation
    print("\n[Voice Casting] Selecting randomized distinct high-quality voices...")
    voice_manager.assign_voices_for_script(
        unique_speakers,
        clean_language,
        manual_genders=selected_genders,
        manual_voice_paths={},  # Empty dictionary ensures fresh randomized assignment
        video_type=video_type,
    )

    # ENFORCE RULE: In roleplay videos, narrator and any character sharing the same
    # gender MUST NOT share the same voice. Every speaker must have a unique reference voice.
    used_reference_names = set()
    speakers_gender = {}
    speakers_voice = {}

    # Order characters first, narrator last so narrator can adapt to avoid character voice collisions
    characters = [s for s in unique_speakers if "narrator" not in s.lower()]
    narrators = [s for s in unique_speakers if "narrator" in s.lower()]
    ordered_speakers = characters + narrators

    for speaker in ordered_speakers:
        gender, abs_path, _ = voice_manager.get_speaker_voice(speaker, clean_language)
        vname = abs_path.name if abs_path else None

        # Collision avoidance: if this reference voice was already assigned to another speaker
        if vname and (vname in used_reference_names):
            pool = voice_manager.get_available_voices(clean_language, gender)
            candidates = [p for p in pool if p.name not in used_reference_names]
            if candidates:
                # Prefer golden voices if available, or any acceptable candidate
                golden_cand = [p for p in candidates if "kokoro_golden" in p.name]
                new_vpath = random.choice(golden_cand if golden_cand else candidates)
                voice_manager.current_assignments[speaker] = (gender, new_vpath)
                abs_path = new_vpath
                vname = new_vpath.name

        if vname:
            used_reference_names.add(vname)

        speakers_gender[speaker] = gender
        if abs_path:
            speakers_voice[speaker] = abs_path.name

    print("\n" + "=" * 64)
    print("🎤 NEW VOICE CASTING:")
    for spk in ordered_speakers:
        g = speakers_gender[spk]
        v = speakers_voice.get(spk, "default")
        print(f"  - {spk:12s} ({g.upper()}): {v}")
    print("=" * 64 + "\n")

    # Update state with new voice assignments
    if "content_metadata" not in script_data:
        script_data["content_metadata"] = {}
    script_data["content_metadata"]["speakers_gender"] = speakers_gender
    script_data["content_metadata"]["speakers_voice"] = speakers_voice
    state_manager.save_script_state(script_id, script_data)

    # 4. Clean up old audio files so no stale segments linger
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

    is_game = video_type == "GAME" or any(s.get("section") in ["challenge", "pressure"] for s in segments)
    is_roleplay = video_type == "ROLEPLAY" or any("dialogue" in (s.get("section") or "").lower() for s in segments)
    is_script_stress_vital = is_stress_pronunciation_vital(script_data)

    segments_to_concat = []

    # 5. Synthesize segments
    for seg in segments:
        idx = seg["index"]
        speaker = seg["speaker"]
        text = seg["text"]
        emotion = seg["emotion"]
        language = seg["language"]
        is_dialogue = seg["is_dialogue"]
        sec_name = (seg.get("section") or "").lower()
        is_seg_stress_vital = is_script_stress_vital or is_stress_pronunciation_vital(script_data, text)

        print(f"\n--- Generating Segment {idx}/{len(segments)} [{speaker}] ({language}) ---")

        gender, ref_voice_path, seed = voice_manager.get_speaker_voice(speaker, clean_language)

        output_prefix = f"audio/script_{script_id}_{idx:02d}_{speaker.replace(' ', '_')}"
        dest_filename = f"segment_{idx:02d}_{speaker.replace(' ', '_')}.flac"
        dest_path = script_output_dir / dest_filename

        norm_text = normalize_multiple_choice_options_for_tts(text, language=clean_language)
        if norm_text != text:
            print(f"  [TTS MC Options Normalized]: '{norm_text}'")

        if comfy_client is None:
            print(f"Error: Qwen3-TTS ComfyUI is offline and needed for segment {idx}.")
            return

        ref_filename = voice_manager.prepare_voice_in_comfy(ref_voice_path)
        if is_game and "narrator" in speaker.lower():
            if is_seg_stress_vital and "challenge" in sec_name:
                context = f"Charismatic game show host presenting a clear pronunciation and word stress challenge in {language}"
                style = (
                    "lively and articulate game show host delivery, upbeat conversational tempo, distinct options with clear syllable stress. "
                    "Crucial pronunciation directive: Deliver educational focus words with authentic syllable stress and natural vowel reduction."
                )
            elif is_seg_stress_vital and "answer" in sec_name:
                context = f"Triumphant game show host explaining the correct syllable stress in {language}"
                style = (
                    "triumphant celebratory delivery, joyful game show reveal cadence with crystal-clear pronunciation. "
                    "Deliver correct syllable stress with unmistakable clarity and authentic vowel reduction."
                )
            elif "hook" in sec_name:
                context = f"Vibrant, charismatic TV trivia show host presenting an educational quiz in {language}"
                style = "electrifying game show host delivery, bold dynamic vocal projection, energetic high-spirited conversational momentum, punchy and enthusiastic, magnetic trivia spirit, charismatic and inviting, warm human flow"
            elif "challenge" in sec_name:
                context = f"Charismatic and engaging trivia host presenting a multiple-choice challenge in {language}"
                style = "lively game show host delivery, engaging conversational momentum, crisp clear presentation of options with upbeat natural cadence, lively human flow without mechanical stalling"
            elif "pressure" in sec_name:
                context = f"Suspenseful game show host leading an intense countdown in {language}"
                style = "gripping game show host countdown, dramatic suspense and urgent anticipation, building high-energy excitement, punchy and thrilling delivery"
            elif "answer" in sec_name:
                context = f"Enthusiastic game show host revealing the correct answer in {language}"
                style = "triumphant celebratory delivery, joyful game show reveal cadence, energetic punchy intonation, warm human flow"
            else:
                context = f"Charismatic language coach explaining the answer in {language}"
                style = "magnetic storyteller cadence, lively and encouraging, clear dynamic intonation, natural and punchy, warm human flow"
        else:
            char_personalities = script_data.get("content_metadata", {}).get("character_personalities", {})
            speaker_personality = char_personalities.get(speaker, "")
            if not speaker_personality and "narrator" in speaker.lower():
                speaker_personality = STATIC_NARRATOR_PERSONALITY

            if is_seg_stress_vital:
                if language.lower() == "english":
                    context = (
                        f"Charismatic language coach and pronunciation mentor demonstrating clear syllable stress in English"
                        if not is_dialogue
                        else (f"Character '{speaker}' ({speaker_personality}) practicing authentic syllable stress and pronunciation in English"
                              if speaker_personality else f"Character '{speaker}' practicing authentic syllable stress and pronunciation in English")
                    )
                    style = (
                        "deliberate articulate broadcast delivery, crystal-clear phoneme articulation, and measured educational pacing. "
                        "Crucial pronunciation directive: Deliver educational focus words with authentic syllable stress and natural vowel reduction."
                    )
                else:
                    context = (
                        f"Charismatic language coach and pronunciation mentor demonstrating clear articulation in {language}"
                        if not is_dialogue
                        else (f"Character '{speaker}' ({speaker_personality}) practicing clear pronunciation in {language}"
                              if speaker_personality else f"Character '{speaker}' practicing clear pronunciation in {language}")
                    )
                    style = (
                        "deliberate articulate broadcast delivery, crystal-clear phoneme articulation, natural rhythm, and measured educational pacing."
                    )
            else:
                if is_roleplay:
                    context = (
                        f"Charismatic storyteller ({speaker_personality}) in a {language} roleplay short"
                        if speaker_personality
                        else f"Charismatic YouTube Shorts storyteller and viral language mentor in a {language} roleplay narrative"
                    ) if not is_dialogue else (
                        f"Character '{speaker}' ({speaker_personality}) in a {language} conversational dialogue"
                        if speaker_personality else f"Character '{speaker}' participating in a {language} conversational dialogue"
                    )
                    style = (
                        "magnetic storyteller cadence, snappy conversational momentum, expressive theatrical inflection, lively and captivating rhythm, warm human flow"
                        if not is_dialogue
                        else "natural theatrical dialogue, lively conversational banter, confident engaging cadence, expressive emotional inflection, warm authentic momentum"
                    )
                else:
                    context = (
                        f"Character '{speaker}' ({speaker_personality}) in a {language} conversational dialogue"
                        if (is_dialogue and speaker_personality)
                        else (f"Narrator ({speaker_personality}) presenting in {language}" if speaker_personality
                              else (f"Character '{speaker}' participating in a {language} conversational dialogue" if is_dialogue
                                     else f"Narrator introducing a language learning topic in {language}"))
                    )
                    style = (
                        "magnetic storyteller cadence, lively conversational tempo, fast and engaging, clear dynamic intonation, natural and punchy"
                        if not is_dialogue
                        else "natural theatrical dialogue, lively conversational banter, confident engaging cadence, expressive emotional inflection, warm authentic momentum"
                    )

        target_text = normalize_multiple_choice_options_for_tts(text, language=language)
        detected_stress_words = []
        if is_seg_stress_vital:
            target_text, detected_stress_words = enhance_stress_text_for_tts(target_text, language=language)
            style = build_stress_style_directive(detected_stress_words, language=language, base_style=style, raw_text=text)
            intentional_errs = detect_intentional_stress_errors(text, detected_stress_words)
            if intentional_errs:
                err_summary = ", ".join([f"{e['token']} -> {e['visual_role']} (in {e['syntactic_role']} slot)" for e in intentional_errs])
                print(f"  [Intentional Pronunciation Error Active]: {err_summary}")
                context += f" (Character intentionally makes a pronunciation mistake on '{err_summary}' for educational contrast)"
            if target_text != text or detected_stress_words:
                print(f"  [TTS Stress Enhanced]: '{target_text}' (Target words: {detected_stress_words})")

        if is_seg_stress_vital and (not emotion or emotion.lower() in ["neutral", "none", "", "normal"]):
            emotion = "articulate, enthusiastic, and deliberate pronunciation mentor"
        else:
            emotion = infer_dialogue_emotion(speaker, text, emotion, section=seg.get("section"), is_game=is_game)
        energy = map_emotion_to_energy(emotion)
        pers_log = f" | Persona: '{context}'" if context else ""
        print(f"[{speaker}] Acting tone: '{emotion}' | Energy: '{energy}'{pers_log}")

        is_high_impact = (
            any(k in sec_name for k in ["hook", "pressure", "payoff", "cta", "reveal"])
            or (is_game and "answer" in sec_name)
            or (is_seg_stress_vital and bool(detected_stress_words))
        )

        if args.candidates is not None:
            seg_candidates = max(1, args.candidates)
        elif is_high_impact:
            seg_candidates = 2
        else:
            seg_candidates = 1

        try:
            if is_seg_stress_vital and detected_stress_words:
                candidate_paths = []
                num_takes = max(2, seg_candidates)
                for take_idx in range(num_takes):
                    take_seed = seed + (take_idx * 101)
                    take_prefix = f"{output_prefix}_take{take_idx+1}"
                    take_filename = f"segment_{idx:02d}_{speaker.replace(' ', '_')}_take{take_idx+1}.flac"
                    take_path = script_output_dir / take_filename
                    print(f"  [Take #{take_idx+1}/{num_takes}]: Generating candidate with seed {take_seed}...")
                    comfy_client.generate_voice_segment(
                        ref_audio_name=ref_filename,
                        target_text=target_text,
                        language=language,
                        gender=gender,
                        context=context,
                        emotion=emotion,
                        energy=energy,
                        style=style,
                        output_prefix=take_prefix,
                        dest_path=take_path,
                        seed=take_seed
                    )
                    candidate_paths.append(take_path)

                select_best_voice_candidate(
                    candidate_paths=candidate_paths,
                    target_words=detected_stress_words,
                    text_context=text,
                    dest_path=dest_path
                )
            elif seg_candidates > 1:
                candidate_paths = []
                for take_idx in range(seg_candidates):
                    take_seed = seed + (take_idx * 777)
                    take_prefix = f"{output_prefix}_take{take_idx+1}"
                    take_filename = f"segment_{idx:02d}_{speaker.replace(' ', '_')}_take{take_idx+1}.flac"
                    take_path = script_output_dir / take_filename
                    print(f"  [High-Impact Take #{take_idx+1}/{seg_candidates}]: Generating candidate with seed {take_seed}...")
                    comfy_client.generate_voice_segment(
                        ref_audio_name=ref_filename,
                        target_text=target_text,
                        language=language,
                        gender=gender,
                        context=context,
                        emotion=emotion,
                        energy=energy,
                        style=style,
                        output_prefix=take_prefix,
                        dest_path=take_path,
                        seed=take_seed
                    )
                    candidate_paths.append(take_path)

                select_best_general_candidate(
                    candidate_paths=candidate_paths,
                    target_text=target_text,
                    language=language,
                    dest_path=dest_path
                )
            else:
                comfy_client.generate_voice_segment(
                    ref_audio_name=ref_filename,
                    target_text=target_text,
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
                score, passes_gate, issues, metrics = evaluate_voice_take(
                    dest_path, target_text=target_text, language=language
                )
                if passes_gate:
                    print(f"  [Quality Gate]: Pass (Score: {score:.2f} | PitchVar: {metrics['pitch_variance']*100:.1f}% | Tempo: {metrics['cps']} c/s)")
                else:
                    print(f"  [Quality Gate]: Take #1 flagged: {', '.join(issues)}. Auto-retrying with seed {seed + 555}...")
                    take1_path = script_output_dir / f"segment_{idx:02d}_{speaker.replace(' ', '_')}_take1.flac"
                    take2_path = script_output_dir / f"segment_{idx:02d}_{speaker.replace(' ', '_')}_take2.flac"
                    if dest_path.exists():
                        if take1_path.exists():
                            take1_path.unlink()
                        shutil.move(str(dest_path), str(take1_path))

                    comfy_client.generate_voice_segment(
                        ref_audio_name=ref_filename,
                        target_text=target_text,
                        language=language,
                        gender=gender,
                        context=context,
                        emotion=emotion,
                        energy=energy,
                        style=style,
                        output_prefix=f"{output_prefix}_take2",
                        dest_path=take2_path,
                        seed=seed + 555
                    )
                    select_best_general_candidate(
                        candidate_paths=[take1_path, take2_path],
                        target_text=target_text,
                        language=language,
                        dest_path=dest_path
                    )
        except Exception as exc:
            print(f"API Error on segment {idx}: {exc}")
            return

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
            print(f"Successfully generated new master audio: {merged_file}")
            if "assets" not in script_data:
                script_data["assets"] = {}
            script_data["assets"]["audio_path"] = str(merged_file)
            script_data["status"]["voice_generation"] = "done"
            # Set video assembly to pending so it can be reassembled with the new audio
            script_data["status"]["video_assembly"] = "pending"
            state_manager.save_script_state(script_id, script_data)

            for seg in segments_to_concat:
                try:
                    if seg["path"].exists():
                        seg["path"].unlink()
                except Exception:
                    pass

            voice_manager.cleanup_comfy_input()
            print(f"\n[Done] Master voice for {script_id} successfully replaced. Video assembly is set to pending.")

    except Exception as exc:
        print(f"Error during audio merge: {exc}")


if __name__ == "__main__":
    main()
