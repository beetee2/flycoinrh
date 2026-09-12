"""Replay all eight historical action logs under tangent_v2 without neural calls.

Every input row is retained. Candidate observation pixels describe the altered
path but were never supplied to a controller. Results are open-loop mechanics.
"""

import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time

from PIL import Image, ImageDraw

from flytrap.arena.core import MAX_COORD, MIN_COORD, MOVEMENT_PER_TICK, Q, State, build_arena, initial_state, step
from flytrap.arena.render import _samples, render
from flytrap.arena.sliding import PHYSICS_VERSION, step_sliding
from flytrap.contracts import ChallengeSpec, ControllerOutput
from scripts.feasibility_trace_diagnostics import contacts, visibility

LABEL = "COUNTERFACTUAL old actions; no neural rerun"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(rows, arena, physics):
    causes = dict(zero_motor=0, quantization=0, collision=0)
    dwell = {name: 0 for name in ("left", "right", "top", "bottom")}
    canceled = []
    wall_stationary = 0
    for row in rows:
        before, after = State(**row["before"]), State(**row["after"])
        action = ControllerOutput.model_validate(row["action"])
        delta = [math.trunc(v * MOVEMENT_PER_TICK * Q) for v in (action.dx, action.dy)]
        actual = [after.x_q - before.x_q, after.y_q - before.y_q]
        stationary = not any(actual)
        active = contacts(before)
        for wall in active:
            dwell[wall] += 1
        if stationary:
            key = "zero_motor" if action.dx == action.dy == 0 else "quantization" if not any(delta) else "collision"
            causes[key] += 1
            wall_stationary += bool(active)
        for axis, (coordinate, requested) in enumerate(zip((before.x_q, before.y_q), delta)):
            if ((coordinate == MIN_COORD * Q and requested < 0)
                    or (coordinate == MAX_COORD * Q and requested > 0)):
                tangent_action = action.model_copy(update={"dx" if axis == 0 else "dy": 0.0})
                tangent_after = physics(arena, before, tangent_action)
                tangent = (tangent_after.x_q - before.x_q, tangent_after.y_q - before.y_q)[1 - axis]
                if tangent != 0 and actual[1 - axis] == 0:
                    canceled.append(after.tick)
                    break
    return dict(ticks=len(rows), final_state=rows[-1]["after"], outcome=rows[-1]["after"]["outcome"],
                pad_contacts=int(rows[-1]["after"]["outcome"] in ("success", "wrong_pad")),
                stationary_ticks=sum(causes.values()), stationary_causes=causes,
                wall_stationary_ticks=wall_stationary, wall_dwell_ticks=dwell,
                canceled_legal_tangent_ticks=canceled)


def draw_paths(path, raster, original, candidate, name, before, after):
    canvas = Image.new("RGB", (576, 700), "#eeeeee")
    canvas.paste(Image.frombytes("L", (96, 96), raster).resize((576, 576), Image.Resampling.NEAREST), (0, 80))
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 8), LABEL, fill="black")
    draw.text((10, 25), name, fill="black")
    draw.text((10, 42), f"v1 {before['outcome']} / tangent_v2 {after['outcome']}", fill="black")
    draw.text((10, 59), f"Stationary ticks: {before['stationary_ticks']} -> {after['stationary_ticks']}", fill="black")
    for rows, color, width in ((original, "#e26910", 4), (candidate, "#008ac0", 2)):
        positions = [rows[0]["before"]] + [r["after"] for r in rows]
        points = [(s["x_q"] / Q * 6, s["y_q"] / Q * 6 + 80) for s in positions]
        draw.line(points, fill=color, width=width)
        x, y = points[-1]
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), outline=color, width=2)
    draw.text((10, 663), "Orange: historical v1. Blue: candidate using old actions.", fill="black")
    draw.text((10, 680), "Candidate pixels were never passed to the neural controller.", fill="black")
    canvas.save(path)
    return canvas


