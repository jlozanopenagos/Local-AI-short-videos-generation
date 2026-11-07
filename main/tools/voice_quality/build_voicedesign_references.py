"""Generates Multi-Tier Studio-Grade Golden Reference Audio for Latin Languages
(French, Spanish, Italian) across 3 distinct pitch registers per gender:
- Female: Alto (185-215 Hz), Mezzo (215-245 Hz), Soprano (250-280 Hz capped)
- Male:   Bass (100-130 Hz), Baritone (135-165 Hz), Tenor (165-195 Hz)
Using Qwen3-TTS-12Hz-1.7B-VoiceDesign (Apache 2.0).
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
import soundfile as sf
# pyrefly: ignore[missing-import]
import torch

MAIN_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MAIN_DIR))
sys.path.insert(0, str(MAIN_DIR / "core"))

import config  # noqa: E402
from config import COMFY_DIR, OPEN_SWARA_DIR, REF_TRANSCRIPTS_PATH  # noqa: E402
from video_creation._B_voice_generation.core.acoustic_evaluator import evaluate_voice_take  # noqa: E402

VOICEDESIGN_MODEL_DIR = COMFY_DIR / "ComfyUI" / "models" / "TTS" / "Qwen" / "Qwen3-TTS-12Hz-1.7B-VoiceDesign"

VOICEDESIGN_REFERENCE_SPECS: List[Dict] = [
    # =========================================================================
    # FRENCH FEMALE
    # =========================================================================
    {
        "language": "french",
        "gender": "female",
        "filename": "french_female_kokoro_golden_alto.wav",
        "pitch_tier": "alto",
        "aliases": ["french_female_kokoro_golden_char1.wav"],
        "role": "char_alto",
        "lang_name": "French",
        "seed": 9876,
        "temperature": 0.76,
        "subtalker_temperature": 0.78,
        "instruct": (
            "Une femme adulte parisienne avec une voix grave, chaude et posée, registre contralto ou alto naturel "
            "(voix de poitrine basse et veloutée autour de 195-205 Hz). Diction calme, rassurante, enveloppante et "
            "très expressive sans aucune note suraiguë ni cri."
        ),
        "text": "Attends, respire un moment. Ce n'est pas si compliqué que tu le penses. Regarde les choses avec calme et tout va bien se passer.",
    },
    {
        "language": "french",
        "gender": "female",
        "filename": "french_female_kokoro_golden_mezzo.wav",
        "pitch_tier": "mezzo",
        "aliases": ["french_female_kokoro_golden_char2.wav"],
        "role": "char_mezzo",
        "lang_name": "French",
        "seed": 20202,
        "temperature": 0.78,
        "subtalker_temperature": 0.80,
        "instruct": (
            "Une jeune femme parisienne naturelle, registre médium équilibré, chaleureux et dynamique (environ 220-235 Hz). "
            "Diction impeccable, intonation souriante et vivante sans ton strident ni aigu forcé."
        ),
        "text": "Respire un grand coup, détends-toi ! C'est super simple, tu vas voir ! Utilise cette phrase avec confiance et tu vas cartonner !",
    },
    {
        "language": "french",
        "gender": "female",
        "filename": "french_female_kokoro_golden_soprano.wav",
        "pitch_tier": "soprano",
        "aliases": [],
        "role": "char_soprano",
        "lang_name": "French",
        "seed": 10101,
        "temperature": 0.80,
        "subtalker_temperature": 0.82,
        "instruct": (
            "Une jeune femme parisienne lumineuse, pétillante et expressive, registre soprano léger et souriant (environ 250-270 Hz). "
            "Très dynamique et réactive dans la conversation, expressive tout en restant agréable et sans crier."
        ),
        "text": "Mais attends une seconde ! Qu'est-ce que ça veut dire exactement ?! Raconte-moi tout de suite, c'est super intrigant !",
    },
    {
        "language": "french",
        "gender": "female",
        "filename": "french_female_kokoro_golden_narrator.wav",
        "pitch_tier": "narrator_female",
        "aliases": [],
        "role": "narrator",
        "lang_name": "French",
        "seed": 4242,
        "temperature": 0.78,
        "subtalker_temperature": 0.80,
        "instruct": (
            "Une créatrice YouTube parisienne jeune, très dynamique, charismatique, souriante et captivante, registre médium expressif (environ 225 Hz). "
            "Diction parisienne impeccable, intonation vive et engageante, débit naturel sans aucune monotonie."
        ),
        "text": "Salut à tous ! Tu connais ce secret incroyable en français ? Aujourd'hui, on découvre ensemble une expression incontournable que les Parisiens utilisent tout le temps !",
    },

    # =========================================================================
    # FRENCH MALE
    # =========================================================================
    {
        "language": "french",
        "gender": "male",
        "filename": "french_male_kokoro_golden_bass.wav",
        "pitch_tier": "bass",
        "aliases": ["french_male_kokoro_golden_char2.wav"],
        "role": "char_bass",
        "lang_name": "French",
        "seed": 30303,
        "temperature": 0.76,
        "subtalker_temperature": 0.78,
        "instruct": (
            "Une voix masculine d'homme adulte, timbre très grave, profond, viril et résonnant (registre de poitrine très bas autour de 115-125 Hz). "
            "Voix basse, posée, rassurante et chaleureuse."
        ),
        "text": "Fais-moi confiance, arrête de stresser. Tu as tout préparé avec soin, garde ton calme et tout va parfaitement se dérouler.",
    },
    {
        "language": "french",
        "gender": "male",
        "filename": "french_male_kokoro_golden_baritone.wav",
        "pitch_tier": "baritone",
        "aliases": ["french_male_kokoro_golden_char1.wav"],
        "role": "char_baritone",
        "lang_name": "French",
        "seed": 7777,
        "temperature": 0.78,
        "subtalker_temperature": 0.80,
        "instruct": (
            "Un homme adulte parisien, voix masculine naturelle de registre baryton chaud, clair et captivant (environ 145-160 Hz). "
            "Diction limpide, rythme engageant et naturel sans monter dans les aigus."
        ),
        "text": "Salut à tous ! Tu veux parler français comme un vrai Parisien ? Aujourd'hui, je te dévoile une expression géniale qui change absolument tout !",
    },
    {
        "language": "french",
        "gender": "male",
        "filename": "french_male_kokoro_golden_tenor.wav",
        "pitch_tier": "tenor",
        "aliases": [],
        "role": "char_tenor",
        "lang_name": "French",
        "seed": 40404,
        "temperature": 0.80,
        "subtalker_temperature": 0.82,
        "instruct": (
            "Un jeune homme parisien dynamique, vif, spontané et sympathique, registre ténor clair et énergique (environ 175-190 Hz). "
            "Rythmé, expressif, engageant et plein d'entrain."
        ),
        "text": "Attends une seconde, mais comment ça ?! Tu es sérieux là ? Raconte-moi tout de suite, je veux absolument comprendre !",
    },
    {
        "language": "french",
        "gender": "male",
        "filename": "french_male_kokoro_golden_narrator.wav",
        "pitch_tier": "narrator_male",
        "aliases": [],
        "role": "narrator",
        "lang_name": "French",
        "seed": 7777,
        "temperature": 0.78,
        "subtalker_temperature": 0.80,
        "instruct": (
            "Un animateur parisien jeune, charismatique, énergique et chaleureux, registre baryton naturel (environ 150 Hz). "
            "Voix masculine claire et captivante, intonation rythmée et enthousiaste, accent parisien impeccable et naturel."
        ),
        "text": "Salut à tous ! Tu veux parler français comme un vrai Parisien ? Aujourd'hui, je te dévoile une expression géniale qui change absolument tout !",
    },

    # =========================================================================
    # SPANISH FEMALE
    # =========================================================================
    {
        "language": "spanish",
        "gender": "female",
        "filename": "spanish_female_kokoro_golden_alto.wav",
        "pitch_tier": "alto",
        "aliases": ["spanish_female_kokoro_golden_char1.wav"],
        "role": "char_alto",
        "lang_name": "Spanish",
        "seed": 8765,
        "temperature": 0.76,
        "subtalker_temperature": 0.78,
        "instruct": (
            "Una mujer adulta hispanohablante con voz grave, cálida y profunda, registro contralto o alto natural de pecho "
            "(alrededor de 190-205 Hz). Dicción serena, envolvente, firme y muy natural, sin agudos estridentes."
        ),
        "text": "Cálmate un momento y escúchame con atención. No hay por qué angustiarse tanto, todo tiene una solución sencilla si mantienes la cabeza fría.",
    },
    {
        "language": "spanish",
        "gender": "female",
        "filename": "spanish_female_kokoro_golden_mezzo.wav",
        "pitch_tier": "mezzo",
        "aliases": ["spanish_female_kokoro_golden_char2.wav"],
        "role": "char_mezzo",
        "lang_name": "Spanish",
        "seed": 100101,
        "temperature": 0.78,
        "subtalker_temperature": 0.80,
        "instruct": (
            "Una mujer hispanohablante alegre, cercana, cálida y comunicativa, registro medio equilibrado (alrededor de 220-235 Hz). "
            "Voz amable, segura y natural, perfecta para una charla de amigos sin estridencias."
        ),
        "text": "¡Tranquila, respira hondo! Lo vas a hacer increíble. Confía en ti misma, di esa frase con toda la seguridad y verás qué bien sale todo.",
    },
    {
        "language": "spanish",
        "gender": "female",
        "filename": "spanish_female_kokoro_golden_soprano.wav",
        "pitch_tier": "soprano",
        "aliases": [],
        "role": "char_soprano",
        "lang_name": "Spanish",
        "seed": 90909,
        "temperature": 0.80,
        "subtalker_temperature": 0.82,
        "instruct": (
            "Una joven hispanohablante despierta, dinámica, fresca y entusiasta, registro soprano ligero y alegre (alrededor de 250-270 Hz). "
            "Muy expresiva pero siempre agradable al oído y sin gritar."
        ),
        "text": "¡Oye, pero qué sorpresa tan buena! No me lo esperaba para nada, cuéntamelo todo ya mismo, ¡estoy súper emocionada!",
    },
    {
        "language": "spanish",
        "gender": "female",
        "filename": "spanish_female_kokoro_golden_narrator.wav",
        "pitch_tier": "narrator_female",
        "aliases": [],
        "role": "narrator",
        "lang_name": "Spanish",
        "seed": 3333,
        "temperature": 0.78,
        "subtalker_temperature": 0.80,
        "instruct": (
            "Una narradora hispanohablante carismática, alegre y dinámica, registro medio natural (alrededor de 225 Hz). "
            "Tono cálido, vibrante y muy cercano para YouTube Shorts, sin agudos forzados."
        ),
        "text": "¡Hola a todos! ¿Sabías este secreto increíble del español? ¡Hoy vamos a descubrir una expresión que los hablantes nativos usan todos los días!",
    },

    # =========================================================================
    # SPANISH MALE
    # =========================================================================
    {
        "language": "spanish",
        "gender": "male",
        "filename": "spanish_male_kokoro_golden_bass.wav",
        "pitch_tier": "bass",
        "aliases": ["spanish_male_kokoro_golden_char2.wav"],
        "role": "char_bass",
        "lang_name": "Spanish",
        "seed": 120303,
        "temperature": 0.76,
        "subtalker_temperature": 0.78,
        "instruct": (
            "Un hombre adulto, voz masculina muy grave, cálida, profunda y resonante (registro de pecho varonil bajo alrededor de 115-125 Hz). "
            "Firme, calmado y fraterno."
        ),
        "text": "Vamos, hermano, confía en ti. Te lo sabes de memoria. Sal ahí afuera con calma y seguridad, y ya verás que te van a aplaudir de pie.",
    },
    {
        "language": "spanish",
        "gender": "male",
        "filename": "spanish_male_kokoro_golden_baritone.wav",
        "pitch_tier": "baritone",
        "aliases": ["spanish_male_kokoro_golden_char1.wav"],
        "role": "char_baritone",
        "lang_name": "Spanish",
        "seed": 130404,
        "temperature": 0.78,
        "subtalker_temperature": 0.80,
        "instruct": (
            "Un presentador hispanohablante adulto, voz masculina de registro barítono cálido, cercano y carismático (alrededor de 140-155 Hz). "
            "Dicción limpia, tono natural y entusiasta."
        ),
        "text": "¡Hola a todos! ¿Te gustaría hablar español como un verdadero nativo? Hoy te explico un modismo genial que todo el mundo usa a diario.",
    },
    {
        "language": "spanish",
        "gender": "male",
        "filename": "spanish_male_kokoro_golden_tenor.wav",
        "pitch_tier": "tenor",
        "aliases": [],
        "role": "char_tenor",
        "lang_name": "Spanish",
        "seed": 110202,
        "temperature": 0.80,
        "subtalker_temperature": 0.82,
        "instruct": (
            "Un joven hispanohablante enérgico, vivaz y simpático, registro tenor ligero y ágil (alrededor de 165-185 Hz). "
            "Muy espontáneo y divertido en el diálogo."
        ),
        "text": "¡¿En serio me dices eso?! ¡No me lo puedo creer! Explícame bien cómo funciona, que quiero aprenderlo ahora mismo.",
    },
    {
        "language": "spanish",
        "gender": "male",
        "filename": "spanish_male_kokoro_golden_narrator.wav",
        "pitch_tier": "narrator_male",
        "aliases": [],
        "role": "narrator",
        "lang_name": "Spanish",
        "seed": 130404,
        "temperature": 0.78,
        "subtalker_temperature": 0.80,
        "instruct": (
            "Un presentador hispanohablante carismático, entusiasta y cercano, voz masculina de registro barítono cálido (alrededor de 145 Hz). "
            "Dicción impecable, ritmo dinámico y atrapante."
        ),
        "text": "¡Hola a todos! ¿Sabías este secreto del idioma español? ¡Hoy vamos a descubrir una expresión fantástica que usan todos los nativos!",
    },

    # =========================================================================
    # ITALIAN FEMALE
    # =========================================================================
    {
        "language": "italian",
        "gender": "female",
        "filename": "italian_female_kokoro_golden_alto.wav",
        "pitch_tier": "alto",
        "aliases": ["italian_female_kokoro_golden_char1.wav"],
        "role": "char_alto",
        "lang_name": "Italian",
        "seed": 7654,
        "temperature": 0.76,
        "subtalker_temperature": 0.78,
        "instruct": (
            "Una donna adulta italiana con voce calda, profonda e posata, registro contralto naturale di petto (circa 195-205 Hz). "
            "Dizione chiara, rassicurante, solare ma priva di toni acuti o striduli."
        ),
        "text": "Fermati un attimo e fai un bel respiro profondo. Vedrai che non è affatto difficile come credevi, basta prenderla con la giusta calma.",
    },
    {
        "language": "italian",
        "gender": "female",
        "filename": "italian_female_kokoro_golden_mezzo.wav",
        "pitch_tier": "mezzo",
        "aliases": ["italian_female_kokoro_golden_char2.wav"],
        "role": "char_mezzo",
        "lang_name": "Italian",
        "seed": 60606,
        "temperature": 0.78,
        "subtalker_temperature": 0.80,
        "instruct": (
            "Un'amica italiana calorosa, solare, sorridente e naturale, registro medio equilibrato (circa 220-235 Hz). "
            "Voce rassicurante, allegra e piena di contagioso ottimismo."
        ),
        "text": "Ma no, calmati, vedrai che andrà benissimo! Quando usi le parole giuste con sicurezza, conquisti tutti al primo colpo!",
    },
    {
        "language": "italian",
        "gender": "female",
        "filename": "italian_female_kokoro_golden_soprano.wav",
        "pitch_tier": "soprano",
        "aliases": [],
        "role": "char_soprano",
        "lang_name": "Italian",
        "seed": 50505,
        "temperature": 0.80,
        "subtalker_temperature": 0.82,
        "instruct": (
            "Una giovane donna italiana briosa, vivace e solare, registro soprano leggero e allegro (circa 250-270 Hz). "
            "Molto espressiva e spontanea ma piacevole e senza strilli."
        ),
        "text": "Ma dai, dici davvero?! Ma è fantastico! Spiegami subito come si usa questa espressione, sono troppo curiosa!",
    },
    {
        "language": "italian",
        "gender": "female",
        "filename": "italian_female_kokoro_golden_narrator.wav",
        "pitch_tier": "narrator_female",
        "aliases": [],
        "role": "narrator",
        "lang_name": "Italian",
        "seed": 5555,
        "temperature": 0.78,
        "subtalker_temperature": 0.80,
        "instruct": (
            "Una presentatrice italiana brillante, solare ed entusiasta, registro medio naturale (circa 225 Hz). "
            "Dizione italiana impeccabile, ricca musicalità naturale, ritmo vivace, caloroso e coinvolgente."
        ),
        "text": "Ciao a tutti! Lo sapevi questo segreto incredibile? Oggi scopriamo insieme un'espressione fantastica della lingua italiana che cambia davvero tutto!",
    },

    # =========================================================================
    # ITALIAN MALE
    # =========================================================================
    {
        "language": "italian",
        "gender": "male",
        "filename": "italian_male_kokoro_golden_bass.wav",
        "pitch_tier": "bass",
        "aliases": ["italian_male_kokoro_golden_char2.wav"],
        "role": "char_bass",
        "lang_name": "Italian",
        "seed": 80808,
        "temperature": 0.76,
        "subtalker_temperature": 0.78,
        "instruct": (
            "Un uomo adulto italiano, voce maschile profonda, calda, grave e rassicurante (registro di petto basso circa 115-125 Hz). "
            "Fraterno, motivatore, calmo e virile."
        ),
        "text": "Fidati di me, respira con calma. Sei preparatissimo, vai lì a testa alta, sfodera questa espressione e andrà alla perfezione.",
    },
    {
        "language": "italian",
        "gender": "male",
        "filename": "italian_male_kokoro_golden_baritone.wav",
        "pitch_tier": "baritone",
        "aliases": ["italian_male_kokoro_golden_char1.wav"],
        "role": "char_baritone",
        "lang_name": "Italian",
        "seed": 8888,
        "temperature": 0.78,
        "subtalker_temperature": 0.80,
        "instruct": (
            "Un brillante conduttore italiano, voce maschile naturale di registro baritono caloroso, limpido e carismatico (circa 140-155 Hz). "
            "Dizione limpida, ritmo vivace e irresistibile simpatia italiana."
        ),
        "text": "Ciao a tutti! Ti sei mai chiesto come parlano davvero i madrelingua? Oggi sveliamo un segreto della lingua italiana che ti lascerà a bocca aperta!",
    },
    {
        "language": "italian",
        "gender": "male",
        "filename": "italian_male_kokoro_golden_tenor.wav",
        "pitch_tier": "tenor",
        "aliases": [],
        "role": "char_tenor",
        "lang_name": "Italian",
        "seed": 70707,
        "temperature": 0.80,
        "subtalker_temperature": 0.82,
        "instruct": (
            "Un giovane uomo italiano dinamico, brillante, ironico e spontaneo, registro tenore agile ed energico (circa 165-185 Hz). "
            "Simpatico, reattivo e vivace senza toni striduli."
        ),
        "text": "Mamma mia, che situazione incredibile! Raccontami bene tutti i dettagli, sono prontissimo a scoprire questa novità!",
    },
    {
        "language": "italian",
        "gender": "male",
        "filename": "italian_male_kokoro_golden_narrator.wav",
        "pitch_tier": "narrator_male",
        "aliases": [],
        "role": "narrator",
        "lang_name": "Italian",
        "seed": 8888,
        "temperature": 0.78,
        "subtalker_temperature": 0.80,
        "instruct": (
            "Un brillante conduttore italiano, voce maschile naturale di registro baritono caloroso ed energico (circa 145 Hz). "
            "Dizione limpida, ritmo incalzante e irresistibile simpatia italiana."
        ),
        "text": "Ciao a tutti! Ti sei mai chiesto come parlano davvero i madrelingua? Oggi sveliamo un segreto della lingua italiana che ti lascerà a bocca aperta!",
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Multi-Tier VoiceDesign Golden References")
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Filter by language: french, italian, spanish",
    )
    args = parser.parse_args()

    if not VOICEDESIGN_MODEL_DIR.exists():
        print(f"Error: Model not found at {VOICEDESIGN_MODEL_DIR}", file=sys.stderr)
        return 1

    print("Loading Qwen3-TTS-12Hz-1.7B-VoiceDesign on GPU...")
    # pyrefly: ignore[missing-import]
    from qwen_tts import Qwen3TTSModel

    model = Qwen3TTSModel.from_pretrained(
        str(VOICEDESIGN_MODEL_DIR),
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )
    print("VoiceDesign model successfully loaded!")

    transcripts: Dict[str, str] = {}
    if REF_TRANSCRIPTS_PATH.exists():
        try:
            transcripts = json.loads(REF_TRANSCRIPTS_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: Could not read existing transcripts registry: {e}")

    specs_to_run = VOICEDESIGN_REFERENCE_SPECS
    if args.language:
        lang_filter = args.language.strip().lower()
        specs_to_run = [s for s in specs_to_run if s["language"].lower() == lang_filter]

    print(f"\nGenerating {len(specs_to_run)} Multi-Tier VoiceDesign Golden References...")
    print("=" * 70)

    for spec in specs_to_run:
        lang = spec["language"]
        gender = spec["gender"]
        fname = spec["filename"]
        seed = spec["seed"]
        rel_path = f"{lang}/{gender}/{fname}"
        dest_dir = OPEN_SWARA_DIR / lang / gender
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / fname

        temp = spec.get("temperature", 0.78)
        sub_temp = spec.get("subtalker_temperature", 0.80)

        print(f"\n[Generating] {rel_path} (Seed: {seed} | Tier: {spec.get('pitch_tier', 'n/a')})")
        print(f"  Instruct: {spec['instruct'][:60]}...")
        print(f"  Text:     {spec['text'][:60]}...")

        # Set deterministic seed
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        np.random.seed(seed % (2**32))

        wavs, sr = model.generate_voice_design(
            text=spec["text"],
            instruct=spec["instruct"],
            language=spec["lang_name"],
            temperature=temp,
            top_p=0.90,
            subtalker_temperature=sub_temp,
            repetition_penalty=1.05,
        )

        samples = wavs[0]
        if samples.ndim > 1:
            samples = np.mean(samples, axis=-1)

        # Normalize peak to -1.5 dBFS
        peak = float(np.max(np.abs(samples)))
        if peak > 1e-5:
            samples = (samples / peak * 0.84).astype(np.float32)

        sf.write(str(dest_path), samples, sr)

        # Register transcript
        transcripts[rel_path] = spec["text"]
        transcripts[fname] = spec["text"]

        # Handle backward-compatible aliases (e.g. char1, char2)
        for alias_name in spec.get("aliases", []):
            alias_dest = dest_dir / alias_name
            shutil.copy2(str(dest_path), str(alias_dest))
            alias_rel = f"{lang}/{gender}/{alias_name}"
            transcripts[alias_rel] = spec["text"]
            transcripts[alias_name] = spec["text"]
            print(f"  -> Created alias copy: {alias_name}")

        # Evaluate acoustic metrics
        score, passes, issues, metrics = evaluate_voice_take(
            str(dest_path), target_text=spec["text"], language=lang
        )
        dur = metrics.get("duration", 0.0)
        f0 = metrics.get("mean_f0", 0.0)
        std_f0 = metrics.get("std_f0", 0.0)
        pvar = metrics.get("pitch_variance", 0.0)
        rms = metrics.get("rms", 0.0)

        print(f"  [Output] {dest_path.name} ({dur:.2f}s | F0: {f0:.1f} Hz | std: {std_f0:.1f} Hz | PitchVar: {pvar*100:.1f}% | RMS: {rms:.4f})")

    # Update transcripts file
    REF_TRANSCRIPTS_PATH.write_text(json.dumps(transcripts, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nUpdated ref transcripts registry: {REF_TRANSCRIPTS_PATH}")
    print("=" * 70)
    print("All Multi-Tier VoiceDesign Golden References generated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
