"""Recompute development metrics and image sheets from every scheduled trace."""

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics

from PIL import Image, ImageDraw

from flytrap.arena.core import State, build_arena
from scripts.feasibility import challenge_for, save
from scripts.feasibility_revision import PHYSICS, observe, sample_coordinates
from scripts.feasibility_trace_diagnostics import diagnose_rows


def visibility_for(crop):
    def inspect(scene, state):
        xs, ys = sample_coordinates(state, crop)
        counts = {side: sum(p.x0 <= x < p.x1 and p.y0 <= y < p.y1 for y in ys for x in xs)
                  for side, p in (("left", scene.left_pad), ("right", scene.right_pad))}
        return dict(sample_x=xs, sample_y=ys, pad_samples=counts, any_pad_samples=any(counts.values()))
    return inspect


def rates_summary(rows):
    if not rows:
        return dict(ticks=0)
    keys = ("steer_L", "steer_R", "fwd_L", "fwd_R", "back", "stop")
    def values(key):
        return [r["motor_rates"][key] for r in rows]
    return dict(ticks=len(rows), rates_hz={key: dict(mean=statistics.mean(values(key)),
                minimum=min(values(key)), maximum=max(values(key))) for key in keys},
                mdn_exceeds_mean_dna01_ticks=sum(r["motor_rates"]["back"] >
                    (r["motor_rates"]["fwd_L"]+r["motor_rates"]["fwd_R"])/2 for r in rows),
                stop_at_least_450_hz_ticks=sum(r["motor_rates"]["stop"] >= 450 for r in rows),
                downward_requested_ticks=sum(r["action"]["dy"] > 0 for r in rows),
                upward_requested_ticks=sum(r["action"]["dy"] < 0 for r in rows))


def compare(a, b):
    """Compare shared environment ticks, retaining unequal terminal lengths.

    Both traces must begin at tick zero and contain every consecutive action.
    Endpoint distance is separately labeled because endpoints can occur at
    different ticks when one episode reaches a terminal pad earlier.
    """
    for rows in (a, b):
        if not rows:
            raise ValueError("Cannot compare empty traces")
        if any(row["before"]["tick"] != index or row["after"]["tick"] != index + 1
               for index, row in enumerate(rows)):
            raise ValueError("Comparison requires complete consecutive ticks from zero")
    pairs = list(zip(a, b))
    def xy(row):
        return row["after"]["x_q"], row["after"]["y_q"]
    return dict(matched_ticks=len(pairs), a_ticks=len(a), b_ticks=len(b),
                last_common_tick=pairs[-1][0]["after"]["tick"],
                different_inputs=sum(x["observation_sha256"] != y["observation_sha256"] for x, y in pairs),
                different_motor_actions=sum((x["action"]["dx"], x["action"]["dy"], x["action"]["click"]) !=
                                           (y["action"]["dx"], y["action"]["dy"], y["action"]["click"]) for x, y in pairs),
                different_positions=sum(xy(x) != xy(y) for x, y in pairs),
                separation_at_last_common_tick_pixels=math.dist(xy(pairs[-1][0]), xy(pairs[-1][1]))/256,
                endpoint_separation_pixels=math.dist(xy(a[-1]), xy(b[-1]))/256)


