"""Verify development artifacts without running the neural model.

This checks evidence integrity and replay, not scientific competence or an
independent reproduction of neural outputs. Fixture mechanics cannot pass the
real experiment gate. Run with --output pointing at the completed trial root.
"""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from PIL import Image

from flytrap.arena.core import MAX_TICKS, MOVEMENT_PER_TICK, build_arena, initial_state, step
from flytrap.arena.render import observation, render
from flytrap.contracts import ChallengeSpec, CheckpointRef, ControllerOutput, create_challenge
from scripts.feasibility_analysis import latency_distribution, summarize_trace, summarize_visual_pairs


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _json(path):
    return json.loads(path.read_text(), parse_constant=lambda value: (_ for _ in ()).throw(
        ValueError(f"Nonfinite JSON number: {value}")))


def _sha(payload):
    return hashlib.sha256(payload).hexdigest()


def _object_sha(value):
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def _file_sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _challenge(side):
    _require(side in ("left", "right"), "Unknown destination side")
    return create_challenge(dict(schema_version="1", preset_version="two_choice_v1",
        renderer_version="grayscale_v1", destination_side=side,
        left_texture="stripes" if side == "left" else "checkerboard",
        right_texture="checkerboard" if side == "left" else "stripes", distractions=[]))


def _crop(raster, state):
    return bytes(round(v * 255) for v in observation(raster, x_q=state.x_q, y_q=state.y_q).pixels)


def _probe_pixels(condition):
    if condition in ("arena_left", "arena_right"):
        return _crop(render(build_arena(_challenge(condition.removeprefix("arena_"))).scene), initial_state())
    if condition == "dark":
        return bytes(256)
    if condition == "bright":
        return bytes([255]) * 256
    if condition == "midgray":
        return bytes([128]) * 256
    if condition == "stripes":
        return bytes(255 if x % 2 == 0 else 0 for y in range(16) for x in range(16))
    if condition == "checkerboard":
        return bytes(255 if (x + y) % 2 == 0 else 0 for y in range(16) for x in range(16))
    raise ValueError("Unknown probe condition")


def _png(path, pixels, size):
    with Image.open(path) as image:
        _require(image.mode == "L" and image.size == size and image.tobytes() == pixels,
                 f"PNG raster mismatch: {path.name}")


def _telemetry(action, expected):
    if expected is not None:
        _require(action.telemetry.sampled_neurons == expected["sampled_neurons"] and
                 action.telemetry.neural_ms == expected["neural_ms"], "Neural telemetry disagrees with model provenance")


def verify_probes(probes, config, output, *, require_real=True, expected_telemetry=None):
    """Check complete matched reset probes; fixture mode is for unit mechanics."""
    expected = {(seed, condition) for seed in config["seeds"] for condition in config["probe_conditions"]}
    seen, calls = set(), 0
    for record in probes:
        key = (record["seed"], record["condition"])
        _require(key in expected and key not in seen, "Unexpected or duplicate visual probe")
        seen.add(key)
        _require(record["step_index"] == 0, "Visual probe must use first reset window")
        pixels = _probe_pixels(record["condition"])
        _require(record["observation_sha256"] == _sha(pixels), "Probe observation hash mismatch")
        _png(output / f"probe-{record['condition']}.png", pixels, (16, 16))
        action = ControllerOutput.model_validate(record["action"])
        _telemetry(action, expected_telemetry)
        if require_real:
            _require(action.model_mode == "windowed_reset", "Fixture action in real probe")
        repetitions = record["repetitions"]
        _require(len(repetitions) == config["probe_repetitions"], "Missing probe repetition")
        for index, repetition in enumerate(repetitions):
            _require(type(repetition["repetition"]) is int and repetition["repetition"] == index,
                     "Probe repetition order mismatch")
            _require(ControllerOutput.model_validate(repetition["action"]).model_dump_json() == action.model_dump_json(),
                     "Repeated probe action mismatch")
            latency_distribution([repetition["step_wall_seconds"]])
            calls += 1
    _require(seen == expected, "Missing scheduled visual probes")
    return dict(probes=len(seen), probe_controller_calls=calls,
                visual_pairs=summarize_visual_pairs(probes))


