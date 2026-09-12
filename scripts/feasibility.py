"""Offline full-graph development trials. No fixtures, tuning, or release claims.

Run: python -m scripts.feasibility --output artifacts/milestones/05/trials
The output directory must not exist. Failures remain in report.json and traces.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import sqlite3
import subprocess
import time
import traceback

from PIL import Image, ImageDraw

from flytrap.arena.core import MAX_TICKS, MOVEMENT_PER_TICK, Q, build_arena, initial_state, step
from flytrap.arena.render import observation, png_bytes, raster_sha256, render
from flytrap.contracts import ControllerOutput, Observation, create_challenge
from flytrap.controllers.fly import FlyController, write_baseline_checkpoint
from flytrap.data.bundle import file_sha256
from scripts.feasibility_analysis import summarize_trace, summarize_visual_pairs


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def source_identity():
    paths = subprocess.check_output([
        "git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]).decode().split("\0")
    files = {p: file_sha256(Path(p)) for p in sorted(set(paths)) if p and Path(p).is_file()}
    return dict(head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                file_sha256=files, source_tree_sha256=digest(files),
                definition="SHA256 of compact sorted-key JSON path-to-file-SHA256 mapping")


def environment():
    return dict(python=platform.python_version(), platform=platform.platform(),
                sqlite_linked=sqlite3.sqlite_version,
                node=subprocess.check_output(["node", "--version"], text=True).strip(),
                cpu=next(line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                         if line.startswith("model name")),
                meminfo=Path("/proc/meminfo").read_text(),
                dependencies={name: importlib.metadata.version(name) for name in
                              ["numpy", "scipy", "pandas", "pyarrow", "pydantic", "fastapi", "pytest", "Pillow"]})


def challenge_for(side):
    return create_challenge(dict(schema_version="1", preset_version="two_choice_v1",
        renderer_version="grayscale_v1", destination_side=side,
        left_texture="stripes" if side == "left" else "checkerboard",
        right_texture="checkerboard" if side == "left" else "stripes", distractions=[]))


def pixels_hash(obs):
    return hashlib.sha256(bytes(round(v * 255) for v in obs.pixels)).hexdigest()


def probe_input(condition):
    if condition.startswith("arena_"):
        raster = render(build_arena(challenge_for(condition.removeprefix("arena_"))).scene)
        state = initial_state()
        return observation(raster, x_q=state.x_q, y_q=state.y_q)
    values = {
        "dark": [0.0] * 256, "bright": [1.0] * 256, "midgray": [128 / 255] * 256,
        "stripes": [float(x % 2 == 0) for y in range(16) for x in range(16)],
        "checkerboard": [float((x + y) % 2 == 0) for y in range(16) for x in range(16)],
    }
    return Observation(schema_version="1", pixels=values[condition])


def apply_scaling(action, multiplier):
    if type(multiplier) is not float or multiplier not in (0.5, 1.0):
        raise ValueError("Only predeclared development scaling is allowed")
    return ControllerOutput.model_validate(dict(action.model_dump(), dx=action.dx * multiplier,
                                                dy=action.dy * multiplier))


def overlay(path, raster, rows, label):
    canvas = Image.new("RGB", (576, 666), "#eeeeee")
    canvas.paste(Image.frombytes("L", (96, 96), raster).resize((576, 576), Image.Resampling.NEAREST), (0, 60))
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 8), "ACTUAL CONNECTOME - UNTRAINED DEVELOPMENT TRIAL", fill="black")
    draw.text((10, 26), label, fill="black")
    draw.text((10, 42), f"{rows[-1]['after']['outcome']}; {len(rows)} ticks; {len(rows)*20} neural ms", fill="black")
    positions = [rows[0]["before"]] + [r["after"] for r in rows]
    points = [(s["x_q"] / Q * 6, s["y_q"] / Q * 6 + 60) for s in positions]
    draw.line(points, fill="#d00000", width=3)
    for (x, y), color in ((points[0], "#0055ff"), (points[-1], "#d00000")):
        draw.ellipse((x-5, y-5, x+5, y+5), fill=color)
    draw.text((10, 645), "Human overlay: blue start, red actual path/end. No learning claim.", fill="black")
    canvas.save(path)


def run(config_path, output, graph_root, raw_root):
    config = json.loads(config_path.read_text())
    # This command is deliberately one frozen development design, not an experiment API.
    if (config["max_ticks"] != MAX_TICKS or config["base_movement_pixels_per_axis"] != MOVEMENT_PER_TICK
            or config["learning_enabled"] is not False):
        raise ValueError("Experiment configuration disagrees with frozen arena/model")
    output.mkdir(parents=True, exist_ok=False)
    report = dict(schema_version="flytrap-feasibility-1", started_utc=datetime.now(timezone.utc).isoformat(),
                  automated_status="RUNNING", human_review="PENDING", fixture=False,
                  learning_claim_status="NOT_RUN", learning_enabled=False,
                  config=config, config_sha256=file_sha256(config_path), source=source_identity(),
                  environment=environment(), trials=[], probes=[], failures=[])
    save(output / "report.json", report)
    save(output / "development-config.json", config)
    try:
        inputs = dict(graph_root=graph_root.resolve(), annotations_path=(raw_root / "body-annotations.feather").resolve(),
                      parameters_path=Path(config["model_parameters"]).resolve(),
                      calibration_path=Path(config["visual_calibration"]).resolve(),
                      checkpoint_path=(output / "baseline.json").resolve())
        start = time.perf_counter()
        write_baseline_checkpoint(**inputs)
        report["checkpoint_preparation_seconds"] = time.perf_counter() - start
        start = time.perf_counter()
        controller = FlyController(**inputs)
        report["fresh_process_controller_load_seconds"] = time.perf_counter() - start
        report["cold_load_caveat"] = "First controller construction in a fresh process; OS file caches not evicted; baseline preparation precedes it"
        report["provenance"] = controller.provenance
        report["checkpoint"] = controller.checkpoint.model_dump()
        if controller.provenance["fixture"] or controller.provenance["learning_enabled"]:
            raise ValueError("Feasibility requires real, untrained model")
        for seed in config["seeds"]:
            for condition in config["probe_conditions"]:
                obs = probe_input(condition)
                Image.frombytes("L", (16, 16), bytes(round(v*255) for v in obs.pixels)).save(output / f"probe-{condition}.png")
                repetitions = []
                for repetition in range(config["probe_repetitions"]):
                    controller.reset(run_seed=seed, checkpoint=controller.checkpoint)
                    start = time.perf_counter()
                    action = controller.step_serialized(obs.model_dump_json().encode())
                    repetitions.append(dict(repetition=repetition, step_wall_seconds=time.perf_counter()-start,
                                            action=ControllerOutput.model_validate_json(action).model_dump()))
                if any(r["action"] != repetitions[0]["action"] for r in repetitions):
                    raise ValueError("Identical input/seed/checkpoint failed repetition")
                report["probes"].append(dict(seed=seed, condition=condition, step_index=0,
                    observation_sha256=pixels_hash(obs), action=repetitions[0]["action"], repetitions=repetitions))
        report["visual_pairs"] = summarize_visual_pairs(report["probes"])
        save(output / "report.json", report)
        for seed in config["seeds"]:
            for condition in config["episode_conditions"]:
                trial_id = f"dev-{seed}-{condition['id']}"
                trial_dir = output / trial_id
                trial_dir.mkdir()
                challenge = challenge_for(condition["destination_side"])
                arena = build_arena(challenge)
                raster = render(arena.scene)
                (trial_dir / "canonical.gray").write_bytes(raster)
                (trial_dir / "canonical.png").write_bytes(png_bytes(raster))
                controller.reset(run_seed=seed, checkpoint=controller.checkpoint)
                state, rows = initial_state(), []
                start_episode = time.perf_counter()
                print(f"START {trial_id}", flush=True)
                with (trial_dir / "trace.jsonl").open("x") as stream:
                    while state.outcome is None:
                        obs = (probe_input("dark") if condition["input"] == "dark" else
                               observation(raster, x_q=state.x_q, y_q=state.y_q))
                        start = time.perf_counter()
                        raw_action = ControllerOutput.model_validate_json(controller.step_serialized(obs.model_dump_json().encode()))
                        elapsed = time.perf_counter() - start
                        action = apply_scaling(raw_action, condition["motor_multiplier"])
                        after = step(arena, state, action)
                        row = dict(before=asdict(state), after=asdict(after), action=action.model_dump(),
                                   raw_action=raw_action.model_dump(), step_wall_seconds=elapsed,
                                   observation_sha256=pixels_hash(obs))
                        stream.write(json.dumps(row, allow_nan=False) + "\n")
                        stream.flush()
                        rows.append(row)
                        state = after
                        if state.tick % 64 == 0:
                            print(f"PROGRESS {trial_id} tick={state.tick} position=({state.x_q/Q:.2f},{state.y_q/Q:.2f})", flush=True)
                trial = dict(trial_id=trial_id, seed=seed, condition=condition, challenge=challenge.model_dump(),
                             frame_sha256=raster_sha256(raster), final_state=asdict(state),
                             elapsed_wall_seconds=time.perf_counter()-start_episode,
                             summary=summarize_trace(rows), trace_sha256=file_sha256(trial_dir / "trace.jsonl"))
                save(trial_dir / "trial.json", trial)
                overlay(trial_dir / "overlay.png", raster, rows, f"{trial_id}; input={condition['input']}; motor x{condition['motor_multiplier']}")
                report["trials"].append(trial)
                save(output / "report.json", report)
                print(f"DONE {trial_id}: {state.outcome}", flush=True)
        if controller.provenance != report["provenance"] or file_sha256(output / "baseline.json") != controller.checkpoint.sha256:
            raise ValueError("Model provenance or checkpoint changed")
        report["automated_status"] = "PASS"
    except Exception as error:
        report["automated_status"] = "FAIL"
        report["failures"].append(dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        raise
    finally:
        report["peak_process_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save(output / "report.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("experiments/feasibility-v1.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--graph-root", type=Path, default=Path("build/flytrap-v1"))
    parser.add_argument("--raw-root", type=Path, default=Path("data"))
    args = parser.parse_args()
    result = run(args.config, args.output, args.graph_root, args.raw_root)
    print(json.dumps({k: result[k] for k in ("automated_status", "peak_process_rss_bytes", "failures")}))
