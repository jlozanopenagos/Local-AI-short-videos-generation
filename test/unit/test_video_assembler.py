"""
test/unit/test_video_assembler.py — Unit and real-FFmpeg smoke tests for typed Stage G Video Assembly.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

# pyrefly: ignore [missing-import]
import ffmpeg
# pyrefly: ignore [missing-import]
from PIL import Image

# pyrefly: ignore [missing-import]
from video_creation._G_video_assembly.assembly.common.audio_mix import build_bgm_volume_expr
# pyrefly: ignore [missing-import]
from video_creation._G_video_assembly.assembly.common.easing import MotionSpec, build_zoompan_expressions
# pyrefly: ignore [missing-import]
from video_creation._G_video_assembly.assembly.common.transitions import (
    TransitionSpec,
    compute_clip_render_durations,
)
# pyrefly: ignore [missing-import]
from video_creation._G_video_assembly.assembly.languages import get_assembly_language_profile
# pyrefly: ignore [missing-import]
from video_creation._G_video_assembly.assembly.types import (
    AssemblyProfileRegistry,
    get_assembly_profile,
)
# pyrefly: ignore [missing-import]
from video_creation._G_video_assembly.core.subtitle_builder import SubtitleBuilder
# pyrefly: ignore [missing-import]
from video_creation._G_video_assembly.core.video_assembler import VideoAssembler

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FFMPEG_BIN = (REPO_ROOT / "main" / "video_creation" / "_G_video_assembly" / "ffmpeg.exe").resolve()
FFPROBE_BIN = (REPO_ROOT / "main" / "video_creation" / "_G_video_assembly" / "ffprobe.exe").resolve()
FFMPEG_AVAILABLE = FFMPEG_BIN.is_file() or shutil.which("ffmpeg")
FFPROBE_AVAILABLE = FFPROBE_BIN.is_file() or shutil.which("ffprobe")


def _write_silent_wav(path: Path, duration_sec: float, sample_rate: int = 22050) -> None:
    num_frames = int(round(duration_sec * sample_rate))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)


def _write_solid_png(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (576, 1024)) -> None:
    Image.new("RGB", size, color).save(path)


class TestAssemblyRegistry(unittest.TestCase):
    def test_resolves_type_names_codes_and_script_ids(self):
        self.assertEqual(get_assembly_profile("expression").video_type, "expression")
        self.assertEqual(get_assembly_profile("E").video_type, "expression")
        self.assertEqual(get_assembly_profile("EE01").video_type, "expression")
        self.assertEqual(get_assembly_profile("game").video_type, "game")
        self.assertEqual(get_assembly_profile("SG02").video_type, "game")
        self.assertEqual(get_assembly_profile("roleplay").video_type, "roleplay")
        self.assertEqual(get_assembly_profile("FR01").video_type, "roleplay")
        self.assertEqual(get_assembly_profile("fun_facts").video_type, "fun_facts")
        self.assertEqual(get_assembly_profile("IF01").video_type, "fun_facts")
        self.assertEqual(AssemblyProfileRegistry.list_supported_types(), ["expression", "fun_facts", "game", "roleplay"])

    def test_language_profiles_default_neutral_across_types(self):
        for lang_in, code in [("English", "english"), ("FR01", "french"), ("español", "spanish"), ("italian", "italian")]:
            lp = get_assembly_language_profile(lang_in)
            self.assertEqual(lp.code, code)
            self.assertIsNone(lp.font_override)
            self.assertEqual(lp.margin_v_offset, 0)
            self.assertEqual(lp.bgm_volume_scale, 1.0)

    def test_legacy_rollback_switch(self):
        with mock.patch.dict(os.environ, {"VIDEO_ASSEMBLY_ENGINE": "legacy"}):
            self.assertIsNone(get_assembly_profile("game"))
            self.assertIsNone(get_assembly_profile("EE01"))
        with mock.patch.dict(os.environ, {"VIDEO_ASSEMBLY_ENGINE": "legacy:game"}):
            self.assertIsNone(get_assembly_profile("game"))
            self.assertIsNone(get_assembly_profile("SG01"))
            self.assertIsNotNone(get_assembly_profile("roleplay"))


class TestMotionTransitionsAndAudio(unittest.TestCase):
    def test_distinct_per_beat_motion_across_all_4_types(self):
        # Chalkboard stays near-static <= 1.02x for readability
        game_prof = get_assembly_profile("game")
        cb_spec = game_prof.get_motion_spec("challenge", is_chalkboard=True)
        self.assertLessEqual(cb_spec.z_end, 1.02)
        self.assertEqual(cb_spec.curve, "linear")
        # Game pressure accelerates with ease_in
        pr_spec = game_prof.get_motion_spec("pressure")
        self.assertEqual(pr_spec.curve, "ease_in")
        self.assertGreater(pr_spec.z_end, pr_spec.z_start)
        # Fun Facts hook is vertical crane tilt-up (y: 0.78 -> 0.22)
        ff_prof = get_assembly_profile("fun_facts")
        ff_hook = ff_prof.get_motion_spec("hook")
        self.assertGreater(ff_hook.y_start, 0.7)
        self.assertLess(ff_hook.y_end, 0.3)
        # Roleplay dialogue_part_1 vs dialogue_part_2 pan in opposite horizontal directions
        rp_prof = get_assembly_profile("roleplay")
        rp_p1 = rp_prof.get_motion_spec("dialogue_part_1")
        rp_p2 = rp_prof.get_motion_spec("dialogue_part_2")
        self.assertLess(rp_p1.x_end, rp_p1.x_start)
        self.assertGreater(rp_p2.x_end, rp_p2.x_start)

    def test_zoompan_expressions_are_safe_even_on_single_frame(self):
        for spec in (
            MotionSpec(1.0, 1.12, 0.5, 0.5, 0.44, 0.40, "cosine"),
            MotionSpec(1.12, 1.0, 0.25, 0.75, 0.78, 0.22, "ease_out"),
            MotionSpec(1.02, 1.15, 0.5, 0.5, 0.46, 0.42, "ease_in"),
            MotionSpec(1.00, 1.015, 0.5, 0.5, 0.5, 0.5, "linear"),
        ):
            z_e, x_e, y_e = build_zoompan_expressions(spec, frames=1)
            self.assertNotIn("+-", z_e)
            self.assertNotIn("/0", z_e)
            self.assertIn("on/1", z_e)
            self.assertTrue(x_e and y_e)
        with self.assertRaises(ValueError):
            build_zoompan_expressions(MotionSpec(curve="unknown"), frames=25)

    def test_xfade_duration_budget_preserves_cumulative_sync(self):
        # Frame-aligned inputs (multiples of 0.04s at 25fps) preserve exact boundaries
        scene_durs = [2.0, 3.0, 2.4, 4.0]
        transitions = [TransitionSpec("fade", 0.24), TransitionSpec("smoothleft", 0.24), TransitionSpec("dissolve", 0.24)]
        render_durs, eff_xfades, offsets = compute_clip_render_durations(scene_durs, transitions, fps=25)
        self.assertEqual(len(render_durs), 4)
        self.assertEqual(len(eff_xfades), 3)
        self.assertEqual(offsets, [2.0, 5.0, 7.4])
        total_out = round(sum(render_durs) - sum(eff_xfades), 4)
        self.assertAlmostEqual(total_out, sum(scene_durs), places=2)

        # Fractional half-frame inputs snap onto exact 25fps frame ticks without xfade shortfall
        frac_durs, frac_xf, frac_off = compute_clip_render_durations([2.0, 3.0, 2.5, 4.0], transitions, fps=25)
        for off in frac_off:
            self.assertAlmostEqual(off * 25, round(off * 25), places=4)
        self.assertAlmostEqual(round(sum(frac_durs) - sum(frac_xf), 4), 11.5, delta=0.04)

        # Very short sections safely disable xfade on that boundary without throwing
        short_durs, short_xf, _ = compute_clip_render_durations([0.20, 3.0], [TransitionSpec("fade", 0.25)], fps=25)
        self.assertEqual(short_xf, [0.0])
        self.assertEqual(round(sum(short_durs) - sum(short_xf), 2), round(sum([0.20, 3.0]), 2))

    def test_bgm_volume_envelope_differs_between_game_and_roleplay(self):
        timings = {
            "hook": {"start": 0.0, "end": 2.0},
            "challenge": {"start": 2.0, "end": 6.0},
            "pressure": {"start": 6.0, "end": 9.0},
            "answer": {"start": 9.0, "end": 12.0},
            "explanation": {"start": 12.0, "end": 16.0},
        }
        game_expr = build_bgm_volume_expr(
            get_assembly_profile("game").get_audio_mix_spec(),
            timings=timings,
            opening_offset=2.0,
            main_duration=16.0,
            closure_duration=3.0,
        )
        self.assertTrue(game_expr.startswith("0.05000"))
        self.assertIn("+0.02500*between(t,8.000,11.000)", game_expr)
        self.assertIn("-0.02500*between(t,11.000,11.600)", game_expr)
        self.assertIn("+0.03000*between(t,18.000,21.000)", game_expr)

        rp_expr = build_bgm_volume_expr(
            get_assembly_profile("roleplay").get_audio_mix_spec(),
            timings={},
            opening_offset=0.0,
            main_duration=10.0,
            closure_duration=3.0,
        )
        self.assertTrue(rp_expr.startswith("0.04000"))
        self.assertIn("+0.04000*between(t,10.000,13.000)", rp_expr)


class TestRealFfmpegTypedAssemblySmoke(unittest.TestCase):
    def test_end_to_end_assemble_all_four_video_types(self):
        if not (FFMPEG_AVAILABLE and FFPROBE_AVAILABLE):
            self.fail("Install FFmpeg and FFprobe to run production assembly tests.")
        """Renders synthetic short videos for EXPRESSION, GAME, ROLEPLAY, and FUN_FACTS via real FFmpeg."""
        type_configs = [
            ("EE99", "expression", "english", ["hook", "setup", "payoff"]),
            ("EG99", "game", "english", ["hook", "challenge", "answer"]),
            ("FR99", "roleplay", "french", ["hook", "dialogue_part_1", "payoff"]),
            ("IF99", "fun_facts", "italian", ["hook", "discovery", "payoff"]),
        ]
        assembler = VideoAssembler()
        sub_builder = SubtitleBuilder()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            open_png = tmp_dir / "open.png"
            close_png = tmp_dir / "close.png"
            wm_png = tmp_dir / "watermark.png"
            bgm_wav = tmp_dir / "bgm.wav"
            _write_solid_png(open_png, (20, 40, 80))
            _write_solid_png(close_png, (80, 30, 20))
            _write_solid_png(wm_png, (255, 255, 255), size=(120, 120))
            _write_silent_wav(bgm_wav, duration_sec=6.0)

            for sid, vtype, lang, sections in type_configs:
                with self.subTest(video_type=vtype):
                    sdir = tmp_dir / sid
                    img_dir = sdir / "images"
                    img_dir.mkdir(parents=True, exist_ok=True)
                    timings = {}
                    script_obj = {}
                    t_cur = 0.0
                    for idx, sec in enumerate(sections):
                        dur = 1.2
                        timings[sec] = {"start": round(t_cur, 2), "end": round(t_cur + dur, 2)}
                        t_cur += dur
                        _write_solid_png(img_dir / f"script_{sid}_{sec}.png", (40 + idx * 50, 120, 180))
                        if sec == "dialogue_part_1":
                            script_obj[sec] = "PERSON_ONE: Hello friend\nPERSON_TWO: Hi there"
                        else:
                            script_obj[sec] = f"Sample {sec} line 21"

                    timings_path = sdir / "timings.json"
                    timings_path.write_text(json.dumps(timings), encoding="utf-8")
                    audio_path = sdir / f"script_{sid}_master.wav"
                    _write_silent_wav(audio_path, duration_sec=t_cur)
                    ass_path = sdir / f"script_{sid}_subtitles.ass"
                    script_data = {
                        "id": sid,
                        "content_metadata": {
                            "video_type": vtype.upper(),
                            "language": lang.title(),
                            "script": script_obj,
                        },
                    }
                    suppress = [(timings["challenge"]["start"], timings["challenge"]["end"])] if "challenge" in timings else []
                    sub_builder.build_ass(
                        [],
                        ass_path,
                        suppress_windows=suppress,
                        script_data=script_data,
                        timings_data=timings,
                        video_type=vtype,
                        language=lang,
                    )

                    out_mp4 = sdir / f"script_{sid}_final.mp4"
                    ok = assembler.assemble(
                        script_id=sid,
                        timings_path=timings_path,
                        image_dir=img_dir,
                        audio_path=audio_path,
                        ass_path=ass_path,
                        output_path=out_mp4,
                        bgm_path=bgm_wav,
                        watermark_path=wm_png,
                        opening_path=open_png,
                        closure_path=close_png,
                        video_type=vtype,
                        script_data=script_data,
                        language=lang,
                    )
                    self.assertTrue(ok, f"FFmpeg assembly failed for {vtype}")
                    self.assertTrue(out_mp4.exists())
                    self.assertGreater(out_mp4.stat().st_size, 5000)

                    probe = ffmpeg.probe(out_mp4.as_posix(), cmd=FFPROBE_BIN.as_posix() if FFPROBE_BIN.is_file() else "ffprobe")
                    v_streams = [s for s in probe["streams"] if s["codec_type"] == "video"]
                    a_streams = [s for s in probe["streams"] if s["codec_type"] == "audio"]
                    self.assertEqual(len(v_streams), 1)
                    self.assertEqual(len(a_streams), 1)
                    self.assertEqual(int(v_streams[0]["width"]), 576)
                    self.assertEqual(int(v_streams[0]["height"]), 1024)
                    expected_dur = 2.0 + t_cur + 3.0
                    actual_dur = float(probe["format"]["duration"])
                    self.assertAlmostEqual(actual_dur, expected_dur, delta=0.35)


class TestAssemblyReplacement(unittest.TestCase):
    def test_replacement_publishes_only_after_successful_render(self):
        # pyrefly: ignore[missing-import]
        from video_creation._G_video_assembly import service as assembly

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            (out_dir / "images").mkdir()
            audio = out_dir / "audio.wav"
            audio.touch()
            (out_dir / "timings.json").write_text("{}", encoding="utf-8")
            subtitles = out_dir / "subtitles.ass"
            subtitles.touch()
            final_video = out_dir / "script_EE99_final.mp4"
            final_video.write_bytes(b"previous render")

            script_data = {
                "id": "EE99",
                "assets": {
                    "audio_path": str(audio),
                    "image_dir": str(out_dir / "images"),
                    "final_video": str(final_video),
                },
                "status": {
                    "voice_generation": "done",
                    "image_generation": "done",
                    "video_assembly": "done",
                },
            }
            state_manager = mock.Mock()
            assembler = mock.Mock()

            def render(*args, **kwargs):
                output = args[5]
                self.assertNotEqual(output, final_video)
                self.assertEqual(final_video.read_bytes(), b"previous render")
                output.write_bytes(b"replacement render")
                return assembler.assemble.call_count == 2

            assembler.assemble.side_effect = render
            with mock.patch.object(assembly, "get_script_output_dir", return_value=out_dir), \
                 mock.patch.object(assembly, "resolve_bank_music", return_value=None), \
                 mock.patch.object(assembly, "resolve_opening_closure_paths", return_value=(None, None)):
                def assemble():
                    return assembly.process_script(
                        script_data, state_manager, assembler=assembler,
                        ass_path=subtitles, regenerate_subtitles=False, dialect="default",
                    )

                self.assertFalse(assemble())
                self.assertEqual(final_video.read_bytes(), b"previous render")
                state_manager.save_script_state.assert_not_called()
                self.assertTrue(assemble())

            self.assertEqual(final_video.read_bytes(), b"replacement render")
            self.assertFalse(list(out_dir.glob(".assembly-*")))
            state_manager.save_script_state.assert_called_once_with("EE99", script_data)


class TestVisualPacingIntegration(unittest.TestCase):
    """Verifies anchor-aware equal-time image pacing and untouched GAME chalkboard behavior."""

    @staticmethod
    def _prepare_mock_script(
        tmp_dir: Path,
        script_id: str,
        video_type: str,
        lang: str,
        section_durs: list[tuple[str, float]],
        image_names: list[str],
    ):
        sdir = tmp_dir / script_id
        img_dir = sdir / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        for idx, name in enumerate(image_names):
            _write_solid_png(img_dir / name, (30 + (idx * 35) % 200, 110, 175))

        timings = {}
        script_obj = {}
        t_cur = 0.0
        for sec, dur in section_durs:
            timings[sec] = {"start": round(t_cur, 4), "end": round(t_cur + dur, 4)}
            t_cur += dur
            script_obj[sec] = f"Sample narration for {sec}."

        timings_path = sdir / "timings.json"
        timings_path.write_text(json.dumps(timings), encoding="utf-8")
        audio_path = sdir / f"script_{script_id}_master.wav"
        _write_silent_wav(audio_path, duration_sec=0.5)

        script_data = {
            "id": script_id,
            "content_metadata": {
                "video_type": video_type.upper(),
                "language": lang.title(),
                "script": script_obj,
            },
        }
        ass_path = sdir / f"script_{script_id}_subtitles.ass"
        SubtitleBuilder().build_ass(
            [],
            ass_path,
            script_data=script_data,
            timings_data=timings,
            video_type=video_type,
            language=lang,
        )
        out_mp4 = sdir / f"script_{script_id}_final.mp4"
        return timings_path, img_dir, audio_path, ass_path, out_mp4, script_data, round(t_cur, 4)

    def _run_assembler_capturing_timeline(
        self,
        *,
        script_id: str,
        video_type: str,
        lang: str,
        section_durs: list[tuple[str, float]],
        image_names: list[str],
    ):
        # pyrefly: ignore[missing-import]
        import video_creation._G_video_assembly.core.video_assembler as va_mod

        assembler = VideoAssembler()
        profile = get_assembly_profile(video_type)
        captured = {"motion_specs": []}
        orig_equalize = va_mod.compute_equalized_visual_durations
        orig_compute = va_mod.compute_clip_render_durations
        orig_get_motion = profile.get_motion_spec

        def _spy_equalize(sections, durations, locked_sections=frozenset()):
            out = orig_equalize(sections, durations, locked_sections=locked_sections)
            captured["sections"] = list(sections)
            captured["durations"] = list(out)
            captured["locked_sections"] = locked_sections
            return out

        def _spy_compute(scene_durations, transitions, fps=25):
            res = orig_compute(scene_durations, transitions, fps=fps)
            captured["transitions"] = list(transitions)
            captured["render_durations"], captured["effective_xfades"], captured["offsets"] = res
            return res

        def _spy_motion(section, punch_in=False, is_chalkboard=False):
            spec = orig_get_motion(section, punch_in=punch_in, is_chalkboard=is_chalkboard)
            captured["motion_specs"].append((section.strip().lower(), spec))
            return spec

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            timings_path, img_dir, audio_path, ass_path, out_mp4, script_data, total_dur = (
                self._prepare_mock_script(tmp_dir, script_id, video_type, lang, section_durs, image_names)
            )
            fake_out = mock.MagicMock()
            fake_out.overwrite_output.return_value.run.return_value = (b"", b"")
            with (
                mock.patch.object(va_mod, "get_assembly_profile", return_value=profile),
                mock.patch.object(profile, "get_motion_spec", side_effect=_spy_motion),
                mock.patch.object(va_mod, "_probe_audio_duration", return_value=total_dur),
                mock.patch.object(va_mod, "compute_equalized_visual_durations", side_effect=_spy_equalize),
                mock.patch.object(va_mod, "compute_clip_render_durations", side_effect=_spy_compute),
                mock.patch.object(va_mod.ffmpeg, "output", return_value=fake_out),
            ):
                ok = assembler.assemble(
                    script_id=script_id,
                    timings_path=timings_path,
                    image_dir=img_dir,
                    audio_path=audio_path,
                    ass_path=ass_path,
                    output_path=out_mp4,
                    video_type=video_type,
                    script_data=script_data,
                    language=lang,
                )
        return ok, total_dur, captured

    def test_equal_visual_pacing_for_fun_facts_expression_and_roleplay(self):
        # pyrefly: ignore[missing-import]
        from video_creation._G_video_assembly.assembly.common.pacing import (
            compute_equalized_visual_durations,
        )

        # Direct unit checks on EF02 (4 imgs) and SE01 (5 imgs)
        ef02_secs = [{"section": s} for s in ("hook", "setup", "discovery", "payoff")]
        ef02_durs = [5.4, 0.99, 46.76, 6.47]
        ef02_eq = compute_equalized_visual_durations(ef02_secs, ef02_durs)
        self.assertEqual(len(ef02_eq), 4)
        self.assertAlmostEqual(sum(ef02_eq), sum(ef02_durs), places=4)
        self.assertLessEqual(max(ef02_eq) - min(ef02_eq), 0.01)

        se01_secs = [{"section": s} for s in ("hook", "setup", "discovery", "example", "payoff")]
        se01_durs = [4.91, 4.22, 15.5, 10.54, 2.9]
        se01_eq = compute_equalized_visual_durations(se01_secs, se01_durs)
        self.assertEqual(len(se01_eq), 5)
        self.assertAlmostEqual(sum(se01_eq), sum(se01_durs), places=4)
        self.assertLessEqual(max(se01_eq) - min(se01_eq), 0.01)

        # End-to-end VideoAssembler integration: EF01 (FUN_FACTS, 5 distinct images, no same-image cuts)
        ok_ef, total_ef, cap_ef = self._run_assembler_capturing_timeline(
            script_id="EF01",
            video_type="FUN_FACTS",
            lang="english",
            section_durs=[("hook", 4.0), ("setup", 5.95), ("discovery", 27.88), ("explanation", 6.22), ("payoff", 2.58)],
            image_names=[
                "script_EF01_hook.png",
                "script_EF01_setup.png",
                "script_EF01_discovery.png",
                "script_EF01_explanation.png",
                "script_EF01_payoff.png",
            ],
        )
        self.assertTrue(ok_ef)
        self.assertEqual(len(cap_ef["sections"]), 5)
        self.assertAlmostEqual(sum(cap_ef["durations"]), total_ef, places=3)
        self.assertLessEqual(max(cap_ef["durations"]) - min(cap_ef["durations"]), 0.01)
        self.assertTrue(all(t.duration >= 0.34 for t in cap_ef["transitions"]))

        # End-to-end VideoAssembler integration: ER01 (ROLEPLAY, 6 distinct images equalized)
        ok_er, total_er, cap_er = self._run_assembler_capturing_timeline(
            script_id="ER01",
            video_type="ROLEPLAY",
            lang="english",
            section_durs=[
                ("hook", 8.41),
                ("dialogue_part_1", 9.56),
                ("dialogue_part_2", 11.8),
                ("dialogue_part_3", 10.94),
                ("dialogue_part_4", 9.34),
                ("payoff", 14.07),
            ],
            image_names=[
                "script_ER01_hook.png",
                "script_ER01_dialogue_part_1.png",
                "script_ER01_dialogue_part_2.png",
                "script_ER01_dialogue_part_3.png",
                "script_ER01_dialogue_part_4.png",
                "script_ER01_payoff.png",
            ],
        )
        self.assertTrue(ok_er)
        self.assertEqual(len(cap_er["sections"]), 6)
        self.assertAlmostEqual(sum(cap_er["durations"]), total_er, places=3)
        self.assertLessEqual(max(cap_er["durations"]) - min(cap_er["durations"]), 0.01)
        self.assertTrue(all(t.duration >= 0.34 for t in cap_er["transitions"]))

    def test_game_chalkboard_and_pressure_stay_strictly_locked_while_answer_explanation_equalize(self):
        cases = [
            (
                "EG01",
                "english",
                [("hook", 7.54), ("challenge", 18.63), ("pressure", 3.63), ("answer", 10.38), ("explanation", 16.23)],
            ),
            (
                "FG01",
                "french",
                [("hook", 3.63), ("challenge", 12.37), ("pressure", 4.87), ("answer", 3.37), ("explanation", 14.64)],
            ),
        ]
        for sid, lang, section_durs in cases:
            with self.subTest(script_id=sid):
                ok, total_dur, cap = self._run_assembler_capturing_timeline(
                    script_id=sid,
                    video_type="GAME",
                    lang=lang,
                    section_durs=section_durs,
                    image_names=[f"script_{sid}_{s}.png" for s, _ in section_durs],
                )
                self.assertTrue(ok)
                self.assertEqual(len(cap["durations"]), 5)
                self.assertAlmostEqual(sum(cap["durations"]), total_dur, places=3)

                d_hook, d_chal, d_pres, d_ans, d_expl = cap["durations"]
                exp_hook, exp_chal, exp_pres, exp_ans, exp_expl = [d for _, d in section_durs]

                # Chalkboard (`challenge`) and waiting screen (`pressure`) stay strictly locked to audio timing
                self.assertAlmostEqual(d_hook, exp_hook, places=3)
                self.assertAlmostEqual(d_chal, exp_chal, places=3)
                self.assertAlmostEqual(d_pres, exp_pres, places=3)

                # Answer & explanation share post-countdown span equally
                self.assertAlmostEqual(d_ans, d_expl, delta=0.01)
                self.assertAlmostEqual(d_ans + d_expl, exp_ans + exp_expl, places=3)

                # Frame-snapped challenge start & end offsets remain identical to audio boundaries
                expected_off0 = round(int(round(exp_hook * 25)) / 25, 4)
                expected_off1 = round(int(round((exp_hook + exp_chal) * 25)) / 25, 4)
                self.assertEqual(cap["offsets"][0], expected_off0)
                self.assertEqual(cap["offsets"][1], expected_off1)

                # Chalkboard motion stays near-static linear <= 1.02x, entry/exit transitions stay crisp 0.18s
                chal_spec = dict(cap["motion_specs"])["challenge"]
                self.assertLessEqual(chal_spec.z_end, 1.02)
                self.assertEqual(chal_spec.curve, "linear")
                self.assertEqual(cap["transitions"][0], TransitionSpec("smoothup", 0.18))
                self.assertEqual(cap["transitions"][1], TransitionSpec("fade", 0.18))


class TestAssemblyPerformanceAndEncoder(unittest.TestCase):
    """Verifies 4x zoompan supersampling and NVENC -> libx264 automatic fallback."""

    def test_zoompan_canvas_defaults_to_4x_and_supports_override(self):
        # pyrefly: ignore[missing-import]
        from video_creation._G_video_assembly.core.video_assembler import _resolve_zoompan_canvas

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ASSEMBLY_ZOOMPAN_SCALE", None)
            self.assertEqual(_resolve_zoompan_canvas(), ("2304", "4096"))
        with mock.patch.dict(os.environ, {"ASSEMBLY_ZOOMPAN_SCALE": "4608x8192"}):
            self.assertEqual(_resolve_zoompan_canvas(), ("4608", "8192"))

    def test_encoder_kwargs_and_nvenc_fallback_to_libx264(self):
        # pyrefly: ignore[missing-import]
        import video_creation._G_video_assembly.core.video_assembler as va_mod

        nvenc_kw = va_mod._build_output_kwargs(use_nvenc=True, ffmpeg_threads=None)
        self.assertEqual(nvenc_kw["vcodec"], "h264_nvenc")
        self.assertEqual(nvenc_kw["cq"], "20")
        self.assertNotIn("threads", nvenc_kw)

        x264_kw = va_mod._build_output_kwargs(use_nvenc=False, ffmpeg_threads=4)
        self.assertEqual(x264_kw["vcodec"], "libx264")
        self.assertEqual(x264_kw["preset"], "faster")
        self.assertEqual(x264_kw["threads"], 4)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            timings_path, img_dir, audio_path, ass_path, out_mp4, script_data, total_dur = (
                TestVisualPacingIntegration._prepare_mock_script(
                    tmp_dir,
                    "EE98",
                    "EXPRESSION",
                    "english",
                    [("hook", 2.0), ("setup", 2.0)],
                    ["script_EE98_hook.png", "script_EE98_setup.png"],
                )
            )
            seen_vcodecs = []

            def _fake_output(*args, **kwargs):
                seen_vcodecs.append(kwargs.get("vcodec"))
                node = mock.MagicMock()
                if kwargs.get("vcodec") == "h264_nvenc":
                    err = va_mod.ffmpeg.Error("ffmpeg", b"", b"nvenc session limit")
                    node.overwrite_output.return_value.run.side_effect = err
                else:
                    node.overwrite_output.return_value.run.return_value = (b"", b"")
                return node

            assembler = VideoAssembler(ffmpeg_threads=3)
            with (
                mock.patch.object(va_mod, "_probe_nvenc_available", return_value=True),
                mock.patch.object(va_mod, "_probe_audio_duration", return_value=total_dur),
                mock.patch.object(va_mod.ffmpeg, "output", side_effect=_fake_output),
            ):
                ok = assembler.assemble(
                    script_id="EE98",
                    timings_path=timings_path,
                    image_dir=img_dir,
                    audio_path=audio_path,
                    ass_path=ass_path,
                    output_path=out_mp4,
                    video_type="EXPRESSION",
                    script_data=script_data,
                    language="english",
                )

            self.assertTrue(ok)
            self.assertEqual(seen_vcodecs, ["h264_nvenc", "libx264"])

    def test_resolve_prerequisites_and_process_script_accept_disk_assets_when_status_pending(self):
        # pyrefly: ignore[missing-import]
        from config import get_script_output_dir
        # pyrefly: ignore[missing-import]
        from video_creation._G_video_assembly import service as asm_service

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            out_dir = get_script_output_dir("EG01", "English", base_dir)
            img_dir = out_dir / "images"
            img_dir.mkdir(parents=True, exist_ok=True)
            wav_path = out_dir / "script_EG01_master.wav"
            _write_silent_wav(wav_path, duration_sec=0.5)
            (out_dir / "timings.json").write_text(json.dumps({"hook": {"start": 0.0, "end": 0.5}}), encoding="utf-8")
            ass_path = out_dir / "script_EG01_subtitles.ass"
            ass_path.write_text("[Script Info]\nTitle: Test\n", encoding="utf-8")

            state = {
                "id": "EG01",
                "metadata": {"LABEL": "English"},
                "status": {"voice_generation": "done", "image_generation": "pending", "video_assembly": "pending"},
                "assets": {},
            }

            # Without PNGs on disk and image_generation=pending, assembly must reject cleanly
            has_v, has_i, _, _ = asm_service.resolve_assembly_prerequisites(state, base_dir=base_dir)
            self.assertTrue(has_v)
            self.assertFalse(has_i)
            mock_sm = mock.MagicMock()
            self.assertFalse(
                asm_service.process_script(
                    script_data=state,
                    state_manager=mock_sm,
                    assembler=mock.MagicMock(),
                    base_dir=base_dir,
                    regenerate_subtitles=False,
                    auto=True,
                )
            )

            # Once scene PNG exists on disk, pending status still allows assembly and saves state
            _write_solid_png(img_dir / "script_EG01_hook.png", (40, 80, 120))
            has_v2, has_i2, res_audio, res_imgs = asm_service.resolve_assembly_prerequisites(state, base_dir=base_dir)
            self.assertTrue(has_v2)
            self.assertTrue(has_i2)
            self.assertEqual(res_audio, wav_path)
            self.assertEqual(res_imgs, img_dir)

            def _fake_assemble(sid, t_path, i_dir, a_path, s_path, out_mp4, **kw):
                Path(out_mp4).write_bytes(b"mp4-bytes")
                return True

            mock_asm = mock.MagicMock()
            mock_asm.assemble.side_effect = _fake_assemble
            ok = asm_service.process_script(
                script_data=state,
                state_manager=mock_sm,
                assembler=mock_asm,
                base_dir=base_dir,
                regenerate_subtitles=False,
                auto=True,
            )
            self.assertTrue(ok)
            self.assertTrue((out_dir / "script_EG01_final.mp4").is_file())
            mock_sm.save_script_state.assert_called_once()

    def test_transcriber_falls_back_to_cpu_when_cuda_generator_raises(self):
        # pyrefly: ignore[missing-import]
        from video_creation._G_video_assembly.core import transcriber as tr_mod

        class _FakeWord:
            word = " hello "
            start = 0.0
            end = 0.4

        class _FakeSeg:
            words = [_FakeWord()]

        class _FakeCudaModel:
            def transcribe(self, *_a, **_kw):
                def _lazy_fail():
                    if False:
                        yield None
                    raise RuntimeError("Library cublas64_12.dll is not found")

                return _lazy_fail(), None

        class _FakeCpuModel:
            def transcribe(self, *_a, **_kw):
                return iter([_FakeSeg()]), None

        models_created = []

        def _fake_whisper_model(size, device="cpu", compute_type="int8"):
            models_created.append((size, device, compute_type))
            return _FakeCudaModel() if device == "cuda" else _FakeCpuModel()

        fake_fw = mock.MagicMock(WhisperModel=_fake_whisper_model)
        with (
            mock.patch.dict("sys.modules", {"faster_whisper": fake_fw}),
            mock.patch.object(tr_mod, "_cuda_available", return_value=True),
        ):
            tr = tr_mod.Transcriber(device="auto")
            self.assertEqual(tr.device, "cuda")
            words = tr.transcribe(Path("dummy.wav"), language="en")

        self.assertEqual(tr.device, "cpu")
        self.assertEqual(words, [{"word": "hello", "start": 0.0, "end": 0.4}])
        self.assertEqual(
            models_created,
            [("base", "cuda", "float16"), ("base", "cpu", "int8")],
        )


if __name__ == "__main__":
    unittest.main()