def verify_trial(trial, output, *, require_real=True, expected_telemetry=None):
    """Recompute a single trial's entire physics and sensory sequence."""
    trial_id = trial["trial_id"]
    _require(type(trial_id) is str and trial_id.startswith("dev-") and
             all(c.isascii() and (c.isalnum() or c in "-_") for c in trial_id), "Invalid trial ID")
    directory = output / trial_id
    _require(_json(directory / "trial.json") == trial, "Trial record disagrees with report")
    condition = trial["condition"]
    challenge = ChallengeSpec.model_validate(trial["challenge"])
    _require(challenge == _challenge(condition["destination_side"]), "Challenge does not match condition")
    arena = build_arena(challenge)
    raster = render(arena.scene)
    _require((directory / "canonical.gray").read_bytes() == raster, "Canonical raster mismatch")
    _require(trial["frame_sha256"] == _sha(raster), "Frame hash mismatch")
    _png(directory / "canonical.png", raster, (96, 96))
    payload = (directory / "trace.jsonl").read_bytes()
    _require(_sha(payload) == trial["trace_sha256"], "Trace hash mismatch")
    _require(payload.endswith(b"\n"), "Truncated trace record")
    rows = [json.loads(line) for line in payload.splitlines()]
    _require(bool(rows), "Empty episode trace")
    multiplier = condition["motor_multiplier"]
    _require(type(multiplier) is float and multiplier in (0.5, 1.0), "Invalid motor scaling")
    _require(condition["input"] in ("canonical", "dark"), "Unknown episode observation condition")
    state = initial_state()
    for row in rows:
        _require(row["before"] == asdict(state), "Trace before-state mismatch")
        pixels = bytes(256) if condition["input"] == "dark" else _crop(raster, state)
        _require(row["observation_sha256"] == _sha(pixels), "Trace observation hash mismatch")
        raw = ControllerOutput.model_validate(row["raw_action"])
        _telemetry(raw, expected_telemetry)
        action = ControllerOutput.model_validate(row["action"])
        if require_real:
            _require(raw.model_mode == "windowed_reset", "Fixture action in real episode")
        expected_action = dict(raw.model_dump(), dx=raw.dx * multiplier, dy=raw.dy * multiplier)
        _require(action.model_dump() == expected_action, "Applied action differs from declared raw scaling")
        state = step(arena, state, action)
        _require(row["after"] == asdict(state), "Recomputed physics mismatch")
    _require(state.outcome is not None, "Incomplete episode has no terminal outcome")
    _require(trial["final_state"] == asdict(state), "Final state mismatch")
    summary = summarize_trace(rows)
    _require(trial["summary"] == summary, "Trace summary mismatch")
    latency_distribution([trial["elapsed_wall_seconds"]])
    _require(trial["elapsed_wall_seconds"] >= summary["controller_wall_seconds"],
             "Episode wall time is less than measured controller time")
    return len(rows)


def verify_trials(trials, config, output, *, require_real=True, expected_telemetry=None):
    """Require every declared seed/condition once, without replacement trials."""
    expected = {f"dev-{seed}-{condition['id']}": (seed, condition)
                for seed in config["seeds"] for condition in config["episode_conditions"]}
    _require(len(expected) == len(config["seeds"]) * len(config["episode_conditions"]),
             "Duplicate scheduled seed or condition")
    seen, steps = set(), 0
    for trial in trials:
        trial_id = trial["trial_id"]
        _require(trial_id in expected and trial_id not in seen, "Unexpected or duplicate episode")
        _require((trial["seed"], trial["condition"]) == expected[trial_id], "Episode condition/seed mismatch")
        seen.add(trial_id)
        steps += verify_trial(trial, output, require_real=require_real, expected_telemetry=expected_telemetry)
    _require(seen == set(expected) and bool(seen), "Missing scheduled episodes")
    return dict(trials=len(seen), replayed_steps=steps)


