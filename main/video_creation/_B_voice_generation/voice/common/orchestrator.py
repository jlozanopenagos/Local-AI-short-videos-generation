"""
voice/common/orchestrator.py — Unified Stage B synthesis orchestrator shared by CLI, modifier, WebUI, and tests.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional, Set

import config
from config import (
    COMFY_API_URL,
    COMFY_OUTPUT_DIR,
    STATIC_NARRATOR_PERSONALITY,
    VOICE_WORKFLOW_PATH,
    get_script_output_dir,
    require_services,
)

try:
    # pyrefly: ignore[missing-import]
    from core.state_manager import StateManager, resolve_lang_and_type
except (ImportError, ModuleNotFoundError):
    from state_manager import StateManager, resolve_lang_and_type  # type: ignore[no-redef]

try:
    from video_creation._B_voice_generation.core.acoustic_evaluator import (
        evaluate_voice_take,
        reference_median_pitch,
        select_best_general_candidate,
        select_best_voice_candidate,
    )
    from video_creation._B_voice_generation.core.audio_processor import (
        concatenate_audios,
        enforce_learner_pace_safety_net,
    )
    from video_creation._B_voice_generation.core.comfy_client import ComfyClient
    from video_creation._B_voice_generation.core.script_parser import (
        extract_language_from_label,
        get_script_segments,
    )
    from video_creation._B_voice_generation.core.stress_enhancer import (
        build_stress_style_directive,
        detect_intentional_stress_errors,
        enhance_stress_text_for_tts,
        normalize_multiple_choice_options_for_tts,
    )
    from video_creation._B_voice_generation.core.voice_manager import VoiceManager
    from video_creation._B_voice_generation.voice.types.roleplay.emotion import EXTENDED_ROLEPLAY_EMOTIONS
except (ImportError, ModuleNotFoundError):
    from core.acoustic_evaluator import (  # type: ignore[no-redef]
        evaluate_voice_take,
        reference_median_pitch,
        select_best_general_candidate,
        select_best_voice_candidate,
    )
    from core.audio_processor import concatenate_audios  # type: ignore[no-redef]
    from core.comfy_client import ComfyClient  # type: ignore[no-redef]
    from core.script_parser import extract_language_from_label, get_script_segments  # type: ignore[no-redef]
    from core.stress_enhancer import (  # type: ignore[no-redef]
        build_stress_style_directive,
        detect_intentional_stress_errors,
        enhance_stress_text_for_tts,
        normalize_multiple_choice_options_for_tts,
    )
    from core.voice_manager import VoiceManager  # type: ignore[no-redef]
    from voice.types.roleplay.emotion import EXTENDED_ROLEPLAY_EMOTIONS  # type: ignore[no-redef]

from .engine import (
    _normalize_section_bucket,
    compute_segment_sampling,
    is_typed_voice_enabled,
    resolve_voice_context,
)
from .delivery import INTENT_NAMES, continuous_narration, delivery_direction, roleplay_turn_direction, turn_intent
from .punctuation import prepare_tts_prosody_text


EMOTION_TRANSLATION_MAP: Dict[str, str] = {
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
    **EXTENDED_ROLEPLAY_EMOTIONS,
}


def is_stress_pronunciation_vital(script_data: dict, text: str = "") -> bool:
    """Detects if a script or specific segment requires vital stress pronunciation or phonetic precision."""
    metadata = script_data.get("metadata", {})
    label = metadata.get("LABEL", "").lower()
    prompt_params = script_data.get("prompt_params", {})
    content_metadata = script_data.get("content_metadata", {})

    stress_pattern = r'\b[a-z]+[A-Z]{2,}\b|\b[A-Z]{2,}[a-z]+\b|\b[a-zA-Z]+-[A-Z]{2,}\b|\b[A-Z]{2,}-[a-zA-Z]+\b'
    if text and re.search(stress_pattern, text):
        matches = re.findall(stress_pattern, text)
        if any(w not in ("XIXe", "XVIIIe", "XXe", "A-NN") for w in matches):
            return True

    full_script = script_data.get("script_text", "")
    full_text = str(full_script)
    if full_text and re.search(stress_pattern, full_text):
        matches = re.findall(stress_pattern, full_text)
        if any(w not in ("XIXe", "XVIIIe", "XXe", "A-NN") for w in matches):
            return True

    subject = str(prompt_params.get("SUBJECT", "")).lower()
    lex_field = str(prompt_params.get("LEXICAL_FIELD", "")).lower()
    topic = str(content_metadata.get("topic", "")).lower()
    category = str(content_metadata.get("category", "")).lower()
    subcategory = str(content_metadata.get("subcategory", "")).lower()
    obj = str(content_metadata.get("learning_objective", "")).lower()

    meta_text = f"{label} {subject} {lex_field} {topic} {category} {subcategory} {obj}".lower()
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
    if any(term in meta_text for term in linguistic_terms):
        if is_psych_stress:
            return any(k in f"{category} {subcategory} {subject}" for k in ["pronunciation", "phonetic", "doppie", "fonet"])
        return True
    return False


def infer_dialogue_emotion(
    speaker: str,
    text: str,
    explicit_emotion: str = None,
    section: str = None,
    is_game: bool = False,
) -> str:
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
        if "challenge" in sec:
            return "lively, charismatic, and enthusiastic game-show host presenting a fun quiz challenge"
        if "pressure" in sec:
            return "tense, dramatic game-show suspense and countdown anticipation"
        if "answer" in sec:
            return "triumphant, celebratory, and excited game-show answer reveal"
        if "explanation" in sec:
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

    if any(w in t for w in ["shaking", "panic", "can't believe", "nervous", "stage fright", "scared", "afraid", "tremble", "peur", "miedo", "nervioso", "angoisse", "paura", "ansia", "agitato", "tremando"]):
        return "intensely anxious, breathless, and trembling with stage fright urgency"
    if any(w in t for w in ["what does that even mean", "bad luck", "what?", "quoi", "qué", "comment", "really?", "de verdad", "cosa?", "davvero?", "sul serio?"]):
        return "sharp comedic disbelief, incredulous, and completely baffled"
    if any(w in t for w in ["calm down", "remember this", "don't worry", "relax", "t'inquiète", "tranquilo", "respira", "calme-toi", "calmati", "non ti preoccupare", "rilassati"]):
        return "grounded, confident, and high-spirited encouragement"
    if any(w in t for w in ["shine", "got this", "do a great job", "no!", "good luck", "bonne chance", "buena suerte", "briller", "tu peux le faire", "buona fortuna", "in bocca al lupo", "ce la puoi fare", "forza"]):
        return "enthusiastic, cheerful, and highly energetic banter"
    if any(w in t for w in ["oh!", "get it now", "thanks", "feel a lot better", "relieved", "merci", "compris", "soulagé", "gracias", "alivio", "grazie", "meno male", "sollevato"]):
        return "relieved, excited, and genuinely bright"
    if any(w in t for w in ["superstar", "go get 'em", "go get them", "awesome", "crush it", "vas-y", "génial", "vamos", "campeón", "fantastico", "bravissimo", "campione", "grandioso"]):
        return "hyped up, celebratory, and shouting with excitement"
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
    if any(k in emo_lower for k in ["whisper", "sad", "hesitant", "chuchot"]):
        return "medium"
    return "high"


def _build_context_and_style(
    speaker: str,
    language: str,
    sec_name: str,
    is_game: bool,
    is_roleplay: bool,
    is_dialogue: bool,
    is_seg_stress_vital: bool,
    script_data: dict,
) -> tuple[str, str]:
    if is_game and "narrator" in speaker.lower():
        if is_seg_stress_vital and "challenge" in sec_name:
            return (
                f"Charismatic game show host presenting a clear pronunciation and word stress challenge in {language}",
                "lively and articulate game show host delivery, upbeat conversational tempo, distinct options with clear syllable stress. "
                "Crucial pronunciation directive: Deliver educational focus words with authentic syllable stress and natural vowel reduction.",
            )
        if is_seg_stress_vital and "answer" in sec_name:
            return (
                f"Triumphant game show host explaining the correct syllable stress in {language}",
                "triumphant celebratory delivery, joyful game show reveal cadence with crystal-clear pronunciation. "
                "Deliver correct syllable stress with unmistakable clarity and authentic vowel reduction.",
            )
        if "hook" in sec_name:
            return (
                f"Vibrant, charismatic TV trivia show host presenting an educational quiz in {language}",
                "electrifying game show host delivery, bold dynamic vocal projection, energetic high-spirited conversational momentum, punchy and enthusiastic, magnetic trivia spirit, charismatic and inviting, warm human flow",
            )
        if "challenge" in sec_name:
            return (
                f"Charismatic and engaging trivia host presenting a multiple-choice challenge in {language}",
                "lively game show host delivery, engaging conversational momentum, crisp clear presentation of options with upbeat natural cadence, lively human flow without mechanical stalling",
            )
        if "pressure" in sec_name:
            return (
                f"Suspenseful game show host leading an intense countdown in {language}",
                "gripping game show host countdown, dramatic suspense and urgent anticipation, building high-energy excitement, punchy and thrilling delivery",
            )
        if "answer" in sec_name:
            return (
                f"Enthusiastic game show host revealing the correct answer in {language}",
                "triumphant celebratory delivery, joyful game show reveal cadence, energetic punchy intonation, warm human flow",
            )
        return (
            f"Charismatic language coach explaining the answer in {language}",
            "magnetic storyteller cadence, lively and encouraging, clear dynamic intonation, natural and punchy, warm human flow",
        )

    char_personalities = script_data.get("content_metadata", {}).get("character_personalities", {})
    speaker_personality = char_personalities.get(speaker, "")
    if not speaker_personality and "narrator" in speaker.lower():
        speaker_personality = STATIC_NARRATOR_PERSONALITY

    if is_seg_stress_vital:
        if language.lower() == "english":
            ctx = (
                "Charismatic language coach and pronunciation mentor demonstrating clear syllable stress in English"
                if not is_dialogue
                else (
                    f"Character '{speaker}' ({speaker_personality}) practicing authentic syllable stress and pronunciation in English"
                    if speaker_personality
                    else f"Character '{speaker}' practicing authentic syllable stress and pronunciation in English"
                )
            )
            st = (
                "deliberate articulate broadcast delivery, crystal-clear phoneme articulation, and measured educational pacing. "
                "Crucial pronunciation directive: Deliver educational focus words with authentic syllable stress and natural vowel reduction."
            )
            return ctx, st
        ctx = (
            f"Charismatic language coach and pronunciation mentor demonstrating clear articulation in {language}"
            if not is_dialogue
            else (
                f"Character '{speaker}' ({speaker_personality}) practicing clear pronunciation in {language}"
                if speaker_personality
                else f"Character '{speaker}' practicing clear pronunciation in {language}"
            )
        )
        return ctx, "deliberate articulate broadcast delivery, crystal-clear phoneme articulation, natural rhythm, and measured educational pacing."

    if is_roleplay:
        if not is_dialogue:
            ctx = (
                f"Charismatic storyteller ({speaker_personality}) in a {language} roleplay short"
                if speaker_personality
                else f"Charismatic YouTube Shorts storyteller and viral language mentor in a {language} roleplay narrative"
            )
            st = "measured, articulate learner-friendly cadence, expressive theatrical inflection, distinct word boundaries, warm human flow"
        else:
            ctx = (
                f"Character '{speaker}' ({speaker_personality}) in a {language} conversational dialogue"
                if speaker_personality
                else f"Character '{speaker}' participating in a {language} conversational dialogue"
            )
            st = "natural theatrical dialogue, clear learner-friendly conversational pacing, distinct word boundaries, expressive emotional inflection, warm authentic flow"
        return ctx, st

    if is_dialogue and speaker_personality:
        ctx = f"Character '{speaker}' ({speaker_personality}) in a {language} conversational dialogue"
    elif speaker_personality:
        ctx = f"Narrator ({speaker_personality}) presenting in {language}"
    elif is_dialogue:
        ctx = f"Character '{speaker}' participating in a {language} conversational dialogue"
    else:
        ctx = f"Narrator introducing a language learning topic in {language}"

    st = (
        "charismatic language-coach cadence, measured unhurried tempo for language learners, distinct word boundaries, clear dynamic intonation, warm human flow"
        if not is_dialogue
        else "natural theatrical dialogue, clear learner-friendly conversational pacing, distinct word boundaries, expressive emotional inflection, warm authentic flow"
    )
    return ctx, st


def _has_non_kokoro_voices(voice_manager: VoiceManager, language: str, genders: Set[str]) -> bool:
    for gend in (genders or {"male", "female"}):
        for p in voice_manager.get_available_voices(language, gend):
            if "kokoro_golden" not in p.name.lower():
                return True
    return False


def synthesize_script_voice(
    script_data: dict,
    state_manager: StateManager,
    comfy_client: Optional[ComfyClient],
    voice_manager: VoiceManager,
    force: bool = False,
    base_dir: Optional[Path] = None,
    candidates: Optional[int] = None,
    manual_genders: Optional[Dict[str, str]] = None,
    exclude_voices: Optional[Set[str]] = None,
    force_fresh_cast: bool = False,
    explicit_accent: Optional[str] = None,
    engine_mode: Optional[str] = None,
    mark_video_assembly_pending: bool = False,
    quality_preview: Optional[str] = None,
    preview_sections: Optional[Set[str]] = None,
    narrator_pitch_anchor: Optional[float] = None,
    narrator_reference: Optional[tuple[Path, str]] = None,
) -> bool:
    """Runs complete Stage B synthesis for one script across legacy or typed voice profiles."""
    script_id = script_data["id"]
    if quality_preview and (quality_preview not in {"baseline", "direction", "reference", "continuity", "roleplay"} or
                            not base_dir or Path(base_dir).resolve() == Path(config.BASE_DIR).resolve()):
        raise ValueError("Voice-quality previews require a supported mode and a separate workspace.")
    if (preview_sections or narrator_pitch_anchor is not None or narrator_reference) and not quality_preview:
        raise ValueError("Section and pitch overrides are only available for voice-quality previews.")
    script_text = script_data.get("script_text", "")
    metadata = script_data.get("metadata", {})
    label = metadata.get("LABEL", "english")
    clean_language, _ = resolve_lang_and_type(script_id, script_data)
    if not clean_language or clean_language == "english":
        extracted = extract_language_from_label(label)
        if extracted != "english":
            clean_language = extracted

    video_type = config.resolve_script_video_type(script_data)
    use_typed = (
        (engine_mode == "typed")
        if engine_mode in ("legacy", "typed")
        else is_typed_voice_enabled(video_type, clean_language)
    )
    lang_profile, type_profile, dialect_hint = resolve_voice_context(
        clean_language,
        video_type,
        script_data=script_data,
        explicit_accent=explicit_accent,
    )

    script_output_dir = get_script_output_dir(script_id, clean_language, base_dir, video_type=video_type)
    script_output_dir.mkdir(parents=True, exist_ok=True)

    for ext in ("segment_*.flac", "segment_*.wav"):
        for old_file in script_output_dir.glob(ext):
            try:
                old_file.unlink()
            except Exception:
                pass

    engine_tag = "TYPED" if use_typed else "LEGACY"
    print("=" * 60)
    print(f"Processing Script ID: {script_id} [{engine_tag}]")
    print(f"Language: {clean_language.upper()} | Type: {video_type.upper()} (Label: {label})")
    print("=" * 60)

    narrator_only = video_type.lower() in {"game", "expression", "fun_facts"}
    continuous_narrator = (
        use_typed and video_type.lower() in {"expression", "fun_facts"}
        and quality_preview != "baseline"
    )
    parser_options = {
        "narrator_only": narrator_only,
        "merge_narration_paragraphs": continuous_narrator or bool(
            quality_preview and quality_preview not in {"baseline", "roleplay"}
        ),
    }
    segments = get_script_segments(script_id, script_text, label, **parser_options)
    if not segments:
        script_dict = script_data.get("content_metadata", {}).get("script")
        if script_dict and isinstance(script_dict, dict):
            segments = get_script_segments(script_id, json.dumps(script_dict), label, **parser_options)
            if segments:
                script_data["script_text"] = json.dumps(script_dict, indent=2)
                state_manager.save_script_state(script_id, script_data)

    if not segments:
        print(f"Error: Script {script_id} has no valid segments.")
        return False

    print(f"Found {len(segments)} segments to synthesize.")

    unique_speakers = list(dict.fromkeys(seg["speaker"] for seg in segments))
    resolved_genders = dict(manual_genders) if manual_genders is not None else dict(
        script_data.get("content_metadata", {}).get("speakers_gender", {}) or {}
    )
    existing_voices = script_data.get("content_metadata", {}).get("speakers_voice", {}) or {}

    manual_voice_paths: Dict[str, Path] = {}
    if not force_fresh_cast and isinstance(existing_voices, dict):
        all_saved_kokoro = bool(existing_voices) and all("kokoro_golden" in str(v).lower() for v in existing_voices.values() if v)
        upgrade_legacy_kokoro = bool(use_typed and force and all_saved_kokoro and _has_non_kokoro_voices(voice_manager, clean_language, set(resolved_genders.values())))
        if not upgrade_legacy_kokoro:
            for spk, vname in existing_voices.items():
                if vname and str(vname).endswith(".wav"):
                    resolved_p = voice_manager.open_swara_dir / vname if not Path(vname).is_absolute() else Path(vname)
                    if not resolved_p.exists() and voice_manager.open_swara_dir.exists():
                        for p in voice_manager.open_swara_dir.rglob("*.wav"):
                            if p.name.lower() == Path(vname).name.lower():
                                resolved_p = p
                                break
                    if resolved_p.exists() and voice_manager._is_acceptable_ref(resolved_p, clean_language):
                        manual_voice_paths[spk] = resolved_p

    voice_manager.assign_voices_for_script(
        unique_speakers,
        clean_language,
        manual_genders=resolved_genders,
        manual_voice_paths=manual_voice_paths,
        video_type=video_type,
        script_id=script_id,
        script_data=script_data,
        exclude_voices=exclude_voices,
        accent_hint=dialect_hint,
        engine_mode="typed" if use_typed else "legacy",
    )

    speakers_gender: Dict[str, str] = {}
    speakers_voice: Dict[str, str] = {}
    for spk in unique_speakers:
        gender, vpath, _ = voice_manager.get_speaker_voice(spk, clean_language)
        speakers_gender[spk] = gender
        if vpath:
            speakers_voice[spk] = Path(vpath).name

    if "content_metadata" not in script_data:
        script_data["content_metadata"] = {}
    script_data["content_metadata"]["speakers_gender"] = speakers_gender
    script_data["content_metadata"]["speakers_voice"] = speakers_voice
    if use_typed:
        script_data["content_metadata"]["voice_profile_meta"] = {
            "engine": "typed",
            "dialect": dialect_hint or "default",
            "video_type": type_profile.video_type,
        }
    vtype_upper = video_type.upper()
    is_game = vtype_upper == "GAME" or any(s.get("section") in ["challenge", "pressure"] for s in segments)
    is_roleplay = vtype_upper == "ROLEPLAY" or any("dialogue" in (s.get("section") or "").lower() for s in segments)
    is_script_stress_vital = is_stress_pronunciation_vital(script_data)

    segments_to_concat: List[Dict[str, Any]] = []
    preview_trace: list[dict] = []
    reference_pitches: dict[Path, float | None] = {}

    previous_character_turn = None
    for seg in segments:
        speaker = seg["speaker"]
        is_dialogue = seg["is_dialogue"]
        is_roleplay_character = (
            use_typed and vtype_upper == "ROLEPLAY" and is_dialogue
            and speaker.casefold() in {"person_one", "person_two"}
        )
        previous_line = ""
        if is_roleplay_character:
            if previous_character_turn and previous_character_turn[0] != speaker.casefold():
                previous_line = previous_character_turn[1]
            previous_character_turn = (speaker.casefold(), seg["text"])
        else:
            previous_character_turn = None
        if preview_sections and seg["section"].casefold() not in preview_sections:
            continue
        idx = seg["index"]
        text = seg["text"]
        raw_text = seg.get("raw_text", text)
        original_emotion = seg["emotion"]
        emotion = original_emotion
        language = seg["language"]
        continuous_roleplay = is_roleplay_character and quality_preview in (None, "direction", "reference", "roleplay")
        sec_name = (seg.get("section") or "").lower()
        is_seg_stress_vital = is_script_stress_vital or is_stress_pronunciation_vital(script_data, text)

        print(f"\n--- Segment {idx}/{len(segments)} [{speaker}] ({language}) ---")

        if is_seg_stress_vital and (not emotion or emotion.lower() in ["neutral", "none", "", "normal"]):
            emotion = "articulate, enthusiastic, and deliberate pronunciation mentor"
        else:
            emotion = infer_dialogue_emotion(speaker, text, emotion, section=seg.get("section"), is_game=is_game)
        energy = map_emotion_to_energy(emotion)

        output_prefix = f"audio/script_{script_id}_{idx:02d}_{speaker.replace(' ', '_')}"
        dest_filename = f"segment_{idx:02d}_{speaker.replace(' ', '_')}.flac"
        dest_path = script_output_dir / dest_filename

        if comfy_client is None:
            try:
                require_services(comfy=True)
                comfy_client = ComfyClient(COMFY_API_URL, VOICE_WORKFLOW_PATH, COMFY_OUTPUT_DIR)
            except Exception as exc:
                print(f"Error: Qwen3-TTS ComfyUI required for segment {idx} but unavailable: {exc}", file=sys.stderr)
                return False

        target_text = normalize_multiple_choice_options_for_tts(text, language=language)
        if target_text != text:
            print(f"  [TTS MC Options Normalized]: '{target_text}'")

        context, style = _build_context_and_style(
            speaker=speaker,
            language=language,
            sec_name=sec_name,
            is_game=is_game,
            is_roleplay=is_roleplay,
            is_dialogue=is_dialogue,
            is_seg_stress_vital=is_seg_stress_vital,
            script_data=script_data,
        )

        detected_stress_words: List[str] = []
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

        prosody_flags: Dict[str, Any] = {"is_cliffhanger": False}
        sampling_overrides = None
        turn_accent_hint = None

        if use_typed:
            gender, ref_voice_path, seed = voice_manager.resolve_turn_voice(
                speaker=speaker,
                language=clean_language,
                emotion=original_emotion or emotion,
                text=target_text,
                section=sec_name,
                video_type=video_type,
                engine_mode="typed",
            )
            target_text, prosody_flags = prepare_tts_prosody_text(
                text=target_text,
                raw_text=raw_text,
                language=clean_language,
                video_type=video_type,
                section=sec_name,
                is_stress_vital=is_seg_stress_vital,
                use_option_micro_pauses=type_profile.use_option_micro_pauses,
                option_micro_pause_sec=type_profile.pauses.option_micro_pause,
                enforce_inverted_punctuation=lang_profile.enforce_inverted_punctuation,
                continuous_turn=continuous_roleplay or continuous_narrator,
            )
            if continuous_roleplay or continuous_narrator:
                target_text = continuous_narration(target_text)
            if not is_seg_stress_vital and lang_profile.instruct_prosody_hint:
                style = f"{style}. {lang_profile.instruct_prosody_hint}"
            is_diag_spk = "dialogue" in context.lower() or ("character" in context.lower() and "narrator" not in context.lower())
            sampling_overrides = compute_segment_sampling(
                lang_profile=lang_profile,
                type_profile=type_profile,
                section=sec_name,
                is_dialogue_speaker=is_diag_spk,
                prosody_flags=prosody_flags,
            )
            turn_accent_hint = dialect_hint
            if getattr(voice_manager, "bank_manifest", None) and ref_voice_path:
                ent = voice_manager.bank_manifest.find_entry_by_audio(ref_voice_path.name)
                if ent and ent.accent:
                    turn_accent_hint = ent.accent
        else:
            gender, ref_voice_path, seed = voice_manager.get_speaker_voice(speaker, clean_language)

        is_narrator = speaker.casefold() == "narrator"
        intent = turn_intent(original_emotion, emotion)
        if quality_preview:
            if is_narrator and quality_preview not in {"baseline", "roleplay"}:
                target_text = continuous_narration(target_text)
            if quality_preview in {"direction", "reference"}:
                gender, ref_voice_path, _ = voice_manager.get_speaker_voice(speaker, clean_language)
                bank = voice_manager.bank_manifest
                if quality_preview == "reference" and bank and ref_voice_path:
                    # For a narrator, use one alternate reference across the entire short.
                    # Roleplay actors may select another reference for their existing identity.
                    tier = "high_energy" if is_narrator or intent == 2 else (
                        "surprised_urgent" if intent in (0, 3) else "baseline"
                    )
                    variant = bank.find_speaker_energy_variant(
                        ref_voice_path.name, tier, open_swara_dir=voice_manager.open_swara_dir,
                    )
                    if variant and variant.is_file():
                        ref_voice_path = variant
            seed_key = f"{script_id}:{idx}:{speaker}".encode()
            seed = int.from_bytes(hashlib.sha256(seed_key).digest()[:6], "big")

        if narrator_reference and is_narrator:
            ref_voice_path = narrator_reference[0]
        ref_filename = voice_manager.prepare_voice_in_comfy(ref_voice_path)
        pers_log = f" | Persona: '{context}'" if context else ""
        print(f"[{speaker}] Ref: '{ref_filename}' | Acting tone: '{emotion}' | Energy: '{energy}'{pers_log}")

        sec_bucket = _normalize_section_bucket(sec_name)
        high_secs = type_profile.high_impact_sections if use_typed else ("hook", "pressure", "payoff", "cta", "reveal")
        is_high_impact = (
            any(k in sec_name or k == sec_bucket for k in high_secs)
            or (is_game and "answer" in sec_name)
            or (is_seg_stress_vital and bool(detected_stress_words))
        )

        if candidates is not None:
            seg_candidates = max(1, candidates)
        elif is_high_impact:
            seg_candidates = 2
        else:
            seg_candidates = 1

        gen_extra: Dict[str, Any] = {}
        if sampling_overrides is not None:
            gen_extra["sampling_overrides"] = sampling_overrides
        if turn_accent_hint is not None:
            gen_extra["accent_hint"] = turn_accent_hint

        if narrator_reference and is_narrator:
            gen_extra.update(use_icl=True, ref_text=narrator_reference[1])
        if continuous_roleplay:
            gen_extra["delivery_direction"] = roleplay_turn_direction(clean_language, intent, previous_line)
        elif (
            is_narrator and use_typed and not detected_stress_words and (
                continuous_narrator
                or (vtype_upper in {"GAME", "ROLEPLAY"} and quality_preview is None)
            )
        ) or quality_preview in {"direction", "reference"}:
            gen_extra["delivery_direction"] = delivery_direction(
                clean_language, sec_name, is_narrator, intent, video_type=video_type,
            )

        eval_vtype = video_type if use_typed else None
        eval_sec = sec_name if use_typed else None

        try:
            if quality_preview and not (is_seg_stress_vital and detected_stress_words):
                if ref_voice_path not in reference_pitches:
                    reference_pitches[ref_voice_path] = reference_median_pitch(ref_voice_path) if ref_voice_path else None
                takes = []
                for take_index in range(seg_candidates + 1):
                    take_seed = seed + take_index * 777
                    take = dest_path.with_name(f"{dest_path.stem}_preview_{take_index + 1}.flac")
                    take_options = dict(gen_extra)
                    if take_index >= seg_candidates and sampling_overrides:
                        calmer = dict(sampling_overrides)
                        for key in ("temperature", "subtalker_temperature"):
                            if key in calmer:
                                calmer[key] = round(max(0.6, float(calmer[key]) - 0.08), 3)
                        take_options["sampling_overrides"] = calmer
                    comfy_client.generate_voice_segment(
                        ref_audio_name=ref_filename, target_text=target_text, language=language,
                        gender=gender, context=context, emotion=emotion, energy=energy, style=style,
                        output_prefix=f"{output_prefix}_preview_{take_index + 1}",
                        dest_path=take, seed=take_seed, **take_options,
                    )
                    score, passed, issues, metrics = evaluate_voice_take(
                        take, target_text, language, eval_vtype, eval_sec,
                        reference_f0=(narrator_pitch_anchor if is_narrator and narrator_pitch_anchor
                                      else reference_pitches[ref_voice_path]),
                    )
                    takes.append((passed, score, take, take_seed, issues, metrics))
                    if passed and take_index + 1 >= seg_candidates:
                        break

                winner = max(takes, key=lambda item: (item[0], item[1]))
                shutil.copyfile(winner[2], dest_path)
                preview_trace.append({
                    "section": sec_name, "speaker": speaker,
                    "original_emotion": original_emotion, "inferred_emotion": emotion,
                    "intensity": energy,
                    "acting_intent": INTENT_NAMES[intent] if intent is not None else None,
                    "reference": ref_voice_path.name if ref_voice_path else None,
                    "text_sent": target_text,
                    "direction": gen_extra.get("delivery_direction"),
                    "winner_seed": winner[3], "review_required": not winner[0],
                    "takes": [
                        {"file": item[2].name, "seed": item[3], "passed": item[0],
                         "score": item[1], "issues": item[4], "metrics": item[5]}
                        for item in takes
                    ],
                })
                (script_output_dir / "voice_preview.json").write_text(
                    json.dumps({"mode": quality_preview, "segments": preview_trace}, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            elif is_seg_stress_vital and detected_stress_words:
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
                        seed=take_seed,
                        **gen_extra,
                    )
                    candidate_paths.append(take_path)

                select_best_voice_candidate(
                    candidate_paths=candidate_paths,
                    target_words=detected_stress_words,
                    text_context=text,
                    dest_path=dest_path,
                )
            elif seg_candidates > 1:
                workflow_inputs = dict(
                    ref_audio_name=ref_filename,
                    target_text=target_text,
                    language=language,
                    gender=gender,
                    context=context,
                    emotion=emotion,
                    energy=energy,
                    style=style,
                    **gen_extra,
                )
                takes = [
                    (
                        script_output_dir / f"segment_{idx:02d}_{speaker.replace(' ', '_')}_take{take_idx + 1}.flac",
                        {"output_prefix": f"{output_prefix}_take{take_idx + 1}", "seed": seed + take_idx * 777},
                    )
                    for take_idx in range(seg_candidates)
                ]
                studio_voice = getattr(comfy_client, "check_cancelled", None) is not None
                queue_candidates = getattr(comfy_client, "generate_voice_candidates", None)
                if studio_voice and queue_candidates is not None and not quality_preview:
                    queue_candidates(takes, **workflow_inputs)
                else:
                    for take_path, take_inputs in takes:
                        comfy_client.generate_voice_segment(
                            dest_path=take_path, **take_inputs, **workflow_inputs,
                        )
                candidate_paths = [path for path, _ in takes]

                if use_typed:
                    candidate_ratings = [
                        evaluate_voice_take(
                            cp,
                            target_text=target_text,
                            language=language,
                            video_type=eval_vtype,
                            section=eval_sec,
                        )
                        for cp in candidate_paths
                    ]
                    any_clean = any(rating[1] for rating in candidate_ratings)
                    if not any_clean:
                        calm_samp = dict(sampling_overrides or {})
                        calm_samp["temperature"] = round(max(0.72, float(calm_samp.get("temperature", 0.84)) - 0.10), 3)
                        calm_samp["subtalker_temperature"] = round(max(0.74, float(calm_samp.get("subtalker_temperature", 0.81)) - 0.06), 3)
                        calm_extra = {**gen_extra, "sampling_overrides": calm_samp}
                        calm_seed = seed + 1999
                        calm_path = script_output_dir / f"segment_{idx:02d}_{speaker.replace(' ', '_')}_take_calm.flac"
                        print(
                            f"  [Pitch/Quality Recovery]: All high-impact takes flagged; retrying calmly "
                            f"(temp={calm_samp['temperature']}, sub={calm_samp['subtalker_temperature']}, seed={calm_seed})..."
                        )
                        if studio_voice:
                            longest_take = max(rating[3].get("duration", 0.0) for rating in candidate_ratings)
                            calm_extra.update(stall_timeout=int(max(90, min(180, 20 + 10 * longest_take))), max_retries=1)
                        try:
                            comfy_client.generate_voice_segment(
                                ref_audio_name=ref_filename,
                                target_text=target_text,
                                language=language,
                                gender=gender,
                                context=context,
                                emotion=emotion,
                                energy=energy,
                                style=style,
                                output_prefix=f"{output_prefix}_calm",
                                dest_path=calm_path,
                                seed=calm_seed,
                                **calm_extra,
                            )
                            candidate_paths.append(calm_path)
                        except TimeoutError:
                            if not studio_voice:
                                raise
                            print("  [Pitch/Quality Recovery]: Time budget reached. Using the completed takes.")


                select_best_general_candidate(
                    candidate_paths=candidate_paths,
                    target_text=target_text,
                    language=language,
                    dest_path=dest_path,
                    video_type=eval_vtype,
                    section=eval_sec,
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
                    seed=seed,
                    **gen_extra,
                )
                score, passes_gate, issues, metrics = evaluate_voice_take(
                    dest_path,
                    target_text=target_text,
                    language=language,
                    video_type=eval_vtype,
                    section=eval_sec,
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
                        seed=seed + 555,
                        **gen_extra,
                    )
                    select_best_general_candidate(
                        candidate_paths=[take1_path, take2_path],
                        target_text=target_text,
                        language=language,
                        dest_path=dest_path,
                        video_type=eval_vtype,
                        section=eval_sec,
                    )
        except InterruptedError:
            return False
        except Exception as exc:
            print(f"API Error on segment {idx}: {exc}", file=sys.stderr)
            return False

        spoken_clean = re.sub(r"\[pause:\d+(?:\.\d+)?\]", " ", target_text)
        seg_words = len(spoken_clean.split())
        if use_typed and type_profile is not None and type_profile.apply_pace_safety_net:
            target_wpm_mid = sum(type_profile.target_wpm_range) / 2.0
            stretched, factor, before_wpm, after_wpm = enforce_learner_pace_safety_net(
                dest_path,
                word_count=seg_words,
                max_wpm=type_profile.max_wpm,
                target_wpm=target_wpm_mid,
                max_slowdown=0.12,
            )
            if stretched:
                print(f"  [Pace Safety Net]: Gently slowed {factor:.2f}x ({before_wpm:.0f} -> {after_wpm:.0f} WPM)")

        segments_to_concat.append({
            "path": dest_path,
            "section": seg["section"],
            "speaker": speaker,
            "is_cliffhanger": bool(prosody_flags.get("is_cliffhanger", False)),
            "word_count": seg_words,
        })

    if not segments_to_concat:
        print(f"No selected sections were available for {script_id}.")
        return False

    print(f"\nSyntheses complete. Merging {len(segments_to_concat)} segments...")
    master_path = script_output_dir / f"script_{script_id}_master.wav"

    try:
        with TemporaryDirectory(prefix=".voice-master-", dir=script_output_dir) as staging:
            staged_master = Path(staging) / master_path.name
            merged_file = concatenate_audios(
                segments_metadata=segments_to_concat,
                output_path=staged_master,
                pause_choreography=type_profile.pauses if use_typed else None,
                mastering_preset=type_profile.mastering if use_typed else None,
            )
            if merged_file:
                staged_timings = Path(staging) / "timings.json"
                timings = script_output_dir / "timings.json"
                backup = Path(staging) / "previous-timings.json"
                if timings.exists():
                    shutil.copyfile(timings, backup)
                staged_timings.replace(timings)
                try:
                    staged_master.replace(master_path)
                except OSError:
                    if backup.exists():
                        backup.replace(timings)
                    else:
                        timings.unlink(missing_ok=True)
                    raise
                merged_file = master_path
        if merged_file:
            try:
                import soundfile as sf
                master_dur = float(sf.info(str(merged_file)).duration)
                total_words = sum(int(s.get("word_count", 0)) for s in segments_to_concat)
                total_wpm = (total_words / (master_dur / 60.0)) if master_dur > 0 else 0.0
                timings_path = merged_file.parent / "timings.json"
                avg_gap = 0.0
                num_gaps = max(0, len(segments_to_concat) - 1)
                if timings_path.exists() and num_gaps > 0:
                    t_map = json.loads(timings_path.read_text(encoding="utf-8"))
                    ordered_secs = sorted(t_map.values(), key=lambda x: x["start"])
                    gaps = [max(0.0, b["start"] - a["end"]) for a, b in zip(ordered_secs, ordered_secs[1:])]
                    avg_gap = sum(gaps) / len(gaps) if gaps else 0.0
                print(
                    f"  [Pace QA]: Words: {total_words} | Duration: {master_dur:.2f}s | "
                    f"Total WPM: {total_wpm:.1f} | Gaps: {num_gaps} (avg {avg_gap:.2f}s)"
                )
            except Exception:
                pass
            print(f"Successfully generated master audio: {merged_file}")
            if "assets" not in script_data:
                script_data["assets"] = {}
            script_data["assets"]["audio_path"] = str(merged_file)
            if "status" not in script_data:
                script_data["status"] = {}
            needs_review = bool(quality_preview and (
                preview_sections or any(segment["review_required"] for segment in preview_trace)
            ))
            script_data["status"]["voice_generation"] = "pending" if needs_review else "done"
            if mark_video_assembly_pending:
                script_data["status"]["video_assembly"] = "pending"
            state_manager.save_script_state(script_id, script_data)

            for seg in segments_to_concat:
                try:
                    if seg["path"].exists():
                        seg["path"].unlink()
                except Exception:
                    pass

            voice_manager.cleanup_comfy_input()
            return True
    except Exception as exc:
        print(f"Error during audio merge: {exc}", file=sys.stderr)

    return False
