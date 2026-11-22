"""voice/languages/spanish.py — Neutral LatAm & Castilian prosodic print with ¿/¡ enforcement."""
from ..common.models import AcousticGateEnvelope, LanguageVoiceProfile, SamplingProfile

SPANISH_VOICE_PROFILE = LanguageVoiceProfile(
    language="spanish",
    display_name="Spanish",
    # User-approved mix: neutral accents only (75% Neutral LatAm, 25% Standard Castilian Spain)
    default_accent_weights={"es_latam_neutral": 0.75, "es_spain_castilian": 0.25},
    narrator_sampling=SamplingProfile(
        temperature=0.85,
        top_p=0.92,
        top_k=50,
        subtalker_temperature=0.82,
        repetition_penalty=1.03,
    ),
    dialogue_sampling=SamplingProfile(
        temperature=0.79,
        top_p=0.90,
        top_k=50,
        subtalker_temperature=0.79,
        repetition_penalty=1.05,
    ),
    question_temp_delta=0.06,
    exclamation_temp_delta=0.06,
    acoustic_gate=AcousticGateEnvelope(
        min_pitch_variance=0.125,
        min_cps=8.5,
        max_cps=19.5,
        target_cps=14.5,
        min_question_f0_ratio=1.04,
        min_exclamation_rms_ratio=1.60,
    ),
    enforce_inverted_punctuation=True,
    instruct_prosody_hint=(
        "Ritmo silábico claro, pausado y bien articulado para estudiantes de idiomas, vocales puras y nítidas, "
        "entonación ascendente marcada en preguntas (¿?) y energía cálida en exclamaciones (¡!), acento neutro comprensible sin modismos locales."
    ),
    accent_instruct_hints={
        "es_latam_neutral": (
            "Acento español latinoamericano neutro estándar, limpio, cálido y universal, sin regionalismos marcados."
        ),
        "es_spain_castilian": (
            "Acento español castellano estándar neutro de España, dicción limpia y clara con distinción natural de s/z, sin jerga regional."
        ),
    },
)
