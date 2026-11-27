"""Create loudness-matched listening samples and optional pitch/identity diagnostics."""
import argparse
import json
import sys
from pathlib import Path

# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
import soundfile as sf
# pyrefly: ignore[missing-import]
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "main"))
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.audio_processor import measure_lufs


def read_span(path, interval):
    with sf.SoundFile(path) as audio:
        sr = audio.samplerate
        audio.seek(round(interval["start"] * sr))
        frames = round((interval["end"] - interval["start"]) * sr)
        return audio.read(frames, always_2d=True).mean(axis=1), sr


def match_loudness(samples, target=-23.0):
    loudness = [measure_lufs(data, sr) for data, sr in samples]
    if not all(np.isfinite(loudness)):
        raise ValueError("Cannot loudness-match a silent sample.")
    peak_limits = [
        level + 20 * np.log10(0.90 / max(1e-8, float(np.abs(data).max())))
        for (data, _), level in zip(samples, loudness)
    ]
    common_level = min(target, *peak_limits)
    return [
        (data * 10 ** ((common_level - level) / 20), sr)
        for (data, sr), level in zip(samples, loudness)
    ]


def pitch_report(data, sr):
    # pyrefly: ignore[missing-import]
    from librosa import pyin
    if sr != 12000:
        data = resample_poly(data, 12000, sr)
    f0, voiced, _ = pyin(data, fmin=65, fmax=650, sr=12000, frame_length=1024, hop_length=120)
    values = f0[voiced & np.isfinite(f0)]
    return [round(float(v), 1) for v in np.percentile(values, [10, 50, 90])] if len(values) else None


def embedding(encoder, data, sr):
    # pyrefly: ignore[missing-import]
    import torch
    if sr != 16000:
        data = resample_poly(data, 16000, sr)
    vector = encoder.encode_batch(torch.as_tensor(data, dtype=torch.float32)[None, :]).flatten()
    return torch.nn.functional.normalize(vector, dim=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path, help="Golden baseline directory for a single ID")
    parser.add_argument("--preview", required=True, type=Path, help="Preview output directory for that ID")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--pyin", action="store_true")
    parser.add_argument("--ecapa-model", type=Path, help="Local SpeechBrain ECAPA model files")
    parser.add_argument("--reference-root", type=Path, help="Reference library for per-take identity checks")
    parser.add_argument("--section", action="append", help="Limit comparisons to named sections")
    args = parser.parse_args()

    encoder = None
    if args.ecapa_model:
        # pyrefly: ignore[missing-import]
        import torch
        # pyrefly: ignore[missing-import]
        from speechbrain.inference.speaker import EncoderClassifier
        # pyrefly: ignore[missing-import]
        from speechbrain.utils.fetching import LocalStrategy

        torch.set_num_threads(2)
        model_dir = str(args.ecapa_model.resolve())
        encoder = EncoderClassifier.from_hparams(
            source=model_dir, savedir=model_dir, overrides={"pretrained_path": model_dir},
            run_opts={"device": "cpu"}, local_strategy=LocalStrategy.COPY,
        )

    before = json.loads((args.baseline / "timings.json").read_text(encoding="utf-8"))
    after = json.loads((args.preview / "timings.json").read_text(encoding="utf-8"))
    base_audio = next(args.baseline.glob("*_master.wav"))
    preview_audio = args.preview / base_audio.name
    trace_path = args.preview / "voice_preview.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))["segments"] if trace_path.is_file() else []
    sections = args.section or list(after)
    args.output.mkdir(parents=True, exist_ok=False)
    report = {}
    for index, section in enumerate(sections):
        if section not in before or section not in after:
            continue
        originals = [read_span(base_audio, before[section]), read_span(preview_audio, after[section])]
        samples = match_loudness(originals)
        keys = ("baseline", "preview") if index % 2 == 0 else ("preview", "baseline")
        section_report = {}
        for label, source in zip(("A", "B"), keys):
            sample = samples[0 if source == "baseline" else 1]
            sf.write(args.output / f"{section}_{label}.wav", *sample)
            section_report[label] = {"source": source, "lufs": round(measure_lufs(*sample), 1)}
            if args.pyin:
                section_report[label]["f0_hz_p10_p50_p90"] = pitch_report(*sample)
        if encoder is not None and not section.startswith("dialogue"):
            vectors = [embedding(encoder, *sample) for sample in samples]
            section_report["cross_render_cosine"] = round(float(vectors[0] @ vectors[1]), 4)
        report[section] = section_report
    if encoder is not None and args.reference_root:
        by_name = {path.name: path for path in args.reference_root.rglob("*.wav")}
        previous = {}
        references = {}
        per_take = []
        for segment in trace:
            ref_name = segment["reference"]
            if ref_name not in by_name:
                continue
            if ref_name not in references:
                ref_audio, ref_rate = sf.read(by_name[ref_name], always_2d=True)
                references[ref_name] = embedding(encoder, ref_audio.mean(axis=1), ref_rate)
            take = next(take for take in segment["takes"] if take["seed"] == segment["winner_seed"])
            data, sr = sf.read(args.preview / take["file"], always_2d=True)
            vector = embedding(encoder, data.mean(axis=1), sr)
            speaker = segment["speaker"]
            per_take.append({
                "section": segment["section"], "speaker": speaker, "reference": ref_name,
                "reference_cosine": round(float(vector @ references[ref_name]), 4),
                "previous_same_role_cosine": (
                    round(float(vector @ previous[speaker]), 4) if speaker in previous else None
                ),
            })
            previous[speaker] = vector
        report["take_identity"] = per_take
    (args.output / "comparison_key.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
