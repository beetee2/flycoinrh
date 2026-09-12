"""Independently replay revision evidence without neural execution or promotion."""

import argparse
from dataclasses import asdict
from datetime import datetime
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from flytrap.arena.core import MAX_TICKS, MOVEMENT_PER_TICK, Q, build_arena, initial_state, step
from flytrap.arena.render import render
from flytrap.arena.sliding import step_sliding
from flytrap.contracts import CheckpointRef, ControllerOutput
from scripts.verify_feasibility import _challenge, _file_sha, _json, _object_sha, _png, _require, _sha

CONFIG = Path("experiments/feasibility-revision-v2.json")
BASELINE = Path("artifacts/milestones/05/trials/baseline.json")
SOURCE_DEPENDENCIES = (
    "scripts/feasibility_revision.py", "scripts/feasibility.py", "scripts/feasibility_analysis.py",
    "scripts/feasibility_motor_telemetry.py", "flytrap/contracts.py", "flytrap/arena/core.py",
    "flytrap/arena/render.py", "flytrap/arena/overview.py", "flytrap/arena/sliding.py",
    "flytrap/controllers/fly.py", "flytrap/data/bundle.py", "flytrap/data/graph.py",
    "flytrap/data/sources.json", "flysim.py", "flyeye.py", "uv.lock", "pyproject.toml",
    "web/package-lock.json",
)


def _finite(value, label, *, positive=False):
    _require(type(value) in (int, float) and math.isfinite(value) and
             (value > 0 if positive else value >= 0), f"Invalid {label}")
    return value


def _schedule(config, stage):
    _require(stage in ("physics", "overview"), "Unknown development stage")
    physics = config["physics"] if stage == "physics" else ["tangent_v2"]
    crop = config["primary_crop"] if stage == "physics" else config["optional_crop"]
    return [dict(id=f"{version}-{crop}-{seed}-{side}-{kind}", physics=version, crop=crop,
                 seed=seed, layout=side, input=kind)
            for version in physics for seed in config["seeds"] for side in config["layouts"]
            for kind in config["inputs"]]


