import argparse
import re
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

EMOTION_TRANSLATION_MAP = {
    # French
    "frustré": "intensely frustrated, exasperated, and complaining with lively reactive banter",
    "frustre": "intensely frustrated, exasperated, and complaining with lively reactive banter",
    "calme": "calm, confident, and warm conversational banter",
    "surpris": "sharp comedic surprise, incredulous and completely baffled",
    "souriant": "warm, smiling, and playfully cheerful conversational banter",
    "rassuré": "relieved, reassured, and bright friendly banter",
    "rassure": "relieved, reassured, and bright friendly banter",
    "inquiet": "anxious, worried, and breathless with urgency",
    "amusé": "amused, playful, and chuckling friendly banter",
    "amuse": "amused, playful, and chuckling friendly banter",
    "enthousiaste": "enthusiastic, cheerful, and highly energetic banter",
    "curieux": "intrigued, curious, and animated conversational tone",
    "confus": "bewildered, comedic confusion and questioning",
    "déterminé": "determined, confident, and energetic tone",
    "determine": "determined, confident, and energetic tone",
    "fier": "proud, boastful, and cheerful confident banter",
    "ironique": "witty, ironic, and playful sarcastic banter",
    "soulagé": "relieved, excited, and genuinely bright",
    "soulage": "relieved, excited, and genuinely bright",
    # Spanish
    "frustrado": "intensely frustrated, exasperated, and complaining with lively reactive banter",
    "tranquilo": "calm, confident, and warm conversational banter",
    "sorprendido": "sharp comedic surprise, incredulous and completely baffled",
    "asombrado": "sharp comedic surprise, incredulous and completely baffled",
    "sonriente": "warm, smiling, and playfully cheerful conversational banter",
    "aliviado": "relieved, reassured, and bright friendly banter",
    "tranquilizado": "relieved, reassured, and bright friendly banter",
    "preocupado": "anxious, worried, and breathless with urgency",
    "divertido": "amused, playful, and chuckling friendly banter",
    "entusiasta": "enthusiastic, cheerful, and highly energetic banter",
    "curioso": "intrigued, curious, and animated conversational tone",
    "confuso": "bewildered, comedic confusion and questioning",
    "determinado": "determined, confident, and energetic tone",
    "orgulloso": "proud, boastful, and cheerful confident banter",
    "irónico": "witty, ironic, and playful sarcastic banter",
    "ironico": "witty, ironic, and playful sarcastic banter",
    # Italian
    "frustrato": "intensely frustrated, exasperated, and complaining with lively reactive banter",
    "calmo": "calm, confident, and warm conversational banter",
    "sorpreso": "sharp comedic surprise, incredulous and completely baffled",
    "sorridente": "warm, smiling, and playfully cheerful conversational banter",
    "sollevato": "relieved, reassured, and bright friendly banter",
    "tranquillizzato": "relieved, reassured, and bright friendly banter",
    "preoccupato": "anxious, worried, and breathless with urgency",
    "divertito": "amused, playful, and chuckling friendly banter",
    "curioso": "intrigued, curious, and animated conversational tone",
    "confuso": "bewildered, comedic confusion and questioning",
    "determinato": "determined, confident, and energetic tone",
    "orgoglioso": "proud, boastful, and cheerful confident banter",
    "ironico": "witty, ironic, and playful sarcastic banter",
    "arrabbiato": "sharp, annoyed, and playfully heated banter",
    # English
    "calm": "calm, confident, and warm conversational banter",
    "frustrated": "intensely frustrated, exasperated, and complaining with lively reactive banter",
    "surprised": "sharp comedic surprise, incredulous and completely baffled",
    "smiling": "warm, smiling, and playfully cheerful conversational banter",
    "reassured": "relieved, reassured, and bright friendly banter",
    "relieved": "relieved, reassured, and bright friendly banter",
    "worried": "anxious, worried, and breathless with urgency",
    "amused": "amused, playful, and chuckling friendly banter",
    "enthusiastic": "enthusiastic, cheerful, and highly energetic banter",
    "curious": "intrigued, curious, and animated conversational tone",
    "confused": "bewildered, comedic confusion and questioning",
    "proud": "proud, boastful, and cheerful confident banter",
}

def infer_dialogue_emotion(speaker: str, text: str, explicit_emotion: str = None, section: str = None, is_game: bool = False) -> str:
    """Infers rich acting emotions from dialogue text, section role, and punctuation."""
    if explicit_emotion:
        exp_clean = explicit_emotion.lower().strip()
        if exp_clean in EMOTION_TRANSLATION_MAP:
            return EMOTION_TRANSLATION_MAP[exp_clean]
        for k, v in EMOTION_TRANSLATION_MAP.items():
            if k in exp_clean:
                return v
        if exp_clean not in ["neutral", "none", "", "normal"]:
            return explicit_emotion
        
    t = text.lower()
    spk = speaker.lower()
    sec = (section or "").lower()
    
    if is_game:
        if "hook" in sec:
            return "vibrant, enthusiastic, and electrifying trivia host bursting with excitement and game-show spirit"
        elif "challenge" in sec:
            return "lively, charismatic, and enthusiastic game-show host presenting a fun quiz challenge"
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
        return "intensely anxious, breathless, and trembling with stage fright urgency"
        
    # 2. Confusion, suspicion, disbelief, questioning
    if any(w in t for w in ["what does that even mean", "bad luck", "what?", "quoi", "qué", "comment", "really?", "de verdad", "cosa?", "davvero?", "sul serio?"]):
        return "sharp comedic disbelief, incredulous, and completely baffled"
        
    # 3. Reassurance, comfort, soothing
    if any(w in t for w in ["calm down", "remember this", "don't worry", "relax", "t'inquiète", "tranquilo", "respira", "calme-toi", "calmati", "non ti preoccupare", "rilassati"]):
        return "grounded, confident, and high-spirited encouragement"
        
    # 4. Encouragement, inspiration, cheering
    if any(w in t for w in ["shine", "got this", "do a great job", "no!", "good luck", "bonne chance", "buena suerte", "briller", "tu peux le faire", "buona fortuna", "in bocca al lupo", "ce la puoi fare", "forza"]):
        return "enthusiastic, cheerful, and highly energetic banter"
        
    # 5. Relief, discovery, gratitude
    if any(w in t for w in ["oh!", "get it now", "thanks", "feel a lot better", "relieved", "merci", "compris", "soulagé", "gracias", "alivio", "grazie", "meno male", "sollevato"]):
        return "relieved, excited, and genuinely bright"
        
    # 6. High excitement, cheering, celebration
    if any(w in t for w in ["superstar", "go get 'em", "go get them", "awesome", "crush it", "vas-y", "génial", "vamos", "campeón", "fantastico", "bravissimo", "campione", "grandioso"]):
        return "hyped up, celebratory, and shouting with excitement"
        
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
    elif any(k in emo_lower for k in ["whisper", "sad", "hesitant", "chuchot"]):
        return "medium"
    return "high"

