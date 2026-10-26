import argparse
import random
import re
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
    from video_creation._B_voice_generation.core.audio_processor import concatenate_audios
    from video_creation._B_voice_generation.core.stress_enhancer import enhance_stress_text_for_tts, build_stress_style_directive
    from video_creation._B_voice_generation.core.acoustic_evaluator import select_best_voice_candidate
except (ImportError, ModuleNotFoundError):
    try:
        from core.script_parser import get_script_segments
        from core.comfy_client import ComfyClient
        from core.voice_manager import VoiceManager
        from core.audio_processor import concatenate_audios
        from core.stress_enhancer import enhance_stress_text_for_tts, build_stress_style_directive
        from core.acoustic_evaluator import select_best_voice_candidate
    except (ImportError, ModuleNotFoundError):
        # pyrefly: ignore [missing-import]
        from _B_voice_generation.core.script_parser import get_script_segments
        # pyrefly: ignore [missing-import]
        from _B_voice_generation.core.comfy_client import ComfyClient
        # pyrefly: ignore [missing-import]
        from _B_voice_generation.core.voice_manager import VoiceManager
        # pyrefly: ignore [missing-import]
        from _B_voice_generation.core.audio_processor import concatenate_audios
        # pyrefly: ignore [missing-import]
        from _B_voice_generation.core.stress_enhancer import enhance_stress_text_for_tts, build_stress_style_directive
        # pyrefly: ignore [missing-import]
        from _B_voice_generation.core.acoustic_evaluator import select_best_voice_candidate

def is_stress_pronunciation_vital(script_data: dict, text: str = "") -> bool:
    """Detects if a script or specific segment requires vital stress pronunciation or phonetic precision.
    
    Checks:
    1. Capitalized syllable stress notation in text (e.g. 'REcord', 'reCORD', 're-CORD', 'PERmit', 'perMIT').
    2. Linguistic pronunciation, word stress, heteronym, minimal pair, or double-consonant keywords in metadata.
    3. Excludes false positives from non-linguistic / psychological stress (e.g. 'stress des examens').
    """
    metadata = script_data.get("metadata", {})
    label = metadata.get("LABEL", "").lower()
    prompt_params = script_data.get("prompt_params", {})
    content_metadata = script_data.get("content_metadata", {})

    # 1. First priority: Check if text contains capitalized syllable stress notation
    # (e.g. REcord, reCORD, re-CORD, PERmit, perMIT)
    stress_pattern = r'\b[a-z]+[A-Z]{2,}\b|\b[A-Z]{2,}[a-z]+\b|\b[a-zA-Z]+-[A-Z]{2,}\b|\b[A-Z]{2,}-[a-zA-Z]+\b'
    if text and re.search(stress_pattern, text):
        m = re.findall(stress_pattern, text)
        if any(w not in ("XIXe", "XVIIIe", "XXe", "A-NN") for w in m):
            return True

    full_script = script_data.get("script_text", "")
    if isinstance(full_script, dict):
        full_text = str(full_script)
    else:
        full_text = str(full_script)
    if full_text and re.search(stress_pattern, full_text):
        m = re.findall(stress_pattern, full_text)
        if any(w not in ("XIXe", "XVIIIe", "XXe", "A-NN") for w in m):
            return True

    # 2. Check linguistic pronunciation / phonetic / rhythm keywords in metadata
    subject = str(prompt_params.get("SUBJECT", "")).lower()
    lex_field = str(prompt_params.get("LEXICAL_FIELD", "")).lower()
    topic = str(content_metadata.get("topic", "")).lower()
    category = str(content_metadata.get("category", "")).lower()
    subcategory = str(content_metadata.get("subcategory", "")).lower()
    obj = str(content_metadata.get("learning_objective", "")).lower()

    meta_text = f"{label} {subject} {lex_field} {topic} {category} {subcategory} {obj}".lower()

    # Check for non-linguistic / psychological stress false positives (e.g. exam stress, managing anxiety)
    is_psych_stress = any(p in meta_text for p in [
        "stress des examens", "gestion du stress", "gérer le stress", "stressé par",
        "situation de stress", "high-stress situation", "situations de stress", "ansia", "panico"
    ])

    linguistic_terms = [
        "word stress", "syllable stress", "heteronym", "minimal pair", "sound shift",
        "pronunciation", "prononciation", "pronuncia", "pronunciación",
        "doppie consonanti", "accento", "dizione", "phonetic", "fonetica", "fonética",
        "rhythm", "rythme", "cadenza vocale", "acoustic contrast"
    ]

    has_linguistic = any(term in meta_text for term in linguistic_terms)
    if has_linguistic:
        if is_psych_stress:
            return any(k in f"{category} {subcategory} {subject}" for k in ["pronunciation", "phonetic", "doppie", "fonet"])
        return True

    return False

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

