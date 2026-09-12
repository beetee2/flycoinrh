"""Synthetic artifact tampering and budget checks; no neural model calls."""

from copy import deepcopy
from dataclasses import asdict
from io import StringIO
import json

from PIL import Image
import pytest

from flytrap.arena.core import build_arena, initial_state
from flytrap.arena.render import png_bytes, render
from flytrap.arena.sliding import step_sliding
from flytrap.contracts import ControllerOutput, Observation
from scripts.feasibility import overlay
from scripts.feasibility_final import CallBudget, coordinates, observe, schedule
from scripts.feasibility_final_motor import calibrate
from scripts.verify_feasibility import _challenge, _file_sha, _sha
from scripts.verify_feasibility_final import (
    _freeze, _real_regression, expected_schedule, verify, verify_trial, verify_trials,
)


@pytest.fixture
def fixture_artifacts(tmp_path):
    """Generate explicitly labeled fixture evidence with fixed prescribed rates."""
    def create(indices=(0,), *, full_schedule=False):
        selected = expected_schedule() if full_schedule else [expected_schedule()[index] for index in indices]
        ledger = []
        for trial in selected:
            directory = tmp_path / trial["id"]
            directory.mkdir()
            arena = build_arena(_challenge(trial["layout"]))
            raster = render(arena.scene)
            (directory / "canonical.gray").write_bytes(raster)
            (directory / "canonical.png").write_bytes(png_bytes(raster))
            state, rows = initial_state(), []
            for _ in range(trial["tick_limit"]):
                obs = observe(raster, state, trial["crop"], trial["input"])
                pixels = bytes(round(value * 255) for value in obs.pixels)
                hz = dict(steer_L=0.0, steer_R=0.0, fwd_L=0.0, fwd_R=0.0, back=450.0, stop=0.0)
                raw = ControllerOutput(schema_version="1", dx=0.0, dy=1.0, click=False, model_mode="fixture",
                    telemetry=dict(schema_version="1", sampled_neurons=0, spike_count=0, neural_ms=0.0))
                applied = calibrate(raw, hz, trial["motor"])
                after = step_sliding(arena, state, applied)
                xs, ys = coordinates(state, trial["crop"])
                rows.append(dict(before=asdict(state), after=asdict(after), action=applied.model_dump(),
                    raw_action=raw.model_dump(), motor_rates=hz, step_wall_seconds=0.001,
                    observation_pixels=list(pixels), observation_sha256=_sha(pixels),
                    sample_xs=xs, sample_ys=ys))
                ledger.append(dict(call=len(ledger) + 1, trial=trial["id"], tick=state.tick))
                if state.tick in (0, 16, 32, 55, 64, 128, 192, 255):
                    Image.frombytes("L", (16, 16), pixels).save(directory / f"input-{state.tick:03}.png")
                state = after
            (directory / "trace.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
            overlay(directory / "trajectory.png", raster, rows, "SYNTHETIC FIXTURE; NO NEURAL CALLS")
            trial.update(status="PASS", ticks=len(rows), final_state=asdict(state), outcome=state.outcome,
                         termination="terminal" if state.outcome else "diagnostic_cutoff",
                         elapsed_wall_seconds=1.0, trace_sha256=_file_sha(directory / "trace.jsonl"))
        (tmp_path / "calls.jsonl").write_text("".join(json.dumps(row) + "\n" for row in ledger))
        return selected, tmp_path
    return create


def test_frozen_schedule_and_attempt_budget():
    assert schedule() == expected_schedule()
    declared = expected_schedule()
    assert len(declared) == 14
    assert sum(trial["tick_limit"] for trial in declared) == 1984
    assert {trial["seed"] for trial in declared if trial["stage"] == "confirm"} == {51003, 51004}
    ledger = StringIO()
    budget = CallBudget(ledger, 2)
    budget.claim("first", 0)
    budget.claim("first", 1)
    with pytest.raises(RuntimeError, match="budget exhausted"):
        budget.claim("unexpected", 0)
    assert budget.calls == 2
    assert [json.loads(line) for line in ledger.getvalue().splitlines()] == [
        dict(call=1, trial="first", tick=0), dict(call=2, trial="first", tick=1)]


def test_all_scheduled_fixture_traces_replay_but_do_not_pass_real_gate(fixture_artifacts):
    trials, root = fixture_artifacts(full_schedule=True)
    result = verify_trials(trials, root, dict(trials=expected_schedule(), max_trial_calls=1984), require_real=False)
    assert result["trials"] == 14 and result["steps"] == 1984
    assert all(t["outcome"] is None for t in trials[:8])
    assert all(t["outcome"] == "trial_timeout" for t in trials[8:])
    with pytest.raises(ValueError, match="real/fixture"):
        verify_trial(trials[0], root)


@pytest.mark.parametrize("mutation", ["raw", "applied", "click", "telemetry", "rates", "nan_rate",
                                     "coordinates", "pixels", "hash", "before", "after", "runtime", "extra"])
def test_redigested_tampering_fails_independent_reconstruction(fixture_artifacts, mutation):
    trials, root = fixture_artifacts(indices=(4,))
    trial = trials[0]
    path = root / trial["id"] / "trace.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    row = rows[0]
    if mutation in ("raw", "applied"):
        row["raw_action" if mutation == "raw" else "action"]["dx"] = 0.9
    elif mutation == "click":
        row["action"]["click"] = True
    elif mutation == "telemetry":
        row["action"]["telemetry"]["spike_count"] = 1
    elif mutation in ("rates", "nan_rate"):
        row["motor_rates"]["back"] = 0 if mutation == "rates" else float("nan")
    elif mutation == "coordinates":
        row["sample_ys"][0] += 1
    elif mutation == "pixels":
        row["observation_pixels"][0] ^= 255
    elif mutation == "hash":
        row["observation_sha256"] = "0" * 64
    elif mutation in ("before", "after"):
        row[mutation]["x_q"] += 1
    elif mutation == "runtime":
        row["step_wall_seconds"] = -1
    else:
        rows.append(deepcopy(rows[-1]))
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    trial["trace_sha256"] = _file_sha(path)
    with pytest.raises(ValueError):
        verify_trial(trial, root, require_real=False)


@pytest.mark.parametrize("mutation", ["cutoff", "outcome", "ticks", "limit", "runtime", "digest",
                                     "missing_input", "input", "trajectory", "canonical", "premature"])
def test_summary_images_and_cutoff_labels_are_verified(fixture_artifacts, mutation):
    trials, root = fixture_artifacts(indices=(4,))
    trial = trials[0]
    directory = root / trial["id"]
    if mutation == "cutoff":
        trial["termination"] = "terminal"
    elif mutation == "outcome":
        trial["outcome"] = "trial_timeout"
    elif mutation == "ticks":
        trial["ticks"] -= 1
    elif mutation == "limit":
        trial["tick_limit"] = 256
    elif mutation == "runtime":
        trial["elapsed_wall_seconds"] = 0
    elif mutation == "digest":
        trial["trace_sha256"] = "0" * 64
    elif mutation == "missing_input":
        (directory / "input-000.png").unlink()
    elif mutation == "input":
        Image.new("L", (16, 16), 17).save(directory / "input-000.png")
    elif mutation == "trajectory":
        Image.new("RGB", (576, 666), "red").save(directory / "trajectory.png")
    elif mutation == "canonical":
        (directory / "canonical.gray").write_bytes(bytes(96 * 96))
    else:
        path = directory / "trace.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()][:-1]
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        trial.update(ticks=len(rows), final_state=rows[-1]["after"], trace_sha256=_file_sha(path))
    with pytest.raises((ValueError, OSError)):
        verify_trial(trial, root, require_real=False)


@pytest.mark.parametrize("mutation", ["missing", "order", "seed", "failed", "calibration", "ledger"])
def test_schedule_and_call_ledger_cannot_hide_changes(fixture_artifacts, mutation):
    trials, root = fixture_artifacts(full_schedule=True)
    config = dict(trials=expected_schedule(), max_trial_calls=1984)
    if mutation == "missing":
        trials.pop()
    elif mutation == "order":
        trials.reverse()
    elif mutation == "seed":
        trials[0]["seed"] += 1
    elif mutation == "failed":
        trials[0]["status"] = "FAIL"
    elif mutation == "calibration":
        trials[0]["motor"] = "dark_balance_v3"
    else:
        with (root / "calls.jsonl").open("a") as stream:
            stream.write(json.dumps(dict(call=1985, trial="unscheduled", tick=0)) + "\n")
    with pytest.raises(ValueError):
        verify_trials(trials, root, config, require_real=False)


def test_real_gate_fails_missing_and_fixture_reports(tmp_path):
    config = tmp_path / "config.json"
    config.write_text("{}")
    with pytest.raises(ValueError, match="missing"):
        verify(tmp_path, config)
    (tmp_path / "report.json").write_text(json.dumps(dict(fixture=True)))
    with pytest.raises(ValueError, match="Fixture"):
        verify(tmp_path, config)


@pytest.mark.parametrize("mutation", [None, "digest", "parameters", "calibration", "source", "calls",
                                     "early", "late", "timezone"])
def test_confirmation_freeze_is_bound_to_source_parameters_and_chronology(tmp_path, mutation):
    from pathlib import Path

    path = tmp_path / "confirmation-freeze.json"
    source = "scripts/feasibility_final_motor.py"
    calibration = {"synthetic_fixture_only": True, "weights": [0.5, 0.7]}
    freeze = dict(config_sha256="a" * 64, calibration=calibration, parameters_changed=False,
                  motor_source_sha256=_file_sha(Path(source)), completed_screening_calls=20,
                  frozen_utc="2026-09-12T00:00:01+00:00")
    report = dict(config_sha256="a" * 64, started_utc="2026-09-12T00:00:00+00:00",
                  finished_utc="2026-09-12T00:00:02+00:00", trials=[dict(stage="screen", ticks=20)],
                  source=dict(file_sha256={source: freeze["motor_source_sha256"]}))
    config = dict(calibration=deepcopy(calibration))
    if mutation == "parameters":
        freeze["parameters_changed"] = True
    elif mutation == "calibration":
        freeze["calibration"]["weights"][0] = 0.9
    elif mutation == "source":
        freeze["motor_source_sha256"] = "b" * 64
    elif mutation == "calls":
        freeze["completed_screening_calls"] = 19
    elif mutation == "early":
        freeze["frozen_utc"] = "2026-09-11T23:59:59+00:00"
    elif mutation == "late":
        freeze["frozen_utc"] = "2026-09-12T00:00:03+00:00"
    elif mutation == "timezone":
        freeze["frozen_utc"] = "2026-09-12T00:00:01"
    path.write_text(json.dumps(freeze))
    report["confirmation-freeze.json"] = "c" * 64 if mutation == "digest" else _file_sha(path)
    if mutation is None:
        _freeze(tmp_path, report, config)
    else:
        with pytest.raises(ValueError):
            _freeze(tmp_path, report, config)


@pytest.mark.parametrize("mutation", [None, "missing", "extra", "repeat", "fixture", "seed", "hash",
                                     "model", "failed", "retry", "xml"])
def test_four_call_regression_accounting_rejects_tampering(tmp_path, mutation):
    # These files are synthetic test inputs for the log parser, not real-model
    # evidence. The real gate also requires pinned graph and execution sources.
    provenance = dict(neurons=12, graph_sha256="a" * 64, annotations_sha256="b" * 64,
                      parameters={"dt": 0.2}, calibration={"gain": 1.0}, model_source_sha256={},
                      neural_state_mode="windowed_reset", gains="all-one-float32", learning_enabled=False)
    header = dict(gate="real_adapter", fixture=False, provenance=deepcopy(provenance))
    rows = []
    observations = [Observation(schema_version="1", pixels=[0.0] * 256),
                    Observation(schema_version="1", pixels=[float((x // 2 + y // 2) % 2)
                                                            for y in range(16) for x in range(16)])]
    for repetition, index in ((0, 0), (0, 1), (1, 0), (1, 1)):
        output = ControllerOutput(schema_version="1", dx=0.0, dy=0.0, click=False, model_mode="windowed_reset",
                                  telemetry=dict(schema_version="1", sampled_neurons=12,
                                                 neural_ms=20.0, spike_count=1))
        rows.append(dict(gate="real_adapter_window", fixture=False, repetition=repetition, step_index=index,
                         run_seed=20260911, observation_sha256=_sha(observations[index].model_dump_json().encode()),
                         output_sha256=_sha(output.model_dump_json().encode()), output=output.model_dump(),
                         wall_seconds=0.1))
    commands = [dict(name="real-adapter", exit_code=0, elapsed_seconds=1.0,
                     argv=["make", "test-controller-real"], started_utc="2026-09-12T00:00:01+00:00")]
    if mutation == "missing":
        rows.pop()
    elif mutation == "extra":
        rows.append(deepcopy(rows[-1]))
    elif mutation == "repeat":
        rows[2]["output"]["dx"] = 0.5
        rows[2]["output_sha256"] = _sha(ControllerOutput.model_validate(rows[2]["output"]).model_dump_json().encode())
    elif mutation == "fixture":
        rows[0]["fixture"] = True
    elif mutation == "seed":
        rows[0]["run_seed"] += 1
    elif mutation == "hash":
        rows[0]["output_sha256"] = "c" * 64
    elif mutation == "model":
        header["provenance"]["parameters"]["dt"] = 0.1
    elif mutation == "failed":
        commands[0]["exit_code"] = 1
    elif mutation == "retry":
        commands.append(deepcopy(commands[0]))
    (tmp_path / "real-adapter.stdout.log").write_text("\n".join(json.dumps(row) for row in [header, *rows]))
    (tmp_path / "commands.jsonl").write_text("\n".join(json.dumps(row) for row in commands))
    failures = 1 if mutation == "xml" else 0
    (tmp_path / "real-controller.xml").write_text(
        f'<testsuites><testsuite tests="1" failures="{failures}" errors="0" skipped="0"/></testsuites>')
    if mutation is None:
        assert _real_regression(tmp_path, provenance, "2026-09-12T00:00:00+00:00") == 4
    else:
        with pytest.raises(ValueError):
            _real_regression(tmp_path, provenance, "2026-09-12T00:00:00+00:00")
