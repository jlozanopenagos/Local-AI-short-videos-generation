"""
core/video_assembler.py — Stage G FFmpeg Video Assembler facade.
Delegates camera motion curves, transitions, companion fallbacks, and BGM volume
envelopes to the type-isolated profiles in `assembly/types/` and `assembly/languages/`.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# pyrefly: ignore [missing-import]
import ffmpeg

from config import resolve_static_scene_path

try:
    from ..assembly.common.audio_mix import build_bgm_volume_expr
    from ..assembly.common.easing import build_zoompan_expressions
    from ..assembly.common.pacing import compute_equalized_visual_durations
    from ..assembly.common.transitions import (
        TransitionSpec,
        chain_clips_with_xfade,
        compute_clip_render_durations,
    )
    from ..assembly.languages import get_assembly_language_profile
    from ..assembly.types import get_assembly_profile
except (ImportError, ValueError):
    from assembly.common.audio_mix import build_bgm_volume_expr  # type: ignore[no-redef]
    from assembly.common.easing import build_zoompan_expressions  # type: ignore[no-redef]
    from assembly.common.pacing import compute_equalized_visual_durations  # type: ignore[no-redef]
    from assembly.common.transitions import (  # type: ignore[no-redef]
        TransitionSpec,
        chain_clips_with_xfade,
        compute_clip_render_durations,
    )
    from assembly.languages import get_assembly_language_profile  # type: ignore[no-redef]
    from assembly.types import get_assembly_profile  # type: ignore[no-redef]

_LEGACY_COMPANION_FALLBACKS = {
    "dialogue_part_1": ["hook"],
    "dialogue_part_4": ["payoff"],
    "payoff": ["dialogue_part_4"],
}


def _normalize_video_stream(stream: Any, fps: int = 25) -> Any:
    return (
        stream
        .filter("setsar", "1")
        .filter("settb", f"1/{fps}")
        .filter("setpts", "PTS-STARTPTS")
        .filter("format", "yuv420p")
    )


def _build_section_image_inputs(consolidated_sections: List[Dict[str, Any]]) -> List[Any]:
    """Build per-section FFmpeg video inputs without invalid PNG input options.

    Uses ``ffmpeg.input(path)`` once per unique image path and fans out any
    reused companion images (e.g. roleplay punch-in cuts) with ``split`` so
    FFmpeg-Python keeps distinct DAG nodes without ``-thread_queue_size``.
    """
    resolved_paths = [sec["path"].resolve().as_posix() for sec in consolidated_sections]
    counts: Dict[str, int] = {}
    for p in resolved_paths:
        counts[p] = counts.get(p, 0) + 1

    split_streams: Dict[str, Any] = {}
    next_index: Dict[str, int] = {}
    for p, count in counts.items():
        base_input = ffmpeg.input(p)
        if count > 1:
            split_streams[p] = ffmpeg.filter_multi_output(base_input, "split", count)
            next_index[p] = 0
        else:
            split_streams[p] = base_input

    inputs: List[Any] = []
    for p in resolved_paths:
        if counts[p] > 1:
            idx = next_index[p]
            next_index[p] = idx + 1
            inputs.append(split_streams[p].stream(idx))
        else:
            inputs.append(split_streams[p])
    return inputs


def _probe_audio_duration(audio_path: Path) -> float:
    try:
        local_ffprobe = (Path(__file__).parent.parent / "ffprobe.exe").resolve()
        ffprobe_path = local_ffprobe.as_posix() if local_ffprobe.exists() else "ffprobe"
        probe = ffmpeg.probe(audio_path.as_posix(), cmd=ffprobe_path)
        return float(probe["format"]["duration"])
    except Exception as exc:
        print(f"Failed to probe audio duration: {exc}")
        return 60.0


def _build_card_stream(card_path: Path, duration_sec: float, fps: int, fade_in: bool = False, fade_out: bool = False) -> Any:
    stream = (
        ffmpeg.input(card_path.as_posix(), loop=1, framerate=fps, t=duration_sec)
        .filter("scale", "576x1024", force_original_aspect_ratio="decrease")
        .filter("pad", "576", "1024", "(ow-iw)/2", "(oh-ih)/2")
    )
    stream = _normalize_video_stream(stream, fps=fps)
    if fade_in:
        stream = stream.filter("fade", t="in", st=0.0, d=0.20)
    if fade_out:
        stream = stream.filter("fade", t="out", st=max(0.0, duration_sec - 0.20), d=0.20)
    return stream


_NVENC_PROBE_CACHE: Dict[str, bool] = {}
_NVENC_PROBE_LOCK = threading.Lock()


def _resolve_zoompan_canvas() -> Tuple[str, str]:
    raw = os.getenv("ASSEMBLY_ZOOMPAN_SCALE", "2304x4096").strip().lower()
    if "x" in raw:
        w_part, h_part = raw.split("x", 1)
        if w_part.isdigit() and h_part.isdigit() and int(w_part) > 0 and int(h_part) > 0:
            return w_part, h_part
    return "2304", "4096"


def _probe_nvenc_available(ffmpeg_path: str) -> bool:
    mode = os.getenv("VIDEO_ENCODER", "auto").strip().lower()
    if mode in ("libx264", "cpu", "software"):
        return False

    with _NVENC_PROBE_LOCK:
        if ffmpeg_path in _NVENC_PROBE_CACHE:
            return _NVENC_PROBE_CACHE[ffmpeg_path]

    available = False
    try:
        proc = subprocess.run(
            [
                ffmpeg_path,
                "-hide_banner",
                "-f", "lavfi",
                "-i", "color=c=black:s=256x256:d=0.2",
                "-c:v", "h264_nvenc",
                "-pix_fmt", "yuv420p",
                "-f", "null", "-",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        available = proc.returncode == 0
    except Exception:
        available = False

    with _NVENC_PROBE_LOCK:
        _NVENC_PROBE_CACHE[ffmpeg_path] = available
    return available


def _build_output_kwargs(use_nvenc: bool, ffmpeg_threads: Optional[int] = None) -> Dict[str, Any]:
    if use_nvenc:
        kwargs: Dict[str, Any] = {
            "vcodec": "h264_nvenc",
            "preset": "p4",
            "rc": "vbr",
            "cq": "20",
            "pix_fmt": "yuv420p",
            "acodec": "aac",
            "shortest": None,
        }
    else:
        kwargs = {
            "vcodec": "libx264",
            "preset": "faster",
            "crf": "20",
            "pix_fmt": "yuv420p",
            "acodec": "aac",
            "shortest": None,
        }
    if ffmpeg_threads is not None and int(ffmpeg_threads) > 0:
        kwargs["threads"] = int(ffmpeg_threads)
    return kwargs


class VideoAssembler:
    def __init__(self, ffmpeg_threads: Optional[int] = None):
        self.ffmpeg_threads = ffmpeg_threads

    def assemble(
        self,
        script_id: str,
        timings_path: Path,
        image_dir: Path,
        audio_path: Path,
        ass_path: Path,
        output_path: Path,
        bgm_path: Path = None,
        watermark_path: Path = None,
        opening_path: Path = None,
        closure_path: Path = None,
        video_type: str = "",
        script_data: dict = None,
        language: str = None,
    ):
        if opening_path:
            opening_path = Path(opening_path)
        if closure_path:
            closure_path = Path(closure_path)

        with timings_path.open("r", encoding="utf-8") as f:
            timings = json.load(f)

        sorted_sections = sorted(timings.items(), key=lambda x: x[1]["start"])

        cm = (script_data.get("content_metadata") or {}) if isinstance(script_data, dict) else {}
        vtype_hint = video_type or cm.get("video_type") or script_id
        lang_hint = language or cm.get("language") or script_id
        profile = get_assembly_profile(vtype_hint)
        lang_profile = get_assembly_language_profile(lang_hint)
        fps = profile.fps if profile is not None else 25

        companion_fallbacks = (
            profile.companion_fallbacks
            if profile is not None
            else _LEGACY_COMPANION_FALLBACKS
        )

        # Collect available images
        available_sections = []
        for section, timing in sorted_sections:
            sec_lower = section.lower().strip()
            img_name = f"script_{script_id}_{section}.png"
            img_path = image_dir / img_name
            punch_in = False

            if not img_path.exists():
                img_name_alt = f"script_{script_id}_{section.replace(' ', '_')}.png"
                if (image_dir / img_name_alt).exists():
                    img_path = image_dir / img_name_alt

            if not img_path.exists():
                static_candidate = resolve_static_scene_path(
                    section_name=sec_lower,
                    script_data=script_data,
                    language=language,
                    video_type=video_type,
                )
                if static_candidate and static_candidate.exists():
                    img_path = static_candidate
                    print(f"Notice: Section '{section}' using centralized static asset '{img_path.name}'.")

            if not img_path.exists() and sec_lower in companion_fallbacks:
                for fallback_sec in companion_fallbacks[sec_lower]:
                    fb_name = f"script_{script_id}_{fallback_sec}.png"
                    fb_path = image_dir / fb_name
                    if fb_path.exists():
                        img_path = fb_path
                        punch_in = True
                        print(f"Notice: Section '{section}' using companion '{fallback_sec}' with dynamic punch-in cut.")
                        break

            if img_path.exists():
                fname_lower = img_path.name.lower()
                is_cb = (sec_lower == "challenge") or ("challenge" in fname_lower) or ("chalkboard" in fname_lower)
                available_sections.append({
                    "path": img_path,
                    "start": timing["start"],
                    "punch_in": punch_in,
                    "section": section,
                    "is_chalkboard": is_cb,
                })
            else:
                print(f"Warning: Missing image for section '{section}': {img_path}")

        if not available_sections:
            print("Error: No images found to assemble video.")
            return False

        # Consolidate consecutive identical companion images unless punch_in state changed
        consolidated_sections = []
        for sec in available_sections:
            if (
                consolidated_sections
                and consolidated_sections[-1]["path"] == sec["path"]
                and consolidated_sections[-1].get("punch_in") == sec.get("punch_in")
            ):
                continue
            consolidated_sections.append(sec)

        total_audio_dur: Optional[float] = None
        scene_durations: List[float] = []
        for i, current in enumerate(consolidated_sections):
            current_start = float(current["start"]) if i > 0 else 0.0
            if i < len(consolidated_sections) - 1:
                next_start = float(consolidated_sections[i + 1]["start"])
                dur = max(0.08, next_start - current_start)
            else:
                total_audio_dur = _probe_audio_duration(audio_path)
                dur = max(0.5, total_audio_dur - current_start)
            scene_durations.append(dur)

        print("Building FFMPEG filter graph for Ken Burns effect...")
        video_streams = []
        section_inputs = _build_section_image_inputs(consolidated_sections)

        if profile is not None:
            scene_durations = compute_equalized_visual_durations(
                consolidated_sections,
                scene_durations,
                locked_sections=profile.get_locked_visual_sections(),
            )
            if scene_durations:
                print(
                    f"[Visual Pacing QA]: Clips: {len(scene_durations)} | "
                    f"Total: {sum(scene_durations):.2f}s | Min: {min(scene_durations):.2f}s | "
                    f"Max: {max(scene_durations):.2f}s | Avg: {sum(scene_durations)/len(scene_durations):.2f}s"
                )
            transitions = [
                profile.get_transition_spec(
                    consolidated_sections[i]["section"],
                    consolidated_sections[i + 1]["section"],
                )
                for i in range(len(consolidated_sections) - 1)
            ]
            render_durations, effective_xfades, offsets = compute_clip_render_durations(
                scene_durations, transitions, fps=fps
            )
            main_duration = round(sum(render_durations) - sum(effective_xfades), 4)

            for i, current in enumerate(consolidated_sections):
                frames = max(2, int(round(render_durations[i] * fps)))
                sec_name = current.get("section", "").lower()
                file_name = current.get("path", Path()).name.lower()
                is_chalkboard = bool(current.get("is_chalkboard", False)) or (sec_name == "challenge") or ("challenge" in file_name) or ("chalkboard" in file_name)

                motion_spec = profile.get_motion_spec(
                    sec_name,
                    punch_in=bool(current.get("punch_in", False)),
                    is_chalkboard=is_chalkboard,
                )
                z_expr, x_expr, y_expr = build_zoompan_expressions(motion_spec, frames)
                zw, zh = _resolve_zoompan_canvas()

                stream = (
                    section_inputs[i]
                    .filter("scale", f"{zw}x{zh}", force_original_aspect_ratio="increase")
                    .filter("crop", zw, zh)
                    .filter("zoompan", z=z_expr, d=frames, x=x_expr, y=y_expr, s="576x1024", fps=fps)
                )
                video_streams.append(_normalize_video_stream(stream, fps=fps))

            main_video = chain_clips_with_xfade(video_streams, transitions, effective_xfades, offsets)
        else:
            # Legacy assembly branch (VIDEO_ASSEMBLY_ENGINE=legacy)
            main_duration = sum(scene_durations)
            vt_clean = str(video_type or "").strip().lower()
            zw, zh = _resolve_zoompan_canvas()
            for i, current in enumerate(consolidated_sections):
                frames = max(1, int(scene_durations[i] * fps))
                sec_name = current.get("section", "").lower()
                file_name = current.get("path", Path()).name.lower()
                is_chalkboard = (sec_name == "challenge") or ("challenge" in file_name) or ("chalkboard" in file_name)

                if is_chalkboard:
                    z_expr = "min(zoom+0.00005,1.02)"
                    y_expr = "ih/2-(ih/zoom/2)"
                elif current.get("punch_in", False):
                    z_expr = "if(lte(on,1),1.18,min(zoom+0.0004,1.25))"
                    y_expr = "max(0,ih/2-(ih/zoom/2)-(ih*0.04))"
                elif vt_clean == "roleplay":
                    z_expr = "min(zoom+0.00025,1.06)"
                    y_expr = "max(0,ih/2-(ih/zoom/2)-(ih*0.04))"
                elif vt_clean in ("fun_facts", "funfacts"):
                    z_expr = "min(zoom+0.0003,1.08)"
                    y_expr = "max(0,ih/2-(ih/zoom/2)-(ih*0.06))"
                else:
                    z_expr = "min(zoom+0.0003,1.08)"
                    y_expr = "max(0,ih/2-(ih/zoom/2)-(ih*0.04))"

                stream = (
                    section_inputs[i]
                    .filter("scale", f"{zw}x{zh}", force_original_aspect_ratio="increase")
                    .filter("crop", zw, zh)
                    .filter("zoompan", z=z_expr, d=frames, x="iw/2-(iw/zoom/2)", y=y_expr, s="576x1024")
                    .filter("setsar", "1")
                    .filter("format", "yuv420p")
                )
                video_streams.append(stream)

            main_video = ffmpeg.concat(*video_streams, v=1, a=0)

        # Apply Watermark if provided
        if watermark_path and watermark_path.exists():
            watermark_input = ffmpeg.input(watermark_path.as_posix())
            watermark_scaled = watermark_input.filter("scale", "120", "-1")
            watermark_faded = watermark_scaled.filter("colorchannelmixer", aa=0.6)
            main_video = ffmpeg.overlay(main_video, watermark_faded, x="main_w-overlay_w-36", y="main_h-overlay_h-90")

        # Overlay subtitles onto main video if provided and exists
        if ass_path and Path(ass_path).exists():
            main_video = main_video.filter("subtitles", filename=Path(ass_path).as_posix())
        else:
            print("Notice: No subtitle file provided or found. Assembling video without subtitles.")

        has_opening = bool(opening_path and opening_path.exists())
        has_closure = bool(closure_path and closure_path.exists())

        if profile is not None:
            main_video = _normalize_video_stream(main_video, fps=fps)
            if has_opening:
                main_video = main_video.filter("fade", t="in", st=0.0, d=0.18)
            if has_closure and main_duration > 0.4:
                main_video = main_video.filter("fade", t="out", st=max(0.0, main_duration - 0.18), d=0.18)

        # Build Final Video and Audio Sequences
        final_video_streams = []
        final_audio_streams = []

        # 1. Opening
        if has_opening:
            print(f"Adding opening card to video timeline: {opening_path.name}")
            if profile is not None:
                opening_stream = _build_card_stream(opening_path, 2.0, fps=fps, fade_out=True)
            else:
                opening_stream = (
                    ffmpeg.input(opening_path.as_posix(), loop=1, framerate=25, t=2)
                    .filter("scale", "576x1024", force_original_aspect_ratio="decrease")
                    .filter("pad", "576", "1024", "(ow-iw)/2", "(oh-ih)/2")
                    .filter("setsar", "1")
                    .filter("format", "yuv420p")
                )
            final_video_streams.append(opening_stream)
            final_audio_streams.append(ffmpeg.input("anullsrc", f="lavfi", t=2))
        else:
            print("Notice: No opening card provided or found.")

        # 2. Main
        final_video_streams.append(main_video)
        final_audio_streams.append(ffmpeg.input(audio_path.as_posix()))

        # 3. Closure
        if has_closure:
            print(f"Adding closure card to video timeline: {closure_path.name}")
            if profile is not None:
                closure_stream = _build_card_stream(closure_path, 3.0, fps=fps, fade_in=True)
            else:
                closure_stream = (
                    ffmpeg.input(closure_path.as_posix(), loop=1, framerate=25, t=3)
                    .filter("scale", "576x1024", force_original_aspect_ratio="decrease")
                    .filter("pad", "576", "1024", "(ow-iw)/2", "(oh-ih)/2")
                    .filter("setsar", "1")
                    .filter("format", "yuv420p")
                )
            final_video_streams.append(closure_stream)
            final_audio_streams.append(ffmpeg.input("anullsrc", f="lavfi", t=3))
        else:
            print("Notice: No closure card provided or found.")

        concat_video = ffmpeg.concat(*final_video_streams, v=1, a=0)
        concat_audio = ffmpeg.concat(*final_audio_streams, v=0, a=1)

        # Apply BGM if provided
        final_audio = concat_audio
        if bgm_path and bgm_path.exists():
            bgm_input = ffmpeg.input(bgm_path.as_posix(), stream_loop=-1)
            if profile is not None:
                vol_expr = build_bgm_volume_expr(
                    profile.get_audio_mix_spec(),
                    timings=timings,
                    opening_offset=2.0 if has_opening else 0.0,
                    main_duration=main_duration,
                    closure_duration=3.0 if has_closure else 0.0,
                    volume_scale=lang_profile.bgm_volume_scale,
                )
                bgm_low = bgm_input.filter("volume", vol_expr, eval="frame")
            else:
                bgm_low = bgm_input.filter("volume", "0.05")
            final_audio = ffmpeg.filter([concat_audio, bgm_low], "amix", inputs=2, duration="first")

        ffmpeg_file = (Path(__file__).parent.parent / "ffmpeg.exe").resolve()
        ffmpeg_path = ffmpeg_file.as_posix() if ffmpeg_file.exists() else "ffmpeg"

        use_nvenc = _probe_nvenc_available(ffmpeg_path)
        print(f"Running FFMPEG to assemble final video [{'h264_nvenc' if use_nvenc else 'libx264'}]...")

        def _run_encode(nvenc: bool) -> None:
            out_kwargs = _build_output_kwargs(use_nvenc=nvenc, ffmpeg_threads=self.ffmpeg_threads)
            (
                ffmpeg
                .output(
                    concat_video,
                    final_audio,
                    output_path.as_posix(),
                    **out_kwargs,
                )
                .overwrite_output()
                .run(cmd=ffmpeg_path, capture_stdout=True, capture_stderr=True)
            )

        try:
            _run_encode(use_nvenc)
            print(f"Video successfully assembled at {output_path}")
            return True
        except ffmpeg.Error as e:
            if use_nvenc:
                print("Notice: h264_nvenc encode failed; falling back to libx264...")
                try:
                    _run_encode(False)
                    print(f"Video successfully assembled at {output_path}")
                    return True
                except ffmpeg.Error as fallback_err:
                    e = fallback_err
            print("FFMPEG ERROR:")
            print(e.stderr.decode("utf-8", errors="replace") if e.stderr else str(e))
            return False
