import sys
import traceback
import random
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

def main():
    try:
        script_number = input("Enter the script number to change (e.g. 1): ").strip()
    except EOFError:
        print("Run this script interactively.")
        return

    script_id = script_number.replace("script_", "").replace(".json", "")
    
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
    
    script_output_dir = get_script_output_dir(script_id, label, base_dir)
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
    
    # Prompt for manual genders
    manual_genders = {}
    try:
        choose_manual = input("Do you want to choose the voices manually? (y/n): ").strip().lower()
        if choose_manual == 'y':
            print("Please enter the gender ('male' or 'female') for each character.")
            for speaker in unique_speakers:
                while True:
                    g = input(f"Gender for '{speaker}': ").strip().lower()
                    if g in ['male', 'female']:
                        manual_genders[speaker] = g
                        break
                    else:
                        print("Invalid input. Please enter 'male' or 'female'.")
    except EOFError:
        pass

    # Get previously assigned genders
    speakers_gender = script_data.get("content_metadata", {}).get("speakers_gender", {})
    
    # Assign NEW voices, strictly enforcing distinct genders for characters, and proper Narrator logic
    voice_manager.assign_voices_for_script(unique_speakers, label, manual_genders)
    
    for speaker in unique_speakers:
        gender, abs_path, _ = voice_manager.get_speaker_voice(speaker, label)
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

    segments_to_concat = []
    
    for seg in segments:
        idx = seg["index"]
        speaker = seg["speaker"]
        text = seg["text"]
        emotion = seg["emotion"]
        language = seg["language"]
        is_dialogue = seg["is_dialogue"]
        sec_name = (seg.get("section") or "").lower()
        
        print(f"\n--- Generating Segment {idx}/{len(segments)} [{speaker}] ({language}) ---")
        
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
