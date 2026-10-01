"""Kokoro-82M Precision Hybrid Engine.

Provides lightweight, deterministic IPA phoneme-to-speech synthesis using
the Kokoro-82M ONNX runtime. Serves as the precision phonetic demonstration
engine for technical linguistics, heteronyms, and dictionary-style pronunciation guides.

Features:
- Sub-100ms on-demand CPU/GPU inference.
- Exact phonetic control via IPA phoneme strings (is_phonemes=True).
- Seamless fallback integration with the Closed-Set Pronunciation Bank.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import soundfile as sf

try:
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

_KOKORO_INSTANCE: Optional["Kokoro"] = None


def get_kokoro_model_paths() -> Tuple[Optional[Path], Optional[Path]]:
    """Locates kokoro-v1.0.onnx and voices-v1.0.bin on the system."""
    for mdir in CANDIDATE_MODEL_DIRS:
        if mdir.exists():
            onnx_candidates = list(mdir.glob("*kokoro*.onnx"))
            voices_candidates = list(mdir.glob("*voices*.bin")) + list(mdir.glob("*voices*.json"))
            if onnx_candidates and voices_candidates:
                return onnx_candidates[0], voices_candidates[0]
    return None, None


class KokoroEngine:
    """Precision TTS engine executing explicit IPA phonemes via Kokoro-82M ONNX."""

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        voices_path: Optional[Union[str, Path]] = None,
        default_voice: str = "af_bella",
    ):
        self.default_voice = default_voice
        self._kokoro = None

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
            return self._kokoro.get_voices()
        except Exception:
            return []

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