def image_sheet(records, output, kind):
    selected = [r for r in records if r["input"] == kind]
    if not selected:
        return
    sheet = Image.new("RGB", (4*384, math.ceil(len(selected)/4)*400), "white")
    draw = ImageDraw.Draw(sheet)
    for index, trial in enumerate(selected):
        x, y = (index % 4)*384, (index//4)*400
        directory = Path(trial["directory"])
        ticks = trial["ticks"]
        label = f"{trial['physics']} / {trial['crop']}"
        draw.text((x+8, y+6), label, fill="black")
        draw.text((x+8, y+22), f"seed {trial['seed']} / {trial['layout']} / {kind} / {ticks} ticks", fill="black")
        with Image.open(directory / "trajectory.png") as trajectory:
            # Scene with actual recorded path, no labels from a resized screenshot.
            scene = trajectory.crop((0, 60, 576, 636)).resize((288, 288), Image.Resampling.NEAREST)
            sheet.paste(scene, (x+8, y+42))
        available = sorted((int(path.stem.split("-")[1]), path) for path in directory.glob("input-*.png"))
        available = [(tick, path) for tick, path in available if 0 <= tick < ticks]
        if not available or available[0][0] != 0:
            raise ValueError("Trajectory sheet requires the actual initial input image")
        # Select genuine saved snapshots; early terminal runs need not have tick 95.
        selected_inputs = [available[i] for i in sorted({0, len(available)//2, len(available)-1})]
        for k, (tick, path) in enumerate(selected_inputs):
            with Image.open(path) as exact:
                sheet.paste(exact.resize((64, 64), Image.Resampling.NEAREST).convert("RGB"), (x+308, y+42+92*k))
            draw.text((x+308, y+109+92*k), f"input {tick}", fill="black")
        metric = trial["diagnosis"]
        stationary = sum(metric["stationary_causes"].values())
        outcome = trial["outcome"]
        outcome_label = f"TERMINAL: {outcome}" if outcome is not None else "INCOMPLETE cutoff"
        draw.text((x+8, y+342), f"{outcome_label}; stationary {stationary}/{ticks}", fill="black")
        draw.text((x+8, y+359), f"Pad-visible inputs {metric['controller_pad_visible_observation_count']}/{ticks}", fill="black")
        draw.text((x+8, y+376), "Blue start; red actual path/end. No learning.", fill="black")
    sheet.save(output / f"{kind}-trajectories-inputs.png")


def analyze(roots, output):
    output.mkdir(parents=True, exist_ok=False)
    records, traces, phase_records = [], {}, []
    matched_observations = defaultdict(list)
    for root in roots:
        report = json.loads((root / "report.json").read_text())
        if report["status"] != "PASS":
            raise ValueError("Cannot summarize incomplete scheduled comparison as passing")
        phase_records.append({key: report[key] for key in
                              ("stage", "status", "elapsed_wall_seconds", "neural_calls", "peak_process_rss_bytes")})
        for trial in report["trials"]:
            directory = root / trial["id"]
            rows = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
            traces[trial["id"]] = rows
            arena = build_arena(challenge_for(trial["layout"]))
            crop = trial["crop"]
            def samples(raster, *, x_q, y_q):
                obs = observe(raster, State(x_q, y_q), crop, "canonical")
                return bytes(round(v*255) for v in obs.pixels)
            diagnosis = diagnose_rows(rows, arena, blank=trial["input"] == "dark",
                physics_step=PHYSICS[trial["physics"]], sample_fn=samples, visibility_fn=visibility_for(crop))
            save(output / f"{trial['id']}-diagnosis.json", diagnosis)
            first = diagnosis["first_wall_contact_tick"]
            groups = dict(all=rows,
                          before_contact=[r for r in rows if first is None or r["after"]["tick"] < first],
                          after_contact=[r for r in rows if first is not None and r["after"]["tick"] > first],
                          at_wall=[r for r in rows if r["before"]["x_q"] in (1024,23552)
                                   or r["before"]["y_q"] in (1024,23552)])
            records.append(dict(trial, directory=str(directory), diagnosis={k:v for k,v in diagnosis.items() if k != "rows"},
                                motor_rates={k:rates_summary(v) for k,v in groups.items()}))
            for row in rows:
                key = (trial["seed"], row["before"]["tick"], row["observation_sha256"])
                matched_observations[key].append((trial["id"], row["action"], row["motor_rates"]))
    # Exact matching uses run seed, internal step index and input bytes/hash.
    matched = [values for values in matched_observations.values() if len(values) > 1]
    equal = all(all(value[1:] == values[0][1:] for value in values) for values in matched)
    if not equal:
        raise ValueError("Identical seed/window/pixels yielded different rates/actions")
    history = []
    for trial in records:
        if trial["physics"] != "no_sliding_v1":
            continue
        suffix = "blank_left" if trial["input"] == "dark" else trial["layout"]
        historical = Path(f"artifacts/milestones/05/trials/dev-{trial['seed']}-{suffix}/trace.jsonl")
        old = [json.loads(line) for line in historical.read_text().splitlines()]
        new = traces[trial["id"]]
        same = len(new) <= len(old) and all(all(a[key] == b[key] for key in ("before", "after", "action", "observation_sha256"))
                   for a,b in zip(new, old))
        if not same:
            raise ValueError("Instrumented real v1 differs from original historical sequence")
        history.append(dict(trial=trial["id"], old=str(historical), matching_ticks=len(new)))
    comparisons = []
    by = {(r["physics"],r["crop"],r["seed"],r["layout"],r["input"]):r for r in records}
    for key, a in by.items():
        physics,crop,seed,side,kind = key
        alternatives = []
        if kind == "canonical":
            alternatives.append(("visual_vs_black", (physics,crop,seed,side,"dark")))
        if side == "left":
            alternatives.append(("swapped_layouts", (physics,crop,seed,"right",kind)))
        if physics == "no_sliding_v1":
            alternatives.append(("physics_only", ("tangent_v2",crop,seed,side,kind)))
        if physics == "tangent_v2" and crop == "crop16_v1":
            alternatives.append(("observation_only", (physics,"overview16_v2",seed,side,kind)))
        for label, other_key in alternatives:
            if other_key in by:
                b = by[other_key]
                comparisons.append(dict(kind=label, a=a["id"], b=b["id"], **compare(traces[a["id"]],traces[b["id"]])))
    analysis_source_paths = ("scripts/feasibility_revision_analysis.py", "scripts/feasibility_trace_diagnostics.py")
    result = dict(analysis_source_sha256={path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                                        for path in analysis_source_paths},
                  input_report_sha256={str(root / "report.json"): hashlib.sha256((root / "report.json").read_bytes()).hexdigest()
                                       for root in roots}, human_review="PENDING", learning_claim_status="NOT_RUN", phases=phase_records, trials=records,
                  matching_seed_window_observation_groups=len(matched), matched_rates_actions_equal=equal,
                  historical_real_neutrality=history, comparisons=comparisons,
                  limitations="96-tick development cutoffs are incomplete; no estimated full-episode success rate or learning evidence")
    save(output / "report.json", result)
    for kind in ("canonical", "dark"):
        image_sheet(records, output, kind)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.roots, args.output)
