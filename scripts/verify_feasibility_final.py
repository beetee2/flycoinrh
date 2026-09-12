"""Replay the final bounded experiment without additional neural calls."""

import argparse
from dataclasses import asdict
from datetime import datetime
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from flytrap.arena.core import build_arena, initial_state
from flytrap.arena.render import render
from flytrap.arena.sliding import step_sliding
from flytrap.contracts import ControllerOutput, Observation
from scripts.feasibility_final_motor import calibration_basis
from scripts.verify_feasibility import _challenge, _file_sha, _json, _png, _require, _sha
from scripts.verify_feasibility_revision import (
    SOURCE_DEPENDENCIES as REVISION_DEPENDENCIES,
    _finite, _motor, _preregistration, _provenance, _sources, _trajectory,
)

ROOT = Path("artifacts/milestones/05/final-sensorimotor")
CONFIG = Path("experiments/feasibility-final-v3.json")
PLAN = Path("docs/implementation/FEASIBILITY-05-FINAL-PLAN.md")
SOURCE_DEPENDENCIES = (*REVISION_DEPENDENCIES, "scripts/feasibility_final.py",
                       "scripts/feasibility_final_motor.py", "flytrap/arena/tracking.py",
                       "tests/real_model/test_real_adapter.py", "Makefile")
SNAPSHOTS = (0, 16, 32, 55, 64, 128, 192, 255)


def expected_schedule():
    """Independent declaration of all 14 fixed conditions and their order."""
    conditions = []
    for crop, mapping in (("crop16_v1", "upstream_pilot_v1"),
                          ("tracking16_v3", "upstream_pilot_v1"),
                          ("tracking16_v3", "dark_balance_v3")):
        for side in ("left", "right"):
            conditions.append(("screen", 51001, crop, mapping, side, "canonical", 56))
    for mapping in ("upstream_pilot_v1", "dark_balance_v3"):
        conditions.append(("screen", 51001, "tracking16_v3", mapping, "left", "dark", 56))
    for seed in (51003, 51004):
        for side, kind in (("left", "canonical"), ("right", "canonical"), ("left", "dark")):
            conditions.append(("confirm", seed, "tracking16_v3", "dark_balance_v3", side, kind, 256))
    return [dict(id=f"{stage}-{seed}-{crop}-{mapping}-{side}-{kind}", stage=stage,
                 seed=seed, crop=crop, motor=mapping, layout=side, input=kind,
                 physics="tangent_v2", tick_limit=limit)
            for stage, seed, crop, mapping, side, kind, limit in conditions]


