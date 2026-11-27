"""
test/unit/test_elevenlabs_voice.py — Unit tests for the isolated ElevenLabs voice package.
Zero live API calls or credits consumed.
"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
import soundfile as sf

MAIN_DIR = Path(__file__).resolve().parent.parent.parent / "main"
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))

# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.audio_processor import trim_audio_silence
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.elevenlabs.catalog import (
    ElevenLabsVoiceCatalog,
    pick_elevenlabs_accent,
)
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.elevenlabs.client import ElevenLabsClient
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.elevenlabs.orchestrator import synthesize_script_voice_elevenlabs
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.elevenlabs.tags import (
    estimate_script_credits,
    map_emotion_to_v3_tag,
    prepare_elevenlabs_text,
    resolve_voice_provider,
)


def _make_wav_bytes(duration_sec: float = 0.6, sr: int = 24000) -> bytes:
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    sig = (0.2 * np.sin(2 * np.pi * 220.0 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, sig, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


class TestElevenLabsVoicePackage(unittest.TestCase):
    def test_hybrid_provider_routing_and_overrides(self):
        self.assertEqual(resolve_voice_provider("roleplay", "auto"), "elevenlabs")
        self.assertEqual(resolve_voice_provider("expression", "auto"), "elevenlabs")
        self.assertEqual(resolve_voice_provider("fun_facts", "auto"), "elevenlabs")
        self.assertEqual(resolve_voice_provider("game", "auto"), "local")

        # Explicit overrides
        self.assertEqual(resolve_voice_provider("game", "elevenlabs"), "elevenlabs")
        self.assertEqual(resolve_voice_provider("roleplay", "local"), "local")

    def test_v3_audio_tags_vs_multilingual_v2_and_flash(self):
        self.assertEqual(map_emotion_to_v3_tag("Anxious"), "[nervous]")
        self.assertEqual(map_emotion_to_v3_tag("Shocked"), "[gasps]")
        self.assertEqual(map_emotion_to_v3_tag("Chuckling"), "[chuckles]")
        self.assertEqual(map_emotion_to_v3_tag("Teasing"), "[playfully]")

        v3_txt = prepare_elevenlabs_text(
            "Wait! [pause:0.3] Did you really spill wine?!",
            emotion="Shocked",
            section="dialogue_part_2",
            model_id="eleven_v3",
            is_narrator=False,
        )
        self.assertTrue(v3_txt.startswith("[gasps] "))
        self.assertNotIn("[pause:", v3_txt)

        v2_txt = prepare_elevenlabs_text(
            "Wait! [pause:0.3] Did you really spill wine?!",
            emotion="Shocked",
            section="dialogue_part_2",
            model_id="eleven_multilingual_v2",
            is_narrator=False,
        )
        self.assertFalse(v2_txt.startswith("["))
        self.assertNotIn("[pause:", v2_txt)

    def test_credit_estimation_respects_model_multiplier(self):
        script_data = {
            "id": "SR08",
            "content_metadata": {
                "language": "spanish",
                "video_type": "roleplay",
                "script": {
                    "title": "Embarazada",
                    "hook": "Una copa rota en plena cena familiar.",
                    "dialogue_part_1": "PERSON_ONE (Anxious): Acabo de volcar el vino.\nPERSON_TWO (Chuckling): Tranquila, limpia el estropicio.",
                },
            },
        }
        v3_est = estimate_script_credits(script_data, model_id="eleven_v3")
        flash_est = estimate_script_credits(script_data, model_id="eleven_flash_v2_5")
        self.assertGreater(v3_est, 80)
        self.assertLess(flash_est, v3_est)
        self.assertAlmostEqual(flash_est / max(1, v3_est), 0.45, delta=0.12)

    def test_spanish_accent_rotation_is_exact_60_latam_40_castilian(self):
        accents = [pick_elevenlabs_accent("spanish", script_id=f"SR{i:02d}") for i in range(1, 11)]
        latam = accents.count("es_latam_neutral")
        spain = accents.count("es_spain_castilian")
        self.assertEqual(latam, 6)
        self.assertEqual(spain, 4)

    def test_catalog_enforces_three_distinct_speakers_in_roleplay(self):
        with tempfile.TemporaryDirectory() as tmp:
            hist = Path(tmp) / "el_hist.json"
            cat = ElevenLabsVoiceCatalog(history_path=hist)
            assigned, genders, accent = cat.cast_script_voices(
                ["Narrator", "PERSON_ONE", "PERSON_TWO"],
                "spanish",
                video_type="roleplay",
                script_id="SR08",
            )
            self.assertEqual(len({e.voice_id for e in assigned.values()}), 3)
            self.assertIn(accent, ("es_latam_neutral", "es_spain_castilian"))
            self.assertTrue(hist.exists())

    @patch("video_creation._B_voice_generation.elevenlabs.client.requests.post")
    def test_client_synthesize_segment_writes_wav_and_counts_header_credits(self, mock_post):
        wav_bytes = _make_wav_bytes()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = wav_bytes
        mock_resp.headers = {"character-cost": "42"}
        mock_post.return_value = mock_resp

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "seg.wav"
            client = ElevenLabsClient(api_key="sk_test_secret_123")
            saved, credits = client.synthesize_segment(
                voice_id="EXAVITQu4vr4xnSDxMaL",
                text="[excited] Hello world!",
                dest_path=dest,
                model_id="eleven_v3",
                language_code="en",
            )
            self.assertTrue(saved.exists())
            self.assertEqual(credits, 42)
            # Confirm API key passed in header and model_id in JSON body
            call_kwargs = mock_post.call_args.kwargs
            self.assertEqual(call_kwargs["headers"]["xi-api-key"], "sk_test_secret_123")
            self.assertEqual(call_kwargs["json"]["model_id"], "eleven_v3")

    def test_orchestrator_end_to_end_saves_metadata_without_touching_local_speakers_voice(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            mock_sm = MagicMock()
            mock_client = MagicMock()
            wav_bytes = _make_wav_bytes()

            def _fake_synth(**kwargs):
                p = Path(kwargs["dest_path"])
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(wav_bytes)
                return p, 50

            mock_client.synthesize_segment.side_effect = _fake_synth

            script_data = {
                "id": "SR08",
                "metadata": {"LABEL": "Spanish | Roleplay"},
                "script_text": '{"hook": "Una copa rota.", "dialogue_part_1": "PERSON_ONE (Anxious): Ay no.\\nPERSON_TWO (Chuckling): Tranquila."}',
                "content_metadata": {
                    "language": "spanish",
                    "video_type": "roleplay",
                    "speakers_voice": {"Narrator": "local_qwen_voice.wav"},
                },
                "status": {},
                "assets": {},
            }

            cat = ElevenLabsVoiceCatalog(history_path=tmp_root / "el_hist.json")
            ok = synthesize_script_voice_elevenlabs(
                script_data=script_data,
                state_manager=mock_sm,
                elevenlabs_client=mock_client,
                catalog=cat,
                model_id="eleven_v3",
                base_dir=tmp_root,
            )
            self.assertTrue(ok)
            self.assertEqual(script_data["status"]["voice_generation"], "done")
            self.assertTrue(Path(script_data["assets"]["audio_path"]).exists())
            # Local speakers_voice remains untouched; ElevenLabs IDs stored separately
            self.assertEqual(script_data["content_metadata"]["speakers_voice"]["Narrator"], "local_qwen_voice.wav")
            self.assertEqual(len(script_data["content_metadata"]["speakers_elevenlabs_voice"]), 3)
            meta = script_data["content_metadata"]["voice_profile_meta"]
            self.assertEqual(meta["provider"], "elevenlabs")
            self.assertEqual(meta["elevenlabs_model"], "eleven_v3")
            self.assertGreater(meta["credits_used"], 0)

            # Roleplay segments have different speakers (Narrator -> PERSON_ONE -> PERSON_TWO):
            # previous_text / next_text MUST NOT bleed across speaker changes, and native speed is 0.94.
            calls = mock_client.synthesize_segment.call_args_list
            self.assertEqual(len(calls), 3)
            for call in calls:
                self.assertIsNone(call.kwargs["previous_text"])
                self.assertIsNone(call.kwargs["next_text"])
                self.assertAlmostEqual(call.kwargs["voice_settings"]["speed"], 0.94, places=2)

    def test_orchestrator_same_speaker_expression_preserves_context_and_uses_narrator_speed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            mock_sm = MagicMock()
            mock_client = MagicMock()
            wav_bytes = _make_wav_bytes()

            def _fake_synth(**kwargs):
                p = Path(kwargs["dest_path"])
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(wav_bytes)
                return p, 40

            mock_client.synthesize_segment.side_effect = _fake_synth

            script_data = {
                "id": "EE01",
                "metadata": {"LABEL": "English | Expression"},
                "script_text": '{"hook": "Break a leg!", "explanation": "It means good luck before a show.", "payoff": "Use it tonight."}',
                "content_metadata": {
                    "language": "english",
                    "video_type": "expression",
                },
                "status": {},
                "assets": {},
            }

            cat = ElevenLabsVoiceCatalog(history_path=tmp_root / "el_hist.json")
            ok = synthesize_script_voice_elevenlabs(
                script_data=script_data,
                state_manager=mock_sm,
                elevenlabs_client=mock_client,
                catalog=cat,
                model_id="eleven_flash_v2_5",
                base_dir=tmp_root,
            )
            self.assertTrue(ok)
            calls = mock_client.synthesize_segment.call_args_list
            self.assertEqual(len(calls), 3)
            # Segment 1 (Narrator) -> next_text populated, previous_text None
            self.assertIsNone(calls[0].kwargs["previous_text"])
            self.assertIsNotNone(calls[0].kwargs["next_text"])
            # Segment 2 (Narrator) -> both previous_text and next_text populated
            self.assertIsNotNone(calls[1].kwargs["previous_text"])
            self.assertIsNotNone(calls[1].kwargs["next_text"])
            # Segment 3 (Narrator) -> previous_text populated, next_text None
            self.assertIsNotNone(calls[2].kwargs["previous_text"])
            self.assertIsNone(calls[2].kwargs["next_text"])
            for call in calls:
                self.assertAlmostEqual(call.kwargs["voice_settings"]["speed"], 0.92, places=2)

    def test_trim_audio_silence_applies_smooth_edge_fades_mono_and_stereo(self):
        sr = 24000
        # 0.5s constant non-zero signal (0.5 amplitude) so edge fades are clearly observable
        mono = np.full(int(sr * 0.5), 0.5, dtype=np.float32)
        trimmed_mono = trim_audio_silence(mono, sr, threshold=0.01, pad_leading=0.01, pad_trailing=0.01)
        self.assertEqual(len(trimmed_mono), len(mono))
        self.assertAlmostEqual(float(trimmed_mono[0]), 0.0, places=5)
        self.assertAlmostEqual(float(trimmed_mono[-1]), 0.0, places=5)
        # Interior remains untouched
        self.assertAlmostEqual(float(trimmed_mono[len(trimmed_mono) // 2]), 0.5, places=5)

        stereo = np.full((int(sr * 0.5), 2), 0.5, dtype=np.float32)
        trimmed_stereo = trim_audio_silence(stereo, sr, threshold=0.01, pad_leading=0.01, pad_trailing=0.01)
        self.assertEqual(trimmed_stereo.shape, stereo.shape)
        self.assertTrue(np.allclose(trimmed_stereo[0], 0.0, atol=1e-5))
        self.assertTrue(np.allclose(trimmed_stereo[-1], 0.0, atol=1e-5))
        self.assertTrue(np.allclose(trimmed_stereo[len(trimmed_stereo) // 2], 0.5, atol=1e-5))

        # Very short array should not raise
        tiny = np.array([0.5, 0.5], dtype=np.float32)
        trimmed_tiny = trim_audio_silence(tiny, sr)
        self.assertEqual(len(trimmed_tiny), 2)

    def test_catalog_full_cycle_lru_rotation_uses_every_voice_before_repeating(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat_file = Path(tmp) / "custom_cat.json"
            hist_file = Path(tmp) / "hist.json"
            voices = [
                {
                    "voice_id": f"fr_f_{i:02d}",
                    "name": f"French Female {i}",
                    "language": "french",
                    "gender": "female",
                    "accent": "fr_standard",
                    "archetypes": ["warm_narrator", "roleplay_actor"],
                }
                for i in range(1, 13)
            ]
            cat_file.write_text('{"voices": ' + __import__("json").dumps(voices) + "}", encoding="utf-8")
            cat = ElevenLabsVoiceCatalog(catalog_path=cat_file, history_path=hist_file)
            picked = []
            for idx in range(1, 13):
                assigned, _, _ = cat.cast_script_voices(
                    ["Narrator"],
                    "french",
                    video_type="expression",
                    script_id=f"FE{idx:02d}",
                    manual_genders={"Narrator": "female"},
                )
                picked.append(assigned["Narrator"].voice_id)
            # All 12 voices used once before ANY repeat
            self.assertEqual(len(set(picked)), 12)
            # 13th script rotates to the least-recently-used (1st) voice
            assigned_13, _, _ = cat.cast_script_voices(
                ["Narrator"],
                "french",
                video_type="expression",
                script_id="FE13",
                manual_genders={"Narrator": "female"},
            )
            self.assertEqual(assigned_13["Narrator"].voice_id, picked[0])


if __name__ == "__main__":
    unittest.main()
