"""Render voice comparisons into a new workspace using frozen golden script states."""
import argparse
import json
import sys
import shutil
from uuid import uuid4
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "main"))

from config import COMFY_API_URL, COMFY_INPUT_DIR, OPEN_SWARA_DIR, VOICE_WORKFLOW_PATH
from core.state_manager import StateManager
from video_creation._B_voice_generation.core.comfy_client import ComfyClient
from video_creation._B_voice_generation.core.acoustic_evaluator import _extract_voiced_pitches
from video_creation._B_voice_generation.core.voice_manager import VoiceManager
from video_creation._B_voice_generation.core.script_parser import get_script_segments
from video_creation._B_voice_generation.voice.common.delivery import continuous_narration
from video_creation._B_voice_generation.voice.common.orchestrator import synthesize_script_voice

GOLDEN_IDS = "EF01 EE01 EG01 ER01 FF04 FE01 FG01 FR01 IF01 IE01 IG01 IR01 SF01 SE01 SG01 SR01".split()


class PreviewComfyClient(ComfyClient):
    """Use the shared instance without interrupting other submitted jobs."""

    @staticmethod
    def original_reference(filename):
        return filename.split("__", 1)[1] if filename.startswith("shorts_preview_") else filename

    def _has_manifest_ref_text(self, ref_audio_name):
        return super()._has_manifest_ref_text(self.original_reference(ref_audio_name))

    def _get_ref_transcript(self, ref_audio_name, language=""):
        return super()._get_ref_transcript(self.original_reference(ref_audio_name), language)

    def ensure_clean_slate(self):
        pass

    def interrupt(self):
        return False

    def poll_for_completion(self, prompt_id, timeout_seconds=900, **kwargs):
        try:
            return super().poll_for_completion(prompt_id, timeout_seconds=timeout_seconds, **kwargs)
        except TimeoutError:
            self._http_post(f"{self.api_url}/queue", json={"delete": [prompt_id]}, timeout=15)
            self._http_post(f"{self.api_url}/interrupt", json={"prompt_id": prompt_id}, timeout=15)
            raise

    def generate_voice_segment(self, **kwargs):
        return super().generate_voice_segment(max_retries=1, stall_timeout=900, **kwargs)



class PreviewVoiceManager(VoiceManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preview_prefix = f"shorts_preview_{uuid4().hex}__"
        self.preview_refs = set()

    def prepare_voice_in_comfy(self, voice_file_path):
        destination = self.comfy_input_dir / f"{self.preview_prefix}{voice_file_path.name}"
        if destination not in self.preview_refs:
            shutil.copy2(voice_file_path, destination)
            self.preview_refs.add(destination)
        return destination.name

    def cleanup_comfy_input(self):
        for path in self.preview_refs:
            path.unlink(missing_ok=True)
        self.preview_refs.clear()


def read_baseline_section(folder, script_id, section):
    import soundfile as sf

    timings = json.loads((folder / "timings.json").read_text(encoding="utf-8"))
    interval = timings[section]
    with sf.SoundFile(folder / f"script_{script_id}_master.wav") as audio:
        sr = audio.samplerate
        audio.seek(round(interval["start"] * sr))
        frames = round((interval["end"] - interval["start"]) * sr)
        return audio.read(frames, always_2d=True).mean(axis=1), sr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--mode", choices=("baseline", "continuity", "direction", "reference", "roleplay"), default="direction")
    parser.add_argument("--candidates", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--ids", nargs="+", choices=GOLDEN_IDS, default=GOLDEN_IDS)
    parser.add_argument("--voice-anchor-section", help="Clone a reviewed, single-narrator section using its script text as the transcript")
    parser.add_argument("--pitch-anchor-section", help="Use a reviewed baseline narrator section as the register reference")
    parser.add_argument("--sections", nargs="+", help="Render just these section keys for each requested ID")
    parser.add_argument("--recast", action="store_true", help="Choose new reference voices for the comparison")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=False)
    state_manager = StateManager(workspace)
    voice_manager = PreviewVoiceManager(
        OPEN_SWARA_DIR, COMFY_INPUT_DIR,
        casting_history_path=workspace / "casting_history.json",
    )
    comfy_client = PreviewComfyClient(COMFY_API_URL, VOICE_WORKFLOW_PATH)
    sections = {section.casefold() for section in args.sections} if args.sections else None
    failures = []
    try:
        for script_id in args.ids:
            path = args.baseline / script_id / f"script_{script_id}.json"
            state = json.loads(path.read_text(encoding="utf-8-sig"))
            pitch_anchor = None
            if args.pitch_anchor_section:
                import numpy as np
                data, sr = read_baseline_section(path.parent, script_id, args.pitch_anchor_section)
                pitches = _extract_voiced_pitches(data, sr)
                if not pitches:
                    raise ValueError(f"No measurable F0 for {script_id} {args.pitch_anchor_section}")
                pitch_anchor = float(np.median(pitches))
            narrator_reference = None
            if args.voice_anchor_section:
                import soundfile as sf

                data, sr = read_baseline_section(path.parent, script_id, args.voice_anchor_section)
                label = state.get("metadata", {}).get("LABEL", "english")
                sections_to_voice = get_script_segments(script_id, state["script_text"], label)
                matched = [segment for segment in sections_to_voice if segment["section"] == args.voice_anchor_section]
                if not matched or any(segment["speaker"] != "Narrator" for segment in matched):
                    raise ValueError(f"{script_id} {args.voice_anchor_section} is not a single-narrator section")
                transcript = continuous_narration(" ".join(segment["text"] for segment in matched))
                anchor_file = workspace / f"{script_id}_approved_anchor.wav"
                sf.write(anchor_file, data, sr)
                narrator_reference = (anchor_file, transcript)
            if not synthesize_script_voice(
                state, state_manager, comfy_client, voice_manager,
                force=True, base_dir=workspace, candidates=args.candidates,
                engine_mode="typed", quality_preview=args.mode, force_fresh_cast=args.recast,
                preview_sections=sections, narrator_pitch_anchor=pitch_anchor, narrator_reference=narrator_reference,
            ):
                failures.append(script_id)
    finally:
        voice_manager.cleanup_comfy_input()
    print(f"Voice preview finished. Failed IDs: {', '.join(failures) or 'none'}")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
