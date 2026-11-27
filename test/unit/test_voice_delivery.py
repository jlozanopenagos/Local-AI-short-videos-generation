import json
from pathlib import Path
from unittest.mock import Mock, patch

# pyrefly: ignore[missing-import]
import numpy as np
# pyrefly: ignore[missing-import]
import pytest
# pyrefly: ignore[missing-import]
import soundfile as sf

# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core import acoustic_evaluator as qa
# pyrefly: ignore[missing-import]
from video_creation._B_voice_generation.core.script_parser import get_script_segments
# pyrefly: ignore[missing-import]
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
    # pyrefly: ignore[missing-import]
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
    # pyrefly: ignore[missing-import]
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
    # pyrefly: ignore[missing-import]
    from config import VOICE_WORKFLOW_PATH
    # pyrefly: ignore[missing-import]
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
    # pyrefly: ignore[missing-import]
    from config import VOICE_WORKFLOW_PATH
    # pyrefly: ignore[missing-import]
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

def test_automatic_narrator_casting_prefers_format_and_avoids_reviewed_extremes(tmp_path):
    from types import SimpleNamespace
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.common.casting import VoiceCastingEngine
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.languages import get_language_voice_profile

    def record(speaker_id, *archetypes):
        return (tmp_path / f"{speaker_id}.wav", speaker_id, 0, SimpleNamespace(
            speaker_id=speaker_id, archetypes=archetypes, accent="en_us_neutral",
        ))

    extreme = record("en_m_us_host_01", "energetic_host", "warm_narrator")
    hosts = [record("host1", "energetic_host"), record("host2", "energetic_host")]
    narrators = [record("narrator1", "warm_narrator"), record("narrator2", "warm_narrator")]
    engine = VoiceCastingEngine()
    with patch.object(engine, "_build_candidate_records", return_value=[extreme, *hosts, *narrators]) as pool:
        def choose(video_type):
            return engine.select_speaker_voice(
                open_swara_dir=tmp_path, language="english", gender="male", role="Narrator",
                video_type=video_type, all_paths=[], manifest=None, is_acceptable_fn=lambda *_: True,
                lang_profile=get_language_voice_profile("english"), used_identities=set(),
                used_filenames=set(), dialect_hint="en_us_neutral",
            )
        assert choose("game") == hosts[0][0]
        assert choose("fun_facts") == narrators[0][0]
        pool.return_value = [extreme]
        assert choose("fun_facts") == extreme[0]


def test_expanded_roleplay_intents_and_fallback_emotion_never_flatten():
    for label, expected_lang in [
        ("Angry", "english"),
        ("Scared", "english"),
        ("Shocked", "italian"),
        ("Grinning", "english"),
        ("Laughing", "english"),
        ("Excited", "english"),
        ("Enthousiaste", "french"),
        ("Confrontativo", "italian"),
        ("Agobiado", "spanish"),
        ("Deadpan", "spanish"),
    ]:
        intent = turn_intent(label, "")
        assert intent is not None, f"Missing intent for {label}"
        direction = roleplay_turn_direction(expected_lang, intent)
        assert direction and "everyday conversation" not in direction.lower()

    # Unknown custom emotion still uses explicit fallback emotion instead of warm conversational default
    custom = roleplay_turn_direction("english", None, fallback_emotion="melancholic")
    assert "melancholic" in custom.lower()


def test_roleplay_reference_falls_back_from_frustrated_to_surprised_urgent(tmp_path):
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.types.roleplay.emotion import resolve_roleplay_turn_reference

    baseline = tmp_path / "cast_baseline.wav"
    urgent = tmp_path / "cast_surprised_urgent.wav"
    urgent.touch()

    def lookup(name, tier, open_swara_dir=None):
        return urgent if tier == "surprised_urgent" else None

    bank = Mock()
    bank.find_speaker_energy_variant.side_effect = lookup
    assert resolve_roleplay_turn_reference(baseline, "Frustrated", "No way!", "dialogue_part_1", bank) == urgent


