"""Phase 0/1 - A/B benchmark of Qwen3-TTS cloning settings AND Kokoro-82M voices per language.

Renders identical test sentences for every combination of:
  * Qwen3-TTS variants (`xvec`, `icl`, `icl_loc`) using top-scoring Open-Swara references
  * Kokoro-82M voices (`ef_dora`, `em_alex`, `ff_siwis`, `if_sara`, `im_nicola`) across speeds
and measures:
  * WER vs. the target text (faster-whisper, CPU)
  * speaking rate (words/s), leading silence, total duration, generation time
WAVs are saved so a human can listen; results.csv + summary.md are written.

Variants:
  xvec      : current production behaviour (x_vector_only = true, English instruct)
  icl       : ICL cloning (x_vector_only = false) with the Whisper transcript as ref_text
  icl_loc   : ICL + instruct written in the target language
  kokoro    : Kokoro-82M built-in neural voices (no reference audio)

Usage:
    py tools/voice_quality/benchmark_voices.py --languages spanish italian french \
        --variants kokoro xvec icl icl_loc --refs-per-gender 1 --kokoro-speeds 0.95 1.03 1.1
"""
import argparse
import csv
import difflib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
import soundfile as sf

MAIN_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MAIN_DIR))
sys.path.insert(0, str(MAIN_DIR / "core"))
from config import (  # noqa: E402
    COMFY_API_URL, COMFY_INPUT_DIR, COMFY_OUTPUT_DIR, OPEN_SWARA_DIR, OUTPUT_DIR, VOICE_WORKFLOW_PATH,
)
from video_creation._B_voice_generation.core.comfy_client import ComfyClient  # noqa: E402
from video_creation._B_voice_generation.core.kokoro_engine import get_kokoro_engine  # noqa: E402

LANG_CODE = {"english": "en", "french": "fr", "spanish": "es", "italian": "it"}

KOKORO_BENCH_VOICES = {
    "spanish": [("female", "ef_dora"), ("male", "em_alex")],
    "italian": [("female", "if_sara"), ("male", "im_nicola")],
    "french": [("female", "ff_siwis"), ("male", "ff_siwis_male")],
}

# Sentences cover liaison/elision, double consonants, accents, questions, numbers and short punchy hooks.
TEST_SENTENCES = {
    "spanish": [
        "¿Sabías que en España nadie dice \"estoy muy cansado\" cuando quiere decir que está harto?",
        "Hoy vamos a aprender una expresión que usan los nativos todos los días: tirar la casa por la ventana.",
        "Ojo, porque si lo dices mal, tus amigos se van a reír de ti. ¡Inténtalo otra vez!",
    ],
    "italian": [
        "Lo sapevi che in Italia nessuno dice \"buona fortuna\" prima di un esame?",
        "Oggi impariamo un'espressione che gli italiani usano ogni giorno: in bocca al lupo!",
        "Attenzione, perché se la pronunci male, i tuoi amici scoppieranno a ridere. Riprova!",
    ],
    "french": [
        "Saviez-vous qu'en France personne ne dit « bonne chance » avant un examen ?",
        "Aujourd'hui, on apprend une expression que les Français utilisent tous les jours : poser un lapin.",
        "Attention, si vous la prononcez mal, vos amis vont éclater de rire. Réessayez !",
    ],
}

INSTRUCT_LOCAL = {
    "spanish": "Un narrador nativo de español, con voz cálida y natural, ritmo conversacional vivo, entonación expresiva y pronunciación clara y auténtica.",
    "italian": "Un narratore madrelingua italiano, voce calda e naturale, ritmo conversazionale vivace, intonazione espressiva e pronuncia chiara e autentica.",
    "french": "Un narrateur natif français, voix chaleureuse et naturelle, rythme conversationnel vif, intonation expressive et prononciation claire et authentique.",
}


def norm_words(text: str) -> list:
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9' ]+", " ", t)
    return t.split()


def wer(ref: str, hyp: str) -> float:
    r, h = norm_words(ref), norm_words(hyp)
    if not r:
        return 0.0
    sm = difflib.SequenceMatcher(a=r, b=h)
    matched = sum(b.size for b in sm.get_matching_blocks())
    return round(1 - matched / len(r), 3)


def lead_silence(x: np.ndarray, sr: int, thr: float = 0.01) -> float:
    idx = np.where(np.abs(x) > thr)[0]
    return round(idx[0] / sr, 2) if len(idx) else 0.0


