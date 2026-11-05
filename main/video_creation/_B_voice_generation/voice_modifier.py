import argparse
import random
import re
import shutil
import sys
import traceback
from pathlib import Path

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
    from video_creation._B_voice_generation.core.kokoro_engine import get_kokoro_engine
    from video_creation._B_voice_generation.core.audio_processor import concatenate_audios
    from video_creation._B_voice_generation.core.stress_enhancer import (
        enhance_stress_text_for_tts,
        build_stress_style_directive,
        detect_intentional_stress_errors
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
    from core.kokoro_engine import get_kokoro_engine
    from core.audio_processor import concatenate_audios
    from core.stress_enhancer import (
        enhance_stress_text_for_tts,
        build_stress_style_directive,
        detect_intentional_stress_errors
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

def main():
    parser = argparse.ArgumentParser(description="Modify or regenerate voice for a specific script.")
    parser.add_argument("--script-id", type=str, default=None, help="Script ID to modify (e.g. EE04, 1, script_1.json)")
    parser.add_argument("--candidates", type=int, default=None, help="Number of candidate takes to generate for stress-vital segments (default: 2)")
    parser.add_argument(
        "--engine",
        type=str,
        default="auto",
        choices=["auto", "kokoro", "qwen3", "hybrid"],
        help="Voice synthesis engine override (default: 'auto' uses VOICE_ENGINE_BY_LANGUAGE)"
    )
    args = parser.parse_args()

    script_id_raw = args.script_id
    if not script_id_raw:
        try:
            script_id_raw = input("Enter the script number to change (e.g. 1 or EE04): ").strip()
        except EOFError:
            print("Run this script interactively or supply --script-id.")
            return

    script_id = script_id_raw.replace("script_", "").replace(".json", "")
    
    base_dir = BASE_DIR
    state_manager = StateManager(base_dir)
    
    script_data = state_manager.get_script_state(script_id)
    
    if not script_data.get("script_text"):
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
    
    script_output_dir = get_script_output_dir(script_id, clean_language, base_dir)
    script_output_dir.mkdir(parents=True, exist_ok=True)
    
    kokoro_engine = get_kokoro_engine()
    kokoro_ready = bool(kokoro_engine and kokoro_engine.is_ready)

    comfy_client = None
    try:
        print("Checking ComfyUI connection...")
        require_services(comfy=True)
        comfy_client = ComfyClient(COMFY_API_URL, VOICE_WORKFLOW_PATH, COMFY_OUTPUT_DIR)
    except ConnectionError as e:
        if kokoro_ready and args.engine != "qwen3":
            print(f"[Notice] ComfyUI offline ({e}); continuing with local Kokoro-82M engine.")
        else:
            print(f"Error: {e}")
            return
        
    voice_manager = VoiceManager(OPEN_SWARA_DIR, COMFY_INPUT_DIR)
    
    segments = get_script_segments(script_id, script_text, label)
    if not segments:
        print(f"Error: Script {script_id} has no valid segments.")
        return
        
    unique_speakers = list(set(seg["speaker"] for seg in segments))
    
    manual_genders = {}
    manual_voice_paths = {}
    try:
        choose_manual = timed_input(
            "Do you want to choose the voices manually? (y/n) [default: n]: ",
            timeout=10.0,
            default="n",
            default_msg="Automatically keeping default voice assignment."
        ).strip().lower()
        if choose_manual == 'y':
            print(f"\nManual Voice Casting for Language: {clean_language.upper()}")
            for speaker in unique_speakers:
                while True:
                    g = input(f"Gender for '{speaker}' (male/female): ").strip().lower()
                    if g in ['male', 'female']:
                        manual_genders[speaker] = g
                        break
                    else:
                        print("Invalid input. Please enter 'male' or 'female'.")

                pool = voice_manager.get_available_voices(clean_language, g)
                if pool:
                    print(f"  Available reference voices for {speaker} ({clean_language} - {g}):")
                    max_display = min(len(pool), 10)
                    for i, v_path in enumerate(pool[:max_display], 1):
                        print(f"    [{i}] {v_path.name}")
                    if len(pool) > max_display:
                        print(f"    ... and {len(pool) - max_display} more available voices in pool.")
                    pick = input(f"  Select voice [1-{max_display}], enter filename, or press Enter for random: ").strip()
                    if pick:
                        if pick.isdigit() and 1 <= int(pick) <= len(pool):
                            manual_voice_paths[speaker] = pool[int(pick) - 1]
                            print(f"  -> Selected: {manual_voice_paths[speaker].name}")
                        else:
                            matched = [p for p in pool if pick.lower() in p.name.lower()]
                            if matched:
                                manual_voice_paths[speaker] = matched[0]
                                print(f"  -> Selected: {manual_voice_paths[speaker].name}")
                            else:
                                print(f"  -> Voice '{pick}' not found in pool. Using random from {clean_language} pool.")
    except (KeyboardInterrupt, EOFError):
        pass

    speakers_gender = script_data.get("content_metadata", {}).get("speakers_gender", {})
    speakers_voice = script_data.get("content_metadata", {}).get("speakers_voice", {})
    
    effective_genders = {**speakers_gender, **manual_genders}
    voice_manager.assign_voices_for_script(unique_speakers, clean_language, manual_genders=effective_genders, manual_voice_paths=manual_voice_paths)
    
    is_multi_spk = len(unique_speakers) > 1
    used_kokoro_voices = set()
    for speaker in unique_speakers:
        gender, abs_path, _ = voice_manager.get_speaker_voice(speaker, clean_language)
        is_spk_diag = "narrator" not in speaker.lower()
        eng_name, k_voice = voice_manager.resolve_engine_for_speaker(
            clean_language,
            gender=gender,
            speaker=speaker,
            is_dialogue=is_spk_diag,
            cli_engine_override=args.engine,
            kokoro_available=kokoro_ready,
            is_multi_speaker_script=is_multi_spk,
        )
        speakers_gender[speaker] = gender
        if eng_name == "kokoro" and k_voice:
            if k_voice in used_kokoro_voices:
                k_voice = f"{k_voice}_alt" if not k_voice.endswith("_alt") else f"{k_voice[:-4]}_narrator"
            used_kokoro_voices.add(k_voice)
            speakers_voice[speaker] = k_voice
            print(f"Assigned new voice for '{speaker}': {gender} -> {k_voice} (Kokoro-82M)")
        else:
            if abs_path:
                speakers_voice[speaker] = abs_path.name
            rel_path = abs_path.name if abs_path else "Fallback"
            print(f"Assigned new voice for '{speaker}': {gender} -> {rel_path}")

    if "content_metadata" not in script_data:
        script_data["content_metadata"] = {}
    script_data["content_metadata"]["speakers_gender"] = speakers_gender
    script_data["content_metadata"]["speakers_voice"] = speakers_voice
    state_manager.save_script_state(script_id, script_data)
        
    video_type = (
        script_data.get("content_metadata", {}).get("video_type")
        or script_data.get("prompt_params", {}).get("VIDEO_TYPE")
        or ""
    ).upper()
    is_game = video_type == "GAME" or any(s.get("section") in ["challenge", "pressure"] for s in segments)
    is_roleplay = video_type == "ROLEPLAY" or any("dialogue" in (s.get("section") or "").lower() for s in segments)
    is_script_stress_vital = is_stress_pronunciation_vital(script_data)

    segments_to_concat = []
    
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
        seg_engine, kokoro_voice = voice_manager.resolve_engine_for_speaker(
            clean_language,
            gender=gender,
            speaker=speaker,
            is_dialogue=is_dialogue,
            cli_engine_override=args.engine,
            kokoro_available=kokoro_ready,
            is_multi_speaker_script=is_multi_spk,
        )
        if seg_engine == "kokoro" and speakers_voice.get(speaker) and not str(speakers_voice[speaker]).endswith(".wav"):
            kokoro_voice = speakers_voice[speaker]

        output_prefix = f"audio/script_{script_id}_{idx:02d}_{speaker.replace(' ', '_')}"
        dest_filename = f"segment_{idx:02d}_{speaker.replace(' ', '_')}.flac"
        dest_path = script_output_dir / dest_filename

        if seg_engine == "kokoro" and kokoro_ready:
            seg_emotion = infer_dialogue_emotion(speaker, text, emotion, section=seg.get("section"), is_game=is_game)
            seg_energy = map_emotion_to_energy(seg_emotion)
            print(f"[{speaker}] Engine: Kokoro-82M (Voice: {kokoro_voice}, Gender: {gender}) | Emotion: '{seg_emotion}' | Energy: '{seg_energy}'")
            res_path = kokoro_engine.synthesize_text(
                text=text,
                output_path=dest_path,
                language=clean_language,
                voice=kokoro_voice,
                gender=gender,
                emotion=seg_emotion,
                energy=seg_energy,
                section=seg.get("section"),
                speaker=speaker,
            )
            if res_path and dest_path.exists():
                score, passes_gate, issues, metrics = evaluate_voice_take(
                    dest_path, target_text=text, language=clean_language
                )
                print(
                    f"  [Kokoro Quality Gate]: Score: {score:.2f} | PitchVar: {metrics['pitch_variance']*100:.1f}% | "
                    f"Tempo: {metrics['cps']} c/s"
                )
                segments_to_concat.append({
                    "path": dest_path,
                    "section": seg["section"],
                    "speaker": speaker
                })
                continue
            else:
                print(f"  [Warning] Kokoro synthesis failed for segment {idx}; falling back to Qwen3-TTS...")

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

        target_text = text
        detected_stress_words = []
        if is_seg_stress_vital:
            target_text, detected_stress_words = enhance_stress_text_for_tts(text, language=language)
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
            print("The previous master voice file has been replaced.")
            if "assets" not in script_data:
                script_data["assets"] = {}
            script_data["assets"]["audio_path"] = str(merged_file)
            script_data["status"]["voice_generation"] = "done"
            state_manager.save_script_state(script_id, script_data)
            
            for seg in segments_to_concat:
                try:
                    if seg["path"].exists():
                        seg["path"].unlink()
                except Exception:
                    pass
            
            voice_manager.cleanup_comfy_input()
            
    except Exception as exc:
        print(f"Error during audio merge: {exc}")

if __name__ == "__main__":
    main()
