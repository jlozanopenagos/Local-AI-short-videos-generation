"""
test/tools/freeze_image_fixtures.py — Freeze the golden-set states and (re)generate Stage C snapshots.

Usage (from shorts_automation/):
    py test/tools/freeze_image_fixtures.py freeze     # copy trimmed golden states from main/state (run once)
    py test/tools/freeze_image_fixtures.py snapshot   # (re)write snapshots from CURRENT code
    py test/tools/freeze_image_fixtures.py corpus     # (re)write corpus baseline over ALL state files
    py test/tools/freeze_image_fixtures.py corpus-diff# compare current code to corpus baseline

Only run `snapshot`/`corpus` on purpose: they redefine "expected" behavior.
In Phases 0-2 they must NEVER be re-run to make a failing test pass.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import image_prompt_harness as H  # noqa: E402

STATE_ROOT = H.MAIN_DIR / "state"
KEEP = ("id", "script_text", "metadata", "content_metadata", "prompt_params", "cast")


def _trim(state: dict) -> dict:
    t = {k: state[k] for k in KEEP if k in state}
    assets = state.get("assets") if isinstance(state.get("assets"), dict) else {}
    t["assets"] = {k: assets[k] for k in ("general_prompt", "character_anchors") if k in assets}
    return t


def _find_state(script_id: str) -> Path | None:
    for p in STATE_ROOT.rglob(f"script_{script_id}.json"):
        return p
    return None


def freeze() -> None:
    H.STATES_DIR.mkdir(parents=True, exist_ok=True)
    for sid in H.GOLDEN_IDS:
        p = _find_state(sid)
        if not p:
            print(f"[MISSING] {sid}")
            continue
        state = json.loads(p.read_text(encoding="utf-8"))
        state.setdefault("id", sid)
        (H.STATES_DIR / f"script_{sid}.json").write_text(
            json.dumps(_trim(state), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(f"[FROZEN] {sid}")


def snapshot() -> None:
    H.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    system_store: dict = {}
    for sid in H.GOLDEN_IDS:
        cap = H.capture_script(H.load_state(sid))
        cond = H.condense(cap, system_store)
        (H.SNAPSHOT_DIR / f"{sid}.json").write_text(
            json.dumps(cond, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(f"[SNAPSHOT] {sid}: {len(cond['calls'])} LLM calls")
    (H.SNAPSHOT_DIR / "_system_prompts.json").write_text(
        json.dumps(system_store, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    (H.SNAPSHOT_DIR / "_sanitizer.json").write_text(
        json.dumps(H.capture_sanitizer(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    (H.SNAPSHOT_DIR / "_environment.json").write_text(
        json.dumps(H.capture_environment_cases(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"[SNAPSHOT] {len(system_store)} distinct system prompts stored")


def _corpus_entry(state: dict) -> dict:
    try:
        cap = H.capture_script(state, include_single_scene=False)
    except Exception as exc:  # recorded so error behavior is also compared
        return {"error": f"{type(exc).__name__}: {exc}"[:200]}
    return {
        "calls": [f"{c['kind']}:{H.sha(c['system'])}:{H.sha(c['user'])}" for c in cap["calls"]],
        "calls_no_gp": [f"{c['kind']}:{H.sha(c['system'])}:{H.sha(c['user'])}" for c in cap["calls_no_gp"]],
        "out": H.sha(json.dumps([cap["outputs"], cap["outputs_no_gp"]], ensure_ascii=False, sort_keys=True)),
    }


def corpus_state() -> dict:
    res = {}
    for p in sorted(STATE_ROOT.rglob("script_*.json")):
        try:
            state = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            res[p.stem] = {"error": f"unreadable: {exc}"[:120]}
            continue
        state.setdefault("id", p.stem.replace("script_", ""))
        res[state["id"]] = _corpus_entry(_trim(state) | {"id": state["id"]})
    return res


def corpus() -> None:
    data = corpus_state()
    H.CORPUS_BASELINE.parent.mkdir(parents=True, exist_ok=True)
    H.CORPUS_BASELINE.write_text(json.dumps(data, indent=0, sort_keys=True), encoding="utf-8")
    errs = sum(1 for v in data.values() if "error" in v)
    print(f"[CORPUS] {len(data)} states recorded ({errs} with recorded errors)")


def corpus_diff() -> int:
    base = json.loads(H.CORPUS_BASELINE.read_text(encoding="utf-8"))
    cur = corpus_state()
    changed = [k for k in sorted(set(base) | set(cur)) if base.get(k) != cur.get(k)]
    print(f"[CORPUS-DIFF] {len(changed)} / {len(cur)} states differ from baseline")
    for k in changed[:50]:
        print("  -", k)
    return 1 if changed else 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "freeze":
        freeze()
    elif cmd == "snapshot":
        snapshot()
    elif cmd == "corpus":
        corpus()
    elif cmd == "corpus-diff":
        sys.exit(corpus_diff())
    else:
        print(__doc__)
