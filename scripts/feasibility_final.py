"""One preregistered final development experiment; never retries neural calls."""

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

from flytrap.arena.core import build_arena, initial_state
from flytrap.arena.render import observation, render, png_bytes
from flytrap.arena.sliding import step_sliding
from flytrap.arena.tracking import tracking_observation, sample_coordinates as tracking_coordinates
from flytrap.controllers.fly import FlyController
from flytrap.data.bundle import file_sha256
from scripts.feasibility import challenge_for, environment, overlay, pixels_hash, probe_input, save, source_identity
from scripts.feasibility_final_motor import calibrate, calibration_basis
from scripts.feasibility_motor_telemetry import MotorRateDiagnostic
from scripts.feasibility_revision import sample_coordinates as old_coordinates

ROOT = Path("artifacts/milestones/05/final-sensorimotor")
CONFIG = Path("experiments/feasibility-final-v3.json")
PLAN = Path("docs/implementation/FEASIBILITY-05-FINAL-PLAN.md")
BASELINE = Path("artifacts/milestones/05/trials/baseline.json")
SNAPSHOTS = (0, 16, 32, 55, 64, 128, 192, 255)


def schedule():
    rows = []
    def add(stage, seed, crop, motor, side, kind, limit):
        rows.append(dict(id=f"{stage}-{seed}-{crop}-{motor}-{side}-{kind}", stage=stage,
                         seed=seed, crop=crop, motor=motor, layout=side, input=kind,
                         physics="tangent_v2", tick_limit=limit))
    for crop, motor in (("crop16_v1", "upstream_pilot_v1"),
                        ("tracking16_v3", "upstream_pilot_v1"),
                        ("tracking16_v3", "dark_balance_v3")):
        for side in ("left", "right"):
            add("screen", 51001, crop, motor, side, "canonical", 56)
    for motor in ("upstream_pilot_v1", "dark_balance_v3"):
        add("screen", 51001, "tracking16_v3", motor, "left", "dark", 56)
    for seed in (51003, 51004):
        for side, kind in (("left", "canonical"), ("right", "canonical"), ("left", "dark")):
            add("confirm", seed, "tracking16_v3", "dark_balance_v3", side, kind, 256)
    return rows


def coordinates(state, crop):
    if crop == "tracking16_v3":
        return tracking_coordinates(state.x_q, state.y_q)
    if crop == "crop16_v1":
        return old_coordinates(state, crop)
    raise ValueError("Unknown observation candidate")


def observe(raster, state, crop, kind):
    if kind == "dark":
        return probe_input("dark")
    if kind != "canonical":
        raise ValueError("Unknown input condition")
    fn = tracking_observation if crop == "tracking16_v3" else observation
    coordinates(state, crop)  # Reject unknown version, including overview.
    return fn(raster, x_q=state.x_q, y_q=state.y_q)


def declare():
    config = dict(schema_version="milestone05-final-development-3", human_review="CHANGES_REQUESTED",
                  plan_sha256=file_sha256(PLAN), calibration=calibration_basis(),
                  trials=schedule(), max_trial_calls=1984, real_regression_max_calls=4,
                  max_total_calls=1988, user_cap=2048, unused_calls=60,
                  wall_budget_seconds=1300, real_regression_timeout_seconds=120,
                  learning_enabled=False, model_parameters="config/flytrap-model-v1.json",
                  visual_calibration="config/flytrap-visual-v1.json", baseline_sha256=file_sha256(BASELINE),
                  runtime=environment(), prior_report_sha256=file_sha256(
                      Path("artifacts/milestones/05/revision/primary/report.json")))
    if CONFIG.exists() or (ROOT / "preregistration.json").exists():
        raise ValueError("Preregistration already frozen")
    save(CONFIG, config)
    save(ROOT / "preregistration.json", dict(declared_utc=datetime.now(timezone.utc).isoformat(),
         config_sha256=file_sha256(CONFIG), config=config, source=source_identity()))
    print(json.dumps(dict(config_sha256=file_sha256(CONFIG), trials=len(config["trials"]), max_calls=1988)))


class CallBudget:
    """Append and flush an attempt before invoking the actual model."""
    def __init__(self, stream, maximum):
        self.stream, self.maximum, self.calls = stream, maximum, 0

    def claim(self, trial_id, tick):
        if self.calls >= self.maximum:
            raise RuntimeError("Frozen model-call budget exhausted")
        self.calls += 1
        self.stream.write(json.dumps(dict(call=self.calls, trial=trial_id, tick=tick)) + "\n")
        self.stream.flush()


def expired(signum, frame):
    raise TimeoutError("Frozen trial wall budget exhausted; infrastructure termination")


