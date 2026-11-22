import json
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest
import soundfile as sf

from video_creation._B_voice_generation.core import acoustic_evaluator as qa
from video_creation._B_voice_generation.core.script_parser import get_script_segments
from video_creation._B_voice_generation.voice.common.delivery import (
    continuous_narration, delivery_direction, roleplay_turn_direction, turn_intent,
)


def test_game_quote_and_option_pauses_keep_one_synthesis_chunk():
    quote = "Your friend texts: 'Good luck in your presentation! I believe in you.'"
    data = json.dumps({"challenge": f"{quote}\n\nA: Bad luck. [pause:0.26] B: Break a leg."})
    segments = get_script_segments("EG01", data, "English", narrator_only=True, merge_narration_paragraphs=True)
    assert len(segments) == 1
    assert segments[0]["speaker"] == "Narrator"
    clean = continuous_narration(segments[0]["text"])
    assert quote in clean
    assert "\n" not in clean and "[pause:" not in clean
    assert "B: Break a leg" in clean


def test_non_roleplay_dialogue_field_does_not_assign_a_character():
    segments = get_script_segments("EE01", '{"dialogue": "A friend: Take it easy."}', "English", narrator_only=True)
    assert {segment["speaker"] for segment in segments} == {"Narrator"}


def test_explicit_french_and_italian_emotions_get_distinct_directions():
    anxious = turn_intent("Ansioso", "natural")
    reassuring = turn_intent("Rassuré", "natural")
    assert anxious is not None and reassuring is not None and anxious != reassuring
    assert "esita" in delivery_direction("italian", "dialogue_part_1", False, anxious)
    assert "chaleur" in delivery_direction("french", "dialogue_part_1", False, reassuring)


def test_roleplay_reference_keeps_the_cast_when_an_acting_clip_is_missing(tmp_path):
    from video_creation._B_voice_generation.voice.types.roleplay.emotion import resolve_roleplay_turn_reference

    baseline = tmp_path / "cast_baseline.wav"
    frustrated = tmp_path / "cast_frustrated.wav"
    frustrated.touch()
    bank = Mock()
    bank.find_speaker_energy_variant.return_value = frustrated

    assert resolve_roleplay_turn_reference(baseline, "Frustrated", "What?!", "dialogue_part_1", bank) == frustrated
    bank.find_speaker_energy_variant.assert_called_once_with(baseline.name, "frustrated", open_swara_dir=None)
    frustrated.unlink()
    assert resolve_roleplay_turn_reference(baseline, "Frustrated", "What?!", "dialogue_part_1", bank) == baseline


@pytest.mark.parametrize(("language", "optimistic", "calm", "context_word"), [
    ("english", "Optimistic", "Calm", "React"),
    ("french", "Optimiste", "Calme", "Réagissez"),
    ("italian", "Ottimista", "Rilassato", "Reagisci"),
    ("spanish", "Optimista", "Tranquila", "Reacciona"),
])
def test_roleplay_direction_distinguishes_optimism_and_uses_localized_context(language, optimistic, calm, context_word):
    optimism = turn_intent(optimistic, "")
    reassurance = turn_intent(calm, "")
    assert optimism is not None and reassurance is not None and optimism != reassurance
    direction = roleplay_turn_direction(language, optimism, "First thought. [pause:0.28] Second thought.")
    assert context_word in direction
    assert "«First thought. Second thought.»" in direction
    assert context_word not in roleplay_turn_direction(language, optimism)


@pytest.mark.parametrize("language", ["english", "french", "italian", "spanish"])
def test_teaching_narrator_direction_varies_by_section(language):
    sections = ("hook", "discovery", "example", "explanation", "payoff")
    directions = {
        delivery_direction(language, section, True, None, video_type="expression")
        for section in sections
    }
    assert len(directions) == len(sections)


@pytest.mark.parametrize("language", ["english", "french", "italian", "spanish"])
def test_narrator_directions_keep_quiz_options_even_and_distinguish_the_formats(language):
    from video_creation._B_voice_generation.voice.common.delivery import GAME_CHALLENGE, NARRATOR

    def note(kind, section):
        return delivery_direction(language, section, True, None, video_type=kind)

    assert note("game", "challenge") == f"{GAME_CHALLENGE[language]} {NARRATOR[language][-1]}"
    assert len({note("game", part) for part in ("hook", "challenge", "pressure", "answer")}) == 4
    assert note("roleplay", "hook") != note("roleplay", "payoff")
    assert note("expression", "discovery") != note("fun_facts", "discovery")


def test_take_selection_prefers_passing_audio(tmp_path: Path):
    flagged = tmp_path / "flagged.flac"
    passing = tmp_path / "passing.flac"
    destination = tmp_path / "selected.flac"
    flagged.write_bytes(b"flagged")
    passing.write_bytes(b"passing")
    with patch.object(qa, "evaluate_voice_take", side_effect=[
        (0.95, False, ["register spike"], {"pitch_variance": 0.2, "cps": 13}),
        (0.75, True, [], {"pitch_variance": 0.1, "cps": 12}),
    ]):
        qa.select_best_general_candidate([flagged, passing], "A line", "english", destination)
    assert destination.read_bytes() == b"passing"


