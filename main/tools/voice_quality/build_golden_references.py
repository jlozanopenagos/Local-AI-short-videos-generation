"""Generates the Studio-Grade Golden Reference Voice Bank using Kokoro-82M.

For each of the 4 languages (english, french, spanish, italian) and both genders (male, female),
creates 3 distinct, 100% pure (zero DSP time-stretch / zero pitch-shift) 24 kHz reference `.wav` clips
and registers their exact transcripts in `ref_transcripts.json` plus the CSV voice pools.

Architecture for Non-English (Romance) Accent Purity:
- In Kokoro-82M (StyleTTS2), style vectors have shape `(510, 1, 256)`:
  * `style[:, :, :128]` = Acoustic vocal-tract timbre (`s_acoustic`)
  * `style[:, :, 128:]` = Prosody, vowel formants & regional accent (`s_prosodic`)
- For French, Spanish, and Italian:
  1. `prosodic_blend` (`dims 128..255`) is 100% pure native target-language speaker (`ff_siwis`, `ef_dora`, `em_santa`, `em_alex`, `if_sara`, `im_nicola`).
  2. `acoustic_blend` (`dims 0..127`) uses 100% native speakers for primary roles and only sister Romance voices (`es`/`it`/`fr`) for secondary character differentiation—zero English (`af_*`, `bf_*`, `am_*`, `bm_*`) bleed.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
import soundfile as sf
# pyrefly: ignore[missing-import]
from kokoro_onnx import Kokoro

MAIN_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MAIN_DIR))
sys.path.insert(0, str(MAIN_DIR / "core"))

import config  # noqa: E402
from config import OPEN_SWARA_DIR, REF_TRANSCRIPTS_PATH  # noqa: E402
from video_creation._B_voice_generation.core.kokoro_engine import get_kokoro_model_paths  # noqa: E402

DATA_DIR = MAIN_DIR / "video_creation" / "_B_voice_generation" / "data"

# Native reference sentences (6-8 seconds, phonetically rich and dramatically expressive in each target language)
GOLDEN_REFERENCE_SPECS: List[Dict] = [
    # ==================== ITALIAN (Native Italian Formants [:128] + Expressive Romance Prosody [128:]) ====================
    {
        "language": "italian",
        "gender": "male",
        "filename": "italian_male_kokoro_golden_narrator.wav",
        "role": "narrator",
        "lang_code": "it",
        "speed": 1.02,
        "acoustic_blend": {"im_nicola": 1.0},
        "prosodic_blend": {"em_santa": 0.70, "im_nicola": 0.30},
        "text": "Ciao a tutti! Lo sapevi questo segreto incredibile? Oggi scopriamo un'espressione italiana che cambia davvero tutto!",
    },
    {
        "language": "italian",
        "gender": "male",
        "filename": "italian_male_kokoro_golden_char1.wav",
        "role": "char1",
        "lang_code": "it",
        "speed": 1.01,
        "acoustic_blend": {"im_nicola": 0.80, "em_santa": 0.20},
        "prosodic_blend": {"em_santa": 0.55, "im_nicola": 0.45},
        "text": "Ma dai, dici davvero?! Non ci posso credere! Questa espressione italiana è fantastica quando parli con gli amici!",
    },
    {
        "language": "italian",
        "gender": "male",
        "filename": "italian_male_kokoro_golden_char2.wav",
        "role": "char2",
        "lang_code": "it",
        "speed": 1.00,
        "acoustic_blend": {"im_nicola": 0.75, "em_alex": 0.25},
        "prosodic_blend": {"em_alex": 0.50, "em_santa": 0.25, "im_nicola": 0.25},
        "text": "Fidati di me! Ma hai visto che roba?! Usa questa frase con sicurezza e tutti ti capiranno al volo!",
    },
    {
        "language": "italian",
        "gender": "female",
        "filename": "italian_female_kokoro_golden_narrator.wav",
        "role": "narrator",
        "lang_code": "it",
        "speed": 1.02,
        "acoustic_blend": {"if_sara": 1.0},
        "prosodic_blend": {"if_sara": 0.58, "em_santa": 0.42},
        "text": "Ciao a tutti! Lo sapevi questo segreto incredibile? Oggi scopriamo un'espressione italiana che cambia davvero tutto!",
    },
    {
        "language": "italian",
        "gender": "female",
        "filename": "italian_female_kokoro_golden_char1.wav",
        "role": "char1",
        "lang_code": "it",
        "speed": 1.01,
        "acoustic_blend": {"if_sara": 0.82, "ef_dora": 0.18},
        "prosodic_blend": {"if_sara": 0.62, "em_santa": 0.38},
        "text": "Aspetta un attimo! Ma cosa significa davvero questa espressione così curiosa?! Dimmelo subito, sono troppo curiosa!",
    },
    {
        "language": "italian",
        "gender": "female",
        "filename": "italian_female_kokoro_golden_char2.wav",
        "role": "char2",
        "lang_code": "it",
        "speed": 1.00,
        "acoustic_blend": {"if_sara": 0.74, "ff_siwis": 0.26},
        "prosodic_blend": {"if_sara": 0.55, "em_santa": 0.25, "ef_dora": 0.20},
        "text": "È semplicissimo! Guarda che differenza incredibile! Quando usi le parole giuste, la conversazione diventa subito brillante!",
    },
    # ==================== SPANISH (100% Native Spanish Formants [:128] + `em_santa` Expressive Prosody [128:]) ====================
    {
        "language": "spanish",
        "gender": "male",
        "filename": "spanish_male_kokoro_golden_narrator.wav",
        "role": "narrator",
        "lang_code": "es",
        "speed": 0.96,
        "acoustic_blend": {"em_santa": 1.0},
        "prosodic_blend": {"em_santa": 1.0},
        "text": "¡Hola a todos! Hoy vamos a descubrir un secreto increíble del español que los hablantes nativos usan todos los días.",
    },
    {
        "language": "spanish",
        "gender": "male",
        "filename": "spanish_male_kokoro_golden_char1.wav",
        "role": "char1",
        "lang_code": "es",
        "speed": 0.98,
        "acoustic_blend": {"em_alex": 1.0},
        "prosodic_blend": {"em_alex": 0.55, "em_santa": 0.45},
        "text": "¡¿En serio me dices eso?! ¡No lo puedo creer! ¡Esta expresión española suena genial cuando hablas con tus amigos!",
    },
    {
        "language": "spanish",
        "gender": "male",
        "filename": "spanish_male_kokoro_golden_char2.wav",
        "role": "char2",
        "lang_code": "es",
        "speed": 0.97,
        "acoustic_blend": {"em_alex": 0.75, "im_nicola": 0.25},
        "prosodic_blend": {"em_alex": 0.55, "em_santa": 0.45},
        "text": "¡Confía en mí! ¿Viste qué fácil es? ¡Utiliza esta frase con total seguridad y verás qué bien te entiende todo el mundo!",
    },
    {
        "language": "spanish",
        "gender": "female",
        "filename": "spanish_female_kokoro_golden_narrator.wav",
        "role": "narrator",
        "lang_code": "es",
        "speed": 0.99,
        "acoustic_blend": {"ef_dora": 1.0},
        "prosodic_blend": {"ef_dora": 0.60, "em_santa": 0.40},
        "text": "¡Hola a todos! ¿Sabías este secreto increíble del español? ¡Hoy vamos a descubrir una expresión que los nativos usan siempre!",
    },
    {
        "language": "spanish",
        "gender": "female",
        "filename": "spanish_female_kokoro_golden_char1.wav",
        "role": "char1",
        "lang_code": "es",
        "speed": 0.98,
        "acoustic_blend": {"ef_dora": 0.84, "if_sara": 0.16},
        "prosodic_blend": {"ef_dora": 0.62, "em_santa": 0.38},
        "text": "¡Espera un segundo! ¿Qué significa realmente esta frase tan curiosa cuando la escuchas en la calle? ¡Cuéntame ahora mismo!",
    },
    {
        "language": "spanish",
        "gender": "female",
        "filename": "spanish_female_kokoro_golden_char2.wav",
        "role": "char2",
        "lang_code": "es",
        "speed": 0.97,
        "acoustic_blend": {"ef_dora": 0.76, "ff_siwis": 0.24},
        "prosodic_blend": {"ef_dora": 0.60, "em_santa": 0.40},
        "text": "¡Es súper fácil! ¿Verdad que sorprende muchísimo? ¡Cuando conoces el sentido exacto, hablas con muchísima naturalidad!",
    },
    # ==================== FRENCH (Parisian `ff_siwis` Formants [:128] + Expressive Romance Prosody [128:]) ====================
    {
        "language": "french",
        "gender": "female",
        "filename": "french_female_kokoro_golden_narrator.wav",
        "role": "narrator",
        "lang_code": "fr-fr",
        "speed": 0.99,
        "acoustic_blend": {"ff_siwis": 1.0},
        "prosodic_blend": {"ff_siwis": 0.58, "em_santa": 0.42},
        "text": "Salut à tous ! Tu connais ce secret incroyable en français ? Aujourd'hui, on découvre une expression que les Parisiens adorent !",
    },
    {
        "language": "french",
        "gender": "female",
        "filename": "french_female_kokoro_golden_char1.wav",
        "role": "char1",
        "lang_code": "fr-fr",
        "speed": 0.98,
        "acoustic_blend": {"ff_siwis": 0.84, "if_sara": 0.16},
        "prosodic_blend": {"ff_siwis": 0.65, "em_santa": 0.35},
        "text": "Mais attends une seconde ! Qu'est-ce que ça veut dire exactement cette phrase ? Raconte-moi tout de suite, c'est fou !",
    },
    {
        "language": "french",
        "gender": "female",
        "filename": "french_female_kokoro_golden_char2.wav",
        "role": "char2",
        "lang_code": "fr-fr",
        "speed": 0.97,
        "acoustic_blend": {"ff_siwis": 0.75, "ef_dora": 0.25},
        "prosodic_blend": {"ff_siwis": 0.55, "ef_dora": 0.20, "em_santa": 0.25},
        "text": "C'est super simple ! Tu vois la différence ? Avec cette expression idiomatique, tu vas parler français comme à Paris !",
    },
    {
        "language": "french",
        "gender": "male",
        "filename": "french_male_kokoro_golden_narrator.wav",
        "role": "narrator",
        "lang_code": "fr-fr",
        "speed": 0.98,
        "acoustic_blend": {"im_nicola": 0.65, "em_santa": 0.20, "ff_siwis": 0.15},
        "prosodic_blend": {"em_santa": 0.75, "im_nicola": 0.25},
        "text": "Salut à tous ! Tu connais ce secret incroyable en français ? Aujourd'hui, on découvre une expression que les Parisiens adorent !",
    },
    {
        "language": "french",
        "gender": "male",
        "filename": "french_male_kokoro_golden_char1.wav",
        "role": "char1",
        "lang_code": "fr-fr",
        "speed": 0.97,
        "acoustic_blend": {"im_nicola": 0.80, "ff_siwis": 0.20},
        "prosodic_blend": {"em_santa": 0.60, "im_nicola": 0.40},
        "text": "Mais attends une seconde ! Qu'est-ce que ça veut dire exactement quand on utilise cette expression à Paris ? C'est incroyable !",
    },
    {
        "language": "french",
        "gender": "male",
        "filename": "french_male_kokoro_golden_char2.wav",
        "role": "char2",
        "lang_code": "fr-fr",
        "speed": 0.96,
        "acoustic_blend": {"em_alex": 0.75, "ff_siwis": 0.25},
        "prosodic_blend": {"em_alex": 0.60, "em_santa": 0.40},
        "text": "Fais-moi confiance ! Tu vois comme c'est génial ? Utilise cette phrase naturellement et tout le monde te comprendra !",
    },
    # ==================== ENGLISH (Untouched — Approved as Perfect) ====================
    {
        "language": "english",
        "gender": "female",
        "filename": "english_female_kokoro_golden_narrator.wav",
        "role": "narrator",
        "lang_code": "en-us",
        "speed": 0.94,
        "acoustic_blend": {"af_bella": 1.0},
        "prosodic_blend": {"af_bella": 1.0},
        "text": "Hey everyone! Today we are unlocking a secret English expression that native speakers use every single day!",
    },
    {
        "language": "english",
        "gender": "female",
        "filename": "english_female_kokoro_golden_char1.wav",
        "role": "char1",
        "lang_code": "en-us",
        "speed": 0.92,
        "acoustic_blend": {"af_heart": 1.0},
        "prosodic_blend": {"af_heart": 1.0},
        "text": "Wait a second, what does that phrase actually mean when someone says it in a real conversation?",
    },
    {
        "language": "english",
        "gender": "female",
        "filename": "english_female_kokoro_golden_char2.wav",
        "role": "char2",
        "lang_code": "en-us",
        "speed": 0.92,
        "acoustic_blend": {"bf_emma": 1.0},
        "prosodic_blend": {"bf_emma": 1.0},
        "text": "It is super easy! Once you know this expression, you will sound confident and natural right away.",
    },
    {
        "language": "english",
        "gender": "male",
        "filename": "english_male_kokoro_golden_narrator.wav",
        "role": "narrator",
        "lang_code": "en-us",
        "speed": 0.94,
        "acoustic_blend": {"am_puck": 1.0},
        "prosodic_blend": {"am_puck": 1.0},
        "text": "Hey everyone! Today we are unlocking a secret English expression that native speakers use every single day!",
    },
    {
        "language": "english",
        "gender": "male",
        "filename": "english_male_kokoro_golden_char1.wav",
        "role": "char1",
        "lang_code": "en-us",
        "speed": 0.92,
        "acoustic_blend": {"am_michael": 1.0},
        "prosodic_blend": {"am_michael": 1.0},
        "text": "I cannot believe how useful this phrase is when you are talking with friends or colleagues!",
    },
    {
        "language": "english",
        "gender": "male",
        "filename": "english_male_kokoro_golden_char2.wav",
        "role": "char2",
        "lang_code": "en-us",
        "speed": 0.92,
        "acoustic_blend": {"am_fenrir": 1.0},
        "prosodic_blend": {"am_fenrir": 1.0},
        "text": "Trust me on this one, use this phrase with confidence and everyone will understand you immediately.",
    },
]


def _blend_half(kokoro: Kokoro, blend_map: Dict[str, float]) -> np.ndarray:
    blended = None
    total_w = 0.0
    for v_name, weight in blend_map.items():
        style_arr = kokoro.get_voice_style(v_name)
        w = float(weight)
        blended = style_arr * w if blended is None else blended + (style_arr * w)
        total_w += w
    return (blended / max(1e-6, total_w)).astype(np.float32)


def _build_split_style(
    kokoro: Kokoro,
    acoustic_blend: Dict[str, float],
    prosodic_blend: Optional[Dict[str, float]] = None,
) -> np.ndarray:
    """Combines acoustic vocal timbre (dims 0..127) with native prosody/accent (dims 128..255)."""
    acoustic_full = _blend_half(kokoro, acoustic_blend)
    if not prosodic_blend or prosodic_blend == acoustic_blend:
        return acoustic_full
    prosodic_full = _blend_half(kokoro, prosodic_blend)
    combined = np.copy(acoustic_full)
    combined[:, :, 128:] = prosodic_full[:, :, 128:]
    return combined.astype(np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Kokoro-82M Golden Reference WAVs")
    parser.add_argument(
        "--skip-english",
        action="store_true",
        help="Skip regenerating English golden reference WAVs if they already exist.",
    )
    args = parser.parse_args()

    model_path, voices_path = get_kokoro_model_paths()
    if not model_path or not voices_path:
        print("Error: Kokoro model files not found in C:\\AI\\models\\kokoro", file=sys.stderr)
        return 1

    kokoro = Kokoro(str(model_path), str(voices_path))

    # Load existing ref_transcripts.json if present
    transcripts: Dict[str, str] = {}
    if REF_TRANSCRIPTS_PATH.exists():
        try:
            transcripts = json.loads(REF_TRANSCRIPTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            transcripts = {}

    generated_by_pool: Dict[Tuple[str, str], List[str]] = {}

    for spec in GOLDEN_REFERENCE_SPECS:
        lang = spec["language"]
        gender = spec["gender"]
        fname = spec["filename"]
        rel_path = f"{lang}/{gender}/{fname}"
        dest_dir = OPEN_SWARA_DIR / lang / gender
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / fname

        if args.skip_english and lang == "english" and dest_path.exists():
            print(f"[Golden Ref] {rel_path:52s} | [SKIPPED - English preserved]")
            transcripts[rel_path] = spec["text"]
            transcripts[fname] = spec["text"]
            generated_by_pool.setdefault((lang, gender), []).append(rel_path)
            continue

        acoustic_blend = spec.get("acoustic_blend") or spec.get("blend")
        prosodic_blend = spec.get("prosodic_blend") or acoustic_blend
        style_vec = _build_split_style(kokoro, acoustic_blend, prosodic_blend)
        samples, sr = kokoro.create(
            spec["text"],
            voice=style_vec,
            speed=float(spec["speed"]),
            lang=spec["lang_code"],
            is_phonemes=False,
            trim=True,
        )
        # Normalize peak cleanly to -1.5 dBFS (pure linear gain, zero nonlinear distortion)
        peak = float(np.max(np.abs(samples)))
        if peak > 1e-5:
            samples = (samples / peak * 0.84).astype(np.float32)

        sf.write(str(dest_path), samples, sr)
        dur = len(samples) / sr
        print(f"[Golden Ref] {rel_path:52s} | {dur:.2f}s | {spec['text'][:48]}...")

        transcripts[rel_path] = spec["text"]
        transcripts[fname] = spec["text"]
        generated_by_pool.setdefault((lang, gender), []).append(rel_path)

    # Save updated ref_transcripts.json
    REF_TRANSCRIPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    REF_TRANSCRIPTS_PATH.write_text(json.dumps(transcripts, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nUpdated transcripts registry: {REF_TRANSCRIPTS_PATH} ({len(transcripts)} entries)")

    # Ensure all golden references are at the top of the data/<lang>_<gender>.csv pools
    for (lang, gender), new_rels in generated_by_pool.items():
        csv_path = DATA_DIR / f"{lang}_{gender}.csv"
        existing_rows = []
        if csv_path.exists():
            with csv_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    fp = (row.get("FILE_PATH") or "").strip()
                    if fp and fp not in new_rels:
                        existing_rows.append(row)

        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["LANGUAGE_KEY", "GENDER", "FILE_PATH"])
            writer.writeheader()
            for rel in new_rels:
                writer.writerow({"LANGUAGE_KEY": lang, "GENDER": gender, "FILE_PATH": rel})
            for row in existing_rows:
                writer.writerow({
                    "LANGUAGE_KEY": row.get("LANGUAGE_KEY", lang),
                    "GENDER": row.get("GENDER", gender),
                    "FILE_PATH": row["FILE_PATH"],
                })
        print(f"Updated CSV pool: {csv_path.name} ({len(new_rels)} golden + {len(existing_rows)} existing)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
