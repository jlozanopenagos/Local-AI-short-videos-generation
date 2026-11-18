"""
test/image_prompt_harness.py — Offline capture harness for Stage C (image prompt) builders.

Purpose (Phase 0 of the image-workflow split):
    Record the EXACT messages sent to the local LLM (system + user) and the final sanitized
    prompts, using a fake LLM client. No llama-server, no ComfyUI, no GPU, no network.

    Because the harness only touches public/used entry points (`ensure_image_prompts_for_script`,
    `VisualPromptBuilder.build_visual_prompt`, `resolve_anchor_environment`,
    `extract_or_build_character_anchors`, `sanitize_and_style_prompt`), it keeps working
    unchanged while the internals are refactored. Snapshots must stay byte-identical in
    Phases 0-2.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest import mock

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
MAIN_DIR = REPO_ROOT / "main"
VIDEO_CREATION_DIR = MAIN_DIR / "video_creation"
for _p in (str(REPO_ROOT), str(MAIN_DIR), str(VIDEO_CREATION_DIR), str(MAIN_DIR / "core"), str(TEST_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

FIXTURE_DIR = TEST_DIR / "fixtures" / "image_prompts"
STATES_DIR = FIXTURE_DIR / "states"
SNAPSHOT_DIR = FIXTURE_DIR / "snapshots"
CORPUS_BASELINE = FIXTURE_DIR / "corpus_baseline.json"

GOLDEN_IDS = [
    "EF01", "EE01", "EG01", "ER01",
    "FF04", "FE01", "FG01", "FR01",
    "IF01", "IE01", "IG01", "IR01",
    "SF01", "SE01", "SG01", "SR01",
]

# Adversarial text covering every sanitizer pass (text bans, quotes, ages, hair, garments,
# gift boxes, eye triggers, proportions, speech verbs, letter mentions).
SANITIZER_PROBES = [
    "A young man whispering the words break a leg to a young woman, aha! 'project' wow.",
    "A 12-year-old kid and an adult in a bakery holding a sign with big letters, saying hello there.",
    "The boy with his hair tied in a sleek bun wearing a bodice and skirt, girl with a quiff.",
    "A large ornate ribbon-wrapped gift box and a stack of ornate gift boxes on the counter.",
    "Tall slender proportions, tall slender build, conspiratorial glance, arched eyebrow, big puzzled eyes.",
    "A scroll that reveals the phrase anno and ano, the letter N, double N, pronunciation of fatto.",
    "He shouts « Bonjour » and \u201cHola\u201d reading the words on a poster showing text; casual clothes, normal clothing.",
    "Clean modern 2D cartoon narrative illustration already styled (high-school student protagonist, thematic costume, ok).",
    "",
]

_CANNED_SCENE_TEXT = (
    "A young man whispering the words break a leg beside a ribbon-wrapped gift box, "
    "tall slender proportions, arched eyebrow, 'aha' moment, 12-year-old kid watching."
)


def sha(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


class _FakeStream:
    def __init__(self, text: str):
        self._text = text

    def __iter__(self):
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=self._text))])

    def close(self):
        pass


class FakeLLM:
    """Records every chat completion call and answers deterministically by call kind."""

    def __init__(self, scene_names: List[str] | None = None):
        self.calls: List[Dict[str, str]] = []
        self.scene_names = scene_names or []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.base_url = "http://fake/v1"
        self.api_key = "fake"

    @staticmethod
    def classify(system: str) -> str:
        if "Lead Visual Storyboard Director" in system:
            return "storyboard"
        if "overarching General Visual Prompt" in system:
            return "general"
        return "single"

    def _create(self, model=None, messages=None, **kwargs):
        system = messages[0]["content"]
        user = messages[1]["content"]
        kind = self.classify(system)
        self.calls.append({"kind": kind, "system": system, "user": user})
        if kind == "storyboard":
            names = self.scene_names or ["hook"]
            payload = {n: f"{n}: {_CANNED_SCENE_TEXT}" for n in names}
            return _FakeStream(json.dumps(payload))
        if kind == "general":
            return _FakeStream(
                "A warm authentic setting. Left: a 15-year-old high-school student girl with fair peach skin, "
                "dark brown cartoon eyes, dark hair in a ponytail, wearing an emerald vest. Right: a 15-year-old "
                "high-school student boy with warm tan skin, short dark hair, wearing a denim vest."
            )
        return _FakeStream(_CANNED_SCENE_TEXT)


def make_builder(llm: FakeLLM):
    from _C_image_generation.core.prompt_builder import VisualPromptBuilder

    builder = VisualPromptBuilder(api_base_url="http://fake/v1", api_key="fake", model_name="fake")
    builder._client = llm
    return builder


class _NullStateManager:
    def save_script_state(self, *_a, **_k):
        return None


def load_state(script_id: str) -> Dict[str, Any]:
    return json.loads((STATES_DIR / f"script_{script_id}.json").read_text(encoding="utf-8"))


def _scene_names_for(state: Dict[str, Any]) -> List[str]:
    from _B_voice_generation.core.script_parser import parse_sections
    from _C_image_generation import main as c_main  # noqa: F401  (ensures path setup)

    sections = parse_sections(state.get("script_text", ""))
    return [k.strip().lower() for k in sections.keys()]


def capture_script(state: Dict[str, Any], *, include_single_scene: bool = True) -> Dict[str, Any]:
    """Run the real pipeline entry points against a fake LLM and return everything observed."""
    import copy

    from _B_voice_generation.core.script_parser import parse_sections
    from _C_image_generation import main as c_main
    from _C_image_generation.core import prompt_builder as pb

    state = copy.deepcopy(state)
    script_id = state["id"]
    sections = parse_sections(state.get("script_text", ""))
    names = [k.strip().lower() for k in sections.keys()]
    llm = FakeLLM(scene_names=names)
    builder = make_builder(llm)
    result: Dict[str, Any] = {"script_id": script_id, "calls": [], "outputs": {}}

    with mock.patch.object(c_main, "ensure_llama_running", lambda *a, **k: None), \
         mock.patch("time.sleep", lambda *_a, **_k: None):
        # 1. Full pipeline path: general prompt (if absent) -> storyboard (force)
        c_main.ensure_image_prompts_for_script(
            script_data=state, state_manager=_NullStateManager(), prompt_builder=builder, force=True,
        )
        result["outputs"]["general_prompt"] = state.get("assets", {}).get("general_prompt", "")
        result["outputs"]["image_prompts"] = dict(state.get("assets", {}).get("image_prompts", {}))
        result["outputs"]["anchor_environment"] = state.get("content_metadata", {}).get("anchor_environment", "")

        # 2. Per-scene fallback path (build_visual_prompt) for every real scene
        if include_single_scene:
            gp = state.get("assets", {}).get("general_prompt", "")
            meta = state.get("metadata", {})
            resolved_lang, resolved_type = c_main.resolve_lang_and_type(script_id, state)
            label = meta.get("LABEL") or resolved_lang
            vt = (
                state.get("content_metadata", {}).get("video_type")
                or state.get("prompt_params", {}).get("VIDEO_TYPE")
                or meta.get("VIDEO_TYPE")
                or resolved_type
                or "EXPRESSION"
            ).upper()
            for sec_name, sec_text in sections.items():
                if not sec_text.strip() or sec_name.strip().lower() in ("title",):
                    continue
                out = builder.build_visual_prompt(
                    script_text=state.get("script_text", ""),
                    label=label,
                    scene_name=sec_name,
                    scene_text=sec_text,
                    script_id=script_id,
                    speakers_gender=state.get("content_metadata", {}).get("speakers_gender", {}),
                    video_type=vt,
                    general_prompt=gp,
                    existing_scene_prompts=dict(result["outputs"]["image_prompts"]),
                )
                result["outputs"].setdefault("single_scene", {})[sec_name] = out

        # 3. Pure helpers
        anchors = pb.extract_or_build_character_anchors(
            general_prompt=state.get("assets", {}).get("general_prompt", ""),
            speakers_gender=state.get("content_metadata", {}).get("speakers_gender", {}),
            video_type=(state.get("content_metadata", {}).get("video_type") or "EXPRESSION"),
            character_anchors=state.get("content_metadata", {}).get("character_anchors"),
        )
        result["outputs"]["character_anchors"] = anchors

    result["calls"] = llm.calls

    # 4. Same pipeline WITHOUT a stored general prompt -> exercises build_general_prompt
    #    (local-LLM general prompt generator) followed by the storyboard.
    state_nogp = copy.deepcopy(state)
    state_nogp.setdefault("assets", {}).pop("general_prompt", None)
    state_nogp["assets"].pop("image_prompts", None)
    llm2 = FakeLLM(scene_names=names)
    builder2 = make_builder(llm2)
    with mock.patch.object(c_main, "ensure_llama_running", lambda *a, **k: None), \
         mock.patch("time.sleep", lambda *_a, **_k: None):
        c_main.ensure_image_prompts_for_script(
            script_data=state_nogp, state_manager=_NullStateManager(), prompt_builder=builder2, force=True,
        )
    result["calls_no_gp"] = llm2.calls
    result["outputs_no_gp"] = {
        "general_prompt": state_nogp.get("assets", {}).get("general_prompt", ""),
        "image_prompts": dict(state_nogp.get("assets", {}).get("image_prompts", {})),
    }
    return result


def capture_sanitizer() -> Dict[str, str]:
    """Single and double application (production applies it twice: storyboard, then process_script)."""
    from _C_image_generation.core.prompt_builder import sanitize_and_style_prompt

    out: Dict[str, str] = {}
    for probe in SANITIZER_PROBES:
        once = sanitize_and_style_prompt(probe)
        out[f"ONCE::{probe}"] = once
        out[f"TWICE::{probe}"] = sanitize_and_style_prompt(once)
    return out


def capture_environment_cases() -> Dict[str, str]:
    from _C_image_generation.core.prompt_builder import resolve_anchor_environment

    cases = {
        "scenario_bakery": dict(script_text="x", scenario="at a bakery counter"),
        "heteronym_record": dict(script_text="x", topic="record"),
        "idiom_cake": dict(script_text="it was a piece of cake", topic="piece of cake"),
        "idiom_leg": dict(script_text="break a leg tonight", topic="break a leg"),
        "kw_airport": dict(script_text="we missed the flight at the airport"),
        "kw_gym": dict(script_text="workout at the gym"),
        "fallback": dict(script_text="hello"),
        "es_idiom": dict(script_text="pan comido", topic="pan comido"),
        "fr_idiom": dict(script_text="poser un lapin", topic="poser un lapin"),
        "it_idiom": dict(script_text="in bocca al lupo", topic="in bocca al lupo"),
    }
    return {k: resolve_anchor_environment(**v) for k, v in cases.items()}


def condense(captured: Dict[str, Any], system_store: Dict[str, str]) -> Dict[str, Any]:
    """Store system prompts once (by hash) to keep snapshots small and diffable."""
    out = {"script_id": captured["script_id"], "outputs": captured["outputs"], "calls": []}
    for c in captured["calls"]:
        h = sha(c["system"])
        system_store[h] = c["system"]
        out["calls"].append({"kind": c["kind"], "system_sha": h, "user": c["user"]})
    out["outputs_no_gp"] = captured.get("outputs_no_gp", {})
    out["calls_no_gp"] = []
    for c in captured.get("calls_no_gp", []):
        h = sha(c["system"])
        system_store[h] = c["system"]
        out["calls_no_gp"].append({"kind": c["kind"], "system_sha": h, "user": c["user"]})
    return out