def run():
    config = json.loads(CONFIG.read_text())
    frozen = json.loads((ROOT / "preregistration.json").read_text())
    if (file_sha256(CONFIG) != frozen["config_sha256"] or config != frozen["config"]
            or file_sha256(PLAN) != config["plan_sha256"] or config["trials"] != schedule()
            or calibration_basis() != config["calibration"]):
        raise ValueError("Frozen experiment configuration changed")
    output = ROOT / "trials"
    output.mkdir(exist_ok=False)
    report = dict(status="RUNNING", fixture=False, learning_enabled=False,
                  human_review="CHANGES_REQUESTED", started_utc=datetime.now(timezone.utc).isoformat(),
                  config_sha256=file_sha256(CONFIG), source=source_identity(), environment=environment(),
                  trials=[dict(t, status="NOT_RUN") for t in config["trials"]], phases={})
    save(output / "report.json", report)
    (output / "baseline.json").write_bytes(BASELINE.read_bytes())
    started = time.perf_counter()
    previous = signal.signal(signal.SIGALRM, expired)
    signal.alarm(config["wall_budget_seconds"])
    budget = None
    try:
        start_load = time.perf_counter()
        controller = FlyController(graph_root=Path("build/flytrap-v1"),
            annotations_path=Path("data/body-annotations.feather"),
            parameters_path=Path(config["model_parameters"]), calibration_path=Path(config["visual_calibration"]),
            checkpoint_path=output / "baseline.json")
        report["controller_load_seconds"] = time.perf_counter()-start_load
        report["provenance"] = controller.provenance
        if controller.provenance["fixture"] or controller.provenance["learning_enabled"]:
            raise ValueError("Real untrained baseline required")
        with (output / "calls.jsonl").open("x") as ledger, MotorRateDiagnostic(controller) as diagnostic:
            budget = CallBudget(ledger, config["max_trial_calls"])
            for trial in report["trials"]:
                if trial["stage"] == "confirm" and "confirmation-freeze.json" not in report:
                    freeze = dict(config_sha256=file_sha256(CONFIG),
                        motor_source_sha256=file_sha256(Path("scripts/feasibility_final_motor.py")),
                        frozen_utc=datetime.now(timezone.utc).isoformat(), calibration=config["calibration"],
                        completed_screening_calls=budget.calls, parameters_changed=False)
                    save(output / "confirmation-freeze.json", freeze)
                    report["confirmation-freeze.json"] = file_sha256(output / "confirmation-freeze.json")
                phase = report["phases"].setdefault(trial["stage"], dict(calls=0, elapsed_trial_seconds=0.0))
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
                    while state.outcome is None and state.tick < trial["tick_limit"]:
                        obs = observe(raster, state, trial["crop"], trial["input"])
                        budget.claim(trial["id"], state.tick)
                        phase["calls"] += 1
                        start_step = time.perf_counter()
                        raw = controller.step(obs)
                        elapsed = time.perf_counter()-start_step
                        if diagnostic.rates is None or diagnostic.error:
                            raise ValueError(f"Motor telemetry failed: {diagnostic.error}")
                        action = calibrate(raw, diagnostic.rates, trial["motor"])
                        after = step_sliding(arena, state, action)
                        xs, ys = coordinates(state, trial["crop"])
                        pixels = bytes(round(v*255) for v in obs.pixels)
                        row = dict(before=asdict(state), after=asdict(after), action=action.model_dump(),
                            raw_action=raw.model_dump(), step_wall_seconds=elapsed, motor_rates=diagnostic.rates,
                            observation_sha256=pixels_hash(obs), observation_pixels=list(pixels),
                            sample_xs=xs, sample_ys=ys)
                        stream.write(json.dumps(row, allow_nan=False) + "\n")
                        stream.flush()
                        rows.append(row)
                        if state.tick in SNAPSHOTS:
                            Image.frombytes("L", (16, 16), pixels).save(directory / f"input-{state.tick:03}.png")
                        state = after
                        if state.tick % 32 == 0:
                            print(f"PROGRESS {trial['id']} tick={state.tick} calls={budget.calls}", flush=True)
                trial.update(status="PASS", ticks=len(rows), final_state=asdict(state), outcome=state.outcome,
                    termination="terminal" if state.outcome else "diagnostic_cutoff",
                    elapsed_wall_seconds=time.perf_counter()-start_episode,
                    trace_sha256=file_sha256(directory / "trace.jsonl"))
                phase["elapsed_trial_seconds"] += trial["elapsed_wall_seconds"]
                overlay(directory / "trajectory.png", raster, rows, trial["id"])
                if state.outcome is None:
                    with Image.open(directory / "trajectory.png") as picture:
                        draw = ImageDraw.Draw(picture)
                        draw.rectangle((0, 40, 575, 58), fill="#eeeeee")
                        draw.text((10, 42), f"INCOMPLETE diagnostic cutoff: {state.tick}/256 ticks", fill="black")
                        picture.save(directory / "trajectory.png")
                save(output / "report.json", report)
                print(f"DONE {trial['id']}: {trial['termination']} {state.outcome}", flush=True)
            if budget.calls != diagnostic.calls:
                raise ValueError("Attempt ledger and pilot calls disagree")
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
        signal.signal(signal.SIGALRM, previous)
        report["neural_calls"] = budget.calls if budget else 0
        report["elapsed_wall_seconds"] = time.perf_counter()-started
        report["peak_process_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save(output / "report.json", report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["declare", "run"])
    args = parser.parse_args()
    declare() if args.mode == "declare" else run()