def _coordinates(state, crop):
    _require(crop in ("crop16_v1", "tracking16_v3"), "Unknown observation version")
    coordinates = []
    for position in (state.x_q, state.y_q):
        if crop == "tracking16_v3":
            # floor(integer + rational) = integer + floor(rational). This uses
            # the preregistered camera equation without calling the candidate.
            offset = (position - 12288) // 1024
            axis = [min(95, max(0, 3 + 6 * i + offset)) for i in range(16)]
        else:
            axis = [min(95, max(0, position // 256 - 60 + 8 * i)) for i in range(16)]
        coordinates.append(axis)
    return coordinates


def _calibrated(raw, applied, rates, version):
    expected = raw.model_dump()
    if version == "dark_balance_v3":
        turn = (rates["steer_R"] - (782 / 815) * rates["steer_L"]) / 450
        forward = (rates["fwd_L"] + rates["fwd_R"]) / 2
        net = max(-1, min(1, (forward - (730 / 1341) * rates["back"]) / 450))
        expected.update(dx=max(-1, min(1, turn)), dy=-net * (1 - min(1, rates["stop"] / 450)))
    else:
        _require(version == "upstream_pilot_v1", "Unknown motor version")
    for key in ("dx", "dy"):
        _require(math.isclose(getattr(applied, key), expected.pop(key), rel_tol=0, abs_tol=1e-15),
                 "Applied motor calibration mismatch")
    _require(all(applied.model_dump()[key] == value for key, value in expected.items()),
             "Calibration changed upstream click or telemetry")


def verify_trial(trial, output, *, require_real=True, provenance=None):
    _require(trial["physics"] == "tangent_v2", "Unknown physics version")
    _require(trial["input"] in ("canonical", "dark"), "Unknown input condition")
    _require(trial["stage"] in ("screen", "confirm") and
             trial["tick_limit"] == (56 if trial["stage"] == "screen" else 256), "Invalid trial limit")
    expected_id = (f"{trial['stage']}-{trial['seed']}-{trial['crop']}-{trial['motor']}-"
                   f"{trial['layout']}-{trial['input']}")
    _require(trial["id"] == expected_id and trial["status"] == "PASS", "Trial failed or identifier mismatch")
    directory = Path(output) / expected_id
    arena = build_arena(_challenge(trial["layout"]))
    raster = render(arena.scene)
    _require((directory / "canonical.gray").read_bytes() == raster, "Canonical raster mismatch")
    _png(directory / "canonical.png", raster, (96, 96))
    payload = (directory / "trace.jsonl").read_bytes()
    _require(_sha(payload) == trial["trace_sha256"] and payload.endswith(b"\n"), "Trace digest or truncation")
    rows = [json.loads(line) for line in payload.splitlines()]
    _require(0 < len(rows) <= trial["tick_limit"], "Empty or over-budget trace")
    state, seconds = initial_state(), 0.0
    for row in rows:
        _require(state.outcome is None and row["before"] == asdict(state), "Before-state replay mismatch")
        xs, ys = _coordinates(state, trial["crop"])
        _require(row["sample_xs"] == xs and row["sample_ys"] == ys, "Sample coordinates mismatch")
        pixels = bytes(256) if trial["input"] == "dark" else bytes(raster[y * 96 + x] for y in ys for x in xs)
        _require(row["observation_pixels"] == list(pixels) and row["observation_sha256"] == _sha(pixels),
                 "Exact input pixels/hash mismatch")
        if state.tick in SNAPSHOTS:
            _png(directory / f"input-{state.tick:03}.png", pixels, (16, 16))
        raw = ControllerOutput.model_validate(row["raw_action"])
        action = ControllerOutput.model_validate(row["action"])
        _require(raw.model_mode == action.model_mode == ("windowed_reset" if require_real else "fixture"),
                 "Wrong real/fixture action label")
        if require_real:
            _require(provenance is not None, "Real telemetry requires provenance")
        if provenance is not None:
            _require(raw.telemetry.sampled_neurons == provenance["neurons"] and
                     raw.telemetry.neural_ms == provenance["parameters"]["dt"] *
                     provenance["parameters"]["sim_steps"] and raw.telemetry.spike_count > 0,
                     "Neural telemetry/provenance mismatch")
        _motor(raw, row["motor_rates"], provenance["calibration"]["click_hz"] if provenance else 330)
        _calibrated(raw, action, row["motor_rates"], trial["motor"])
        state = step_sliding(arena, state, action)
        _require(row["after"] == asdict(state), "After-state physics replay mismatch")
        seconds += _finite(row["step_wall_seconds"], "step wall seconds", positive=True)
    _require(trial["ticks"] == len(rows) and trial["final_state"] == asdict(state), "Final state/count mismatch")
    _require(trial["outcome"] == state.outcome, "Outcome mismatch")
    termination = "terminal" if state.outcome else "diagnostic_cutoff"
    _require(trial["termination"] == termination, "Diagnostic cutoff mislabeled as terminal/timeout")
    _require(state.outcome is not None or state.tick == trial["tick_limit"], "Premature diagnostic cutoff")
    _require(_finite(trial["elapsed_wall_seconds"], "trial wall seconds") >= seconds,
             "Trial runtime below neural runtime")
    _trajectory(directory / "trajectory.png", raster, rows)
    return dict(steps=len(rows), neural_wall_seconds=seconds)


def verify_trials(trials, output, config, *, require_real=True, provenance=None):
    scheduled = expected_schedule()
    _require(config["trials"] == scheduled and len(trials) == 14, "Missing or changed frozen schedule")
    calls, seconds, ledger = 0, 0.0, []
    for trial, expected in zip(trials, scheduled, strict=True):
        _require(all(trial.get(key) == value for key, value in expected.items()), "Scheduled condition/order mismatch")
        checked = verify_trial(trial, output, require_real=require_real, provenance=provenance)
        for tick in range(checked["steps"]):
            calls += 1
            ledger.append(dict(call=calls, trial=trial["id"], tick=tick))
        seconds += trial["elapsed_wall_seconds"]
    payload = (Path(output) / "calls.jsonl").read_bytes()
    _require(payload.endswith(b"\n"), "Truncated call ledger")
    recorded = [json.loads(line) for line in payload.splitlines()]
    _require(recorded == ledger and calls <= config["max_trial_calls"] == 1984,
             "Attempted call ledger/budget mismatch")
    return dict(trials=14, steps=calls, wall_seconds=seconds)


def _instant(value):
    result = datetime.fromisoformat(value)
    _require(result.utcoffset() is not None, "Evidence timestamp requires timezone")
    return result


def _freeze(output, report, config):
    path = output / "confirmation-freeze.json"
    frozen = _json(path)
    _require(report["confirmation-freeze.json"] == _file_sha(path), "Confirmation freeze digest mismatch")
    _require(frozen["config_sha256"] == report["config_sha256"] and
             frozen["calibration"] == config["calibration"] and frozen["parameters_changed"] is False,
             "Confirmation parameters were not frozen")
    source = "scripts/feasibility_final_motor.py"
    _require(frozen["motor_source_sha256"] == report["source"]["file_sha256"][source] ==
             _file_sha(Path(source)), "Confirmation motor source changed")
    screening_calls = sum(t["ticks"] for t in report["trials"] if t["stage"] == "screen")
    _require(frozen["completed_screening_calls"] == screening_calls <= 448,
             "Confirmation started before screening completed")
    _require(_instant(report["started_utc"]) < _instant(frozen["frozen_utc"]) <
             _instant(report["finished_utc"]), "Confirmation freeze chronology mismatch")


def _preserved(root):
    preserved = _json(root / "preserved-evidence.json")
    _require(len(preserved["files"]) == 496, "Historical preservation inventory changed")
    for path, digest in preserved["files"].items():
        _require(_file_sha(Path(path)) == digest, f"Preserved historical evidence changed: {path}")
    return len(preserved["files"])


def _real_regression(root, provenance, declared_utc):
    records, headers = [], []
    for line in (root / "real-adapter.stdout.log").read_text().splitlines():
        start = line.find("{")
        if start >= 0:
            try:
                record = json.loads(line[start:])
            except json.JSONDecodeError:
                continue
            if record.get("gate") == "real_adapter_window":
                records.append(record)
            elif record.get("gate") == "real_adapter":
                headers.append(record)
    _require(len(headers) == 1 and headers[0]["fixture"] is False, "Missing real regression provenance")
    for key in ("graph_sha256", "annotations_sha256", "parameters", "calibration", "model_source_sha256",
                "neural_state_mode", "gains", "learning_enabled", "neurons"):
        _require(headers[0]["provenance"][key] == provenance[key], "Real regression model configuration mismatch")
    _require(len(records) == 4, "Real regression must record exactly four calls")
    observations = [Observation(schema_version="1", pixels=[0.0] * 256),
                    Observation(schema_version="1", pixels=[float((x // 2 + y // 2) % 2)
                                                            for y in range(16) for x in range(16)])]
    for record, (repetition, index) in zip(records, ((0, 0), (0, 1), (1, 0), (1, 1)), strict=True):
        output = ControllerOutput.model_validate(record["output"])
        _require(record["fixture"] is False and record["repetition"] == repetition and
                 record["step_index"] == index and record["run_seed"] == 20260911,
                 "Real regression window identity mismatch")
        _require(record["observation_sha256"] == _sha(observations[index].model_dump_json().encode()) and
                 record["output_sha256"] == _sha(output.model_dump_json().encode()), "Real regression hash mismatch")
        _require(output.model_mode == "windowed_reset" and
                 output.telemetry.sampled_neurons == provenance["neurons"] and
                 output.telemetry.neural_ms == 20 and output.telemetry.spike_count > 0,
                 "Real regression telemetry mismatch")
        _finite(record["wall_seconds"], "real regression runtime", positive=True)
    _require(all(records[index]["output"] == records[index + 2]["output"] for index in (0, 1)),
             "Real regression is not repeatable")
    commands = [json.loads(line) for line in (root / "commands.jsonl").read_text().splitlines()]
    commands = [record for record in commands if record["name"] == "real-adapter"]
    _require(len(commands) == 1 and commands[0]["exit_code"] == 0 and
             commands[0]["argv"][:2] == ["make", "test-controller-real"] and
             0 < commands[0]["elapsed_seconds"] <= 120 and
             _instant(commands[0]["started_utc"]) > _instant(declared_utc),
             "Real regression command failed, repeated, or outside budget")
    suites = ET.parse(root / "real-controller.xml").getroot().iter("testsuite")
    totals = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.attrib[key])
    _require(totals == dict(tests=1, failures=0, errors=0, skipped=0), "Real regression did not pass exactly once")
    return 4


def _verify(output, config_path):
    report, config = _json(output / "report.json"), _json(config_path)
    _require(report["fixture"] is False, "Fixture report cannot pass the real gate")
    _require(report["status"] == "PASS", "Final experiment is incomplete or failed")
    _require(report["human_review"] == config["human_review"] == "CHANGES_REQUESTED" and
             report["learning_enabled"] is config["learning_enabled"] is False, "Review/learning mismatch")
    _require(config["schema_version"] == "milestone05-final-development-3" and
             report["config_sha256"] == _file_sha(config_path) and
             config["plan_sha256"] == _file_sha(PLAN), "Frozen configuration/plan mismatch")
    fixed = dict(max_trial_calls=1984, real_regression_max_calls=4, max_total_calls=1988,
                 user_cap=2048, unused_calls=60, wall_budget_seconds=1300, real_regression_timeout_seconds=120)
    _require(all(config.get(key) == value for key, value in fixed.items()), "Frozen compute budget changed")
    _preregistration(output, report, config)
    preregistration = _json(output.parent / "preregistration.json")
    dependencies = (*SOURCE_DEPENDENCIES, config["model_parameters"], config["visual_calibration"])
    _sources(preregistration["source"], dependencies)
    _sources(report["source"], dependencies)
    _require(config["calibration"] == calibration_basis(), "Calibration basis changed")
    _require(config["baseline_sha256"] == _file_sha(output / "baseline.json"), "Frozen baseline digest mismatch")
    _require(config["prior_report_sha256"] == _file_sha(Path("artifacts/milestones/05/revision/primary/report.json")),
             "Historical calibration report changed")
    provenance = _provenance(report, output, config | {"action_mapping": "upstream-pilot-divide-90-v1"})
    _require(provenance["neurons"] == _json(Path("build/flytrap-v1/manifest.json"))["stats"]["bodies"],
             "Recorded neuron count differs from graph manifest")
    checked = verify_trials(report["trials"], output, config, provenance=provenance)
    _require(report["neural_calls"] == checked["steps"], "Reported call count mismatch")
    for stage in ("screen", "confirm"):
        selected = [trial for trial in report["trials"] if trial["stage"] == stage]
        _require(report["phases"][stage]["calls"] == sum(trial["ticks"] for trial in selected) and
                 math.isclose(report["phases"][stage]["elapsed_trial_seconds"],
                              sum(trial["elapsed_wall_seconds"] for trial in selected), rel_tol=0, abs_tol=1e-9),
                 "Phase totals mismatch")
    elapsed = _finite(report["elapsed_wall_seconds"], "total runtime", positive=True)
    _require(checked["wall_seconds"] + _finite(report["controller_load_seconds"], "load runtime", positive=True)
             <= elapsed <= config["wall_budget_seconds"], "Trial wall budget exceeded")
    _finite(report["peak_process_rss_bytes"], "peak RSS", positive=True)
    _require(_instant(report["started_utc"]) < _instant(report["finished_utc"]), "Run chronology mismatch")
    for key in ("cpu", "dependencies", "node", "platform", "python", "sqlite_linked"):
        _require(report["environment"][key] == config["runtime"][key], "Declared execution runtime changed")
    _freeze(output, report, config)
    regression_calls = _real_regression(output.parent, provenance, preregistration["declared_utc"])
    total = checked["steps"] + regression_calls
    _require(total <= config["max_total_calls"] <= config["user_cap"], "Combined model-call budget exceeded")
    preserved = _preserved(output.parent)
    return dict(automated_status="PASS", fixture=False, human_review="CHANGES_REQUESTED",
                learning_claim_status="NOT_RUN", trials=checked["trials"], replayed_steps=checked["steps"],
                regression_calls=regression_calls, total_model_calls=total, preserved_files=preserved,
                report_sha256=_file_sha(output / "report.json"), config_sha256=_file_sha(config_path),
                limitation="Artifact replay, not neural reproduction or interaction approval. Freeze order is "
                "supported by the frozen runner and ledger; individual trial UTC starts were not recorded.")


def verify(output=ROOT / "trials", config_path=CONFIG):
    try:
        return _verify(Path(output), Path(config_path))
    except (KeyError, TypeError, OSError, StopIteration, OverflowError, IndexError, ET.ParseError) as error:
        raise ValueError(f"Invalid or missing final evidence: {error}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "trials")
    parser.add_argument("--config", type=Path, default=CONFIG)
    args = parser.parse_args()
    try:
        result = verify(args.output, args.config)
    except ValueError as error:
        result = dict(automated_status="FAIL", error=str(error))
    (args.output.parent / "verify.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["automated_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
