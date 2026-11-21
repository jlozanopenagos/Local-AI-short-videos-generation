"""
test/unit/test_voice_characterization.py — Phase 0/1 Offline 16-Golden-ID Stage B Characterization Suite.

Exercises end-to-end Stage B orchestration (`synthesize_script_voice`) across all 16 Golden IDs
(`EF01, EE01, EG01, ER01, FF04, FE01, FG01, FR01, IF01, IE01, IG01, IR01, SF01, SE01, SG01, SR01`)
under both `VOICE_ENGINE=legacy` and `VOICE_ENGINE=typed`, locking all MUST-KEEP invariants:
  1. English heteronyms + intentional learner error phonetic rewrites (`ri-cord`, `PUR-mit`)
  2. GAME `2.20s` `pressure_gap` & normalized `Option A/B/C` (no stress giveaways)
  3. ROLEPLAY 3-speaker voice uniqueness (`Narrator` vs `Person One` vs `Person Two`)
  4. Target-language accent purity (`english` never leaks to `french`/`spanish`/`italian`)
  5. Stage G `timings.json` section boundaries & `master.wav` schema integrity
  6. Selective rollback switch (`VOICE_ENGINE=legacy:game`)
"""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import soundfile as sf

# pyrefly: ignore[missing-import]
import config
# pyrefly: ignore[missing-import]
from core.state_manager import StateManager
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.audio_processor import measure_lufs
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.voice_manager import VoiceManager
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.voice.common.orchestrator import synthesize_script_voice


GOLDEN_IDS = [
    "EF01", "EE01", "EG01", "ER01",
    "FF04", "FE01", "FG01", "FR01",
    "IF01", "IE01", "IG01", "IR01",
    "SF01", "SE01", "SG01", "SR01",
]


def _make_expressive_wav(path: Path, sr: int = 24000, duration: float = 1.6, rising_end: bool = True) -> None:
    """Writes valid speech-like modulated audio (passes AcousticGate & rising-F0 checks cleanly)."""
    n = int(sr * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    base_f0 = 175.0 + 38.0 * np.sin(2.0 * np.pi * 3.5 * t)
    if rising_end:
        # Smooth upward pitch contour in the last 30% so `?` rising gate passes
        tail_ramp = np.clip((t - 0.65 * duration) / (0.35 * duration), 0.0, 1.0)
        base_f0 = base_f0 + 35.0 * tail_ramp
    phase = 2.0 * np.pi * np.cumsum(base_f0) / sr
    # Modulated amplitude envelope with crisp exclamation peak
    amp = 0.25 * (1.0 + 0.35 * np.sin(2.0 * np.pi * 2.2 * t))
    sig = (amp * np.sin(phase) + 0.08 * amp * np.sin(2.0 * phase)).astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), sig, sr)


class RecordingFakeComfyClient:
    """Fake ComfyClient that records every call and writes valid modulated `.flac`/`.wav` takes."""

    def __init__(self, ref_transcripts: dict = None):
        self.calls = []
        self.ref_transcripts = ref_transcripts or {}

    def generate_voice_segment(
        self,
        ref_audio_name: str,
        target_text: str,
        language: str,
        gender: str,
        context: str,
        emotion: str,
        energy: str,
        style: str,
        output_prefix: str,
        dest_path: Path,
        seed: int = None,
        sampling_overrides: dict = None,
        accent_hint: str = None,
        **kwargs,
    ) -> Path:
        self.calls.append({
            "ref_audio_name": ref_audio_name,
            "target_text": target_text,
            "language": language,
            "gender": gender,
            "context": context,
            "emotion": emotion,
            "energy": energy,
            "style": style,
            "output_prefix": output_prefix,
            "dest_path": str(dest_path),
            "seed": seed,
            "sampling_overrides": sampling_overrides,
            "accent_hint": accent_hint,
        })
        # Duration roughly proportional to text length to produce healthy ~13.5 CPS
        clean_len = max(12, len(target_text.replace(" ", "")))
        dur = max(0.8, min(4.5, clean_len / 13.5))
        _make_expressive_wav(Path(dest_path), duration=dur, rising_end=True)
        return Path(dest_path)


def _build_synthetic_open_swara(root: Path) -> None:
    """Populates a tiny isolated `open_swara` directory with Kokoro + multiple human voices per language."""
    # Include both kokoro_golden AND multiple clean open_swara clips per lang/gender
    for lang in ("english", "french", "spanish", "italian"):
        for gend in ("male", "female"):
            d = root / lang / gend
            d.mkdir(parents=True, exist_ok=True)
            for tag in ("narrator", "baritone", "tenor", "bass", "alto", "mezzo", "char1", "char2"):
                (d / f"{lang}_{gend}_kokoro_golden_{tag}.wav").write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")
            for num in ("003", "005", "007", "009"):
                (d / f"{lang}_{gend}_open_swara_{num}.wav").write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")