def pick_refs(audit_csv: Path, lang: str, per_gender: int) -> list:
    if not audit_csv.exists():
        return []
    rows = list(csv.DictReader(audit_csv.open(encoding="utf-8")))
    out = []
    for g in ("female", "male"):
        cand = [r for r in rows if r["language"] == lang and r["gender"] == g and str(r["lang_ok"]) == "True"]
        if not cand:
            cand = [r for r in rows if r["language"] == lang and r["gender"] == g]
        cand.sort(key=lambda r: -int(r["score"]))
        out.extend(cand[:per_gender])
    return out


def evaluate_audio(out_wav: Path, sentence: str, lang: str, asr, gen_s: float, ref_name: str, gender: str, variant: str, idx: int) -> dict:
    x, sr = sf.read(str(out_wav))
    if x.ndim > 1:
        x = x.mean(axis=1)
    segs, _ = asr.transcribe(str(out_wav), language=LANG_CODE[lang], beam_size=5)
    hyp = " ".join(s.text.strip() for s in segs)
    dur = len(x) / sr
    return {
        "language": lang,
        "ref": ref_name,
        "gender": gender,
        "variant": variant,
        "sentence_idx": idx,
        "wer": wer(sentence, hyp),
        "duration_s": round(dur, 2),
        "words_per_s": round(len(norm_words(sentence)) / max(dur, 0.1), 2),
        "lead_sil_s": lead_silence(x, sr),
        "gen_time_s": round(gen_s, 2),
        "hyp": hyp,
        "error": "",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--languages", nargs="+", default=["spanish", "italian", "french"])
    ap.add_argument("--variants", nargs="+", default=["kokoro", "xvec", "icl", "icl_loc"])
    ap.add_argument("--kokoro-speeds", nargs="+", type=float, default=[1.0])
    ap.add_argument("--refs-per-gender", type=int, default=1)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--whisper-model", default="small")
    ap.add_argument("--run-name", default=time.strftime("run_%Y%m%d_%H%M%S"))
    args = ap.parse_args()

    audit_dir = OUTPUT_DIR / "voice_quality" / "audit"
    audit_csv = audit_dir / "reference_audit.csv"
    transcripts_path = audit_dir / "ref_transcripts.json"
    transcripts = json.loads(transcripts_path.read_text(encoding="utf-8")) if transcripts_path.exists() else {}
    run_dir = OUTPUT_DIR / "voice_quality" / "bench" / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    # pyrefly: ignore[missing-import]
    from faster_whisper import WhisperModel
    asr = WhisperModel(args.whisper_model, device="cpu", compute_type="int8")

    qwen_variants = [v for v in args.variants if v in ("xvec", "icl", "icl_loc")]
    client = None
    if qwen_variants:
        try:
            client = ComfyClient(COMFY_API_URL, VOICE_WORKFLOW_PATH, COMFY_OUTPUT_DIR)
            client.check_connection()
        except Exception as exc:
            print(f"[Warning] ComfyUI unavailable ({exc}); skipping Qwen3 variants {qwen_variants}.")
            qwen_variants = []

    kokoro = get_kokoro_engine() if "kokoro" in args.variants else None

    rows = []
    for lang in args.languages:
        # 1. Run Kokoro variants first (fast, deterministic, zero reference audio)
        if kokoro and kokoro.is_ready:
            for gender, voice_id in KOKORO_BENCH_VOICES.get(lang, []):
                for spd in args.kokoro_speeds:
                    v_label = "kokoro" if len(args.kokoro_speeds) == 1 and spd == 1.0 else f"kokoro_{spd:.2f}x"
                    for i, sentence in enumerate(TEST_SENTENCES[lang]):
                        out_wav = run_dir / lang / f"{gender}_{voice_id}_{v_label}_s{i}.wav"
                        out_wav.parent.mkdir(parents=True, exist_ok=True)
                        t0 = time.time()
                        res_path = kokoro.synthesize_text(
                            text=sentence,
                            output_path=out_wav,
                            language=lang,
                            voice=voice_id,
                            gender=gender,
                            speed=spd,
                        )
                        gen_s = time.time() - t0
                        if not res_path or not out_wav.exists():
                            rows.append({
                                "language": lang, "ref": voice_id, "gender": gender, "variant": v_label,
                                "sentence_idx": i, "wer": 1.0, "error": "Kokoro synthesis failed",
                            })
                            continue
                        row = evaluate_audio(out_wav, sentence, lang, asr, gen_s, voice_id, gender, v_label, i)
                        rows.append(row)
                        print(
                            f"  {lang:8} {voice_id:15} {v_label:12} s{i} WER={row['wer']:.2f} "
                            f"dur={row['duration_s']:.1f}s wps={row['words_per_s']:.2f} gen={gen_s:.2f}s",
                            flush=True,
                        )

        # 2. Run Qwen3-TTS variants if requested and ComfyUI is reachable
        if qwen_variants and client:
            refs = pick_refs(audit_csv, lang, args.refs_per_gender)
            print(f"[{lang}] Qwen3 references: {[r['file'] for r in refs]}", flush=True)
            for ref in refs:
                ref_abs = Path(OPEN_SWARA_DIR) / ref["rel_path"]
                comfy_name = ref_abs.name
                dst = COMFY_INPUT_DIR / comfy_name
                if not dst.exists():
                    dst.write_bytes(ref_abs.read_bytes())
                for variant in qwen_variants:
                    for i, sentence in enumerate(TEST_SENTENCES[lang]):
                        wf = client._prepare_workflow(
                            ref_audio_name=comfy_name, target_text=sentence, language=lang,
                            gender=ref["gender"], context="narrator", emotion="warm, energetic and friendly",
                            energy="medium", style="lively storytelling", output_prefix=f"vqbench/{lang}", seed=args.seed + i,
                        )
                        wf["35"]["inputs"]["x_vector_only"] = variant == "xvec"
                        if variant != "xvec":
                            wf["35"]["inputs"]["ref_text"] = transcripts.get(ref["rel_path"], "")
                        if variant == "icl_loc":
                            wf["39"]["inputs"]["instruct"] = INSTRUCT_LOCAL[lang]
                        out_wav = run_dir / lang / f"{ref['gender']}_{ref_abs.stem}_{variant}_s{i}.flac"
                        out_wav.parent.mkdir(parents=True, exist_ok=True)
                        t0 = time.time()
                        try:
                            pid = client.queue_prompt(wf)
                            hist = client.poll_for_completion(pid, timeout_seconds=300)
                            info = hist["outputs"]["8"]["audio"][0]
                            client.download_file(info["filename"], info.get("subfolder", ""), info.get("type", "output"), out_wav)
                        except Exception as exc:
                            print(f"  FAILED {out_wav.name}: {exc}", flush=True)
                            rows.append({"language": lang, "ref": ref_abs.stem, "gender": ref["gender"], "variant": variant,
                                         "sentence_idx": i, "wer": 1.0, "error": str(exc)})
                            continue
                        gen_s = time.time() - t0
                        row = evaluate_audio(out_wav, sentence, lang, asr, gen_s, ref_abs.stem, ref["gender"], variant, i)
                        rows.append(row)
                        print(
                            f"  {lang:8} {ref_abs.stem[-18:]:18} {variant:8} s{i} WER={row['wer']:.2f} "
                            f"dur={row['duration_s']:.1f}s lead={row['lead_sil_s']}s gen={gen_s:.1f}s",
                            flush=True,
                        )

    fields = ["language", "ref", "gender", "variant", "sentence_idx", "wer", "duration_s", "words_per_s",
              "lead_sil_s", "gen_time_s", "hyp", "error"]
    with (run_dir / "results.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    # summary per language x variant
    seen_variants = []
    for r in rows:
        if r["variant"] not in seen_variants:
            seen_variants.append(r["variant"])

    lines = [
        "| language | variant | n | mean WER | mean words/s | mean lead silence (s) | mean gen time (s) |",
        "|---|---|---|---|---|---|---|",
    ]
    for lang in args.languages:
        for v in seen_variants:
            sub = [r for r in rows if r["language"] == lang and r["variant"] == v and not r.get("error")]
            if sub:
                lines.append(
                    f"| {lang} | {v} | {len(sub)} | {np.mean([r['wer'] for r in sub]):.3f} | "
                    f"{np.mean([r['words_per_s'] for r in sub]):.2f} | "
                    f"{np.mean([r['lead_sil_s'] for r in sub]):.2f} | "
                    f"{np.mean([r['gen_time_s'] for r in sub]):.2f} |"
                )
    (run_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "\n".join(lines))
    print(f"\nListen to the WAVs in: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
