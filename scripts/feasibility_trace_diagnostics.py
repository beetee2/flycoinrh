"""Read-only v1 trace diagnosis; sampling geometry never enters the controller.

All time-at-contact figures sum recorded controller compute latency for rows
whose BEFORE state is at contact. They are not simulated environment seconds.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path

from flytrap.arena.core import MAX_COORD, MIN_COORD, MOVEMENT_PER_TICK, Q, State, build_arena, step
from flytrap.arena.render import _samples, render
from flytrap.contracts import ChallengeSpec, ControllerOutput
from scripts.feasibility_analysis import summarize_trace


def sample_coordinates(x_q, y_q):
    return tuple([min(95, max(0, (q + (-60 + 8 * i) * Q) // Q)) for i in range(16)]
                 for q in (x_q, y_q))


def visibility(scene, state):
    xs, ys = sample_coordinates(state.x_q, state.y_q)
    counts = {side: sum(pad.x0 <= x < pad.x1 and pad.y0 <= y < pad.y1 for y in ys for x in xs)
              for side, pad in (("left", scene.left_pad), ("right", scene.right_pad))}
    return dict(sample_x=xs, sample_y=ys, pad_samples=counts, any_pad_samples=any(counts.values()))


def contacts(state):
    walls = []
    for axis, value, low, high in (("x", state.x_q, "left", "right"), ("y", state.y_q, "top", "bottom")):
        if value == MIN_COORD * Q:
            walls.append(low)
        elif value == MAX_COORD * Q:
            walls.append(high)
    return walls


def diagnose_rows(rows, arena, *, blank=False, motor_multiplier=1.0, physics_step=step, sample_fn=_samples, visibility_fn=visibility):
    summary = summarize_trace(rows)
    raster = render(arena.scene)
    dwell = {name: dict(ticks=0, controller_wall_seconds=0.0) for name in
             ("left", "right", "top", "bottom", "left_top", "left_bottom", "right_top", "right_bottom")}
    detail = []
    for row in rows:
        before, after = State(**row["before"]), State(**row["after"])
        action = ControllerOutput.model_validate(row["action"])
        raw = ControllerOutput.model_validate(row.get("raw_action", row["action"]))
        if action.dx != raw.dx * motor_multiplier or action.dy != raw.dy * motor_multiplier:
            raise ValueError("Recorded motor multiplier mismatch")
        if physics_step(arena, before, action) != after:
            raise ValueError("Physics replay mismatch")
        pixels = bytes(256) if blank else sample_fn(raster, x_q=before.x_q, y_q=before.y_q)
        if hashlib.sha256(pixels).hexdigest() != row["observation_sha256"]:
            raise ValueError("Observation replay mismatch")
        active = contacts(before)
        for name in active + (["_".join(active)] if len(active) == 2 else []):
            dwell[name]["ticks"] += 1
            dwell[name]["controller_wall_seconds"] += row["step_wall_seconds"]
        quantized = [math.trunc(value * MOVEMENT_PER_TICK * Q) for value in (action.dx, action.dy)]
        actual = [after.x_q - before.x_q, after.y_q - before.y_q]
        requested = [value * MOVEMENT_PER_TICK for value in (action.dx, action.dy)]
        raw_requested = [value * MOVEMENT_PER_TICK for value in (raw.dx, raw.dy)]
        stationary = not any(actual)
        cause = None
        if stationary:
            cause = "zero_motor" if not any(requested) else "quantization" if not any(quantized) else "collision"
        blocked = [axis for axis, value, delta in ((0, before.x_q, quantized[0]), (1, before.y_q, quantized[1]))
                   if (value == MIN_COORD * Q and delta < 0) or (value == MAX_COORD * Q and delta > 0)]
        canceled_legal_tangent = False
        for axis in blocked:
            tangent = 1 - axis
            candidate = action.model_copy(update={"dx" if axis == 0 else "dy": 0.0})
            legal = physics_step(arena, before, candidate)
            legal_delta = (legal.x_q - before.x_q, legal.y_q - before.y_q)[tangent]
            canceled_legal_tangent |= legal_delta != 0 and actual[tangent] == 0
        geometry = visibility_fn(arena.scene, before)
        detail.append(dict(tick=after.tick, observation_state_tick=before.tick,
                           before=row["before"], after=row["after"],
                           raw_requested_pixels=raw_requested, requested_pixels=requested,
                           quantized_requested_q=quantized, actual_q=actual,
                           stationary_cause=cause, before_walls=active, after_walls=contacts(after),
                           canceled_legal_tangent=canceled_legal_tangent,
                           geometric_visibility=geometry, controller_has_pad_pixels=not blank and geometry["any_pad_samples"],
                           observation_sha256=row["observation_sha256"], controller_wall_seconds=row["step_wall_seconds"]))
    first_contact = next((d["tick"] for d in detail if d["after_walls"]), None)
    first_loss = next((d["observation_state_tick"] for d in detail if not d["geometric_visibility"]["any_pad_samples"]), None)
    transitions = [dict(state_tick=d["observation_state_tick"], visible=d["geometric_visibility"]["any_pad_samples"])
                   for i, d in enumerate(detail) if i == 0 or d["geometric_visibility"]["any_pad_samples"] != detail[i - 1]["geometric_visibility"]["any_pad_samples"]]
    def motion_stats(selected):
        return dict(ticks=len(selected),
                    raw_requested_pixels=[math.fsum(d["raw_requested_pixels"][axis] for d in selected) for axis in (0, 1)],
                    requested_pixels=[math.fsum(d["requested_pixels"][axis] for d in selected) for axis in (0, 1)],
                    quantized_requested_pixels=[sum(d["quantized_requested_q"][axis] for d in selected) / Q for axis in (0, 1)],
                    actual_displacement_pixels=[sum(d["actual_q"][axis] for d in selected) / Q for axis in (0, 1)],
                    raw_requested_distance_pixels=math.fsum(math.hypot(*d["raw_requested_pixels"]) for d in selected),
                    requested_distance_pixels=math.fsum(math.hypot(*d["requested_pixels"]) for d in selected),
                    actual_distance_pixels=math.fsum(math.hypot(*d["actual_q"]) / Q for d in selected),
                    mean_requested_vertical_pixels=math.fsum(d["requested_pixels"][1] for d in selected) / len(selected) if selected else None,
                    mean_actual_vertical_pixels=sum(d["actual_q"][1] for d in selected) / Q / len(selected) if selected else None)
    return dict(summary=summary, first_wall_contact_tick=first_contact,
                controller_seconds_through_first_contact=math.fsum(d["controller_wall_seconds"] for d in detail if first_contact is not None and d["tick"] <= first_contact),
                contact_dwell=dwell, motion=motion_stats(detail),
                vertical_drift=dict(before_first_contact=motion_stats([d for d in detail if first_contact is None or d["tick"] < first_contact]),
                                    contact_tick=motion_stats([d for d in detail if d["tick"] == first_contact]),
                                    after_first_contact=motion_stats([d for d in detail if first_contact is not None and d["tick"] > first_contact])),
                stationary_causes={cause: sum(d["stationary_cause"] == cause for d in detail) for cause in ("zero_motor", "quantization", "collision")},
                canceled_legal_tangent_ticks=[d["tick"] for d in detail if d["canceled_legal_tangent"]],
                first_geometric_pad_loss_state_tick=first_loss, geometric_visibility_transitions=transitions,
                geometric_pad_visible_observation_count=sum(d["geometric_visibility"]["any_pad_samples"] for d in detail),
                controller_pad_visible_observation_count=sum(d["controller_has_pad_pixels"] for d in detail),
                unique_observation_count=len({d["observation_sha256"] for d in detail}), rows=detail)


def write_visuals(output, arenas, rows):
    from PIL import Image, ImageDraw
    positions = [("start", State(48 * Q, 76 * Q)), ("path_80", State(60 * Q, 80 * Q)),
                 ("path_87", State(30 * Q, 87 * Q)), ("cutoff_88", State(48 * Q, 88 * Q)),
                 ("bottom_middle", State(48 * Q, 92 * Q)), ("bottom_left", State(4 * Q, 92 * Q))]
    positions += [(f"actual_tick_{tick}", State(**rows[tick]["before"])) for tick in (16, 64, 128)]
    canvas = Image.new("RGB", (960, len(positions) * 330), "white")
    draw = ImageDraw.Draw(canvas)
    records = []
    for i, (label, state) in enumerate(positions):
        top = i * 330
        xs, ys = sample_coordinates(state.x_q, state.y_q)
        samples = []
        record = dict(label=label, state=asdict(state), **visibility(arenas[0].scene, state))
        draw.text((8, top + 5), f'{label}: x={state.x_q / Q}, y={state.y_q / Q}; yellow crosses = sampled pixel centers', fill="black")
        draw.text((8, top + 23), f'x={xs}', fill="black")
        draw.text((8, top + 40), f'y={ys}', fill="black")
        for j, arena in enumerate(arenas):
            raster = render(arena.scene)
            exact = _samples(raster, x_q=state.x_q, y_q=state.y_q)
            samples.append(exact)
            prefix = f'{label}-{arena.target_side}'
            scene_img = Image.frombytes("L", (96, 96), raster).convert("RGB").resize((240, 240), Image.Resampling.NEAREST)
            marker = ImageDraw.Draw(scene_img)
            for y in set(ys):
                for x in set(xs):
                    px, py = int((x + 0.5) * 2.5), int((y + 0.5) * 2.5)
                    marker.line((px - 1, py, px + 1, py), fill="yellow")
                    marker.line((px, py - 1, px, py + 1), fill="yellow")
            canvas.paste(scene_img, (j * 480, top + 68))
            sample_img = Image.frombytes("L", (16, 16), exact)
            sample_img.save(output / f'{prefix}-input.png')
            canvas.paste(sample_img.convert("RGB").resize((208, 208), Image.Resampling.NEAREST), (j * 480 + 252, top + 68))
            draw.text((j * 480 + 252, top + 282), f'{arena.target_side} layout; exact 16x16', fill="black")
        record["swapped_different_pixels"] = sum(a != b for a, b in zip(*samples))
        record["sampled_raw_pixels_by_layout"] = {arena.target_side: list(sample) for arena, sample in zip(arenas, samples)}
        records.append(record)
    canvas.save(output / "crop-comparison.png")
    for arena in arenas:
        Image.frombytes("L", (96, 96), render(arena.scene)).save(output / f'canonical-{arena.target_side}.png')
    (output / "crop-comparison.json").write_text(json.dumps(records, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("artifacts/milestones/05/trials"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/milestones/05/revision/diagnosis"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    results, sources = {}, {}
    arena_by_side = {}
    example_rows = None
    for directory in sorted(args.input.glob("dev-*")):
        # Read every file in every episode, including historical rendered imagery.
        files = {path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()}
        sources[directory.name] = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
        trial = json.loads(files["trial.json"])
        rows = [json.loads(line) for line in files["trace.jsonl"].splitlines()]
        if len(rows) != 256 or hashlib.sha256(files["trace.jsonl"]).hexdigest() != trial["trace_sha256"]:
            raise ValueError("Historical episode completeness or digest mismatch")
        arena = build_arena(ChallengeSpec.model_validate(trial["challenge"]))
        if render(arena.scene) != files["canonical.gray"]:
            raise ValueError("Canonical raster mismatch")
        result = diagnose_rows(rows, arena, blank=trial["condition"]["input"] == "dark",
                               motor_multiplier=trial["condition"]["motor_multiplier"])
        (args.output / f'{directory.name}.json').write_text(json.dumps(result, indent=2) + "\n")
        results[directory.name] = {key: value for key, value in result.items() if key != "rows"}
        arena_by_side[arena.target_side] = arena
        if directory.name == "dev-51001-left":
            example_rows = rows
    if len(results) != 8:
        raise ValueError("Expected all eight historical episodes")
    write_visuals(args.output, [arena_by_side[side] for side in ("left", "right")], example_rows)
    result = dict(scope="Complete eight historical development episodes; no neural runs", physics_version="two_choice_v1_no_sliding",
                  crop_version="crop16_v1", y_direction="positive is down",
                  time_definition="Contact dwell uses BEFORE-state ticks and summed recorded controller compute seconds; environment seconds are undefined.",
                  contact_definition="Exact outer-wall contact; corner ticks also count toward each constituent wall.",
                  visibility_definition="Destination rectangle sample locations, independent of pixel brightness; black controls contain no pad cues.",
                  source_files=sources, episodes=results)
    (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
