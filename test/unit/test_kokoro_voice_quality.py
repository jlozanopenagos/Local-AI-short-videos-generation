"""Unit tests for Kokoro-82M full-text engine, VoiceManager engine routing,
reference voice filtering, and ComfyClient ICL / localized instruct generation.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
import soundfile as sf

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAIN_DIR = PROJECT_ROOT / "main"
for p in [str(MAIN_DIR), str(MAIN_DIR / "core"), str(MAIN_DIR / "video_creation")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.kokoro_engine import (
    KokoroEngine,
    split_text_into_sentences,
    _pitch_shift_resample,
)
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.voice_manager import VoiceManager
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.comfy_client import ComfyClient


class TestKokoroEngineAndVoiceQuality(unittest.TestCase):
    """Tests for KokoroEngine full-text synthesis, sentence chunking, and voice routing."""

    def test_split_text_into_sentences(self):
        text = (
            "¿Sabías que nadie dice esto? Hoy vamos a aprender una expresión genial. "
            "¡Inténtalo otra vez!"
        )
        chunks = split_text_into_sentences(text)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], "¿Sabías que nadie dice esto?")
        self.assertEqual(chunks[1], "Hoy vamos a aprender una expresión genial.")
        self.assertEqual(chunks[2], "¡Inténtalo otra vez!")

    def test_resolve_voice_per_language_and_gender(self):
        self.assertEqual(KokoroEngine.resolve_voice("spanish", "female"), "ef_dora")
        self.assertEqual(KokoroEngine.resolve_voice("spanish", "male"), "em_alex")
        self.assertEqual(KokoroEngine.resolve_voice("french", "female"), "ff_siwis")
        self.assertEqual(KokoroEngine.resolve_voice("italian", "female"), "if_sara")
        self.assertEqual(KokoroEngine.resolve_voice("italian", "male"), "im_nicola")

    def test_pronunciation_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "overrides.csv"
            csv_path.write_text(
                "LANGUAGE,PATTERN,REPLACEMENT,IS_REGEX,CASE_SENSITIVE,NOTES\n"
                "spanish,YouTube,Yu Tub,false,false,test\n",
                encoding="utf-8",
            )
            eng = KokoroEngine(overrides_csv_path=csv_path)
            out = eng.apply_pronunciation_overrides("Sube esto a YouTube «ahora» [risas]", "spanish")
            self.assertIn("Yu Tub", out)
            self.assertNotIn("[risas]", out)
            self.assertNotIn("«", out)

    def test_synthesize_text_with_mock_kokoro(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_wav = Path(tmpdir) / "out.wav"
            eng = KokoroEngine()
            mock_k = MagicMock()
            sr = 24000
            t = np.linspace(0, 0.4, int(sr * 0.4), endpoint=False, dtype=np.float32)
            fake_samples = 0.25 * np.sin(2 * np.pi * 200 * t).astype(np.float32)
            mock_k.create.return_value = (fake_samples, sr)
            mock_k.get_voice_style.return_value = None
            eng._kokoro = mock_k

            res = eng.synthesize_text(
                text="Hola amigos. ¡Bienvenidos al canal!",
                output_path=out_wav,
                language="spanish",
                gender="female",
                speed=1.05,
                sentence_pause_s=0.10,
                emotion="enthusiastic",
                energy="high",
                section="hook",
                speaker="Narrator",
            )
            self.assertEqual(res, out_wav)
            self.assertTrue(out_wav.exists())
            self.assertEqual(mock_k.create.call_count, 2)
            call_kwargs = mock_k.create.call_args_list[0].kwargs
            self.assertEqual(call_kwargs["voice"], "ef_dora")
            self.assertEqual(call_kwargs["lang"], "es")
            self.assertFalse(call_kwargs["is_phonemes"])

            data, read_sr = sf.read(str(out_wav))
            self.assertEqual(read_sr, 24000)
            self.assertGreater(len(data), len(fake_samples) * 2)

    def test_pitch_shift_resample(self):
        sr = 24000
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False, dtype=np.float32)
        sig = 0.3 * np.sin(2 * np.pi * 220 * t).astype(np.float32)
        shifted = _pitch_shift_resample(sig, sr, semitones=-3.0)
        self.assertGreater(len(shifted), int(sr * 0.4))
        self.assertLess(len(shifted), int(sr * 0.6))

    def test_voice_manager_engine_routing_and_hybrid_french(self):
        # Default auto mode now routes all languages through Qwen3-TTS with Kokoro Golden References
        eng_es_auto, v_es_auto = VoiceManager.resolve_engine_for_speaker(
            "spanish", gender="male", speaker="Narrator", is_dialogue=False, cli_engine_override="auto", kokoro_available=True
        )
        self.assertEqual((eng_es_auto, v_es_auto), ("qwen3", None))

        # Explicit kokoro override routes Spanish narrator to em_alex_narrator
        eng_es, v_es = VoiceManager.resolve_engine_for_speaker(
            "spanish", gender="male", speaker="Narrator", is_dialogue=False, cli_engine_override="kokoro", kokoro_available=True
        )
        self.assertEqual((eng_es, v_es), ("kokoro", "em_alex_narrator"))

        # Explicit kokoro override routes Spanish dialogue character to em_alex
        eng_es_d, v_es_d = VoiceManager.resolve_engine_for_speaker(
            "spanish", gender="male", speaker="PERSON_ONE", is_dialogue=True, cli_engine_override="kokoro", kokoro_available=True
        )
        self.assertEqual((eng_es_d, v_es_d), ("kokoro", "em_alex"))

        # French narrator in hybrid mode uses native ff_siwis_narrator
        eng_fr_nar, v_fr_nar = VoiceManager.resolve_engine_for_speaker(
            "french", gender="female", speaker="Narrator", is_dialogue=False, cli_engine_override="hybrid", kokoro_available=True
        )
        self.assertEqual((eng_fr_nar, v_fr_nar), ("kokoro", "ff_siwis_narrator"))

        # French male dialogue character in hybrid mode falls back to Qwen3
        eng_fr_m, v_fr_m = VoiceManager.resolve_engine_for_speaker(
            "french", gender="male", speaker="Person 1", is_dialogue=True, cli_engine_override="hybrid", kokoro_available=True
        )
        self.assertEqual((eng_fr_m, v_fr_m), ("qwen3", None))

        # When kokoro_available=False, gracefully falls back to qwen3
        eng_fb, v_fb = VoiceManager.resolve_engine_for_speaker(
            "italian", gender="female", speaker="Narrator", is_dialogue=False, cli_engine_override="kokoro", kokoro_available=False
        )
        self.assertEqual((eng_fb, v_fb), ("qwen3", None))

    def test_voice_manager_excludes_english_tagged_italian_refs(self):
        self.assertFalse(
            VoiceManager._is_acceptable_ref(Path("italian_male_english_open_swara_001.wav"), "italian")
        )
        self.assertTrue(
            VoiceManager._is_acceptable_ref(Path("italian_male_open_swara_001.wav"), "italian")
        )
        self.assertFalse(
            VoiceManager._is_acceptable_ref(Path("french_male_open_swara_001.wav"), "french")
        )

    def test_comfy_client_icl_and_localized_instruct(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wf_path = Path(tmpdir) / "wf.json"
            wf_path.write_text(
                '{"6":{"inputs":{}},"8":{"inputs":{}},"35":{"inputs":{"x_vector_only":true,"ref_text":["40",0]}},"39":{"inputs":{}}}',
                encoding="utf-8",
            )
            client = ComfyClient("http://127.0.0.1:8188", wf_path)
            wf = client._prepare_workflow(
                ref_audio_name="spanish_female_open_swara_009.wav",
                target_text="Hola a todos.",
                language="spanish",
                gender="female",
                context="Narrator",
                emotion="warm",
                energy="high",
                style="lively",
                output_prefix="audio/test",
                seed=42,
                use_icl=True,
                ref_text="Hola, soy una voz de referencia.",
                localize_instruct=True,
            )
            self.assertFalse(wf["35"]["inputs"]["x_vector_only"])
            self.assertEqual(wf["35"]["inputs"]["ref_text"], "Hola, soy una voz de referencia.")
            self.assertIn("Un narrador nativo de español", wf["39"]["inputs"]["instruct"])


if __name__ == "__main__":
    unittest.main()