def test_game_casting_excludes_understated_intimate_and_low_narrators(tmp_path):
    from types import SimpleNamespace
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.common.casting import VoiceCastingEngine
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.languages import get_language_voice_profile

    def record(speaker_id, *archetypes):
        return (tmp_path / f"{speaker_id}.wav", speaker_id, 0, SimpleNamespace(
            speaker_id=speaker_id, archetypes=archetypes, accent="es_latam_neutral",
        ))

    understated = record("es_f_intimate_storyteller_09", "energetic_host", "warm_narrator")
    low_narr = record("es_f_narrator_low_07", "energetic_host", "warm_narrator")
    host = record("es_f_latam_host_01", "energetic_host", "warm_narrator")
    engine = VoiceCastingEngine()
    with patch.object(engine, "_build_candidate_records", return_value=[understated, low_narr, host]):
        chosen = engine.select_speaker_voice(
            open_swara_dir=tmp_path, language="spanish", gender="female", role="Narrator",
            video_type="game", all_paths=[], manifest=None, is_acceptable_fn=lambda *_: True,
            lang_profile=get_language_voice_profile("spanish"), used_identities=set(),
            used_filenames=set(), dialect_hint="es_latam_neutral",
        )
    assert chosen == host[0]


def test_sampling_caps_prevent_unstable_high_subtalker_temperature():
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.common.engine import compute_segment_sampling
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.languages import get_language_voice_profile
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.types import get_video_type_voice_profile

    for lang in ("english", "french", "italian", "spanish"):
        lp = get_language_voice_profile(lang)
        gp = get_video_type_voice_profile("game")
        s = compute_segment_sampling(lp, gp, "answer", False, {"has_question": True, "has_exclamation": True})
        assert s["temperature"] <= 0.85
        assert s["subtalker_temperature"] <= 0.80


def test_prepare_workflow_removes_sensevoice_node_when_xvector_or_ref_text_known():
    # pyrefly: ignore[missing-import]
    from config import VOICE_WORKFLOW_PATH
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.core.comfy_client import ComfyClient

    client = ComfyClient("http://127.0.0.1:8188", VOICE_WORKFLOW_PATH)
    wf_xvec = client._prepare_workflow(
        ref_audio_name="voice.wav", target_text="Hello there!",
        language="english", gender="female", context="dialogue",
        emotion="happy", energy="high", style="natural",
        output_prefix="test", seed=1, use_icl=False,
    )
    assert "40" not in wf_xvec
    assert wf_xvec["35"]["inputs"]["x_vector_only"] is True
    assert wf_xvec["35"]["inputs"]["ref_text"] == ""

    wf_icl = client._prepare_workflow(
        ref_audio_name="voice.wav", target_text="Hello there!",
        language="english", gender="female", context="narrator",
        emotion="warm", energy="high", style="natural",
        output_prefix="test", seed=1, use_icl=True, ref_text="Known reference transcript.",
    )
    assert "40" not in wf_icl
    assert wf_icl["35"]["inputs"]["x_vector_only"] is False
    assert wf_icl["35"]["inputs"]["ref_text"] == "Known reference transcript."


def test_calibrated_qa_gate_allows_payoff_breath_and_bright_female_ref(tmp_path):
    sr = 24000
    t = np.linspace(0, 1.2, int(sr * 1.2), endpoint=False)
    voiced = 0.25 * np.sin(2 * np.pi * np.cumsum(300.0 + 35.0 * np.sin(2 * np.pi * 3.5 * t)) / sr)
    breath = np.zeros(int(sr * 1.1))
    wav = tmp_path / "payoff_bright.wav"
    sf.write(wav, np.concatenate((voiced, breath, voiced)).astype(np.float32), sr)

    _, _, issues, _ = qa.evaluate_voice_take(
        wav,
        target_text="When the lights go up, knowing this saves you. Follow for more!",
        language="english",
        video_type="roleplay",
        section="payoff",
        reference_f0=285.0,
    )
    assert not any("Internal silence freeze" in i for i in issues)
    assert not any("Excessive shrillness" in i for i in issues)


def test_roleplay_multi_energy_enabled_and_dialogue_sampling_within_caps():
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.common.engine import compute_segment_sampling
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.languages import get_language_voice_profile
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.types import get_video_type_voice_profile

    rp = get_video_type_voice_profile("roleplay")
    assert rp.support_multi_energy_roles is True
    for lang in ("english", "french", "italian", "spanish"):
        lp = get_language_voice_profile(lang)
        samp = compute_segment_sampling(
            lp, rp, "dialogue_part_1", True, {"has_question": True, "has_exclamation": True},
        )
        assert samp["temperature"] <= 0.85
        assert samp["subtalker_temperature"] <= 0.80


