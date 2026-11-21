"""voice/languages/italian.py — High-energy melodic prosodic print & geminate clarity for Italian."""
from ..common.models import AcousticGateEnvelope, LanguageVoiceProfile, SamplingProfile

ITALIAN_VOICE_PROFILE = LanguageVoiceProfile(
    language="italian",
    display_name="Italian",
    default_accent_weights={"it_standard": 1.0},
    narrator_sampling=SamplingProfile(
        temperature=0.87,
        top_p=0.93,
        top_k=50,
        subtalker_temperature=0.83,
        repetition_penalty=1.03,
    ),
    dialogue_sampling=SamplingProfile(
        temperature=0.83,
        top_p=0.92,
        top_k=50,
        subtalker_temperature=0.80,
        repetition_penalty=1.04,
    ),
    question_temp_delta=0.06,
    exclamation_temp_delta=0.07,
    acoustic_gate=AcousticGateEnvelope(
        min_pitch_variance=0.135,
        min_cps=8.0,
        max_cps=18.5,
        target_cps=13.0,
        min_question_f0_ratio=1.04,
        min_exclamation_rms_ratio=1.60,
    ),
    enforce_inverted_punctuation=False,
    instruct_prosody_hint=(
        "Energia italiana brillante, solare e teatrale con ampie escursioni melodiche, "
        "picchi espressivi coinvolgenti su domande ed esclamazioni, vocali aperte e doppie consonanti nitide (tt, nn, ll)."
    ),
    accent_instruct_hints={
        "it_standard": (
            "Accento italiano standard neutro, solare, brillante e ricco di vitalità naturale."
        ),
    },
)
