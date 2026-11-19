"""
test/unit/test_video_assembler.py — Unit and real-FFmpeg smoke tests for typed Stage G Video Assembly.
"""
from __future__ import annotations

import json
import os
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


@unittest.skipUnless(FFMPEG_BIN.exists() and FFPROBE_BIN.exists(), "Bundled ffmpeg.exe/ffprobe.exe required")
class TestRealFfmpegTypedAssemblySmoke(unittest.TestCase):
    def test_end_to_end_assemble_all_four_video_types(self):
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

                    probe = ffmpeg.probe(out_mp4.as_posix(), cmd=FFPROBE_BIN.as_posix())
                    v_streams = [s for s in probe["streams"] if s["codec_type"] == "video"]
                    a_streams = [s for s in probe["streams"] if s["codec_type"] == "audio"]
                    self.assertEqual(len(v_streams), 1)
                    self.assertEqual(len(a_streams), 1)
                    self.assertEqual(int(v_streams[0]["width"]), 576)
                    self.assertEqual(int(v_streams[0]["height"]), 1024)
                    expected_dur = 2.0 + t_cur + 3.0
                    actual_dur = float(probe["format"]["duration"])
                    self.assertAlmostEqual(actual_dur, expected_dur, delta=0.35)


if __name__ == "__main__":
    unittest.main()
