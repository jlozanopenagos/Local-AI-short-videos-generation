"""Phase 0 - audit every reference voice clip (open-swara) used for Qwen3-TTS cloning.

Read-only for the pipeline: writes reports to <OUTPUT_DIR>/voice_quality/audit/.

Per clip: duration, peak, clipping %, noise floor, SNR estimate, edge silence,
Whisper transcript + detected language (transcript is later used as `ref_text`
for ICL cloning), language-mismatch flag and an overall 0-100 quality score.

Usage:
    py tools/voice_quality/audit_reference_voices.py [--languages spanish italian french english]
                                                     [--whisper-model small] [--limit N]
"""
import argparse
import csv
import json
import sys
from pathlib import Path

# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
import soundfile as sf

MAIN_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MAIN_DIR))
from config import OPEN_SWARA_DIR, OUTPUT_DIR  # noqa: E402

LANG_CODE = {"english": "en", "french": "fr", "spanish": "es", "italian": "it"}


def frame_rms_db(x: np.ndarray, sr: int, frame_ms: int = 20) -> np.ndarray:
    n = int(sr * frame_ms / 1000)
    frames = len(x) // n
    if frames == 0:
        return np.array([-120.0])
    f = x[: frames * n].reshape(frames, n)
    return 20 * np.log10(np.sqrt(np.mean(f ** 2, axis=1)) + 1e-9)


def analyse_signal(path: Path) -> dict:
    x, sr = sf.read(str(path))
    if x.ndim > 1:
        x = x.mean(axis=1)
    db = frame_rms_db(x, sr)
    speech_db = float(np.percentile(db, 90))
    noise_db = float(np.percentile(db, 10))
    active = np.where(db > noise_db + 12)[0]
    lead = float(active[0] * 0.02) if len(active) else 0.0
    trail = float((len(db) - 1 - active[-1]) * 0.02) if len(active) else 0.0
    return {
        "duration_s": round(len(x) / sr, 2),
        "sample_rate": sr,
        "peak": round(float(np.max(np.abs(x))), 3),
        "clip_pct": round(float(np.mean(np.abs(x) > 0.99)) * 100, 3),
        "noise_floor_db": round(noise_db, 1),
        "snr_db": round(speech_db - noise_db, 1),
        "lead_sil_s": round(lead, 2),
        "trail_sil_s": round(trail, 2),
    }


def score(m: dict, lang_ok: bool, is_accented_name: bool = False) -> int:
    s = 100.0
    s -= max(0.0, 35 - m["snr_db"]) * 1.5          # noisy
    s -= m["clip_pct"] * 20                          # clipped
    s -= 0 if 4.0 <= m["duration_s"] <= 9.0 else 10  # length
    s -= 0 if m["noise_floor_db"] < -55 else (m["noise_floor_db"] + 55) * 1.2
    s -= 25 if not lang_ok else 0
    s -= 30 if is_accented_name else 0
    return int(max(0, min(100, s)))


def save_outputs(out_dir: Path, rows: list) -> None:
    if not rows:
        return
    sorted_rows = sorted(rows, key=lambda r: (r["language"], r["gender"], -int(r["score"])))
    fields = list(sorted_rows[0].keys())
    with (out_dir / "reference_audit.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(sorted_rows)
    (out_dir / "ref_transcripts.json").write_text(
        json.dumps({r["rel_path"]: r["transcript"] for r in sorted_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--languages", nargs="+", default=["spanish", "italian", "french", "english"])
    ap.add_argument("--whisper-model", default="small")
    ap.add_argument("--limit", type=int, default=0, help="max clips per language (0 = all)")
    ap.add_argument("--no-resume", action="store_true", help="Ignore existing reference_audit.csv")
    args = ap.parse_args()

    # pyrefly: ignore[missing-import]
    from faster_whisper import WhisperModel
    model = WhisperModel(args.whisper_model, device="cpu", compute_type="int8")

    out_dir = OUTPUT_DIR / "voice_quality" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "reference_audit.csv"

    rows = []
    seen_rel = set()
    if csv_path.exists() and not args.no_resume:
        try:
            with csv_path.open("r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    rows.append(r)
                    seen_rel.add(r["rel_path"])
            print(f"Resumed {len(rows)} existing rows from {csv_path}")
        except Exception:
            rows = []
            seen_rel = set()

    for lang in args.languages:
        files = []
        for gend_sub in ("female", "male"):
            gfiles = sorted((Path(OPEN_SWARA_DIR) / lang / gend_sub).rglob("*.wav"))
            if args.limit:
                gfiles = gfiles[: args.limit]
            files.extend(gfiles)
        if not files:
            files = sorted((Path(OPEN_SWARA_DIR) / lang).rglob("*.wav"))
            if args.limit:
                files = files[: args.limit]
        for p in files:
            rel_path = p.relative_to(OPEN_SWARA_DIR).as_posix()
            if rel_path in seen_rel:
                continue
            m = analyse_signal(p)
            segs, info = model.transcribe(str(p), language=None, beam_size=5)
            text = " ".join(s.text.strip() for s in segs).strip()
            detected = info.language
            lang_ok = detected == LANG_CODE[lang]
            is_accented = lang != "english" and "_english_" in p.name.lower()
            gender = "female" if "/female/" in p.as_posix() or "_female_" in p.name else "male"
            row = {
                "language": lang,
                "gender": gender,
                "file": p.name,
                "rel_path": rel_path,
                "detected_lang": detected,
                "lang_prob": round(info.language_probability, 2),
                "lang_ok": lang_ok and not is_accented,
                "transcript": text,
                "score": score(m, lang_ok, is_accented),
                **m,
            }
            rows.append(row)
            seen_rel.add(rel_path)
            print(f"{lang:8} {p.name:45} score={row['score']:3} snr={m['snr_db']:5} lang={detected}", flush=True)
            save_outputs(out_dir, rows)

    save_outputs(out_dir, rows)
    print(f"\nWrote {out_dir / 'reference_audit.csv'} ({len(rows)} clips)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