def test_roleplay_variant_f0_drift_guard_rejects_outlier_and_falls_back(tmp_path):
    from types import SimpleNamespace
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.types.roleplay.emotion import resolve_roleplay_turn_reference

    baseline = tmp_path / "actor_baseline.wav"
    urgent = tmp_path / "actor_surprised_urgent.wav"
    high_e = tmp_path / "actor_high_energy.wav"
    for p in (baseline, urgent, high_e):
        p.touch()

    entries = {
        baseline.name: SimpleNamespace(f0_mean=130.0),
        urgent.name: SimpleNamespace(f0_mean=195.0),  # +7.0 ST (> 4.5 ST drift)
        high_e.name: SimpleNamespace(f0_mean=148.0),  # +2.2 ST (aligned)
    }

    bank = Mock()
    bank.find_entry_by_audio.side_effect = lambda name: entries.get(name)
    bank.find_speaker_energy_variant.side_effect = lambda _n, tier, open_swara_dir=None: {
        "surprised_urgent": urgent,
        "high_energy": high_e,
    }.get(tier)

    # First-choice surprised_urgent drifts > 4.5 ST -> falls back to aligned high_energy
    assert resolve_roleplay_turn_reference(baseline, "Shocked", "What?!", "dialogue_part_2", bank) == high_e

    # If fallback also drifts > 4.5 ST -> falls back to baseline
    entries[high_e.name] = SimpleNamespace(f0_mean=190.0)
    assert resolve_roleplay_turn_reference(baseline, "Shocked", "What?!", "dialogue_part_2", bank) == baseline


def test_casting_blends_roleplay_actors_for_narrator_and_keeps_single_actor_for_dialogue(tmp_path):
    from types import SimpleNamespace
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.common.casting import VoiceCastingEngine
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.languages import get_language_voice_profile

    def record(speaker_id, *archetypes):
        return (tmp_path / f"{speaker_id}.wav", speaker_id, 0, SimpleNamespace(
            speaker_id=speaker_id, archetypes=archetypes, accent="es_latam_neutral",
        ))

    dry_actor = record("es_m_roleplay_dry_06", "roleplay_actor")
    expressive_actor = record("es_m_roleplay_warm_06", "roleplay_actor")
    calm_narrator = record("es_m_narrator_conversational_08", "warm_narrator", "energetic_host")
    host_narrator = record("es_m_latam_host_01", "energetic_host")

    engine = VoiceCastingEngine()
    lp = get_language_voice_profile("spanish")

    # 1. Non-game Narrator blends expressive roleplay_actor + warm_narrator while excluding roleplay_dry
    with patch.object(
        engine, "_build_candidate_records",
        return_value=[dry_actor, expressive_actor, calm_narrator],
    ):
        chosen_narr = engine.select_speaker_voice(
            open_swara_dir=tmp_path, language="spanish", gender="male", role="Narrator",
            video_type="roleplay", all_paths=[], manifest=None, is_acceptable_fn=lambda *_: True,
            lang_profile=lp, used_identities={expressive_actor[1]},
            used_filenames={expressive_actor[0].name.lower()}, dialect_hint="es_latam_neutral",
        )
        # Never picks roleplay_dry or the actor already assigned to a character
        assert chosen_narr == calm_narrator[0]

        # When expressive_actor is NOT already used by a character, it's eligible for Narrator too
        chosen_exp_narr = engine.select_speaker_voice(
            open_swara_dir=tmp_path, language="spanish", gender="male", role="Narrator",
            video_type="expression", all_paths=[], manifest=None, is_acceptable_fn=lambda *_: True,
            lang_profile=lp, used_identities={calm_narrator[1]},
            used_filenames={calm_narrator[0].name.lower()}, dialect_hint="es_latam_neutral",
        )
        assert chosen_exp_narr == expressive_actor[0]

    # 2. Dialogue role keeps single remaining roleplay_actor instead of falling back to calm narrator
    #    and prefers an actor that has emotional variants in the manifest.
    actor_no_vars = record("es_m_latam_actor_no_var", "roleplay_actor")
    manifest = Mock()
    manifest.find_speaker_energy_variant.side_effect = lambda name, tier, open_swara_dir=None: (
        (tmp_path / f"{expressive_actor[1]}_{tier}.wav")
        if name == expressive_actor[0].name and tier == "surprised_urgent"
        else None
    )
    engine2 = VoiceCastingEngine()
    with patch.object(
        engine2, "_build_candidate_records",
        return_value=[calm_narrator, host_narrator, actor_no_vars, expressive_actor],
    ):
        chosen_char = engine2.select_speaker_voice(
            open_swara_dir=tmp_path, language="spanish", gender="male", role="PERSON_TWO",
            video_type="roleplay", all_paths=[], manifest=manifest, is_acceptable_fn=lambda *_: True,
            lang_profile=lp, used_identities=set(), used_filenames=set(),
            dialect_hint="es_latam_neutral", script_id="SR08",
        )
        assert chosen_char == expressive_actor[0]

        # Even if only actor_no_vars remains without emotional variants, it still beats calm_narrator
        chosen_single = engine2.select_speaker_voice(
            open_swara_dir=tmp_path, language="spanish", gender="male", role="PERSON_TWO",
            video_type="roleplay", all_paths=[], manifest=manifest, is_acceptable_fn=lambda *_: True,
            lang_profile=lp, used_identities={expressive_actor[1]},
            used_filenames={expressive_actor[0].name.lower()},
            dialect_hint="es_latam_neutral", script_id="SR08",
        )
        assert chosen_single == actor_no_vars[0]


