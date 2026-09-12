"""Export deterministic, explicitly scripted fixture frames and action traces.

Run with python -m scripts.arena_samples --output artifacts/milestones/04/samples.
These examples exercise physics; they measure no neural behavior or competence.
"""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from PIL import Image, ImageDraw

from flytrap.arena.core import MAX_TICKS, Q, build_arena, initial_state, step
from flytrap.arena.render import observation, observation_sha256, png_bytes, raster_sha256, render
from flytrap.contracts import ControllerOutput, create_challenge


def fixture_action(dx, dy):
    return ControllerOutput(schema_version="1", dx=dx, dy=dy, click=False, model_mode="fixture",
                            telemetry=dict(schema_version="1", sampled_neurons=0, spike_count=0, neural_ms=0.0))


def export_samples(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    challenge = create_challenge(dict(schema_version="1", preset_version="two_choice_v1",
        renderer_version="grayscale_v1", destination_side="left", left_texture="stripes",
        right_texture="checkerboard", distractions=["top", "middle", "bottom"]))
    arena = build_arena(challenge)
    raster = render(arena.scene)
    (output / "canonical.png").write_bytes(png_bytes(raster))
    (output / "canonical.gray").write_bytes(raster)
    state = initial_state()
    crop = observation(raster, x_q=state.x_q, y_q=state.y_q)
    crop_bytes = bytes(round(v * 255) for v in crop.pixels)
    Image.frombytes("L", (16, 16), crop_bytes).save(output / "observation.png")
    cases = {
        "left_success": [(-1, 0)] * 3 + [(0, -1)] * 6,
        "right_wrong_pad": [(1, 0)] * 3 + [(0, -1)] * 6,
        "blocked_timeout": [(0, -1)] * MAX_TICKS,
        "wall_timeout": [(1, 1)] * MAX_TICKS,
    }
    results = {}
    for name, actions in cases.items():
        state = initial_state()
        positions = [(state.x_q / Q, state.y_q / Q)]
        trace = []
        for dx, dy in actions:
            action = fixture_action(dx, dy)
            before = state
            state = step(arena, state, action)
            trace.append(dict(before=asdict(before), action=action.model_dump(), after=asdict(state),
                              observation_sha256=observation_sha256(raster, x_q=before.x_q, y_q=before.y_q)))
            positions.append((state.x_q / Q, state.y_q / Q))
            if state.outcome:
                break
        record = dict(fixture=True, label="SCRIPTED FIXTURE — NOT REAL MODEL", challenge=challenge.model_dump(),
                      target_texture="stripes", frame_sha256=raster_sha256(raster),
                      arena_version="two_choice_v1", renderer_version="grayscale_v1",
                      reward_version="destination_v1", movement_per_tick=8, coordinate_quantum="1/256 pixel",
                      max_ticks=MAX_TICKS, environment_ticks=state.tick, neural_ms=0,
                      final_state=asdict(state), actions=trace)
        (output / (name + ".json")).write_text(json.dumps(record, indent=2) + "\n")
        # Human overlay is composed from a copy AFTER the canonical bytes and
        # observations are saved. The renderer has no API for labels or traces.
        canvas = Image.new("RGB", (576, 654), "#eeeeee")
        canvas.paste(Image.frombytes("L", (96, 96), raster).resize((576, 576), Image.Resampling.NEAREST), (0, 54))
        draw = ImageDraw.Draw(canvas)
        draw.text((10, 8), "SCRIPTED FIXTURE - NOT REAL MODEL", fill="black")
        draw.text((10, 28), f"{name}: {state.outcome}, {state.tick} environment ticks; 0 neural ms", fill="black")
        draw.line([(x * 6, y * 6 + 54) for x, y in positions], fill="#d00000", width=3)
        for (x, y), fill in ((positions[0], "#0055ff"), (positions[-1], "#d00000")):
            draw.ellipse((x * 6 - 5, y * 6 + 49, x * 6 + 5, y * 6 + 59), fill=fill)
        draw.text((10, 635), "Human overlay only: blue start, red recorded path/end; stripes rewarded", fill="black")
        canvas.save(output / (name + "-overlay.png"))
        results[name] = dict(outcome=state.outcome, ticks=state.tick, x=state.x_q / Q, y=state.y_q / Q)
    summary = dict(fixture=True, competence_claim=False, results=results,
                   frame_sha256=raster_sha256(raster), observation_sha256=observation_sha256(
                       raster, x_q=initial_state().x_q, y_q=initial_state().y_q))
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(export_samples(parser.parse_args().output), indent=2))