class TestVoiceCharacterization(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_root = Path(self._tmp.name)
        self.base_dir = self.tmp_root / "main"
        (self.base_dir / "state").mkdir(parents=True, exist_ok=True)
        self.open_swara_dir = self.tmp_root / "open_swara"
        _build_synthetic_open_swara(self.open_swara_dir)
        self.comfy_input_dir = self.tmp_root / "comfy_input"
        self.comfy_input_dir.mkdir(parents=True, exist_ok=True)

        self.fixture_dir = Path(__file__).resolve().parents[1] / "fixtures" / "image_prompts" / "states"
        self.test_sm = StateManager(self.base_dir)

    def tearDown(self):
        self._tmp.cleanup()

    def _prepare_golden_state(self, script_id: str) -> dict:
        raw = json.loads((self.fixture_dir / f"script_{script_id}.json").read_text(encoding="utf-8"))
        lang = config.resolve_script_language(raw)
        vtype = config.resolve_script_video_type(raw)
        # Clear legacy speakers_voice so fresh casting runs cleanly inside test sandbox
        raw.setdefault("content_metadata", {})["speakers_voice"] = {}
        raw.setdefault("assets", {})["audio_path"] = ""
        raw.setdefault("status", {})["voice_generation"] = "pending"
        self.test_sm.save_script_state(script_id, raw)
        out_dir = self.base_dir / "output" / "video_assets" / lang / vtype / f"script_{script_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        return raw

    def test_all_16_golden_ids_legacy_and_typed_invariants(self):
        """Runs all 16 Golden IDs offline in both `legacy` and `typed` mode and verifies core invariants."""
        for engine_mode in ("legacy", "typed"):
            with self.subTest(engine_mode=engine_mode), patch.dict(os.environ, {"VOICE_ENGINE": engine_mode}):
                vm = VoiceManager(self.open_swara_dir, self.comfy_input_dir)
                for sid in GOLDEN_IDS:
                    script_data = self._prepare_golden_state(sid)
                    lang = config.resolve_script_language(script_data)
                    vtype = config.resolve_script_video_type(script_data)
                    fake_comfy = RecordingFakeComfyClient()

                    ok = synthesize_script_voice(
                        script_data=script_data,
                        state_manager=self.test_sm,
                        comfy_client=fake_comfy,
                        voice_manager=vm,
                        force=True,
                        base_dir=self.base_dir,
                        candidates=1,
                    )
                    self.assertTrue(ok, f"[{engine_mode}] synthesize_script_voice failed on {sid}")
                    self.assertGreater(len(fake_comfy.calls), 0, f"[{engine_mode}] Zero TTS calls for {sid}")

                    updated = self.test_sm.get_script_state(sid)
                    master_wav = Path(updated["assets"]["audio_path"])
                    self.assertTrue(master_wav.exists(), f"Master WAV missing for {sid}")
                    self.assertEqual(updated["status"]["voice_generation"], "done")

                    # Invariant: Target language accent purity (no english ref on non-english scripts)
                    speakers_voice = updated["content_metadata"]["speakers_voice"]
                    self.assertGreater(len(speakers_voice), 0)
                    for spk, vname in speakers_voice.items():
                        if lang != "english":
                            self.assertFalse(
                                vname.lower().startswith("english_"),
                                f"[{engine_mode}] {sid} assigned English voice '{vname}' to {lang} speaker '{spk}'",
                            )

                    # Invariant: timings.json contract
                    timings_path = master_wav.parent / "timings.json"
                    self.assertTrue(timings_path.exists(), f"timings.json missing for {sid}")
                    timings = json.loads(timings_path.read_text(encoding="utf-8"))
                    self.assertGreater(len(timings), 0)
                    for sec_key, span in timings.items():
                        self.assertIn("start", span)
                        self.assertIn("end", span)
                        self.assertGreater(span["end"], span["start"], f"{sid} invalid span for {sec_key}")

                    # Invariant: GAME 2.20s pressure_gap + Option normalization
                    if vtype == "game":
                        self.assertIn("pressure", timings)
                        self.assertIn("answer", timings)
                        gap = timings["answer"]["start"] - timings["pressure"]["end"]
                        self.assertGreaterEqual(gap, 2.15, f"[{engine_mode}] {sid} pressure_gap shrunk to {gap:.3f}s")
                        challenge_texts = [c["target_text"] for c in fake_comfy.calls]
                        has_opt = any(
                            token in txt
                            for txt in challenge_texts
                            for token in ("Option A:", "Opción A:", "Opzione A:")
                        )
                        self.assertTrue(has_opt, f"[{engine_mode}] {sid} missing normalized Quiz Options")

                    # Invariant: ROLEPLAY 3-speaker uniqueness
                    if vtype == "roleplay" and len(speakers_voice) >= 2:
                        assigned_names = [v.lower() for v in speakers_voice.values()]
                        self.assertEqual(
                            len(assigned_names),
                            len(set(assigned_names)),
                            f"[{engine_mode}] {sid} duplicate voice across roleplay speakers: {speakers_voice}",
                        )

                    # Invariant: Typed mode Spanish ¿ / ¡ + louder Narrator mastering vs Roleplay
                    data, sr = sf.read(str(master_wav))
                    lufs = measure_lufs(data, sr)
                    peak = float(np.max(np.abs(data)))
                    self.assertLessEqual(peak, 0.892, f"{sid} exceeded peak ceiling")
                    if engine_mode == "typed":
                        if lang == "spanish":
                            for call in fake_comfy.calls:
                                t = call["target_text"]
                                if "?" in t:
                                    self.assertIn("¿", t, f"[{sid}] missing opening ¿ in '{t}'")
                        if vtype == "game":
                            self.assertAlmostEqual(lufs, -15.0, delta=1.5)
                        elif vtype in ("fun_facts", "expression"):
                            self.assertAlmostEqual(lufs, -15.2, delta=1.5)
                        elif vtype == "roleplay":
                            self.assertAlmostEqual(lufs, -16.0, delta=1.5)

    def test_heteronym_and_intentional_learner_error_preserved_in_typed_mode(self):
        """Ensures heteronym syntactic carriers and intentional learner error rewrites stay intact in `typed` mode."""
        script_id = "EE99"
        heteronym_state = {
            "id": script_id,
            "metadata": {"LABEL": "English | Pronunciation | Word stress & heteronyms"},
            "prompt_params": {"SUBJECT": "Word stress", "VIDEO_TYPE": "EXPRESSION"},
            "content_metadata": {
                "video_type": "EXPRESSION",
                "language": "english",
                "speakers_gender": {"Narrator": "male"},
                "speakers_voice": {},
            },
            "script_text": json.dumps({
                "hook": "Stop! Did you just say a reCORD?!",
                "discovery": "Use the noun REcord for the album, and the verb reCORD to tape it!",
                "payoff": "Use the noun PERmit correctly! Try it now?",
            }),
            "assets": {},
            "status": {"script_generation": "done", "voice_generation": "pending"},
        }
        self.test_sm.save_script_state(script_id, heteronym_state)
        (self.base_dir / "output" / "video_assets" / "english" / "expression" / f"script_{script_id}").mkdir(parents=True, exist_ok=True)

        fake_comfy = RecordingFakeComfyClient()
        vm = VoiceManager(self.open_swara_dir, self.comfy_input_dir)
        with patch.dict(os.environ, {"VOICE_ENGINE": "typed"}), patch(
            "video_creation._B_voice_generation.core.acoustic_evaluator.evaluate_acoustic_prominence",
            return_value=(2.4, {"transcript": "record", "occurrences": []}),
        ):
            ok = synthesize_script_voice(
                script_data=heteronym_state,
                state_manager=self.test_sm,
                comfy_client=fake_comfy,
                voice_manager=vm,
                force=True,
                base_dir=self.base_dir,
            )
        self.assertTrue(ok)
        all_texts = " || ".join(c["target_text"] for c in fake_comfy.calls)
        all_contexts = " || ".join(c["context"] for c in fake_comfy.calls)
        self.assertIn("ri-cord", all_texts)
        self.assertIn("noun a record", all_texts)
        self.assertIn("verb to record", all_texts)
        self.assertIn("Intentional", "Intentional" if "mistake" in all_contexts else "MISSING")

    def test_selective_legacy_rollback_switch(self):
        """Verifies `VOICE_ENGINE=legacy:game` rolls back GAME while keeping EXPRESSION typed."""
        vm = VoiceManager(self.open_swara_dir, self.comfy_input_dir)
        with patch.dict(os.environ, {"VOICE_ENGINE": "legacy:game"}):
            # SG01 -> legacy (no Option micro-pause, -16 LUFS); SE01 -> typed (-15.2 LUFS, ¿?)
            sg01 = self._prepare_golden_state("SG01")
            fake_g = RecordingFakeComfyClient()
            self.assertTrue(synthesize_script_voice(sg01, self.test_sm, fake_g, vm, force=True, base_dir=self.base_dir, candidates=1))
            self.assertFalse(any("[pause:0.26]" in c["target_text"] for c in fake_g.calls))

            se01 = self._prepare_golden_state("SE01")
            fake_e = RecordingFakeComfyClient()
            self.assertTrue(synthesize_script_voice(se01, self.test_sm, fake_e, vm, force=True, base_dir=self.base_dir, candidates=1))
            self.assertIsNotNone(fake_e.calls[0]["sampling_overrides"])


if __name__ == "__main__":
    unittest.main()
