"""Labeled synthetic artifacts exercise verifier mechanics, never its real gate."""

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json

from PIL import Image
import pytest

from flytrap.arena.core import build_arena, initial_state, step
from flytrap.arena.render import observation, png_bytes, render
from flytrap.contracts import ControllerOutput, create_challenge
from scripts.feasibility_analysis import summarize_trace
from scripts.verify_feasibility import verify_experiment, verify_probes, verify_trial, verify_trials


def sha(value):
    return hashlib.sha256(value).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False) + "\n")


def action(dx=0.0, dy=0.0):
    return ControllerOutput(schema_version="1", dx=dx, dy=dy, click=False, model_mode="fixture",
                            telemetry=dict(schema_version="1", sampled_neurons=0, spike_count=0, neural_ms=0.0))


@pytest.fixture
def fixture_trial(tmp_path):
    """Scripted fixture path with explicit half scaling to the left pad."""
    challenge = create_challenge(dict(schema_version="1", preset_version="two_choice_v1",
        renderer_version="grayscale_v1", destination_side="left", left_texture="stripes",
        right_texture="checkerboard", distractions=[]))
    arena = build_arena(challenge)
    raster = render(arena.scene)
    trial_id = "dev-7-fixture"
    directory = tmp_path / trial_id
    directory.mkdir()
    (directory / "canonical.gray").write_bytes(raster)
    (directory / "canonical.png").write_bytes(png_bytes(raster))
    state, rows = initial_state(), []
    for dx, dy in [(-1.0, 0.0)] * 6 + [(0.0, -1.0)] * 12:
        raw, applied = action(dx, dy), action(dx / 2, dy / 2)
        after = step(arena, state, applied)
        pixels = bytes(round(v * 255) for v in observation(raster, x_q=state.x_q, y_q=state.y_q).pixels)
        rows.append(dict(before=asdict(state), after=asdict(after), raw_action=raw.model_dump(),
                         action=applied.model_dump(), step_wall_seconds=0.25, observation_sha256=sha(pixels)))
        state = after
        if state.outcome:
            break
    trial = dict(trial_id=trial_id, seed=7, fixture=True,
                 label="SCRIPTED FIXTURE — NOT REAL MODEL", challenge=challenge.model_dump(),
                 condition=dict(id="fixture", destination_side="left", input="canonical", motor_multiplier=0.5),
                 frame_sha256=sha(raster), final_state=asdict(state), elapsed_wall_seconds=10.0,
                 summary=summarize_trace(rows))
    persist_trial(tmp_path, trial, rows)
    return tmp_path, trial, rows


def persist_trial(output, trial, rows):
    directory = output / trial["trial_id"]
    payload = b"".join((json.dumps(row) + "\n").encode() for row in rows)
    (directory / "trace.jsonl").write_bytes(payload)
    trial["trace_sha256"] = sha(payload)
    save(directory / "trial.json", trial)


def test_fixture_trial_replays_with_explicit_mechanics_mode(fixture_trial):
    output, trial, rows = fixture_trial
    assert verify_trial(trial, output, require_real=False) == len(rows)
    assert trial["final_state"]["outcome"] == "success"


def test_real_trial_verification_rejects_fixture_actions(fixture_trial):
    output, trial, _ = fixture_trial
    with pytest.raises(ValueError, match="Fixture action"):
        verify_trial(trial, output)


@pytest.mark.parametrize("mutation, message", [
    ("physics", "physics"), ("raw_action", "scaling"), ("observation", "observation"),
    ("summary", "summary"), ("final", "Final state"), ("incomplete", "Incomplete"),
    ("frame", "Frame hash"), ("elapsed", "wall time"),
])
def test_tampering_fails_even_after_trace_digest_is_recomputed(fixture_trial, mutation, message):
    output, trial, rows = fixture_trial
    if mutation == "physics":
        rows[0]["after"]["x_q"] += 1
    elif mutation == "raw_action":
        rows[0]["raw_action"]["dx"] = -0.5
    elif mutation == "observation":
        rows[0]["observation_sha256"] = "0" * 64
    elif mutation == "summary":
        trial["summary"]["motor_nonzero_fraction"] = 0
    elif mutation == "final":
        trial["final_state"]["outcome"] = "wrong_pad"
    elif mutation == "incomplete":
        rows.pop()
    elif mutation == "frame":
        trial["frame_sha256"] = "0" * 64
    elif mutation == "elapsed":
        trial["elapsed_wall_seconds"] = 0.1
    persist_trial(output, trial, rows)
    with pytest.raises(ValueError, match=message):
        verify_trial(trial, output, require_real=False)


@pytest.mark.parametrize("filename", ["canonical.gray", "canonical.png", "trace.jsonl", "trial.json"])
def test_missing_artifact_is_not_accepted(fixture_trial, filename):
    output, trial, _ = fixture_trial
    (output / trial["trial_id"] / filename).unlink()
    with pytest.raises(FileNotFoundError):
        verify_trial(trial, output, require_real=False)


def test_truncated_trace_hash_is_rejected(fixture_trial):
    output, trial, _ = fixture_trial
    path = output / trial["trial_id"] / "trace.jsonl"
    path.write_bytes(path.read_bytes()[:-5])
    with pytest.raises(ValueError, match="Trace hash"):
        verify_trial(trial, output, require_real=False)


def test_blank_control_hash_uses_explicit_dark_pixels(fixture_trial):
    output, trial, rows = fixture_trial
    trial["condition"]["input"] = "dark"
    for row in rows:
        row["observation_sha256"] = sha(bytes(256))
    trial["summary"] = summarize_trace(rows)
    persist_trial(output, trial, rows)
    assert verify_trial(trial, output, require_real=False) == len(rows)
    rows[0]["observation_sha256"] = sha(bytes([128]) * 256)
    persist_trial(output, trial, rows)
    with pytest.raises(ValueError, match="observation"):
        verify_trial(trial, output, require_real=False)


