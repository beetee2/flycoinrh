"""Generated geometry/replay properties; all actions are labeled physics fixtures."""

import math

import pytest
from hypothesis import given, settings, strategies as st

from flytrap.arena.core import MAX_COORD, MIN_COORD, MOVEMENT_PER_TICK, Q, build_arena, generate_challenge, initial_state, step
from flytrap.contracts import ControllerOutput, verify_challenge_hash


def fixture_action(dx, dy):
    return ControllerOutput(
        schema_version="1", dx=dx, dy=dy, click=False, model_mode="fixture",
        telemetry={"schema_version": "1", "sampled_neurons": 0, "spike_count": 0, "neural_ms": 0.0},
    )


SEEDS = st.integers(min_value=0, max_value=2**32 - 1)
BOUNDED = st.floats(min_value=-1, max_value=1, allow_nan=False, allow_infinity=False)


@given(SEEDS, st.integers(0, 3), st.sampled_from(["stripes", "checkerboard"]))
def test_generated_presets_are_deterministic_legal_and_preserve_cohort(seed, count, texture):
    challenge = generate_challenge(seed=seed, distraction_count=count, target_texture=texture)
    assert challenge == generate_challenge(seed=seed, distraction_count=count, target_texture=texture)
    verify_challenge_hash(challenge)
    assert len(challenge.distractions) == len(set(challenge.distractions)) == count
    assert challenge.distractions == sorted(challenge.distractions, key=["top", "middle", "bottom"].index)
    assert challenge.left_texture != challenge.right_texture
    assert getattr(challenge, f"{challenge.destination_side}_texture") == texture
    world = build_arena(challenge, target_texture=texture)
    scene = world.scene
    assert scene.left_pad.x1 < scene.right_pad.x0
    for rectangle in (scene.left_pad, scene.right_pad, *scene.obstacles):
        assert MIN_COORD < rectangle.x0 < rectangle.x1 < MAX_COORD
        assert MIN_COORD < rectangle.y0 < rectangle.y1 < MAX_COORD
    assert all(rectangle.y0 > scene.left_pad.y1 for rectangle in scene.obstacles)
    assert all(rectangle.x0 > 24 and rectangle.x1 < 72 for rectangle in scene.obstacles)
    assert all(rectangle.y1 < 76 for rectangle in scene.obstacles)


def test_seeded_generation_counterbalances_both_target_positions():
    sides = {generate_challenge(seed=seed).destination_side for seed in range(64)}
    assert sides == {"left", "right"}


@settings(max_examples=70)
@given(SEEDS, st.integers(0, 3), st.lists(st.tuples(BOUNDED, BOUNDED), min_size=1, max_size=80))
def test_replay_is_deterministic_bounded_and_does_not_enter_obstacles(seed, count, vectors):
    world = build_arena(generate_challenge(seed=seed, distraction_count=count))
    state = initial_state()
    replay = initial_state()
    for dx, dy in vectors:
        before = state
        command = fixture_action(dx, dy)
        state = step(world, state, command)
        replay = step(world, replay, command.model_copy(deep=True))
        assert state == replay
        assert state.tick == before.tick + 1
        assert MIN_COORD * Q <= state.x_q <= MAX_COORD * Q
        assert MIN_COORD * Q <= state.y_q <= MAX_COORD * Q
        assert abs(state.x_q - before.x_q) <= abs(math.trunc(dx * MOVEMENT_PER_TICK * Q))
        assert abs(state.y_q - before.y_q) <= abs(math.trunc(dy * MOVEMENT_PER_TICK * Q))
        for obstacle in world.scene.obstacles:
            assert not (obstacle.x0 * Q < state.x_q < obstacle.x1 * Q
                        and obstacle.y0 * Q < state.y_q < obstacle.y1 * Q)
        if state.outcome is not None:
            break


@given(BOUNDED, BOUNDED)
def test_one_free_step_exactly_matches_quantized_action(dx, dy):
    world = build_arena(generate_challenge(seed=0))
    before = initial_state()
    after = step(world, before, fixture_action(dx, dy))
    assert after.x_q == before.x_q + math.trunc(dx * MOVEMENT_PER_TICK * Q)
    assert after.y_q == before.y_q + math.trunc(dy * MOVEMENT_PER_TICK * Q)


@given(st.sampled_from([float("nan"), float("inf"), -float("inf"), 1.0001, -1.0001]),
       st.sampled_from(["dx", "dy"]))
def test_untrusted_action_revalidates_even_if_pydantic_copy_bypassed_validation(value, field):
    world = build_arena(generate_challenge(seed=0))
    forged = fixture_action(0.0, 0.0).model_copy(update={field: value})
    with pytest.raises(ValueError):
        step(world, initial_state(), forged)


@given(st.one_of(st.integers(max_value=-1), st.integers(min_value=2**32), st.booleans(), st.text()))
def test_illegal_generation_seed_rejected(seed):
    with pytest.raises((ValueError, TypeError)):
        generate_challenge(seed=seed)


@given(st.one_of(st.integers(max_value=-1), st.integers(min_value=4), st.booleans()))
def test_illegal_distraction_count_rejected(count):
    with pytest.raises((ValueError, TypeError)):
        generate_challenge(seed=0, distraction_count=count)