def test_window_register_flags_local_shift_against_cast_reference():
    sr = 24000
    duration = 3
    lower = np.sin(2 * np.pi * 200 * np.arange(sr * duration) / sr)
    upper = np.sin(2 * np.pi * 320 * np.arange(sr * duration) / sr)
    assert qa.max_window_pitch_shift(lower, sr, 200) < 1
    assert qa.max_window_pitch_shift(np.concatenate([lower, upper]), sr, 200) > 6



def test_preview_reference_cleanup_is_scoped_to_each_run(tmp_path):
    from test.tools.render_voice_preview import PreviewComfyClient, PreviewVoiceManager

    shared = tmp_path / "comfy-input"
    shared.mkdir()
    source = tmp_path / "voice.wav"
    source.write_bytes(b"reference used in test")
    first = PreviewVoiceManager(tmp_path, shared, casting_history_path=tmp_path / "first.json")
    second = PreviewVoiceManager(tmp_path, shared, casting_history_path=tmp_path / "second.json")
    one = first.prepare_voice_in_comfy(source)
    two = second.prepare_voice_in_comfy(source)
    assert one != two
    assert PreviewComfyClient.original_reference(one) == "voice.wav"
    first.cleanup_comfy_input()
    assert not (shared / one).exists()
    assert (shared / two).is_file()
    second.cleanup_comfy_input()
    assert source.is_file()


def test_short_acting_direction_reaches_the_comfy_workflow():
    from config import VOICE_WORKFLOW_PATH
    from video_creation._B_voice_generation.core.comfy_client import ComfyClient

    client = ComfyClient("http://127.0.0.1:8188", VOICE_WORKFLOW_PATH)
    instruction = "Répondez avec chaleur et posez la fin de la phrase."
    workflow = client._prepare_workflow(
        ref_audio_name="voice.wav", target_text="Ne t'inquiète pas.",
        language="french", gender="male", context="dialogue",
        emotion="calm", energy="medium", style="natural",
        output_prefix="voice-preview", seed=1, delivery_direction=instruction,
        use_icl=False,
    )
    assert workflow["39"]["inputs"]["instruct"] == instruction
    assert workflow["39"]["inputs"]["target_text"] == "Ne t'inquiète pas."

def test_voice_queue_preloads_one_take_and_cancels_only_pending_prompts(tmp_path):
    from config import VOICE_WORKFLOW_PATH
    from video_creation._B_voice_generation.core.comfy_client import ComfyClient

    client = ComfyClient("http://127.0.0.1:8188", VOICE_WORKFLOW_PATH)
    client.pool = None
    client._prepare_workflow = Mock(side_effect=lambda **inputs: inputs)
    events = []

    def queue(workflow):
        prompt_id = workflow["output_prefix"]
        events.append(("queue", prompt_id))
        return prompt_id

    def poll(prompt_id):
        events.append(("poll", prompt_id))
        if prompt_id == "take2":
            raise InterruptedError("Cancelled")
        return {}

    client.queue_prompt = queue
    client.poll_for_completion = poll
    client._save_completed_voice = lambda _, path: events.append(("save", path.stem))
    client._http_post = Mock()
    takes = [(tmp_path / f"take{i}.flac", {"output_prefix": f"take{i}"}) for i in range(1, 4)]

    with pytest.raises(InterruptedError):
        client.generate_voice_candidates(takes)
    assert events == [
        ("queue", "take1"), ("queue", "take2"), ("poll", "take1"), ("save", "take1"),
        ("queue", "take3"), ("poll", "take2"),
    ]
    assert [call.kwargs["json"] for call in client._http_post.call_args_list] == [
        {"delete": ["take2", "take3"]}, {"prompt_id": "take2"}, {"prompt_id": "take3"},
    ]


def test_voice_gate_ignores_edge_silence_but_flags_a_mid_line_freeze(tmp_path):
    sample_rate = 24000
    voiced = 0.2 * np.sin(2 * np.pi * 180 * np.arange(sample_rate) / sample_rate)
    quiet = np.zeros(sample_rate)
    edges = tmp_path / "edges.wav"
    internal = tmp_path / "internal.wav"
    sf.write(edges, np.concatenate((quiet, voiced, voiced, quiet)), sample_rate)
    sf.write(internal, np.concatenate((voiced, quiet, voiced)), sample_rate)

    for path, expected in [(edges, False), (internal, True)]:
        _, _, issues, _ = qa.evaluate_voice_take(path, "An example line of dialogue.", "english")
        assert any("Internal silence freeze" in issue for issue in issues) is expected