def process_script(
    script_data: dict,
    state_manager: StateManager,
    comfy_client: ComfyClient,
    voice_manager: VoiceManager,
    force: bool,
    base_dir: Path,
    candidates: Optional[int] = None
) -> bool:
    script_id = script_data["id"]
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
    print(f"Language: {clean_language.upper()} (Label: {label})")
    print("=" * 60)
    
    segments = get_script_segments(script_id, script_text, label)
    if not segments:
        print(f"Error: Script {script_id} has no valid segments.")
        return False
        
    print(f"Found {len(segments)} segments to synthesize.")
    
    unique_speakers = list(set(seg["speaker"] for seg in segments))
    existing_genders = script_data.get("content_metadata", {}).get("speakers_gender", {})
    existing_voices = script_data.get("content_metadata", {}).get("speakers_voice", {})
    manual_voice_paths = {}
    if existing_voices and isinstance(existing_voices, dict):
        for spk, vname in existing_voices.items():
            if vname:
                resolved_p = voice_manager.open_swara_dir / vname if not Path(vname).is_absolute() else Path(vname)
                if not resolved_p.exists():
                    for p in voice_manager.open_swara_dir.rglob("*.wav"):
                        if p.name.lower() == Path(vname).name.lower():
                            resolved_p = p
                            break
                if resolved_p.exists():
                    manual_voice_paths[spk] = resolved_p

    voice_manager.assign_voices_for_script(unique_speakers, clean_language, manual_genders=existing_genders, manual_voice_paths=manual_voice_paths)
    
    # Save the assigned genders and voice filenames into the script state
    speakers_gender = {}
    speakers_voice = {}
    for spk in unique_speakers:
        gender, vpath, _ = voice_manager.get_speaker_voice(spk, clean_language)
        speakers_gender[spk] = gender
        if vpath:
            speakers_voice[spk] = Path(vpath).name
        
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
        
        print(f"\n--- Segment {idx}/{len(segments)} [{speaker}] ({language}) ---")
        
        gender, ref_voice_path, seed = voice_manager.get_speaker_voice(speaker, clean_language)
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
        
        output_prefix = f"audio/script_{script_id}_{idx:02d}_{speaker.replace(' ', '_')}"
        dest_filename = f"segment_{idx:02d}_{speaker.replace(' ', '_')}.flac"
        dest_path = script_output_dir / dest_filename

        # Determine candidate sampling count:
        # If user explicitly supplied --candidates, respect it.
        # Otherwise, default to 2 candidate takes for stress-vital segments with detected target words.
        if candidates is not None:
            seg_candidates = max(1, candidates)
        elif is_seg_stress_vital and detected_stress_words:
            seg_candidates = 2
        else:
            seg_candidates = 1
        
        if dest_path.exists() and not force:
            print(f"Audio segment already exists at {dest_path.name}. Skipping API call.")
        else:
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
    args = parser.parse_args()
    
    base_dir = BASE_DIR
    state_manager = StateManager(base_dir)
    
    workflow_template_path = VOICE_WORKFLOW_PATH
    if not workflow_template_path.exists():
        print(f"Error: Could not locate template {workflow_template_path}", file=sys.stderr)
        return 1
            
    comfy_client = ComfyClient(COMFY_API_URL, workflow_template_path, COMFY_OUTPUT_DIR)
    try:
        print("Checking AI services connection (ComfyUI)...")
        require_services(comfy=True)
        print("AI services connection verified.")
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Production Mode Selection: Mass-produce (default in 10s), Specific ID, Group Range, Fun Facts, CSV List, or Ready Scripts CSV
    # pyrefly: ignore [missing-import]
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
                if process_script(script, state_manager, comfy_client, voice_manager, args.force, base_dir, candidates=args.candidates):
                    success_count += 1
                    time.sleep(0.3)  # Cooldown between scripts ("go ahead, don't stop")
                else:
                    print(f"Failed to generate voice for script ID {script['id']}.", file=sys.stderr)
                    return 1
            except Exception as exc:
                print(f"Unexpected error processing script ID {script['id']}: {exc}", file=sys.stderr)
                traceback.print_exc()
                return 1
                
        print(f"\n[Completed] Process complete. Successfully voiced {success_count} script(s).")

        # If in group_range, fun_facts, ready_scripts, or mass_ready_scripts mode, prompt whether to process more
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