@pytest.fixture
def fixture_probes(tmp_path):
    config = dict(seeds=[7, 11], probe_conditions=["dark", "bright"], probe_repetitions=2)
    probes = []
    for seed in config["seeds"]:
        for condition in config["probe_conditions"]:
            pixels = bytes([0 if condition == "dark" else 255]) * 256
            Image.frombytes("L", (16, 16), pixels).save(tmp_path / f"probe-{condition}.png")
            probes.append(dict(seed=seed, condition=condition, step_index=0, fixture=True,
                               observation_sha256=sha(pixels), action=action().model_dump(),
                               repetitions=[dict(repetition=i, step_wall_seconds=0.1,
                                                 action=action().model_dump()) for i in range(2)]))
    return tmp_path, config, probes


def test_all_probe_repetitions_counted(fixture_probes):
    output, config, probes = fixture_probes
    result = verify_probes(probes, config, output, require_real=False)
    assert result["probes"] == 4
    assert result["probe_controller_calls"] == 8


def test_repetition_signed_zero_difference_fails_serialized_equality(fixture_probes):
    output, config, probes = fixture_probes
    probes[0]["repetitions"][1]["action"]["dx"] = -0.0
    with pytest.raises(ValueError, match="Repeated probe action"):
        verify_probes(probes, config, output, require_real=False)


@pytest.mark.parametrize("mutation, message", [
    ("missing", "Missing scheduled"), ("duplicate", "duplicate"), ("repetition", "Missing probe repetition"),
    ("mismatch", "Repeated probe action"), ("index", "first reset"), ("hash", "observation hash"),
    ("order", "repetition order"), ("seed", "Unexpected"),
])
def test_probe_corruption_cannot_hide_failures(fixture_probes, mutation, message):
    output, config, probes = fixture_probes
    if mutation == "missing":
        probes.pop()
    elif mutation == "duplicate":
        probes.append(deepcopy(probes[0]))
    elif mutation == "repetition":
        probes[0]["repetitions"].pop()
    elif mutation == "mismatch":
        probes[0]["repetitions"][1]["action"]["dx"] = 0.1
    elif mutation == "index":
        probes[0]["step_index"] = 1
    elif mutation == "hash":
        probes[0]["observation_sha256"] = "0" * 64
    elif mutation == "order":
        probes[0]["repetitions"].reverse()
    elif mutation == "seed":
        probes[0]["seed"] = 999
    with pytest.raises(ValueError, match=message):
        verify_probes(probes, config, output, require_real=False)


def test_real_probe_verification_rejects_fixture_actions(fixture_probes):
    output, config, probes = fixture_probes
    with pytest.raises(ValueError, match="Fixture action"):
        verify_probes(probes, config, output)


@pytest.mark.parametrize("expected", [dict(sampled_neurons=1, neural_ms=0), dict(sampled_neurons=0, neural_ms=20)])
def test_probe_telemetry_must_match_recorded_model(fixture_probes, expected):
    output, config, probes = fixture_probes
    with pytest.raises(ValueError, match="Neural telemetry"):
        verify_probes(probes, config, output, require_real=False, expected_telemetry=expected)


@pytest.mark.parametrize("expected", [dict(sampled_neurons=1, neural_ms=0), dict(sampled_neurons=0, neural_ms=20)])
def test_episode_telemetry_must_match_recorded_model(fixture_trial, expected):
    output, trial, _ = fixture_trial
    with pytest.raises(ValueError, match="Neural telemetry"):
        verify_trial(trial, output, require_real=False, expected_telemetry=expected)


def test_complete_fixture_schedule_is_counted(fixture_trial):
    output, trial, rows = fixture_trial
    config = dict(seeds=[7], episode_conditions=[trial["condition"]])
    assert verify_trials([trial], config, output, require_real=False) == dict(trials=1, replayed_steps=len(rows))


@pytest.mark.parametrize("mutation, message", [
    ("missing", "Missing scheduled"), ("duplicate", "duplicate episode"),
    ("schedule_duplicate", "Duplicate scheduled"), ("seed", "condition/seed"),
    ("scaling", "condition/seed"),
])
def test_episode_schedule_cannot_drop_or_substitute_trials(fixture_trial, mutation, message):
    output, trial, _ = fixture_trial
    config = dict(seeds=[7], episode_conditions=[deepcopy(trial["condition"])])
    trials = [trial]
    if mutation == "missing":
        trials = []
    elif mutation == "duplicate":
        trials.append(deepcopy(trial))
    elif mutation == "schedule_duplicate":
        config["seeds"].append(7)
    elif mutation == "seed":
        trial["seed"] = 8
    elif mutation == "scaling":
        trial["condition"]["motor_multiplier"] = 1.0
    with pytest.raises(ValueError, match=message):
        verify_trials(trials, config, output, require_real=False)


def test_real_gate_rejects_fixture_manifest_before_examining_other_artifacts(tmp_path):
    save(tmp_path / "report.json", dict(fixture=True, automated_status="PASS"))
    with pytest.raises(ValueError, match="Fixture manifest cannot pass"):
        verify_experiment(tmp_path)


@pytest.mark.parametrize("status", ["RUNNING", "FAIL", "BLOCKED"])
def test_real_gate_rejects_partial_or_failed_reports(tmp_path, status):
    save(tmp_path / "report.json", dict(fixture=False, schema_version="flytrap-feasibility-1",
                                       automated_status=status))
    with pytest.raises(ValueError, match="not a completed"):
        verify_experiment(tmp_path)