def main():
    parser = argparse.ArgumentParser(description="Modify or regenerate voice for a specific script.")
    parser.add_argument("--script-id", type=str, default=None, help="Script ID to modify (e.g. EE04, 1, script_1.json)")
    parser.add_argument("--candidates", type=int, default=None, help="Number of candidate takes to generate for stress-vital segments (default: 2)")
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
    
    # Check if script actually exists / has text
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
    
    print("Checking ComfyUI connection...")
    try:
        require_services(comfy=True)
    except ConnectionError as e:
        print(f"Error: {e}")
        return
    comfy_client = ComfyClient(COMFY_API_URL, VOICE_WORKFLOW_PATH, COMFY_OUTPUT_DIR)
        
    voice_manager = VoiceManager(OPEN_SWARA_DIR, COMFY_INPUT_DIR)
    
    segments = get_script_segments(script_id, script_text, label)
    if not segments:
        print(f"Error: Script {script_id} has no valid segments.")
        return
        
    unique_speakers = list(set(seg["speaker"] for seg in segments))
    
    # Prompt for manual voice casting / gender selection
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

    # Get previously assigned genders
    speakers_gender = script_data.get("content_metadata", {}).get("speakers_gender", {})
    
    # Assign NEW voices, strictly enforcing distinct genders for characters, and proper Narrator logic
    voice_manager.assign_voices_for_script(unique_speakers, clean_language, manual_genders, manual_voice_paths)
    
    for speaker in unique_speakers:
        gender, abs_path, _ = voice_manager.get_speaker_voice(speaker, clean_language)
        speakers_gender[speaker] = gender
        rel_path = abs_path.name if abs_path else "Fallback"
        print(f"Assigned new voice for '{speaker}': {gender} -> {rel_path}")

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
        ref_filename = voice_manager.prepare_voice_in_comfy(ref_voice_path)
        if is_game and "narrator" in speaker.lower():
            if is_seg_stress_vital and "challenge" in sec_name:
                context = f"Articulate quizmaster presenting a clear pronunciation and word stress challenge in {language}"
                style = (
                    "deliberate articulate broadcast pacing, clear and steady cadence, distinct pauses between options, engaging quizmaster delivery. "
                    "Crucial pronunciation directive: Deliver educational focus words with crystal-clear syllable stress and authentic vowel reduction."
                )
            elif is_seg_stress_vital and "answer" in sec_name:
                context = f"Triumphant game show host explaining the correct syllable stress in {language}"
                style = (
                    "triumphant celebratory delivery, joyful game show reveal cadence with crystal-clear pronunciation. "
                    "Deliver correct syllable stress with unmistakable clarity and authentic vowel reduction."
                )
            elif "hook" in sec_name:
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

        target_text = text
        detected_stress_words = []
        if is_seg_stress_vital:
            target_text, detected_stress_words = enhance_stress_text_for_tts(text, language=language)
            style = build_stress_style_directive(detected_stress_words, language=language, base_style=style)
            if target_text != text or detected_stress_words:
                print(f"  [TTS Stress Enhanced]: '{target_text}' (Target words: {detected_stress_words})")

        if is_seg_stress_vital and (not emotion or emotion.lower() in ["neutral", "none", "", "normal"]):
            emotion = "articulate, enthusiastic, and deliberate pronunciation mentor"
        else:
            emotion = infer_dialogue_emotion(speaker, text, emotion, section=seg.get("section"), is_game=is_game)
        energy = map_emotion_to_energy(emotion)
        pers_log = f" | Persona: '{context}'" if context else ""
        print(f"[{speaker}] Acting tone: '{emotion}' | Energy: '{energy}'{pers_log}")
        
        # Determine candidate sampling count:
        if args.candidates is not None:
            seg_candidates = max(1, args.candidates)
        elif is_seg_stress_vital and detected_stress_words:
            seg_candidates = 2
        else:
            seg_candidates = 1

        output_prefix = f"audio/script_{script_id}_{idx:02d}_{speaker.replace(' ', '_')}"
        dest_filename = f"segment_{idx:02d}_{speaker.replace(' ', '_')}.flac"
        dest_path = script_output_dir / dest_filename
        
        try:
            if seg_candidates > 1 and is_seg_stress_vital and detected_stress_words:
                candidate_paths = []
                for take_idx in range(seg_candidates):
                    take_seed = seed + (take_idx * 101)
                    take_prefix = f"{output_prefix}_take{take_idx+1}"
                    take_filename = f"segment_{idx:02d}_{speaker.replace(' ', '_')}_take{take_idx+1}.flac"
                    take_path = script_output_dir / take_filename
                    print(f"  [Take #{take_idx+1}/{seg_candidates}]: Generating candidate with seed {take_seed}...")
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
            # Update state manager
            if "assets" not in script_data:
                script_data["assets"] = {}
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
            
    except Exception as exc:
        print(f"Error during audio merge: {exc}")

if __name__ == "__main__":
    main()
