"""
test/unit/test_voice_upgrade_modules.py — Unit tests for Phases 2–5 of the Stage B Voice Upgrade:
  - Phase 2: Anti-repetition neutral Spanish casting (75% es_latam_neutral / 25% es_spain_castilian),
             dialect locking, Kokoro twin deduplication, modifier exclusion, VoiceDesign builder dry-run
  - Phase 3: Spanish paired ¿/¡ injection, GAME challenge intra-option micro-pauses,
             interrogative pitch-rise & exclamatory dynamic-energy acoustic gate checks
  - Phase 4: Per-type tactical pause choreography (`0.45s` pre-discovery, `0.24s` cliffhanger, `2.20s` pressure_gap),
             Roleplay same-speaker multi-energy reference switching
  - Phase 5: Pure scipy broadcast vocal mastering (presence boost EQ, LUFS targets, peak ceiling <= 0.891)
"""
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
from video_creation._B_voice_generation.core.acoustic_evaluator import evaluate_voice_take
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.audio_processor import (
    concatenate_audios,
    master_and_normalize_audio,
    measure_lufs,
)
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.comfy_client import ComfyClient
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.voice_manager import VoiceManager
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.tools.build_voice_bank import (
    _passes_gender_pitch_gate,
    build_voice_bank,
    load_persona_catalog,
)
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.voice.common.bank_manifest import sanitize_ref_transcript
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.voice.common.engine import compute_segment_sampling, is_typed_voice_enabled
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.voice.common.punctuation import prepare_tts_prosody_text
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.voice.languages import get_language_voice_profile
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.voice.types import get_video_type_voice_profile
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.voice.types.roleplay.emotion import classify_roleplay_energy_tier


def _write_tone(path: Path, freq_fn, amp_fn=None, sr: int = 24000, duration: float = 1.8) -> None:
    t = np.linspace(0.0, duration, int(sr * duration), endpoint=False)
    f = freq_fn(t, duration)
    phase = 2.0 * np.pi * np.cumsum(f) / sr
    amp = amp_fn(t, duration) if amp_fn else np.full_like(t, 0.25)
    sig = (amp * np.sin(phase)).astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), sig, sr)


