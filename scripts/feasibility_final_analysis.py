"""Recompute final diagnostic motion, feedback, comparisons, and exact black controls."""

import argparse
from collections import defaultdict
from dataclasses import asdict
import json
import math
from pathlib import Path
import statistics

from PIL import Image, ImageDraw

from flytrap.arena.core import State, build_arena, initial_state
from flytrap.arena.render import render, png_bytes
from flytrap.arena.sliding import step_sliding
from flytrap.contracts import ControllerOutput
from flytrap.data.bundle import file_sha256
from scripts.feasibility import challenge_for, overlay, save
from scripts.feasibility_analysis import summarize_trace
from scripts.feasibility_final import ROOT, SNAPSHOTS, coordinates
from scripts.feasibility_final_motor import calibrate
from scripts.feasibility_revision_analysis import compare
from scripts.feasibility_trace_diagnostics import contacts


def metrics(rows, trial):
    """All motion sums use pixels, dwell uses BEFORE-state environment ticks."""
    summary = summarize_trace(rows)
    arena = build_arena(challenge_for(trial["layout"]))
    raster = render(arena.scene)
    walls = {name: 0 for name in ("left", "right", "top", "bottom",
                                "left_top", "left_bottom", "right_top", "right_bottom")}
    motion = {name: [0.0, 0.0] for name in ("raw_requested", "requested", "quantized", "executed")}
    directions = {name: 0 for name in ("left", "right", "up", "down")}
    stationary = {name: 0 for name in ("zero_motor", "quantization", "collision")}
    visible = both_visible = contrast = moving = changed = adjacent_changes = band = outward = 0
    first_wall = None
    for i, row in enumerate(rows):
        before, after = State(**row["before"]), State(**row["after"])
        active = contacts(before)
        if first_wall is None and contacts(after):
            first_wall = after.tick
        for name in active + (["_".join(active)] if len(active) == 2 else []):
            walls[name] += 1
        band += min(before.x_q-1024,23552-before.x_q,before.y_q-1024,23552-before.y_q) <= 8*256
        raw = [row["raw_action"][axis]*8 for axis in ("dx", "dy")]
        request = [row["action"][axis]*8 for axis in ("dx", "dy")]
        quantized = [math.trunc(v*256)/256 for v in request]
        executed = [(after.x_q-before.x_q)/256, (after.y_q-before.y_q)/256]
        for name, values in (("raw_requested", raw), ("requested", request),
                             ("quantized", quantized), ("executed", executed)):
            for axis in (0, 1):
                motion[name][axis] += values[axis]
        directions["left"] += request[0] < 0
        directions["right"] += request[0] > 0
        directions["up"] += request[1] < 0
        directions["down"] += request[1] > 0
        outward += (("left" in active and request[0] < 0) or ("right" in active and request[0] > 0)
                    or ("top" in active and request[1] < 0) or ("bottom" in active and request[1] > 0))
        if not any(executed):
            stationary["zero_motor" if not any(request) else "quantization" if not any(quantized) else "collision"] += 1
        xs, ys = coordinates(before, trial["crop"])
        pad_values = [[raster[y*96+x] for y in ys for x in xs
                       if p.x0 <= x < p.x1 and p.y0 <= y < p.y1]
                      for p in (arena.scene.left_pad, arena.scene.right_pad)]
        if trial["input"] != "dark":
            visible += any(pad_values)
            both_visible += all(pad_values)
            contrast += all(set(v) == {0, 255} for v in pad_values)
        if i + 1 < len(rows):
            different = row["observation_sha256"] != rows[i+1]["observation_sha256"]
            adjacent_changes += different
            if any(executed):
                moving += 1
                changed += different
    states = [rows[0]["before"]] + [r["after"] for r in rows]
    bins = {(min(11, s["x_q"]//2048), min(11, s["y_q"]//2048)) for s in states}
    rates = {k: statistics.mean(r["motor_rates"][k] for r in rows) for k in rows[0]["motor_rates"]}
    return dict(summary=summary, motion_pixels=motion,
        mean_requested_pixels=[v/len(rows) for v in motion["requested"]], directions=directions,
        wall_corner_before_ticks=walls, boundary_band_before_ticks=band,
        boundary_band_fraction=band/len(rows), exact_wall_before_ticks=sum(
            bool(contacts(State(**r["before"]))) for r in rows), outward_at_wall_ticks=outward,
        first_wall_contact_tick=first_wall, stationary_causes=stationary,
        any_pad_visible_inputs=visible, both_pads_visible_inputs=both_visible,
        both_pads_contrast_inputs=contrast, adjacent_input_changes=adjacent_changes,
        moved_steps_with_next_input=moving, movement_followed_by_changed_input=changed,
        visited_8px_bins=len(bins), visited_bin_coordinates=sorted(bins),
        x_extent_pixels=[min(s["x_q"] for s in states)/256,max(s["x_q"] for s in states)/256],
        y_extent_pixels=[min(s["y_q"] for s in states)/256,max(s["y_q"] for s in states)/256],
        pad_contacts=int(rows[-1]["after"]["outcome"] in ("success", "wrong_pad")), mean_rates_hz=rates)


def derive_black(source, rows, output, side, motor):
    """Exact reuse: black pixels and reset window seeds do not depend on position."""
    if source["input"] != "dark" or any(r["observation_pixels"] != [0]*256 for r in rows):
        raise ValueError("Only identical all-black input allows this rate-sequence reuse")
    trial = dict(source, id=f"derived-{source['stage']}-{source['seed']}-{motor}-{side}-dark",
                 layout=side, motor=motor, derived=True, source_trial=source["id"],
                 source_trace_sha256=source["trace_sha256"], additional_model_calls=0)
    trial.pop("metrics", None)  # The derived path needs its own recomputed metrics.
    directory = output / trial["id"]
    directory.mkdir()
    trial["directory"] = str(directory)
    arena = build_arena(challenge_for(side))
    raster = render(arena.scene)
    state, derived = initial_state(), []
    for row in rows:
        if state.outcome is not None:
            break
        raw = ControllerOutput.model_validate(row["raw_action"])
        action = calibrate(raw, row["motor_rates"], motor)
        after = step_sliding(arena, state, action)
        xs, ys = coordinates(state, trial["crop"])
        derived.append(dict(row, before=asdict(state), after=asdict(after), action=action.model_dump(),
                            sample_xs=list(xs), sample_ys=list(ys), step_wall_seconds=0.0,
                            source_window=row["before"]["tick"],
                            reused_model_step_wall_seconds=row["step_wall_seconds"]))
        state = after
    trial.update(ticks=len(derived), final_state=asdict(state), outcome=state.outcome,
                 termination="terminal" if state.outcome else "source_prefix_cutoff", elapsed_wall_seconds=0.0)
    (directory / "trace.jsonl").write_text("".join(json.dumps(r, allow_nan=False)+"\n" for r in derived))
    trial["trace_sha256"] = file_sha256(directory / "trace.jsonl")
    (directory / "canonical.gray").write_bytes(raster)
    (directory / "canonical.png").write_bytes(png_bytes(raster))
    for row in derived:
        if row["before"]["tick"] in SNAPSHOTS:
            Image.frombytes("L", (16,16), bytes(256)).save(directory / f"input-{row['before']['tick']:03}.png")
    overlay(directory / "trajectory.png", raster, derived, "EXACT BLACK REUSE: " + trial["id"])
    save(directory / "trial.json", trial)
    return trial, derived


def sheet(records, path):
    canvas = Image.new("RGB", (4*400, math.ceil(len(records)/4)*420), "white")
    draw = ImageDraw.Draw(canvas)
    for i, record in enumerate(records):
        x, y = i%4*400, i//4*420
        t, m = record, record["metrics"]
        draw.text((x+5,y+4), f"{t['stage']} {t['seed']} {t['layout']} {t['input']}", fill="black")
        draw.text((x+5,y+20), f"{t['crop']} / {t['motor']}", fill="black")
        directory = Path(t["directory"])
        with Image.open(directory / "trajectory.png") as picture:
            canvas.paste(picture.crop((0,60,576,636)).resize((288,288), Image.Resampling.NEAREST), (x+5,y+40))
        available = sorted(directory.glob("input-*.png"))
        for j, idx in enumerate(sorted({0, len(available)//2, len(available)-1})):
            with Image.open(available[idx]) as picture:
                canvas.paste(picture.resize((64,64), Image.Resampling.NEAREST).convert("RGB"), (x+310,y+45+j*91))
            draw.text((x+308,y+111+j*91), available[idx].stem, fill="black")
        outcome = t["outcome"] or "INCOMPLETE cutoff"
        draw.text((x+5,y+335), f"{outcome}; {t['ticks']} ticks; bins {m['visited_8px_bins']}", fill="black")
        draw.text((x+5,y+351), f"Wall band {m['boundary_band_before_ticks']}/{t['ticks']}; contacts {m['pad_contacts']}", fill="black")
        draw.text((x+5,y+367), f"Both pad contrast inputs {m['both_pads_contrast_inputs']}/{t['ticks']}", fill="black")
        draw.text((x+5,y+383), "Exact black reuse: zero new calls" if t.get("derived") else "Actual model trial; blue start, red path/end", fill="black")
        draw.text((x+5,y+399), "No recognition or learning claim", fill="black")
    canvas.save(path)


def analyze(root=ROOT):
    report_path = root / "trials/report.json"
    report = json.loads(report_path.read_text())
    if report["status"] != "PASS":
        raise ValueError("Preserve incomplete schedule; cannot issue a passing analysis")
    output = root / "analysis"
    output.mkdir(exist_ok=False)
    records, traces = [], {}
    for trial in report["trials"]:
        directory = root / "trials" / trial["id"]
        rows = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
        records.append(dict(trial, directory=str(directory), metrics=metrics(rows, trial), derived=False))
        traces[trial["id"]] = rows
    originals = list(records)
    for trial in originals:
        if trial["input"] == "dark" and trial["motor"] == "dark_balance_v3":
            for motor, side in (("dark_balance_v3", "right"), ("upstream_pilot_v1", "left"),
                                ("upstream_pilot_v1", "right")):
                # Screening already has a genuinely executed uncalibrated black left control.
                if trial["stage"] == "screen" and motor == "upstream_pilot_v1" and side == "left":
                    continue
                derived, rows = derive_black(trial, traces[trial["id"]], output, side, motor)
                derived["metrics"] = metrics(rows, derived)
                records.append(derived)
                traces[derived["id"]] = rows
    pairs, keys = [], {}
    for trial in records:
        keys[(trial["stage"],trial["seed"],trial["crop"],trial["motor"],trial["layout"],trial["input"])] = trial
    for key, a in keys.items():
        stage,seed,crop,motor,side,kind = key
        alternatives = []
        if side == "left":
            alternatives.append(("mirrored_layout", (stage,seed,crop,motor,"right",kind)))
        if kind == "canonical":
            alternatives.append(("visual_vs_black", (stage,seed,crop,motor,side,"dark")))
        if motor == "upstream_pilot_v1":
            alternatives.append(("motor_only", (stage,seed,crop,"dark_balance_v3",side,kind)))
        if crop == "crop16_v1":
            alternatives.append(("observation_only", (stage,seed,"tracking16_v3",motor,side,kind)))
        for label, other in alternatives:
            if other in keys:
                b = keys[other]
                pairs.append(dict(kind=label, a=a["id"], b=b["id"],
                                  includes_exact_reuse=a["derived"] or b["derived"],
                                  **compare(traces[a["id"]],traces[b["id"]])))
    matched = defaultdict(list)
    for t in originals:
        for row in traces[t["id"]]:
            matched[(t["seed"],row["before"]["tick"],row["observation_sha256"])].append(row)
    groups = [v for v in matched.values() if len(v)>1]
    same = all(all((r["raw_action"],r["motor_rates"]) == (g[0]["raw_action"],g[0]["motor_rates"])
                   for r in g) for g in groups)
    if not same:
        raise ValueError("Matched input/seed/window neural output differs")
    historic = []
    for t in originals:
        if t["stage"] == "screen" and t["motor"] == "upstream_pilot_v1" and (t["crop"] == "crop16_v1" or t["input"] == "dark"):
            p = Path(f"artifacts/milestones/05/revision/primary/tangent_v2-crop16_v1-51001-{t['layout']}-{t['input']}/trace.jsonl")
            old = [json.loads(line) for line in p.read_text().splitlines()]
            rows = traces[t["id"]]
            identical = all(all(a[k] == b[k] for k in ("before","after","raw_action","motor_rates","observation_sha256"))
                            for a,b in zip(rows,old))
            if not identical:
                raise ValueError("Matched historical configuration no longer reproduces")
            historic.append(dict(trial=t["id"], source=str(p), source_sha256=file_sha256(p), matching_ticks=len(rows)))
    result = dict(status="PASS", human_review="CHANGES_REQUESTED", milestone06="BLOCKED",
                  learning_enabled=False, learning_claim_status="NOT_RUN", source_report_sha256=file_sha256(report_path),
                  analysis_source_sha256=file_sha256(Path(__file__)), trials=records, comparisons=pairs,
                  matched_neural_groups=len(groups), matched_neural_outputs_equal=same,
                  historical_exact_prefixes=historic,
                  trial_calls=report["neural_calls"], real_regression_calls=4,
                  total_new_model_calls=report["neural_calls"]+4,
                  phases=report["phases"], elapsed_wall_seconds=report["elapsed_wall_seconds"],
                  peak_process_rss_bytes=report["peak_process_rss_bytes"],
                  limitations="Development-only; uncalibrated visual comparisons are 56-tick cutoffs. Derived black controls reuse exact calls and are not independent neural samples.")
    save(output / "report.json", result)
    for stage in ("screen", "confirm"):
        sheet([r for r in originals if r["stage"] == stage], output / f"{stage}-trajectories-inputs.png")
    sheet([r for r in records if r["derived"]], output / "derived-black-trajectories-inputs.png")
    print(json.dumps(dict(trials=len(originals), derived=len(records)-len(originals), comparisons=len(pairs),
                          total_new_model_calls=result["total_new_model_calls"])))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    analyze(args.root)