def _coordinates(state, crop):
    if crop == "overview16_v2":
        return [3 + 6*i for i in range(16)], [3 + 6*i for i in range(16)]
    _require(crop == "crop16_v1", "Unknown observation version")
    return tuple([max(0, min(95, (coordinate - 60*Q + 8*i*Q)//Q)) for i in range(16)]
                 for coordinate in (state.x_q, state.y_q))


def _motor(action, rates, click_hz):
    _require(set(rates) == {"steer_L", "steer_R", "fwd_L", "fwd_R", "back", "stop"},
             "Missing or extra motor populations")
    for name, value in rates.items():
        _finite(value, f"motor rate {name}")
    turn = max(-1, min(1, (rates["steer_R"] - rates["steer_L"]) / 450))
    forward = (rates["fwd_L"] + rates["fwd_R"]) / 2 / 450
    backward = rates["back"] / 450
    stop = max(0, min(1, rates["stop"] / 450))
    speed = max(-1, min(1, forward-backward)) * (1-stop)
    _require(math.isclose(action.dx, turn, rel_tol=0, abs_tol=1e-15) and
             math.isclose(action.dy, -speed, rel_tol=0, abs_tol=1e-15) and
             action.click == (rates["stop"] >= click_hz and speed < 0.25),
             "Motor rates disagree with original action mapping")


def _trajectory(path, raster, rows):
    """Check the actual scene/path region, independent of title typography."""
    expected = Image.frombytes("L", (96, 96), raster).convert("RGB").resize(
        (576, 576), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(expected)
    states = [rows[0]["before"]] + [row["after"] for row in rows]
    points = [(state["x_q"]/Q*6, state["y_q"]/Q*6) for state in states]
    draw.line(points, fill="#d00000", width=3)
    for (x, y), color in ((points[0], "#0055ff"), (points[-1], "#d00000")):
        draw.ellipse((x-5, y-5, x+5, y+5), fill=color)
    with Image.open(path) as actual:
        _require(actual.mode == "RGB" and actual.size == (576, 666) and
                 actual.crop((0, 60, 576, 636)).tobytes() == expected.tobytes(),
                 "Trajectory image does not depict replayed path")


def verify_trial(trial, output, config, *, require_real=True, provenance=None):
    """Replay mechanics; require_real=False labels synthetic unit artifacts only."""
    _require(trial["physics"] in ("no_sliding_v1", "tangent_v2"), "Unknown physics version")
    _require(trial["input"] in ("canonical", "dark"), "Unknown input condition")
    expected_id = f"{trial['physics']}-{trial['crop']}-{trial['seed']}-{trial['layout']}-{trial['input']}"
    _require(trial["id"] == expected_id, "Trial identifier/condition mismatch")
    _require(trial["status"] == "PASS", "Scheduled trial failed or incomplete")
    directory = Path(output) / expected_id
    arena = build_arena(_challenge(trial["layout"]))
    raster = render(arena.scene)
    _require((directory / "canonical.gray").read_bytes() == raster, "Canonical raster mismatch")
    _png(directory / "canonical.png", raster, (96, 96))
    payload = (directory / "trace.jsonl").read_bytes()
    _require(_sha(payload) == trial["trace_sha256"], "Trace digest mismatch")
    _require(payload.endswith(b"\n"), "Truncated trace")
    rows = [json.loads(line) for line in payload.splitlines()]
    _require(0 < len(rows) <= config["diagnostic_tick_limit"], "Empty or over-budget trace")
    state, cue_free, wall_seconds = initial_state(), 0, 0.0
    physics = step if trial["physics"] == "no_sliding_v1" else step_sliding
    for row in rows:
        _require(row["before"] == asdict(state), "Before-state replay mismatch")
        xs, ys = _coordinates(state, trial["crop"])
        _require(row["sample_xs"] == xs and row["sample_ys"] == ys, "Sample coordinates mismatch")
        pixels = bytes(256) if trial["input"] == "dark" else bytes(raster[y*96+x] for y in ys for x in xs)
        _require(row["observation_pixels"] == list(pixels), "Exact observation pixels mismatch")
        _require(row["observation_sha256"] == _sha(pixels), "Observation hash mismatch")
        count = sum(pad.x0 <= x < pad.x1 and pad.y0 <= y < pad.y1
                    for pad in (arena.scene.left_pad, arena.scene.right_pad) for y in ys for x in xs)
        _require(row["pad_sample_count"] == count, "Pad sample count mismatch")
        cue_free += count == 0
        if state.tick in (0, 16, 32, 64, 95):
            _png(directory / f"input-{state.tick:03}.png", pixels, (16, 16))
        action = ControllerOutput.model_validate(row["action"])
        _require(row["raw_action"] == row["action"], "Applied action differs from raw action")
        _require(action.model_mode == ("windowed_reset" if require_real else "fixture"),
                 "Wrong real/fixture action label")
        if provenance is not None:
            _require(action.telemetry.sampled_neurons == provenance["neurons"] and
                     action.telemetry.neural_ms == provenance["parameters"]["dt"] *
                     provenance["parameters"]["sim_steps"], "Neural telemetry/provenance mismatch")
        _motor(action, row["motor_rates"], provenance["calibration"]["click_hz"] if provenance else 330)
        state = physics(arena, state, action)
        _require(row["after"] == asdict(state), "After-state physics replay mismatch")
        wall_seconds += _finite(row["step_wall_seconds"], "step wall seconds")
    _require(trial["ticks"] == len(rows) and trial["final_state"] == asdict(state), "Final state/count mismatch")
    _require(trial["outcome"] == state.outcome, "Outcome mismatch")
    termination = "terminal" if state.outcome else "diagnostic_cutoff"
    _require(trial["termination"] == termination, "Diagnostic cutoff mislabeled as terminal/timeout")
    _require(state.outcome is not None or state.tick == config["diagnostic_tick_limit"], "Premature cutoff")
    _require(trial["cue_free_ticks"] == cue_free, "Cue visibility summary mismatch")
    _require(_finite(trial["elapsed_wall_seconds"], "trial wall seconds") >= wall_seconds,
             "Trial runtime below summed neural runtime")
    _trajectory(directory / "trajectory.png", raster, rows)
    return dict(steps=len(rows), cue_free_ticks=cue_free, neural_wall_seconds=wall_seconds)


def _provenance(report, output, config):
    baseline_bytes = (output / "baseline.json").read_bytes()
    _require(baseline_bytes == BASELINE.read_bytes(), "Historical v1 baseline bytes changed")
    baseline, provenance = _json(output / "baseline.json"), report["provenance"]
    _require(all(provenance.get(key) == value for key, value in baseline.items()), "Baseline provenance mismatch")
    checkpoint = CheckpointRef.model_validate(provenance["checkpoint"])
    _require(checkpoint.sha256 == _sha(baseline_bytes) and checkpoint.checkpoint_id == "fly-baseline-v1"
             and checkpoint.model_mode == "windowed_reset", "Baseline checkpoint mismatch")
    _require(provenance["fixture"] is False and provenance["learning_enabled"] is False and
             provenance["gains"] == "all-one-float32" and provenance["neural_state_mode"] == "windowed_reset"
             and provenance["action_mapping"] == config["action_mapping"], "Invalid real untrained provenance")
    graph_root = Path("build/flytrap-v1")
    manifest = _json(graph_root / "manifest.json")
    _require(manifest["source"] == _json(Path("flytrap/data/sources.json")) and
             manifest["source"]["fixture"] is False, "Graph is not pinned real source")
    _require(checkpoint.graph_sha256 == provenance["graph_sha256"] == manifest["graph_sha256"] ==
             _file_sha(graph_root / "graph.npz"), "Graph checksum mismatch")
    _require(provenance["upstream_revision"] == manifest["builder"]["upstream_revision"], "Upstream mismatch")
    annotations = next(item for item in manifest["source"]["files"]
                       if item["filename"] == "body-annotations.feather")
    _require(provenance["annotations_sha256"] == annotations["sha256"] ==
             _file_sha(Path("data/body-annotations.feather")), "Annotation checksum mismatch")
    for key, path in (("flysim", "flysim.py"), ("flyeye", "flyeye.py"), ("adapter", "flytrap/controllers/fly.py")):
        _require(provenance["model_source_sha256"][key] == report["source"]["file_sha256"][path],
                 "Protected model source mismatch")
    for key, path in (("parameters", config["model_parameters"]), ("calibration", config["visual_calibration"])):
        _require(provenance[key] == _json(Path(path)) and provenance[key+"_sha256"] == _file_sha(Path(path)),
                 "Model configuration mismatch")
    _require(type(provenance["neurons"]) is int and provenance["neurons"] > 0, "Invalid neuron count")
    return provenance


def verify_trials(trials, output, config, stage, *, require_real=True, provenance=None):
    """Verify every predeclared condition in order, including fixed seed identity."""
    scheduled = _schedule(config, stage)
    prefix = "primary" if stage == "physics" else "optional"
    _require(len(scheduled) == config[prefix+"_episodes"] and
             len({trial["id"] for trial in scheduled}) == len(scheduled), "Invalid scheduled episode count")
    _require(len(trials) == len(scheduled), "Missing scheduled results")
    steps, seconds = 0, 0.0
    for trial, expected in zip(trials, scheduled, strict=True):
        _require(all(trial.get(key) == value for key, value in expected.items()), "Scheduled condition/order mismatch")
        result = verify_trial(trial, output, config, require_real=require_real, provenance=provenance)
        steps += result["steps"]
        seconds += trial["elapsed_wall_seconds"]
    return dict(trials=len(scheduled), steps=steps, wall_seconds=seconds)


def _sources(source, paths):
    _require(source["source_tree_sha256"] == _object_sha(source["file_sha256"]), "Source digest mismatch")
    for path in paths:
        _require(source["file_sha256"].get(path) == _file_sha(Path(path)), f"Execution source changed: {path}")


def _preregistration(output, report, config):
    declaration = _json(output.parent / "preregistration.json")
    _require(declaration["config"] == config and declaration["config_sha256"] == report["config_sha256"],
             "Preregistration configuration/digest mismatch")
    declared = datetime.fromisoformat(declaration["declared_utc"])
    started = datetime.fromisoformat(report["started_utc"])
    _require(declared.utcoffset() is not None and started.utcoffset() is not None and declared < started,
             "Budget/configuration declaration must precede neural run start")


def _verify(output, config_path):
    report, config = _json(output / "report.json"), _json(config_path)
    _require(report["fixture"] is False, "Fixture report cannot pass the real gate")
    _require(report["schema_version"] == "milestone05-revision-evidence-2" and report["status"] == "PASS",
             "Revision is not complete and passing")
    _require(report["human_review"] == "PENDING" and report["learning_enabled"] is False and
             report["learning_claim_status"] == "NOT_RUN", "Review/learning status mismatch")
    _require(report["config"] == config == _json(output / "config.json") and
             report["config_sha256"] == _file_sha(config_path) == _file_sha(output / "config.json"),
             "Configuration bytes/digest mismatch")
    _preregistration(output, report, config)
    frozen = dict(physics=["no_sliding_v1", "tangent_v2"], primary_crop="crop16_v1",
                  optional_crop="overview16_v2", arena_max_ticks=MAX_TICKS,
                  movement_pixels_per_axis_per_tick=MOVEMENT_PER_TICK, motor_multiplier=1.0,
                  action_mapping="upstream-pilot-divide-90-v1", preset="two_choice_v1",
                  renderer="grayscale_v1", distractions=[], learning_enabled=False, human_review="PENDING")
    _require(all(config.get(key) == value for key, value in frozen.items()), "Unknown or altered declared versions")
    _require(0 < config["diagnostic_tick_limit"] < MAX_TICKS, "Diagnostic must stop before arena timeout")
    source = report["source"]
    _sources(source, (*SOURCE_DEPENDENCIES, config["model_parameters"], config["visual_calibration"]))
    provenance = _provenance(report, output, config)
    prefix = "primary" if report["stage"] == "physics" else "optional"
    checked = verify_trials(report["trials"], output, config, report["stage"], provenance=provenance)
    steps, trial_seconds = checked["steps"], checked["wall_seconds"]
    _require(report["neural_calls"] == steps <= config[prefix+"_max_neural_calls"], "Neural call budget mismatch")
    elapsed = _finite(report["elapsed_wall_seconds"], "phase runtime", positive=True)
    _require(trial_seconds + _finite(report["controller_load_seconds"], "load runtime", positive=True) <= elapsed
             <= config[prefix+"_wall_budget_seconds"], "Phase wall budget/runtime mismatch")
    _finite(report["peak_process_rss_bytes"], "peak RSS", positive=True)
    _require(bool(report["environment"]) and bool(report["started_utc"]) and bool(report["finished_utc"]),
             "Missing environment/timing identity")
    if report["stage"] == "physics":
        _require(report["trigger"] is None, "Unexpected primary trigger")
    else:
        primary = output.parent / "primary"
        primary_summary = verify(primary, config_path=config_path)
        previous = _json(primary / "report.json")
        selected = [trial for trial in previous["trials"]
                    if trial["physics"] == "tangent_v2" and trial["input"] == "canonical"]
        absent, total = sum(t["cue_free_ticks"] for t in selected), sum(t["ticks"] for t in selected)
        _require(report["trigger"] == dict(primary_report_sha256=primary_summary["report_sha256"],
                 cue_free_ticks=absent, ticks=total, fraction=absent/total) and absent/total >= 0.5,
                 "Optional cue-loss trigger not established")
        _require(steps + primary_summary["replayed_steps"] <= config["total_max_neural_calls"] and
                 elapsed + previous["elapsed_wall_seconds"] <= config["total_wall_budget_seconds"],
                 "Combined development budget exceeded")
    return dict(automated_status="PASS", fixture=False, human_review="PENDING", learning_claim_status="NOT_RUN",
                stage=report["stage"], trials=checked["trials"], replayed_steps=steps,
                report_sha256=_file_sha(output / "report.json"),
                limitation="Artifact integrity and physics/sensory replay; no neural reproduction or competence claim")


def verify(output, config_path=CONFIG):
    """Real artifact gate. All malformed, missing, or inconsistent data fail closed."""
    try:
        return _verify(Path(output), Path(config_path))
    except (KeyError, TypeError, OSError, StopIteration, OverflowError, IndexError) as error:
        raise ValueError(f"Invalid or missing revision evidence: {error}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=CONFIG)
    args = parser.parse_args()
    try:
        result = verify(args.output, args.config)
    except ValueError as error:
        print(json.dumps(dict(automated_status="FAIL", error=str(error))))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
