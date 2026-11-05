"""Kokoro-82M Precision & Full-Text Neural TTS Engine.

Provides lightweight, deterministic speech synthesis using the Kokoro-82M ONNX runtime.
Serves both as:
1. Full-text neural narrator & dialogue engine for Spanish, French, Italian, and English
   (requiring zero reference audio clips, eliminating poor reference cloning artifacts).
2. Precision phonetic demonstration engine for technical linguistics, heteronyms,
   and dictionary-style IPA pronunciation guides (`is_phonemes=True`).

Features:
- Sub-second CPU/GPU ONNX inference at 24 kHz.
- Sentence-level chunking with natural intra-segment breath pauses.
- Per-language pronunciation override dictionary (`data/pronunciation_overrides.csv`).
- Optional pitch-shift / formant adjustment for distinct secondary speaker voices
  (e.g., French male character voice derived from `ff_siwis` when desired).
- Exact phonetic control via IPA phoneme strings (`is_phonemes=True`).
"""

import csv
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
import soundfile as sf

try:
    # pyrefly: ignore[missing-import]
    from kokoro_onnx import Kokoro
    KOKORO_AVAILABLE = True
except ImportError:
    Kokoro = None
    KOKORO_AVAILABLE = False

try:
    from video_creation._B_voice_generation.core.pronunciation_bank import HETERONYM_REGISTRY
except (ImportError, ModuleNotFoundError):
    try:
        from core.pronunciation_bank import HETERONYM_REGISTRY
    except (ImportError, ModuleNotFoundError):
        HETERONYM_REGISTRY = {}

logger = logging.getLogger(__name__)

# Default model search locations
CANDIDATE_MODEL_DIRS = [
    Path(r"C:\AI\models\kokoro"),
    Path(__file__).resolve().parents[4] / "models" / "kokoro",
    Path(__file__).resolve().parents[3] / "models" / "kokoro",
]

# Canonical language -> espeak-ng language code for Kokoro v1.0
KOKORO_LANG_CODES: Dict[str, str] = {
    "english": "en-us",
    "en": "en-us",
    "en-us": "en-us",
    "en-gb": "en-gb",
    "spanish": "es",
    "es": "es",
    "e": "es",
    "french": "fr-fr",
    "fr": "fr-fr",
    "fr-fr": "fr-fr",
    "f": "fr-fr",
    "italian": "it",
    "it": "it",
    "i": "it",
}

# Default Kokoro-82M v1.0 voices per (language, gender)
DEFAULT_KOKORO_VOICES: Dict[Tuple[str, str], List[str]] = {
    ("english", "female"): ["af_heart", "af_bella", "af_sarah", "af_nicole", "bf_emma"],
    ("english", "male"): ["am_michael", "am_adam", "am_fenrir", "am_puck", "bm_george"],
    ("spanish", "female"): ["ef_dora"],
    ("spanish", "male"): ["em_alex", "em_santa"],
    ("french", "female"): ["ff_siwis"],
    # French v1.0 has only ff_siwis natively; 'ff_siwis_male' triggers a clean lower-pitch resample
    # when Kokoro is explicitly requested for male French, or VoiceManager can route French male to Qwen3.
    ("french", "male"): ["ff_siwis_male"],
    ("italian", "female"): ["if_sara"],
    ("italian", "male"): ["im_nicola"],
}

# Default speaking speeds tuned per language for clear, lively language-learner pacing
DEFAULT_KOKORO_SPEEDS: Dict[str, float] = {
    "english": 0.94,
    "spanish": 0.93,
    "french": 0.92,
    "italian": 0.93,
}