def verify_experiment(output, *, config_path=Path("experiments/feasibility-v1.json"),
                      graph_root=Path("build/flytrap-v1")):
    """Real gate only; all scheduled trials must finish and retain authentic labels."""
    output = Path(output)
    report = _json(output / "report.json")
    _require(report["fixture"] is False, "Fixture manifest cannot pass real feasibility")
    _require(report["schema_version"] == "flytrap-feasibility-1" and report["automated_status"] == "PASS",
             "Experiment is not a completed passing feasibility run")
    _require(report["learning_enabled"] is False and report["learning_claim_status"] == "NOT_RUN",
             "Feasibility must not enable learning or claim improvement")
    _require(report["human_review"] in ("PENDING", "APPROVED"), "Invalid human review status")
    _require(report["failures"] == [], "Experiment contains failures")
    config = _json(config_path)
    _require(report["config"] == config == _json(output / "development-config.json"),
             "Development configuration changed")
    _require(report["config_sha256"] == _file_sha(config_path), "Configuration source hash mismatch")
    frozen = dict(preset="two_choice_v1", renderer="grayscale_v1", crop="crop16_v1", target_texture="stripes",
                  distractions=[], max_ticks=MAX_TICKS, base_movement_pixels_per_axis=MOVEMENT_PER_TICK,
                  learning_enabled=False)
    _require(all(config.get(key) == value for key, value in frozen.items()),
             "Configuration claims disagree with implemented experiment")
    source = report["source"]
    _require(source["source_tree_sha256"] == _object_sha(source["file_sha256"]), "Source identity digest mismatch")
    # Only execution dependencies must match the current verifier environment;
    # adding reports or this verifier after execution does not alter the model.
    for filename in ("scripts/feasibility.py", "scripts/feasibility_analysis.py", "flytrap/contracts.py",
                     "flytrap/arena/core.py", "flytrap/arena/render.py", "flytrap/controllers/fly.py",
                     "flytrap/data/bundle.py", "flytrap/data/graph.py", "flytrap/data/sources.json",
                     "flysim.py", "flyeye.py", "uv.lock", "pyproject.toml", "web/package-lock.json",
                     config["model_parameters"], config["visual_calibration"]):
        _require(source["file_sha256"].get(filename) == _file_sha(Path(filename)),
                 f"Execution source changed: {filename}")
    checkpoint = CheckpointRef.model_validate(report["checkpoint"])
    _require(checkpoint.model_mode == "windowed_reset" and checkpoint.checkpoint_id == "fly-baseline-v1",
             "Not a real baseline checkpoint")
    _require(checkpoint.sha256 == _file_sha(output / "baseline.json"), "Baseline checksum mismatch")
    baseline = _json(output / "baseline.json")
    provenance = report["provenance"]
    _require(all(provenance.get(key) == value for key, value in baseline.items()), "Baseline provenance mismatch")
    _require(provenance["fixture"] is False and provenance["learning_enabled"] is False
             and provenance["neural_state_mode"] == "windowed_reset"
             and provenance["gains"] == "all-one-float32", "Invalid real untrained provenance")
    _require(provenance["checkpoint"] == report["checkpoint"], "Checkpoint provenance mismatch")
    manifest = _json(graph_root / "manifest.json")
    _require(manifest["source"] == _json(Path("flytrap/data/sources.json")) and manifest["source"]["fixture"] is False,
             "Graph is not the pinned real source")
    _require(checkpoint.graph_sha256 == provenance["graph_sha256"] == manifest["graph_sha256"]
             == _file_sha(graph_root / "graph.npz"), "Graph checksum mismatch")
    _require(provenance["upstream_revision"] == manifest["builder"]["upstream_revision"], "Upstream identity mismatch")
    annotations = next(f for f in manifest["source"]["files"] if f["filename"] == "body-annotations.feather")
    _require(provenance["annotations_sha256"] == annotations["sha256"], "Annotation identity mismatch")
    for key, filename in (("flysim", "flysim.py"), ("flyeye", "flyeye.py"), ("adapter", "flytrap/controllers/fly.py")):
        _require(provenance["model_source_sha256"][key] == source["file_sha256"][filename], "Model source mismatch")
    for key, filename in (("parameters", config["model_parameters"]), ("calibration", config["visual_calibration"])):
        _require(provenance[key] == _json(Path(filename)) and provenance[key + "_sha256"] == _file_sha(Path(filename)),
                 f"Model {key} mismatch")
    _require(type(provenance["neurons"]) is int and provenance["neurons"] > 0, "Invalid neuron count")
    for metric in ("fresh_process_controller_load_seconds", "checkpoint_preparation_seconds", "peak_process_rss_bytes"):
        latency_distribution([report[metric]])
        _require(report[metric] > 0, f"Missing measured {metric}")
    _require(bool(report["environment"]) and bool(report["started_utc"]) and bool(report["finished_utc"]),
             "Missing environment or timing provenance")
    telemetry = dict(sampled_neurons=provenance["neurons"],
                     neural_ms=provenance["parameters"]["dt"] * provenance["parameters"]["sim_steps"])
    probes = verify_probes(report["probes"], config, output, expected_telemetry=telemetry)
    _require(report["visual_pairs"] == probes.pop("visual_pairs"), "Paired visual summary mismatch")
    trials = verify_trials(report["trials"], config, output, expected_telemetry=telemetry)
    return dict(automated_status="PASS", fixture=False, human_review=report["human_review"],
                learning_claim_status="NOT_RUN", **trials, **probes,
                report_sha256=_file_sha(output / "report.json"),
                limitation="Artifact consistency and physics replay; no neural re-execution or learning claim")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("experiments/feasibility-v1.json"))
    parser.add_argument("--graph-root", type=Path, default=Path("build/flytrap-v1"))
    args = parser.parse_args()
    try:
        result = verify_experiment(args.output, config_path=args.config, graph_root=args.graph_root)
    except (ValueError, KeyError, TypeError, OSError, StopIteration, OverflowError) as error:
        print(json.dumps(dict(automated_status="FAIL", error_type=type(error).__name__, error=str(error))))
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
