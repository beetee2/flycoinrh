"""Arena/controller boundary using the real adapter on an explicitly synthetic graph."""

import json

import numpy as np
import pytest

from flytrap.arena.core import build_arena, initial_state
from flytrap.arena.render import observation, render
from flytrap.contracts import create_challenge
from flytrap.controllers.fly import FlyController


def paired_cohorts():
    content = dict(schema_version="1", preset_version="two_choice_v1", renderer_version="grayscale_v1",
                   left_texture="stripes", right_texture="checkerboard", distractions=["middle"])
    return (
        build_arena(create_challenge({**content, "destination_side": "left"}), target_texture="stripes"),
        build_arena(create_challenge({**content, "destination_side": "right"}), target_texture="checkerboard"),
    )


def test_changed_hidden_cohort_scoring_keeps_actual_adapter_output_identical(adapter_files):
    controller = FlyController(**adapter_files)
    arenas = paired_cohorts()
    assert arenas[0].target_side != arenas[1].target_side
    assert arenas[0].challenge_sha256 != arenas[1].challenge_sha256
    assert render(arenas[0].scene) == render(arenas[1].scene)
    traces = []
    for arena in arenas:
        controller.reset(run_seed=725, checkpoint=controller.checkpoint)
        trace = []
        for x, y in ((48, 76), (24, 48), (72, 32)):
            crop = observation(render(arena.scene), x_q=x * 256, y_q=y * 256)
            envelope = crop.model_dump_json().encode()
            assert set(json.loads(envelope)) == {"schema_version", "pixels"}
            trace.append(controller.step_serialized(envelope))
        traces.append(trace)
    assert traces[0] == traces[1]
    assert all(json.loads(value)["model_mode"] == "fixture" for value in traces[0])


def test_canonical_crop_retina_matches_scalar_sampling_oracle(adapter_files):
    controller = FlyController(**adapter_files)
    state = initial_state()
    arena = paired_cohorts()[0]
    pixels = np.asarray(observation(render(arena.scene), x_q=state.x_q, y_q=state.y_q).pixels,
                        dtype=np.float32).reshape(16, 16)
    actual = controller._eye.look(pixels, 8, 8)
    for indices, uv, off in ((controller._eye.on_idx, controller._eye.on_uv, False),
                             (controller._eye.off_idx, controller._eye.off_uv, True)):
        sampled = np.array([pixels[min(15, max(0, int(16 * float(v)))),
                                   min(15, max(0, int(16 * float(u))))] for u, v in zip(*uv)])
        rates = (1 - sampled) * 180 * 0.6 if off else sampled * 180
        np.testing.assert_array_equal(actual[tuple(indices)], rates)


def test_renderer_rejects_scoring_and_state_objects():
    arena = paired_cohorts()[0]
    with pytest.raises(ValueError):
        render(arena)
    with pytest.raises(ValueError):
        render(initial_state())
