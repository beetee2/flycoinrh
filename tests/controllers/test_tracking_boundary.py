"""Tracking pixels through the actual adapter on an explicitly synthetic graph."""

import json

import numpy as np
import pytest

from flytrap.arena.core import build_arena
from flytrap.arena.render import render
from flytrap.arena.tracking import tracking_observation
from flytrap.contracts import create_challenge
from flytrap.controllers.fly import FlyController


def paired_hidden_cohorts():
    content = dict(schema_version="1", preset_version="two_choice_v1", renderer_version="grayscale_v1",
                   left_texture="stripes", right_texture="checkerboard", distractions=["middle"])
    return (
        build_arena(create_challenge({**content, "destination_side": "left"}), target_texture="stripes"),
        build_arena(create_challenge({**content, "destination_side": "right"}), target_texture="checkerboard"),
    )


def test_tracking_hidden_scoring_cannot_change_synthetic_graph_adapter_output(adapter_files):
    controller = FlyController(**adapter_files)
    cohorts = paired_hidden_cohorts()
    assert cohorts[0].target_side != cohorts[1].target_side
    assert cohorts[0].challenge_sha256 != cohorts[1].challenge_sha256
    assert render(cohorts[0].scene) == render(cohorts[1].scene)
    traces = []
    for arena in cohorts:
        controller.reset(run_seed=725, checkpoint=controller.checkpoint)
        trace = []
        for x, y in ((48, 76), (4, 92), (92, 4)):
            observation = tracking_observation(render(arena.scene), x_q=x * 256, y_q=y * 256)
            envelope = observation.model_dump_json().encode()
            assert set(json.loads(envelope)) == {"schema_version", "pixels"}
            trace.append(controller.step_serialized(envelope))
        traces.append(trace)
    assert traces[0] == traces[1]
    assert all(json.loads(output)["model_mode"] == "fixture" for output in traces[0])


@pytest.mark.parametrize("position", [(48, 76), (4, 4), (4, 92), (92, 4), (92, 92)])
def test_tracking_retinal_drive_matches_scalar_sampling_oracle(adapter_files, position):
    controller = FlyController(**adapter_files)
    raster = render(paired_hidden_cohorts()[0].scene)
    observation = tracking_observation(raster, x_q=position[0] * 256, y_q=position[1] * 256)
    pixels = np.asarray(observation.pixels, dtype=np.float32).reshape(16, 16)
    actual = controller._eye.look(pixels, 8, 8)
    for indices, uv, off in ((controller._eye.on_idx, controller._eye.on_uv, False),
                             (controller._eye.off_idx, controller._eye.off_uv, True)):
        sampled = np.array([pixels[min(15, max(0, int(16 * float(v)))),
                                   min(15, max(0, int(16 * float(u))))] for u, v in zip(*uv)])
        expected = (1 - sampled) * 180 * 0.6 if off else sampled * 180
        np.testing.assert_array_equal(actual[tuple(indices)], expected)