def test_local_spanish_accent_rotation_is_exact_60_latam_40_castilian():
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.common.casting import pick_weighted_accent
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.languages import get_language_voice_profile

    lp = get_language_voice_profile("spanish")
    accents = [pick_weighted_accent(lp, script_id=f"SG{i:02d}") for i in range(1, 11)]
    assert accents.count("es_latam_neutral") == 6
    assert accents.count("es_spain_castilian") == 4


def test_game_and_fun_facts_narrator_casting_excludes_roleplay_actors_and_trims_high_impact(tmp_path):
    from types import SimpleNamespace
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.common.casting import VoiceCastingEngine
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.languages import get_language_voice_profile
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.types.fun_facts.profile import FUN_FACTS_VOICE_PROFILE
    # pyrefly: ignore[missing-import]
    from video_creation._B_voice_generation.voice.types.game.profile import GAME_VOICE_PROFILE

    assert GAME_VOICE_PROFILE.high_impact_sections == ("hook", "answer")
    assert FUN_FACTS_VOICE_PROFILE.high_impact_sections == ("hook",)

    def record(speaker_id, *archetypes):
        return (tmp_path / f"{speaker_id}.wav", speaker_id, 0, SimpleNamespace(
            speaker_id=speaker_id, archetypes=archetypes, accent="en_us_neutral",
        ))

    rp_warm = record("en_m_roleplay_warm_06", "roleplay_actor")
    rp_quick = record("en_f_roleplay_quick_05", "roleplay_actor")
    host = record("en_f_us_host_01", "energetic_host", "warm_narrator")
    narr = record("en_m_narrator_conversational_08", "warm_narrator", "energetic_host")

    engine = VoiceCastingEngine()
    lp = get_language_voice_profile("english")

    with patch.object(engine, "_build_candidate_records", return_value=[rp_warm, rp_quick, host, narr]):
        for vtype in ("game", "fun_facts"):
            chosen = engine.select_speaker_voice(
                open_swara_dir=tmp_path, language="english", gender="male", role="Narrator",
                video_type=vtype, all_paths=[], manifest=None, is_acceptable_fn=lambda *_: True,
                lang_profile=lp, used_identities=set(), used_filenames=set(),
                script_id="EG01", dialect_hint="en_us_neutral",
            )
            assert chosen in (host[0], narr[0])

    # Recasting off the only clean UK male voice must fall back to a clean US narrator,
    # NEVER the blacklisted en_m_intimate_storyteller_09.
    uk_good = (tmp_path / "en_m_uk_narrator_03.wav", "en_m_uk_narrator_03", 0, SimpleNamespace(
        speaker_id="en_m_uk_narrator_03", archetypes=("warm_narrator", "energetic_host"), accent="en_uk_neutral",
    ))
    uk_bad = (tmp_path / "en_m_intimate_storyteller_09.wav", "en_m_intimate_storyteller_09", 0, SimpleNamespace(
        speaker_id="en_m_intimate_storyteller_09", archetypes=("warm_narrator",), accent="en_uk_neutral",
    ))
    with patch.object(engine, "_build_candidate_records", return_value=[uk_good, uk_bad, narr]):
        recast_choice = engine.select_speaker_voice(
            open_swara_dir=tmp_path, language="english", gender="male", role="Narrator",
            video_type="fun_facts", all_paths=[], manifest=None, is_acceptable_fn=lambda *_: True,
            lang_profile=lp, used_identities=set(), used_filenames=set(),
            script_id="EF01", dialect_hint="en_uk_neutral",
            exclude_voices={"en_m_uk_narrator_03.wav"},
        )
        assert recast_choice == narr[0]

