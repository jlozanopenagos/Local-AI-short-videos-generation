"""voice/languages/french.py — Prosodic print for French musicality & legato groupe rythmique."""
from ..common.models import AcousticGateEnvelope, LanguageVoiceProfile, SamplingProfile

FRENCH_VOICE_PROFILE = LanguageVoiceProfile(
    language="french",
    display_name="French",
    default_accent_weights={"fr_standard": 1.0},
    narrator_sampling=SamplingProfile(
        temperature=0.85,
        top_p=0.91,
        top_k=50,
        subtalker_temperature=0.81,
        repetition_penalty=1.04,
    ),
    dialogue_sampling=SamplingProfile(
        temperature=0.80,
        top_p=0.90,
        top_k=50,
        subtalker_temperature=0.78,
        repetition_penalty=1.05,
    ),
    question_temp_delta=0.05,
    exclamation_temp_delta=0.05,
    acoustic_gate=AcousticGateEnvelope(
        min_pitch_variance=0.120,
        min_cps=8.0,
        max_cps=18.5,
        target_cps=13.5,
        min_question_f0_ratio=1.04,
        min_exclamation_rms_ratio=1.55,
    ),
    enforce_inverted_punctuation=False,
    instruct_prosody_hint=(
        "Esprit parisien vif, pétillant et complice, musicalité française legato authentique, "
        "groupes rythmiques chantants avec appui expressif en fin de groupe, liaisons naturelles soignées et sourire dans la voix."
    ),
    accent_instruct_hints={
        "fr_standard": (
            "Accent français parisien standard (France métropolitaine), fluide, musical et expressif, "
            "sans accent étranger ni coupure saccadée."
        ),
    },
)
