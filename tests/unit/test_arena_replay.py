"""Closed-loop replay using the explicitly synthetic fixture controller."""

from dataclasses import replace

import pytest

from flytrap.arena.core import MAX_TICKS, OBSTACLES, Rect, build_arena, generate_challenge, initial_state, step
from flytrap.arena.render import observation, observation_sha256, render
from flytrap.controllers.fixture import FixtureController, fixture_checkpoint


def fixture_run(seed):
    arena = build_arena(generate_challenge(seed=7, distraction_count=3))
    raster = render(arena.scene)
    controller = FixtureController()
    controller.reset(run_seed=seed, checkpoint=fixture_checkpoint())
    state = initial_state()
    trace = []
    while state.outcome is None:
        crop = observation(raster, x_q=state.x_q, y_q=state.y_q)
        command = controller.step(crop)
        assert command.model_mode == "fixture"
        assert command.telemetry.neural_ms == 0
        digest = observation_sha256(raster, x_q=state.x_q, y_q=state.y_q)
        state = step(arena, state, command)
        trace.append((digest, command, state))
    return arena, trace


def test_identical_seed_pixels_and_checkpoint_reproduce_entire_fixture_trial():
    arena, trace = fixture_run(123)
    assert (arena, trace) == fixture_run(123)
    assert trace != fixture_run(124)[1]
    assert len(trace) <= MAX_TICKS
    assert trace[-1][2].outcome in ("success", "wrong_pad", "trial_timeout")


def test_recorded_fixture_actions_recompute_every_state_and_observation_hash():
    arena, trace = fixture_run(234)
    raster = render(arena.scene)
    state = initial_state()
    for digest, command, expected in trace:
        assert observation_sha256(raster, x_q=state.x_q, y_q=state.y_q) == digest
        state = step(arena, state, command)
        assert state == expected


@pytest.mark.parametrize("updates", [
    {"width": 95}, {"height": 95}, {"width": True},
    {"left_pad": Rect(13, 12, 37, 28)},
    {"right_pad": Rect(12, 12, 36, 28)},  # Overlaps left pad.
    {"obstacles": (Rect(4, 32, 92, 40),)},  # Blocks both corridors.
    {"obstacles": (OBSTACLES[0], OBSTACLES[0])},
    {"obstacles": (OBSTACLES[1], OBSTACLES[0])},
    {"obstacles": list(OBSTACLES)},
])
def test_arbitrary_geometry_cannot_bypass_preset_reachability_rules(updates):
    scene = build_arena(generate_challenge(seed=0)).scene
    with pytest.raises(ValueError):
        replace(scene, **updates)