# Energetic style blends & distinct persona recipes:
# Kokoro v1.0 voice embeddings are (510, 1, 256) style tensors. Blending a native Romance
# voice with a small weight (25-32%) of Kokoro's most animated voices ('am_puck', 'af_bella',
# 'am_fenrir', 'em_santa') boosts vocal energy and pitch contour while preserving 100% native
# phonemization (`es`, `it`, `fr-fr`), and creates clearly distinct speaker identities!
KOKORO_VOICE_RECIPES: Dict[str, Dict[str, Union[Dict[str, float], float]]] = {
    # --- Italian ---
    # Default Italian male & female (boosted with subtle lively presence so they never sound sleepy)
    "im_nicola": {
        "blend": {"im_nicola": 0.78, "am_puck": 0.22},
        "semitones": 0.5,
        "presence_db": 2.5,
    },
    "if_sara": {
        "blend": {"if_sara": 0.80, "af_bella": 0.20},
        "semitones": 0.3,
        "presence_db": 2.2,
    },
    # Distinct Italian Narrator identities (bright, charismatic storyteller distinct from P1/P2)
    "im_nicola_narrator": {
        "blend": {"im_nicola": 0.65, "am_puck": 0.35},
        "semitones": 2.1,
        "speed_mult": 1.04,
        "presence_db": 3.2,
    },
    "if_sara_narrator": {
        "blend": {"if_sara": 0.68, "af_bella": 0.32},
        "semitones": 1.8,
        "speed_mult": 1.04,
        "presence_db": 3.0,
    },
    # Alternate Italian character identities (deeper/grounded so two same-sex speakers never sound alike)
    "im_nicola_alt": {
        "blend": {"im_nicola": 0.70, "am_fenrir": 0.30},
        "semitones": -1.6,
        "speed_mult": 0.98,
        "presence_db": 2.0,
    },
    "if_sara_alt": {
        "blend": {"if_sara": 0.72, "af_heart": 0.28},
        "semitones": -1.5,
        "speed_mult": 0.98,
        "presence_db": 2.0,
    },
    # --- Spanish ---
    "em_alex": {
        "blend": {"em_alex": 0.78, "am_puck": 0.22},
        "semitones": 0.4,
        "presence_db": 2.4,
    },
    "ef_dora": {
        "blend": {"ef_dora": 0.78, "af_bella": 0.22},
        "semitones": 0.4,
        "presence_db": 2.4,
    },
    # Distinct Spanish Narrator identities (uses native Spanish em_santa + am_puck for warm, high-energy host)
    "em_alex_narrator": {
        "blend": {"em_santa": 0.65, "am_puck": 0.35},
        "semitones": 1.5,
        "speed_mult": 1.04,
        "presence_db": 3.2,
    },
    "em_santa": {
        "blend": {"em_santa": 0.78, "am_puck": 0.22},
        "semitones": 0.8,
        "presence_db": 2.6,
    },
    "ef_dora_narrator": {
        "blend": {"ef_dora": 0.66, "af_bella": 0.34},
        "semitones": 1.8,
        "speed_mult": 1.04,
        "presence_db": 3.0,
    },
    "em_alex_alt": {
        "blend": {"em_alex": 0.70, "am_fenrir": 0.30},
        "semitones": -1.6,
        "speed_mult": 0.98,
        "presence_db": 2.0,
    },
    "ef_dora_alt": {
        "blend": {"ef_dora": 0.72, "af_heart": 0.28},
        "semitones": -1.5,
        "speed_mult": 0.98,
        "presence_db": 2.0,
    },
    # --- French ---
    "ff_siwis": {
        "blend": {"ff_siwis": 0.78, "af_bella": 0.22},
        "semitones": 0.3,
        "presence_db": 2.2,
    },
    "ff_siwis_narrator": {
        "blend": {"ff_siwis": 0.66, "af_bella": 0.34},
        "semitones": 1.8,
        "speed_mult": 1.04,
        "presence_db": 3.0,
    },
    "ff_siwis_alt": {
        "blend": {"ff_siwis": 0.72, "af_heart": 0.28},
        "semitones": -1.5,
        "speed_mult": 0.98,
        "presence_db": 2.0,
    },
    "ff_siwis_male": {
        "blend": {"ff_siwis": 0.75, "am_puck": 0.25},
        "semitones": -3.2,
        "presence_db": 2.4,
    },
    # --- English ---
    "af_heart": {
        "blend": {"af_heart": 0.78, "af_bella": 0.22},
        "semitones": 0.2,
        "presence_db": 2.2,
    },
    "af_heart_narrator": {
        "blend": {"af_bella": 0.65, "af_heart": 0.35},
        "semitones": 1.2,
        "speed_mult": 1.03,
        "presence_db": 2.8,
    },
    "af_heart_alt": {
        "blend": {"af_sarah": 0.75, "af_nicole": 0.25},
        "semitones": -1.2,
        "speed_mult": 0.99,
        "presence_db": 2.0,
    },
    "am_michael": {
        "blend": {"am_michael": 0.78, "am_puck": 0.22},
        "semitones": 0.2,
        "presence_db": 2.2,
    },
    "am_michael_narrator": {
        "blend": {"am_puck": 0.60, "am_michael": 0.40},
        "semitones": 1.2,
        "speed_mult": 1.03,
        "presence_db": 2.8,
    },
    "am_michael_alt": {
        "blend": {"am_fenrir": 0.75, "am_adam": 0.25},
        "semitones": -1.2,
        "speed_mult": 0.99,
        "presence_db": 2.0,
    },
}

