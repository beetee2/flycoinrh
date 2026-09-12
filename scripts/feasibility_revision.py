"""Predeclared, bounded milestone-05 development comparison, with passive rates."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import resource
import signal
import time
import traceback

from PIL import Image, ImageDraw

from flytrap.arena.core import build_arena, initial_state, step
from flytrap.arena.overview import SAMPLE_COORDINATES, overview_observation
from flytrap.arena.render import observation, png_bytes, render
from flytrap.arena.sliding import step_sliding
from flytrap.controllers.fly import FlyController
from flytrap.data.bundle import file_sha256
from scripts.feasibility import challenge_for, environment, overlay, pixels_hash, probe_input, save, source_identity
from scripts.feasibility_motor_telemetry import MotorRateDiagnostic

CONFIG = Path("experiments/feasibility-revision-v2.json")
PHYSICS = {"no_sliding_v1": step, "tangent_v2": step_sliding}


def sample_coordinates(state, crop):
    if crop == "overview16_v2":
        return list(SAMPLE_COORDINATES), list(SAMPLE_COORDINATES)
    if crop != "crop16_v1":
        raise ValueError("Unknown crop")
    return tuple([min(95, max(0, (v + (-60 + 8*i)*256)//256)) for i in range(16)]
                 for v in (state.x_q, state.y_q))


def observe(raster, state, crop, input_kind):
    if input_kind == "dark":
        return probe_input("dark")
    if input_kind != "canonical":
        raise ValueError("Unknown input")
    if crop == "overview16_v2":
        return overview_observation(raster)
    if crop != "crop16_v1":
        raise ValueError("Unknown crop")
    return observation(raster, x_q=state.x_q, y_q=state.y_q)


def pad_samples(arena, state, crop):
    xs, ys = sample_coordinates(state, crop)
    return sum(p.x0 <= x < p.x1 and p.y0 <= y < p.y1
               for p in (arena.scene.left_pad, arena.scene.right_pad) for y in ys for x in xs)


def schedule(config, stage):
    versions = config["physics"] if stage == "physics" else ["tangent_v2"]
    crop = config["primary_crop"] if stage == "physics" else config["optional_crop"]
    return [dict(id=f"{physics}-{crop}-{seed}-{side}-{kind}", physics=physics, crop=crop,
                 seed=seed, layout=side, input=kind)
            for physics in versions for seed in config["seeds"] for side in config["layouts"]
            for kind in config["inputs"]]


def deadline(signum, frame):
    raise TimeoutError("Predeclared phase wall budget exhausted")


def run(output, stage, primary):
    config = json.loads(CONFIG.read_text())
    trigger = None
    if stage == "overview":
        prior = json.loads((primary / "report.json").read_text())
        if prior["status"] != "PASS" or prior["config_sha256"] != file_sha256(CONFIG):
            raise ValueError("Completed matched primary evidence required")
        selected = [trial for trial in prior["trials"]
                    if trial["physics"] == "tangent_v2" and trial["input"] == "canonical"]
        total = sum(trial["ticks"] for trial in selected)
        absent = sum(trial["cue_free_ticks"] for trial in selected)
        trigger = dict(primary_report_sha256=file_sha256(primary / "report.json"),
                       cue_free_ticks=absent, ticks=total, fraction=absent/total)
        if trigger["fraction"] < 0.5:
            raise ValueError("Predeclared optional sensory experiment trigger not met")
    output.mkdir(parents=True, exist_ok=False)
    report = dict(schema_version="milestone05-revision-evidence-2", status="RUNNING", stage=stage,
                  started_utc=datetime.now(timezone.utc).isoformat(), human_review="PENDING",
                  fixture=False, learning_enabled=False, learning_claim_status="NOT_RUN",
                  config=config, config_sha256=file_sha256(CONFIG), source=source_identity(),
                  environment=environment(), trigger=trigger, trials=schedule(config, stage))
    for trial in report["trials"]:
        trial["status"] = "NOT_RUN"
    save(output / "report.json", report)
    (output / "config.json").write_bytes(CONFIG.read_bytes())
    start_phase = time.perf_counter()
    previous_handler = signal.signal(signal.SIGALRM, deadline)
    budget = config["primary_wall_budget_seconds" if stage == "physics" else "optional_wall_budget_seconds"]
    signal.alarm(budget)
    try:
        baseline = Path("artifacts/milestones/05/trials/baseline.json")
        (output / "baseline.json").write_bytes(baseline.read_bytes())
        start_load = time.perf_counter()
        controller = FlyController(graph_root=Path("build/flytrap-v1"),
            annotations_path=Path("data/body-annotations.feather"),
            parameters_path=Path(config["model_parameters"]), calibration_path=Path(config["visual_calibration"]),
            checkpoint_path=output / "baseline.json")
        report["controller_load_seconds"] = time.perf_counter()-start_load
        report["provenance"] = controller.provenance
        if controller.provenance["fixture"] or controller.provenance["learning_enabled"]:
            raise ValueError("Real untrained model required")
        with MotorRateDiagnostic(controller) as diagnostic:
            for trial in report["trials"]:
                directory = output / trial["id"]
                directory.mkdir()
                trial["status"] = "RUNNING"
                save(output / "report.json", report)
                arena = build_arena(challenge_for(trial["layout"]))
                raster = render(arena.scene)
                (directory / "canonical.gray").write_bytes(raster)
                (directory / "canonical.png").write_bytes(png_bytes(raster))
                controller.reset(run_seed=trial["seed"], checkpoint=controller.checkpoint)
                state, rows = initial_state(), []
                start_episode = time.perf_counter()
                print(f"START {trial['id']}", flush=True)
                with (directory / "trace.jsonl").open("x") as stream:
                    while state.outcome is None and state.tick < config["diagnostic_tick_limit"]:
                        obs = observe(raster, state, trial["crop"], trial["input"])
                        started = time.perf_counter()
                        action = controller.step(obs)
                        elapsed = time.perf_counter()-started
                        if diagnostic.rates is None or diagnostic.error:
                            raise ValueError(f"Motor diagnostic failed: {diagnostic.error}")
                        after = PHYSICS[trial["physics"]](arena, state, action)
                        xs, ys = sample_coordinates(state, trial["crop"])
                        pixels = bytes(round(v*255) for v in obs.pixels)
                        row = dict(before=asdict(state), after=asdict(after), action=action.model_dump(),
                                   raw_action=action.model_dump(), step_wall_seconds=elapsed,
                                   motor_rates=diagnostic.rates, observation_sha256=pixels_hash(obs),
                                   observation_pixels=list(pixels), sample_xs=xs, sample_ys=ys,
                                   pad_sample_count=pad_samples(arena, state, trial["crop"]))
                        stream.write(json.dumps(row, allow_nan=False) + "\n")
                        stream.flush()
                        rows.append(row)
                        if state.tick in (0, 16, 32, 64, 95):
                            Image.frombytes("L", (16, 16), pixels).save(directory / f"input-{state.tick:03}.png")
                        state = after
                        if state.tick % 32 == 0:
                            print(f"PROGRESS {trial['id']} tick={state.tick}", flush=True)
                trial.update(status="PASS", ticks=len(rows), final_state=asdict(state),
                             outcome=state.outcome, termination="terminal" if state.outcome else "diagnostic_cutoff",
                             elapsed_wall_seconds=time.perf_counter()-start_episode,
                             cue_free_ticks=sum(r["pad_sample_count"] == 0 for r in rows),
                             trace_sha256=file_sha256(directory / "trace.jsonl"))
                overlay(directory / "trajectory.png", raster, rows, trial["id"])
                if state.outcome is None:
                    with Image.open(directory / "trajectory.png") as picture:
                        draw = ImageDraw.Draw(picture)
                        draw.rectangle((0, 40, 575, 58), fill="#eeeeee")
                        draw.text((10, 42), f"INCOMPLETE: diagnostic cutoff at {state.tick}/256 ticks; no pad contact",
                                  fill="black")
                        picture.save(directory / "trajectory.png")
                save(output / "report.json", report)
                print(f"DONE {trial['id']}: {trial['termination']} outcome={state.outcome}", flush=True)
            report["neural_calls"] = diagnostic.calls
        report["status"] = "PASS"
    except Exception as error:
        report["status"] = "FAIL"
        report["error"] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
        for trial in report["trials"]:
            if trial["status"] == "RUNNING":
                trial["status"] = "FAIL"
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)
        report["elapsed_wall_seconds"] = time.perf_counter()-start_phase
        report["peak_process_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save(output / "report.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["physics", "overview"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--primary", type=Path, default=Path("artifacts/milestones/05/revision/primary"))
    args = parser.parse_args()
    run(args.output, args.stage, args.primary)
