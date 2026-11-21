"""voice/languages/english.py — Prosodic print and sampling/gate envelope for English."""
from ..common.models import AcousticGateEnvelope, LanguageVoiceProfile, SamplingProfile

ENGLISH_VOICE_PROFILE = LanguageVoiceProfile(
    language="english",
    display_name="English",
    default_accent_weights={"en_us_neutral": 0.70, "en_uk_neutral": 0.30},
    narrator_sampling=SamplingProfile(
        temperature=0.84,
        top_p=0.92,
        top_k=50,
        subtalker_temperature=0.81,
        repetition_penalty=1.03,
    ),
    dialogue_sampling=SamplingProfile(
        temperature=0.77,
        top_p=0.90,
        top_k=50,
        subtalker_temperature=0.78,
        repetition_penalty=1.05,
    ),
    question_temp_delta=0.04,
    exclamation_temp_delta=0.05,
    acoustic_gate=AcousticGateEnvelope(
        min_pitch_variance=0.115,
        min_cps=8.0,
        max_cps=19.2,
        target_cps=13.5,
        min_question_f0_ratio=1.03,
        min_exclamation_rms_ratio=1.55,
    ),
    enforce_inverted_punctuation=False,
    instruct_prosody_hint=(
        "Punchy stress-timed creator rhythm, strong stressed-to-unstressed contrast, "
        "authentic vowel reduction, crisp interrogative pitch rise on questions, and vibrant conversational momentum."
    ),
    accent_instruct_hints={
        "en_us_neutral": "Clear, energetic General American storyteller accent with natural conversational rhythm.",
        "en_uk_neutral": "Crisp, articulate Modern Standard British RP storyteller accent with dynamic wit and clarity.",
    },
)