class TestVoiceUpgradeModules(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_neutral_spanish_casting_rotation_and_dialect_lock(self):
        """Verifies consecutive Spanish scripts rotate without back-to-back repeats & use only neutral accents."""
        open_swara = self.root / "open_swara"
        bank_dir = open_swara / "voice_design_bank"
        comfy_in = self.root / "comfy_in"

        voices = []
        for idx, accent in enumerate(["es_latam_neutral", "es_latam_neutral", "es_latam_neutral", "es_spain_castilian"], 1):
            for gend in ("male", "female"):
                sid = f"es_{gend[0]}_{idx:02d}"
                rel = f"spanish/{gend}/{sid}_baseline.wav"
                wav_p = bank_dir / rel
                wav_p.parent.mkdir(parents=True, exist_ok=True)
                wav_p.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")
                voices.append({
                    "voice_id": f"{sid}_baseline",
                    "speaker_id": sid,
                    "language": "spanish",
                    "gender": gend,
                    "accent": accent,
                    "energy_tier": "baseline",
                    "archetypes": ["warm_narrator", "energetic_host", "roleplay_actor"],
                    "rel_path": rel,
                    "ref_text": "¡Hola! ¿Cómo estás?",
                    "source": "voice_design",
                    "lang_prob": 0.99,
                    "active": True,
                })
                if idx == 1:
                    for tier in ("high_energy", "surprised_urgent"):
                        vrel = f"spanish/{gend}/{sid}_{tier}.wav"
                        vpath = bank_dir / vrel
                        vpath.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")
                        voices.append({
                            "voice_id": f"{sid}_{tier}",
                            "speaker_id": sid,
                            "language": "spanish",
                            "gender": gend,
                            "accent": accent,
                            "energy_tier": tier,
                            "archetypes": ["roleplay_actor"],
                            "rel_path": vrel,
                            "ref_text": "¡Increíble!",
                            "source": "voice_design",
                            "lang_prob": 0.99,
                            "active": True,
                        })

        (bank_dir / "voice_bank_manifest.json").write_text(
            json.dumps({"version": "1.0", "voices": voices}), encoding="utf-8"
        )

        with patch.dict(os.environ, {"VOICE_ENGINE": "typed", "VOICE_BANK_DIR": str(bank_dir)}):
            vm = VoiceManager(open_swara, comfy_in)
            chosen_seq = []
            for num in range(1, 13):
                vm.assign_voices_for_script(
                    ["Narrator"],
                    "spanish",
                    manual_genders={"Narrator": "male"},
                    video_type="expression",
                    script_id=f"SE{num:02d}",
                )
                _, vpath, _ = vm.get_speaker_voice("Narrator", "spanish")
                chosen_seq.append(vpath.name)

            # No two back-to-back scripts share the same narrator voice
            for a, b in zip(chosen_seq, chosen_seq[1:]):
                self.assertNotEqual(a, b, f"Back-to-back repeat detected in {chosen_seq}")
            # Both neutral LatAm (01/02/03) and Castilian Spain (04) are represented across 12 scripts
            self.assertGreaterEqual(len(set(chosen_seq)), 3)
            self.assertIn("es_m_04_baseline.wav", chosen_seq)

            # Explicit Spain script locks to Castilian speaker
            spain_script = {"id": "SF99", "prompt_params": {"TOPIC": "Uso de vosotros en España (Castellano)"}}
            vm.assign_voices_for_script(["Narrator"], "spanish", manual_genders={"Narrator": "female"}, script_data=spain_script, script_id="SF99")
            _, spain_p, _ = vm.get_speaker_voice("Narrator", "spanish")
            self.assertEqual(spain_p.name, "es_f_04_baseline.wav")

            # Roleplay multi-energy resolution keeps same speaker_id across emotions!
            vm.assign_voices_for_script(["Person One"], "spanish", manual_genders={"Person One": "male"}, video_type="roleplay", script_id="SR01", accent_hint="es_latam_neutral")
            _, base_p, _ = vm.get_speaker_voice("Person One", "spanish")
            if "es_m_01" in base_p.name:
                _, urg_p, _ = vm.resolve_turn_voice("Person One", "spanish", "surprised", "¿Qué acabas de decir?!", "dialogue_part_1", "roleplay")
                self.assertEqual(urg_p.name, "es_m_01_surprised_urgent.wav")

    def test_sanitize_open_swara_typos(self):
        self.assertIn("calidez", sanitize_ref_transcript("La calidad del sol de la mañana trae calma.", "spanish", "spanish_male_open_swara_006.wav"))
        self.assertIn("chiarezza", sanitize_ref_transcript("Il calore del sole mattutino porto un senso di calma e chiaretta.", "italian", "italian_female_open_swara_007.wav"))
        self.assertIn("La chaleur", sanitize_ref_transcript("L'achelleur du soleil matinale apporte le calme.", "french", "french_female_open_swara_007.wav"))
        self.assertEqual(sanitize_ref_transcript("Hola, soy una voz personalizada.", "spanish", "custom.wav"), "Hola, soy una voz personalizada.")

    def test_punctuation_spanish_inverted_and_game_micro_pauses(self):
        shaped, flags = prepare_tts_prosody_text(
            text="Sabes qué significa? Increíble! Ya lo entiendo.",
            language="spanish",
            video_type="expression",
            section="hook",
            enforce_inverted_punctuation=True,
        )
        self.assertEqual(shaped, "¿Sabes qué significa? ¡Increíble! Ya lo entiendo.")
        self.assertTrue(flags["has_question"])
        self.assertTrue(flags["has_exclamation"])

        # Does not double existing inverted punctuation
        shaped2, _ = prepare_tts_prosody_text(
            text="¿En serio? ¡Claro que sí!",
            language="spanish",
            enforce_inverted_punctuation=True,
        )
        self.assertEqual(shaped2, "¿En serio? ¡Claro que sí!")

        # Injects option micro-pauses inside GAME challenge
        game_txt, _ = prepare_tts_prosody_text(
            text="Which idiom means good luck? Option A: Break a leg. Option B: Break a cup. Option C: Break ice.",
            language="english",
            video_type="game",
            section="challenge",
            use_option_micro_pauses=True,
            option_micro_pause_sec=0.26,
        )
        self.assertIn("[pause:0.26] Option B:", game_txt)
        self.assertIn("[pause:0.26] Option C:", game_txt)

    def test_intonation_contour_question_and_exclamation_gate(self):
        with patch.dict(os.environ, {"VOICE_ENGINE": "typed"}):
            flat_q = self.root / "flat_q.flac"
            rise_q = self.root / "rise_q.flac"
            # Flat pitch variance around 180 Hz -> fails rising `?` check
            _write_tone(flat_q, lambda t, d: 180.0 + 30.0 * np.sin(2 * np.pi * 4.0 * t))
            # Clear rising contour (+50 Hz in final 25%) -> passes rising `?` check
            _write_tone(rise_q, lambda t, d: 165.0 + 25.0 * np.sin(2 * np.pi * 3.5 * t) + 55.0 * np.clip((t - 0.7 * d) / (0.3 * d), 0.0, 1.0))

            s_flat, p_flat, issues_flat, _ = evaluate_voice_take(flat_q, "¿Cómo estás hoy, amigo mío?", language="spanish", video_type="expression", section="hook")
            s_rise, p_rise, issues_rise, m_rise = evaluate_voice_take(rise_q, "¿Cómo estás hoy, amigo mío?", language="spanish", video_type="expression", section="hook")
            self.assertFalse(p_flat)
            self.assertTrue(any("question" in i.lower() for i in issues_flat))
            self.assertTrue(p_rise, f"Unexpected issues on rising question: {issues_rise}")
            self.assertGreater(m_rise["final_25pct_f0_ratio"], 1.04)
            self.assertGreater(s_rise, s_flat)

    def test_pause_choreography_differences_and_pressure_gap(self):
        seg1 = self.root / "s1.wav"
        seg2 = self.root / "s2.wav"
        seg3 = self.root / "s3.wav"
        for p in (seg1, seg2, seg3):
            _write_tone(p, lambda t, d: 180.0 + 30.0 * np.sin(2 * np.pi * 4.0 * t), duration=0.6)

        # FUN_FACTS: 0.45s pre_discovery_gap before discovery
        ff_profile = get_video_type_voice_profile("fun_facts")
        ff_out = self.root / "ff" / "script_EF99_master.wav"
        concatenate_audios(
            [
                {"path": seg1, "section": "hook", "speaker": "Narrator"},
                {"path": seg2, "section": "discovery", "speaker": "Narrator"},
            ],
            ff_out,
            pause_choreography=ff_profile.pauses,
            mastering_preset=ff_profile.mastering,
        )
        ff_timings = json.loads((ff_out.parent / "timings.json").read_text(encoding="utf-8"))
        self.assertAlmostEqual(ff_timings["discovery"]["start"] - ff_timings["hook"]["end"], 0.45, delta=0.02)

        # GAME: 2.20s pressure_gap preserved before answer
        gm_profile = get_video_type_voice_profile("game")
        gm_out = self.root / "gm" / "script_EG99_master.wav"
        concatenate_audios(
            [
                {"path": seg1, "section": "pressure", "speaker": "Narrator"},
                {"path": seg2, "section": "answer", "speaker": "Narrator"},
            ],
            gm_out,
            pause_choreography=gm_profile.pauses,
            mastering_preset=gm_profile.mastering,
        )
        gm_timings = json.loads((gm_out.parent / "timings.json").read_text(encoding="utf-8"))
        self.assertAlmostEqual(gm_timings["answer"]["start"] - gm_timings["pressure"]["end"], 2.20, delta=0.02)

        # ROLEPLAY: dynamic 0.24s cliffhanger turn gap after ?/!
        rp_profile = get_video_type_voice_profile("roleplay")
        rp_out = self.root / "rp" / "script_ER99_master.wav"
        concatenate_audios(
            [
                {"path": seg1, "section": "dialogue_part_1", "speaker": "Person One", "is_cliffhanger": True},
                {"path": seg2, "section": "dialogue_part_2", "speaker": "Person Two", "is_cliffhanger": False},
            ],
            rp_out,
            pause_choreography=rp_profile.pauses,
            mastering_preset=rp_profile.mastering,
        )
        rp_timings = json.loads((rp_out.parent / "timings.json").read_text(encoding="utf-8"))
        self.assertAlmostEqual(rp_timings["dialogue_part_2"]["start"] - rp_timings["dialogue_part_1"]["end"], 0.24, delta=0.02)

    def test_roleplay_emotion_tier_classifier(self):
        self.assertEqual(classify_roleplay_energy_tier("Surpris", "Comment ça?!", "dialogue_part_2"), "surprised_urgent")
        self.assertEqual(classify_roleplay_energy_tier("enthousiaste", "C'est génial !", "dialogue_part_4"), "high_energy")
        self.assertEqual(classify_roleplay_energy_tier("calm", "Sure, let's look at the menu.", "dialogue_part_1"), "baseline")

    def test_broadcast_mastering_eq_lufs_and_peak_ceiling(self):
        """Verifies per-type scipy DSP chain boosts 3.5kHz presence over 250Hz mud & nails LUFS/peak targets."""
        sr = 24000
        rng = np.random.default_rng(7)
        noise = rng.normal(0.0, 0.04, size=sr * 3).astype(np.float32)

        exp_preset = get_video_type_voice_profile("expression").mastering
        mastered, orig_lufs, final_lufs = master_and_normalize_audio(noise, sr, mastering_preset=exp_preset)
        self.assertFalse(np.isnan(mastered).any())
        self.assertFalse(np.isinf(mastered).any())
        self.assertLessEqual(float(np.max(np.abs(mastered))), 0.892)
        self.assertAlmostEqual(final_lufs, -15.2, delta=0.9)
        self.assertGreater(final_lufs, orig_lufs)

        # Verify spectral lift at 3.5 kHz compared to 250 Hz mud band
        fft_in = np.abs(np.fft.rfft(noise))
        fft_out = np.abs(np.fft.rfft(mastered))
        freqs = np.fft.rfftfreq(len(noise), 1.0 / sr)
        mud_mask = (freqs >= 210) & (freqs <= 310)
        pres_mask = (freqs >= 3000) & (freqs <= 4000)
        in_ratio = float(np.mean(fft_in[pres_mask]) / np.mean(fft_in[mud_mask]))
        out_ratio = float(np.mean(fft_out[pres_mask]) / np.mean(fft_out[mud_mask]))
        self.assertGreater(out_ratio, in_ratio * 1.4, "Expected clear +3.5 dB presence boost vs 260 Hz mud cut")

    def test_voice_design_persona_catalog_and_builder_dry_run(self):
        """Validates `voice_bank_personas.json` neutrality rules and `build_voice_bank.py --dry-run`."""
        cat = load_persona_catalog()
        personas = cat["personas"]
        self.assertGreaterEqual(len(personas), 24)
        spanish_accents = {p["accent"] for p in personas if p["language"] == "spanish"}
        self.assertEqual(spanish_accents, {"es_latam_neutral", "es_spain_castilian"})

        summary = build_voice_bank(bank_dir=self.root / "dry_bank", dry_run=True)
        self.assertTrue(summary["dry_run"])
        self.assertEqual(summary["planned_baseline_clips"], len(personas))
        self.assertGreater(summary["planned_variant_clips"], 0)

        filtered = build_voice_bank(
            bank_dir=self.root / "dry_bank",
            speaker_ids=["es_f_latam_host_01", "fr_m_host_01"],
            dry_run=True,
        )
        self.assertEqual(filtered["planned_baseline_clips"], 2)

    def test_english_manifest_icl_enabled_and_subtalker_capped(self):
        """Verifies English VoiceBankManifest entries enable ICL while loose English stays x-vector; subtalker_temperature <= 0.86."""
        bank_dir = self.root / "bank_icl"
        wav_path = bank_dir / "english" / "female" / "english_female_en_f_uk_narrator_03_baseline.wav"
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        wav_path.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")
        expected_ref = "Have you ever wondered why British speakers say it this way?!"
        (bank_dir / "voice_bank_manifest.json").write_text(
            json.dumps({
                "version": "1.0",
                "voices": [{
                    "voice_id": "en_f_uk_narrator_03_baseline",
                    "speaker_id": "en_f_uk_narrator_03",
                    "language": "english",
                    "gender": "female",
                    "accent": "en_uk_neutral",
                    "energy_tier": "baseline",
                    "archetypes": ["warm_narrator"],
                    "rel_path": "english/female/english_female_en_f_uk_narrator_03_baseline.wav",
                    "ref_text": expected_ref,
                    "source": "voice_design",
                    "lang_prob": 0.996,
                    "active": True,
                }],
            }),
            encoding="utf-8",
        )
        wf_path = self.root / "wf.json"
        wf_path.write_text('{"6":{"inputs":{}},"8":{"inputs":{}},"35":{"inputs":{"x_vector_only":true}},"39":{"inputs":{}}}', encoding="utf-8")

        with patch.dict(os.environ, {"VOICE_BANK_DIR": str(bank_dir), "QWEN3_USE_ICL": "true"}):
            client = ComfyClient("http://127.0.0.1:8188", wf_path)
            wf_manifest = client._prepare_workflow(
                ref_audio_name="english_female_en_f_uk_narrator_03_baseline.wav",
                target_text="Here is the wild truth!",
                language="English",
                gender="female",
                context="Narrator",
                emotion="curious",
                energy="high",
                style="lively",
                output_prefix="audio/test",
            )
            self.assertFalse(wf_manifest["35"]["inputs"]["x_vector_only"])
            self.assertEqual(wf_manifest["35"]["inputs"]["ref_text"], expected_ref)

            wf_loose = client._prepare_workflow(
                ref_audio_name="english_female_open_swara_035.wav",
                target_text="Here is the wild truth!",
                language="English",
                gender="female",
                context="Narrator",
                emotion="curious",
                energy="high",
                style="lively",
                output_prefix="audio/test_loose",
            )
            self.assertTrue(wf_loose["35"]["inputs"]["x_vector_only"])

        for lang in ("english", "french", "spanish", "italian"):
            lp = get_language_voice_profile(lang)
            for vtype in ("expression", "game", "roleplay", "fun_facts"):
                tp = get_video_type_voice_profile(vtype)
                for sec in ("hook", "discovery", "answer", "pressure"):
                    samp = compute_segment_sampling(
                        lang_profile=lp,
                        type_profile=tp,
                        section=sec,
                        is_dialogue_speaker=False,
                        prosody_flags={"has_question": True, "has_exclamation": True},
                    )
                    self.assertLessEqual(samp["subtalker_temperature"], 0.86)

    def test_gender_pitch_gate_rejects_flips_and_childlike(self):
        self.assertFalse(_passes_gender_pitch_gate("male", 244.3)[0])
        self.assertTrue(_passes_gender_pitch_gate("male", 155.0)[0])
        self.assertFalse(_passes_gender_pitch_gate("male", 170.0, mf_energy_ratio=0.04)[0])
        self.assertFalse(_passes_gender_pitch_gate("female", 170.0)[0])
        self.assertFalse(_passes_gender_pitch_gate("female", 325.0)[0])
        self.assertFalse(_passes_gender_pitch_gate("female", 215.0, p25_f0=170.0, mf_energy_ratio=0.08)[0])
        self.assertFalse(_passes_gender_pitch_gate("female", 220.0, p25_f0=205.0, mf_energy_ratio=0.25)[0])
        self.assertTrue(_passes_gender_pitch_gate("female", 240.0, p25_f0=210.0, mf_energy_ratio=0.02)[0])

    def test_casting_history_persists_across_runs(self):
        """Verifies VOICE_CASTING_HISTORY_PATH persistence rotates consecutive runs away from the last speaker."""
        open_swara = self.root / "open_swara"
        bank_dir = open_swara / "voice_design_bank"
        comfy_in = self.root / "comfy_in"
        history_path = self.root / "voice_quality" / "casting_history.json"

        voices = []
        for idx in (1, 2):
            sid = f"es_f_{idx:02d}"
            rel = f"spanish/female/{sid}_baseline.wav"
            wav_p = bank_dir / rel
            wav_p.parent.mkdir(parents=True, exist_ok=True)
            wav_p.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")
            voices.append({
                "voice_id": f"{sid}_baseline",
                "speaker_id": sid,
                "language": "spanish",
                "gender": "female",
                "accent": "es_latam_neutral",
                "energy_tier": "baseline",
                "archetypes": ["warm_narrator", "energetic_host"],
                "rel_path": rel,
                "ref_text": "¡Hola! ¿Cómo estás?",
                "source": "voice_design",
                "lang_prob": 0.99,
                "active": True,
            })

        (bank_dir / "voice_bank_manifest.json").write_text(
            json.dumps({"version": "1.0", "voices": voices}), encoding="utf-8"
        )

        with patch.dict(os.environ, {"VOICE_ENGINE": "typed", "VOICE_BANK_DIR": str(bank_dir)}):
            vm1 = VoiceManager(open_swara, comfy_in, casting_history_path=history_path)
            vm1.assign_voices_for_script(
                ["Narrator"],
                "spanish",
                manual_genders={"Narrator": "female"},
                video_type="expression",
                script_id="SE01",
            )
            _, first_p, _ = vm1.get_speaker_voice("Narrator", "spanish")
            self.assertTrue(history_path.exists())
            saved = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertIn("spanish:female", saved)

            # Brand-new VoiceManager on the same script_id must rotate away from the persisted choice
            vm2 = VoiceManager(open_swara, comfy_in, casting_history_path=history_path)
            vm2.assign_voices_for_script(
                ["Narrator"],
                "spanish",
                manual_genders={"Narrator": "female"},
                video_type="expression",
                script_id="SE01",
            )
            _, second_p, _ = vm2.get_speaker_voice("Narrator", "spanish")
            self.assertNotEqual(first_p.name, second_p.name)


if __name__ == "__main__":
    unittest.main()