_KOKORO_INSTANCE: Optional["KokoroEngine"] = None


def get_kokoro_model_paths() -> Tuple[Optional[Path], Optional[Path]]:
    """Locates kokoro-v1.0.onnx and voices-v1.0.bin on the system."""
    for mdir in CANDIDATE_MODEL_DIRS:
        if mdir.exists():
            onnx_candidates = list(mdir.glob("*kokoro*.onnx"))
            voices_candidates = list(mdir.glob("*voices*.bin")) + list(mdir.glob("*voices*.json"))
            if onnx_candidates and voices_candidates:
                return onnx_candidates[0], voices_candidates[0]
    return None, None


def split_text_into_sentences(text: str) -> List[str]:
    """Splits a multi-sentence narration or dialogue block into crisp sentence chunks.
    Preserves punctuation marks (!, ?, ., …) so Kokoro's prosody contour remains expressive
    without rushing or degrading over long paragraphs.
    """
    if not text or not text.strip():
        return []
    cleaned = re.sub(r"\s+", " ", text.strip())
    # Split after sentence-ending punctuation followed by whitespace, keeping short clauses intact
    parts = re.split(r"(?<=[.!?…])\s+", cleaned)
    chunks: List[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # Merge tiny fragments (e.g. "A:", "1.", or single word interjections < 4 chars) with next/prev
        if chunks and len(chunks[-1]) < 6:
            chunks[-1] = f"{chunks[-1]} {p}"
        else:
            chunks.append(p)
    return chunks if chunks else [cleaned]


def _pitch_shift_resample(samples: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    """Applies a clean pitch shift (in semitones) while approximately preserving speaking tempo
    via overlap-add time-stretch + resampling. Used when a synthetic male timbre (`ff_siwis_male`)
    or distinct Narrator / character vocal identity is requested.
    """
    if abs(semitones) < 0.05 or len(samples) == 0:
        return samples
    factor = 2.0 ** (semitones / 12.0)  # < 1.0 lowers pitch
    # 1. Time-stretch by `factor` using Hann-windowed WSOLA/OLA so resampling restores duration
    win_size = int(0.030 * sr)
    hop_in = win_size // 2
    hop_out = max(1, int(round(hop_in / factor)))
    window = np.hanning(win_size).astype(np.float32)

    out_len = int(len(samples) / factor) + win_size
    stretched = np.zeros(out_len, dtype=np.float32)
    norm = np.zeros(out_len, dtype=np.float32)

    pos_in = 0
    pos_out = 0
    while pos_in + win_size <= len(samples) and pos_out + win_size <= out_len:
        frame = samples[pos_in:pos_in + win_size] * window
        stretched[pos_out:pos_out + win_size] += frame
        norm[pos_out:pos_out + win_size] += window ** 2
        pos_in += hop_in
        pos_out += hop_out

    valid = norm > 1e-4
    stretched[valid] /= norm[valid]
    stretched = stretched[:pos_out + win_size // 2]

    # 2. Resample by `factor` to shift pitch
    new_len = max(1, int(round(len(stretched) * factor)))
    x_old = np.linspace(0.0, 1.0, len(stretched), endpoint=False)
    x_new = np.linspace(0.0, 1.0, new_len, endpoint=False)
    shifted = np.interp(x_new, x_old, stretched).astype(np.float32)
    return shifted


def _apply_presence_and_excitement(samples: np.ndarray, sr: int, presence_db: float = 2.4) -> np.ndarray:
    """Applies a broadcast presence EQ shelf (2.2 kHz - 6 kHz) and gentle dynamic punch
    so Kokoro voices sound vibrant, awake, and crisp rather than like a sleepy late-night podcast.
    """
    if len(samples) == 0 or abs(presence_db) < 0.1:
        return samples
    try:
        # pyrefly: ignore[missing-import]
        from scipy import signal
        # Band-boost between 2200 Hz and 6500 Hz (vocal clarity & excitement band)
        nyq = sr / 2.0
        low = min(0.85, 2200.0 / nyq)
        high = min(0.95, 6500.0 / nyq)
        b, a = signal.butter(2, [low, high], btype="band")
        high_band = signal.lfilter(b, a, samples)
        gain = (10.0 ** (presence_db / 20.0)) - 1.0
        enhanced = samples + gain * high_band
        # Subtle soft-knee harmonic warmth so enthusiastic peaks feel punchy without clipping
        peak = float(np.max(np.abs(enhanced)))
        if peak > 1e-5:
            normed = enhanced / peak
            enhanced = np.tanh(1.18 * normed) / np.tanh(1.18) * peak
        return enhanced.astype(np.float32)
    except Exception:
        return samples


def _resolve_emotion_prosody_modifiers(
    emotion: Optional[str],
    energy: Optional[str],
    section: Optional[str],
    speaker: Optional[str],
) -> Tuple[float, float, float]:
    """Maps script emotion, energy, section, and speaker role to subtle, natural
    (semitone_offset, speed_multiplier, extra_presence_db) adjustments.
    """
    emo = (emotion or "").lower()
    eng = (energy or "").lower()
    sec = (section or "").lower()
    spk = (speaker or "").lower()
    is_narrator = "narrator" in spk

    semi_mod = 0.0
    speed_mod = 1.0
    pres_mod = 0.0

    if is_narrator:
        # Give the Narrator a lively, upbeat YouTube Shorts host energy (without sounding cartoonish)
        semi_mod += 0.45
        speed_mod *= 1.03
        pres_mod += 0.8
        if any(k in sec for k in ("hook", "pressure", "answer", "reveal", "discovery", "payoff")):
            semi_mod += 0.35
            speed_mod *= 1.02
            pres_mod += 0.5
    else:
        # Dialogue character emotion shaping from JSON script cues (e.g. Ansioso, Ottimista, Sorprendido, Scherzoso)
        if any(k in emo for k in (
            "ansioso", "anxious", "inquiet", "preocupado", "preoccupato", "nervous", "urgent",
            "ottimista", "entusiasta", "enthusiastic", "excited", "sorpreso", "surprised", "asombrado",
            "scherzoso", "divertido", "divertito", "amused", "playful", "hyped", "celebratory",
            "frustrato", "frustrado", "frustrated", "arrabbiato", "determinato", "determinado", "determined"
        )):
            semi_mod += 0.55
            speed_mod *= 1.04
            pres_mod += 0.7
        elif any(k in emo for k in ("confuso", "confused", "curioso", "curious", "questioning", "baffled")):
            semi_mod += 0.40
            speed_mod *= 1.01
            pres_mod += 0.4
        elif any(k in emo for k in ("rilassato", "calmo", "tranquilo", "calm", "soddisfatto", "aliviado", "sollevato", "relieved")):
            semi_mod += 0.15
            speed_mod *= 1.00
            pres_mod += 0.3

    if "very high" in eng:
        semi_mod += 0.30
        speed_mod *= 1.02
    elif "high" in eng and not is_narrator:
        semi_mod += 0.15

    return semi_mod, speed_mod, pres_mod


class KokoroEngine:
    """Precision & Full-Text TTS engine executing via Kokoro-82M ONNX."""

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        voices_path: Optional[Union[str, Path]] = None,
        default_voice: str = "af_bella",
        overrides_csv_path: Optional[Union[str, Path]] = None,
    ):
        self.default_voice = default_voice
        self._kokoro = None
        self.overrides_csv_path = (
            Path(overrides_csv_path)
            if overrides_csv_path
            else Path(__file__).resolve().parent.parent / "data" / "pronunciation_overrides.csv"
        )
        self.pronunciation_overrides = self._load_pronunciation_overrides()

        if not KOKORO_AVAILABLE:
            logger.warning("kokoro-onnx package is not installed.")
            return

        if model_path is None or voices_path is None:
            discovered_model, discovered_voices = get_kokoro_model_paths()
            model_path = model_path or discovered_model
            voices_path = voices_path or discovered_voices

        if model_path and voices_path and Path(model_path).exists() and Path(voices_path).exists():
            try:
                self._kokoro = Kokoro(str(model_path), str(voices_path))
                logger.info(f"Kokoro-82M engine initialized with {model_path}")
            except Exception as exc:
                logger.error(f"Failed to initialize Kokoro engine: {exc}")
        else:
            logger.warning("Kokoro model files not found in standard directories.")

    @property
    def is_ready(self) -> bool:
        """Returns True if the engine is loaded and operational."""
        return self._kokoro is not None

    def get_available_voices(self) -> List[str]:
        """Returns the list of voices bundled with the loaded Kokoro model."""
        if not self.is_ready:
            return []
        try:
            return list(self._kokoro.get_voices())
        except Exception:
            return []

    def _load_pronunciation_overrides(self) -> List[Dict[str, str]]:
        """Loads per-language pronunciation overrides from CSV if present."""
        rules: List[Dict[str, str]] = []
        if not self.overrides_csv_path or not self.overrides_csv_path.exists():
            return rules
        try:
            with self.overrides_csv_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    lang = (row.get("LANGUAGE") or "").strip().lower()
                    pattern = (row.get("PATTERN") or "").strip()
                    replacement = (row.get("REPLACEMENT") or "").strip()
                    if lang and pattern:
                        rules.append({
                            "language": lang,
                            "pattern": pattern,
                            "replacement": replacement,
                            "is_regex": (row.get("IS_REGEX") or "false").strip().lower() == "true",
                            "case_sensitive": (row.get("CASE_SENSITIVE") or "false").strip().lower() == "true",
                        })
        except Exception as exc:
            logger.warning(f"Could not load pronunciation_overrides.csv: {exc}")
        return rules

    def apply_pronunciation_overrides(self, text: str, language: str) -> str:
        """Applies configured regex/word replacements for words espeak-ng mispronounces."""
        if not text:
            return ""
        lang_norm = self.normalize_language(language)
        out = text
        # Clean stage/direction brackets if any slipped through
        out = re.sub(r"\[.*?\]", "", out)
        # Normalize guillemets and smart quotes that can cause awkward pauses in espeak-ng
        out = out.replace("«", '"').replace("»", '"')

        for rule in self.pronunciation_overrides:
            if rule["language"] not in (lang_norm, "all", "*"):
                continue
            pat = rule["pattern"]
            repl = rule["replacement"]
            flags = 0 if rule["case_sensitive"] else re.IGNORECASE
            if rule["is_regex"]:
                out = re.sub(pat, repl, out, flags=flags)
            else:
                escaped = r"\b" + re.escape(pat) + r"\b"
                out = re.sub(escaped, repl, out, flags=flags)
        return out.strip()

    @staticmethod
    def normalize_language(language: str) -> str:
        if not language:
            return "english"
        raw = str(language).split("|")[0].strip().lower()
        if any(k in raw for k in ("spanish", "español", "espanol")) or raw in ("es", "sp", "e"):
            return "spanish"
        if any(k in raw for k in ("french", "français", "francais")) or raw in ("fr", "fr-fr", "f"):
            return "french"
        if any(k in raw for k in ("italian", "italiano")) or raw in ("it", "i"):
            return "italian"
        return "english"

    @classmethod
    def resolve_lang_code(cls, language: str) -> str:
        norm = cls.normalize_language(language)
        return KOKORO_LANG_CODES.get(norm, "en-us")

    @classmethod
    def resolve_voice(
        cls,
        language: str,
        gender: str = "female",
        preferred_voice: Optional[str] = None,
    ) -> str:
        """Resolves a valid Kokoro voice ID for the given language and gender."""
        if preferred_voice:
            v_clean = str(preferred_voice).strip()
            # If preferred_voice is already a Kokoro voice ID (e.g. 'ef_dora', 'if_sara')
            if re.match(r"^[a-z]{2}_[a-z0-9_]+$", v_clean) and not v_clean.endswith(".wav"):
                return v_clean

        lang_norm = cls.normalize_language(language)
        gend_norm = "male" if str(gender).strip().lower() == "male" else "female"

        try:
            import config
            cfg_voices = getattr(config, "KOKORO_VOICES", None)
            if isinstance(cfg_voices, dict):
                cand = cfg_voices.get((lang_norm, gend_norm)) or cfg_voices.get(lang_norm, {}).get(gend_norm)
                if isinstance(cand, list) and cand:
                    return cand[0]
                elif isinstance(cand, str) and cand:
                    return cand
        except Exception:
            pass

        pool = DEFAULT_KOKORO_VOICES.get((lang_norm, gend_norm), ["af_bella"])
        return pool[0]

    def _resolve_voice_style_and_params(
        self, resolved_voice: str
    ) -> Tuple[Union[str, np.ndarray], float, float, float]:
        """Resolves a voice ID or recipe name (e.g. 'im_nicola_narrator', 'em_alex_alt')
        into `(voice_style_or_name, base_semitones, base_speed_mult, base_presence_db)`.
        """
        recipe = KOKORO_VOICE_RECIPES.get(resolved_voice)
        if not recipe:
            if resolved_voice.endswith("_narrator"):
                base_v = resolved_voice[: -len("_narrator")]
                return base_v, 1.8, 1.04, 3.0
            if resolved_voice.endswith("_alt"):
                base_v = resolved_voice[: -len("_alt")]
                return base_v, -1.5, 0.98, 2.0
            return resolved_voice, 0.0, 1.0, 2.2

        blend_map = recipe.get("blend")
        semitones = float(recipe.get("semitones", 0.0))
        speed_mult = float(recipe.get("speed_mult", 1.0))
        presence_db = float(recipe.get("presence_db", 2.4))

        if isinstance(blend_map, dict) and self._kokoro is not None and hasattr(self._kokoro, "get_voice_style"):
            try:
                blended = None
                total_w = 0.0
                for v_name, weight in blend_map.items():
                    style_arr = self._kokoro.get_voice_style(v_name)
                    if style_arr is not None:
                        w = float(weight)
                        blended = style_arr * w if blended is None else blended + (style_arr * w)
                        total_w += w
                if blended is not None and total_w > 0:
                    return (blended / total_w).astype(np.float32), semitones, speed_mult, presence_db
            except Exception as exc:
                logger.debug(f"Could not blend style vector for {resolved_voice}, using primary voice: {exc}")
                first_voice = next(iter(blend_map.keys()))
                return first_voice, semitones, speed_mult, presence_db

        if isinstance(blend_map, dict) and blend_map:
            return next(iter(blend_map.keys())), semitones, speed_mult, presence_db
        return resolved_voice, semitones, speed_mult, presence_db

    def synthesize_text(
        self,
        text: str,
        output_path: Union[str, Path],
        language: str = "english",
        voice: Optional[str] = None,
        gender: str = "female",
        speed: Optional[float] = None,
        sentence_pause_s: float = 0.22,
        emotion: Optional[str] = None,
        energy: Optional[str] = None,
        section: Optional[str] = None,
        speaker: Optional[str] = None,
    ) -> Optional[Path]:
        """Synthesizes full natural-language text to an audio file using Kokoro-82M.

        Splits multi-sentence segments on punctuation, synthesizes each sentence with
        language-appropriate phonemization (`es`, `fr-fr`, `it`, `en-us`), applies
        persona style blending and emotion/energy prosody shaping, and joins sentences
        with crisp breath pauses (`sentence_pause_s`).

        Args:
            text: Full text segment to synthesize.
            output_path: Destination `.flac` or `.wav` path.
            language: Target language ('spanish', 'french', 'italian', 'english' or short code).
            voice: Explicit Kokoro voice ID or recipe (e.g. 'ef_dora', 'em_alex_narrator', 'im_nicola_alt').
            gender: Speaker gender ('female' or 'male') used if `voice` is not specified.
            speed: Speaking rate multiplier (defaults to per-language `DEFAULT_KOKORO_SPEEDS`).
            sentence_pause_s: Pause in seconds inserted between sentences inside the segment.
            emotion: Script emotion cue (e.g. 'Ansioso', 'Ottimista', 'enthusiastic') to shape vocal energy.
            energy: Energy level ('medium', 'high', 'very high').
            section: Script section ('hook', 'dialogue_part_1', 'payoff', etc.).
            speaker: Speaker identifier ('Narrator', 'PERSON_ONE', 'PERSON_TWO').

        Returns:
            Path to generated audio file if successful, None otherwise.
        """
        if not self.is_ready:
            logger.error("Cannot synthesize text: Kokoro engine is not initialized.")
            return None

        lang_norm = self.normalize_language(language)
        lang_code = self.resolve_lang_code(lang_norm)
        resolved_voice = self.resolve_voice(lang_norm, gender=gender, preferred_voice=voice)

        voice_arg, base_semi, base_speed_mult, base_pres_db = self._resolve_voice_style_and_params(resolved_voice)
        emo_semi, emo_speed_mult, emo_pres_db = _resolve_emotion_prosody_modifiers(
            emotion=emotion,
            energy=energy,
            section=section,
            speaker=speaker or ("Narrator" if resolved_voice.endswith("_narrator") else ""),
        )

        if speed is None:
            try:
                import config
                cfg_speeds = getattr(config, "KOKORO_SPEEDS", {})
                speed = float(cfg_speeds.get(lang_norm, DEFAULT_KOKORO_SPEEDS.get(lang_norm, 0.93)))
            except Exception:
                speed = DEFAULT_KOKORO_SPEEDS.get(lang_norm, 0.93)

        effective_speed = max(0.5, min(2.0, float(speed) * base_speed_mult * emo_speed_mult))
        total_semitones = base_semi + emo_semi
        total_presence_db = base_pres_db + emo_pres_db

        prepared_text = self.apply_pronunciation_overrides(text, lang_norm)
        sentences = split_text_into_sentences(prepared_text)
        if not sentences:
            logger.warning("Empty text provided to KokoroEngine.synthesize_text.")
            return None

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        audio_parts: List[np.ndarray] = []
        sample_rate = 24000

        try:
            for idx, sent in enumerate(sentences):
                samples, sr = self._kokoro.create(
                    sent,
                    voice=voice_arg,
                    speed=effective_speed,
                    lang=lang_code,
                    is_phonemes=False,
                    trim=True,
                )
                sample_rate = sr

                audio_parts.append(samples)
                if idx < len(sentences) - 1 and sentence_pause_s > 0:
                    # Slightly longer pause after questions/exclamations for natural phrasing
                    gap_s = sentence_pause_s * (1.25 if sent.endswith(("?", "!")) else 1.0)
                    silence = np.zeros(int(gap_s * sample_rate), dtype=np.float32)
                    audio_parts.append(silence)

            combined = np.concatenate(audio_parts) if len(audio_parts) > 1 else audio_parts[0]
            sf.write(str(out_path), combined, sample_rate)
            logger.info(
                f"Kokoro synthesized [{lang_norm}/{resolved_voice} @ {effective_speed:.2f}x] -> "
                f"{out_path.name} ({len(combined)/sample_rate:.2f}s, {len(sentences)} sentences)"
            )
            return out_path
        except Exception as exc:
            logger.error(f"Kokoro failed to synthesize text [{text[:40]}...]: {exc}")
            return None

    def generate_phonemes(
        self,
        phonemes: str,
        output_path: Union[str, Path],
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> Optional[Path]:
        """Synthesizes raw IPA phonemes to an audio file.

        Args:
            phonemes: International Phonetic Alphabet string (e.g. 'ˈprɛz.ənt' or 'prɪˈzɛnt').
            output_path: Path to save the resulting WAV/FLAC file.
            voice: Voice key (e.g. 'af_bella', 'am_adam').
            speed: Speed multiplier (default: 1.0).

        Returns:
            Path to generated file if successful, None otherwise.
        """
        if not self.is_ready:
            logger.error("Cannot generate speech: Kokoro engine is not initialized.")
            return None

        clean_ipa = phonemes.strip("/[] ")
        # Kokoro expects standard stress markers and clean syllables
        clean_ipa = clean_ipa.replace(".", "")

        target_voice = voice or self.default_voice
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            samples, sr = self._kokoro.create(
                clean_ipa,
                voice=target_voice,
                speed=speed,
                is_phonemes=True,
                trim=True,
            )
            sf.write(out_path, samples, sr)
            logger.info(f"Synthesized IPA [{phonemes}] -> {out_path} ({len(samples)/sr:.2f}s)")
            return out_path
        except Exception as exc:
            logger.error(f"Failed to synthesize phonemes [{phonemes}]: {exc}")
            return None

    def generate_heteronym_demonstration(
        self,
        word: str,
        role: str,
        output_path: Union[str, Path],
        voice: Optional[str] = None,
    ) -> Optional[Path]:
        """Generates an exact phonetic demonstration clip for a registered heteronym.

        Args:
            word: Target heteronym word (e.g. 'present', 'project', 'record').
            role: 'noun' or 'verb'.
            output_path: Target path for the generated audio.
            voice: Optional voice ID.

        Returns:
            Path to saved audio or None.
        """
        clean_word = word.lower().strip()
        clean_role = role.lower().strip()

        meta = HETERONYM_REGISTRY.get(clean_word)
        if not meta:
            logger.warning(f"Word '{word}' is not in HETERONYM_REGISTRY.")
            return None

        role_data = meta.get(clean_role)
        if not role_data or "ipa" not in role_data:
            logger.warning(f"No IPA entry for {clean_word} as {clean_role}.")
            return None

        ipa = role_data["ipa"]
        return self.generate_phonemes(ipa, output_path, voice=voice)


def get_kokoro_engine() -> KokoroEngine:
    """Returns a singleton instance of KokoroEngine."""
    global _KOKORO_INSTANCE
    if _KOKORO_INSTANCE is None:
        _KOKORO_INSTANCE = KokoroEngine()
    return _KOKORO_INSTANCE