def run(source, output):
    started = time.perf_counter()
    directories = sorted(source.glob("dev-*"))
    if len(directories) != 8:
        raise ValueError("Exactly eight historical episodes required")
    output.mkdir(parents=True, exist_ok=False)
    source_paths = [Path(__file__), Path("flytrap/arena/core.py"), Path("flytrap/arena/sliding.py"),
                    Path("flytrap/arena/render.py"), Path("scripts/feasibility_trace_diagnostics.py")]
    report = dict(label=LABEL, physics_version=PHYSICS_VERSION, neural_calls=0, learning_enabled=False,
                  limitations="Old actions remain fixed despite changed observations. No closed-loop behavior or competence claim.",
                  timing="Only local replay runtime is measured. No historical neural latency is attributed to candidate states.",
                  source_head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                  source_sha256={str(p): digest(p) for p in source_paths}, episodes={})
    montage = Image.new("RGB", (576 * 4, 700 * 2), "white")
    for index, directory in enumerate(directories):
        trial = json.loads((directory / "trial.json").read_text())
        if digest(directory / "trace.jsonl") != trial["trace_sha256"]:
            raise ValueError("Historical trace digest mismatch")
        old = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
        if len(old) != 256:
            raise ValueError("Historical trace must be complete")
        arena = build_arena(ChallengeSpec.model_validate(trial["challenge"]))
        raster = render(arena.scene)
        blank = trial["condition"]["input"] == "dark"
        candidate, full_rows = [], []
        state, original_state = initial_state(), initial_state()
        for original in old:
            action = ControllerOutput.model_validate(original["action"])
            if State(**original["before"]) != original_state:
                raise ValueError("Historical state chain mismatch")
            original_state = step(arena, original_state, action)
            if asdict(original_state) != original["after"]:
                raise ValueError("Historical physics replay mismatch")
            record = dict(label=LABEL, historical_row=original, candidate_applied=state.outcome is None)
            if state.outcome is None:
                after = step_sliding(arena, state, action)
                pixels = bytes(256) if blank else _samples(raster, x_q=state.x_q, y_q=state.y_q)
                row = dict(before=asdict(state), after=asdict(after), action=original["action"],
                           candidate_unconsumed_observation_pixels=list(pixels),
                           candidate_unconsumed_observation_sha256=hashlib.sha256(pixels).hexdigest(),
                           geometry=visibility(arena.scene, state),
                           historical_input_sha256=original["observation_sha256"])
                candidate.append(row)
                record["candidate"] = row
                state = after
            full_rows.append(record)
        before, after = metrics(old, arena, step), metrics(candidate, arena, step_sliding)
        target = output / directory.name
        target.mkdir()
        (target / "trace.jsonl").write_text("".join(json.dumps(row, allow_nan=False) + "\n" for row in full_rows))
        picture = draw_paths(target / "trajectory.png", raster, old, candidate, directory.name, before, after)
        montage.paste(picture, ((index % 4) * 576, (index // 4) * 700))
        report["episodes"][directory.name] = dict(
            condition=trial["condition"], historical_trace_sha256=digest(directory / "trace.jsonl"),
            counterfactual_trace_sha256=digest(target / "trace.jsonl"), scheduled_old_actions=len(old),
            unused_old_actions=len(old) - len(candidate), v1=before, candidate=after,
            delta_stationary_ticks=after["stationary_ticks"] - before["stationary_ticks"],
            delta_canceled_tangent_ticks=len(after["canceled_legal_tangent_ticks"]) - len(before["canceled_legal_tangent_ticks"]),
            candidate_geometric_cue_visible_ticks=sum(r["geometry"]["any_pad_samples"] for r in candidate),
            candidate_controller_cue_visible_ticks=0 if blank else sum(r["geometry"]["any_pad_samples"] for r in candidate),
            changed_unconsumed_observations=sum(r["candidate_unconsumed_observation_sha256"] != r["historical_input_sha256"]
                                               for r in candidate))
    montage.save(output / "trajectories.png")
    report["runtime_seconds"] = time.perf_counter() - started
    report["status"] = "PASS"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({name: {key: value for key, value in result.items() if key.startswith("delta_")}
                      for name, result in report["episodes"].items()}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("artifacts/milestones/05/trials"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/milestones/05/revision/counterfactual"))
    args = parser.parse_args()
    run(args.input, args.output)
