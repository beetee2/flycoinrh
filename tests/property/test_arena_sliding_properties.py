"""Generated tangent_v2 mechanics and replay checks; actions are fixtures."""

from dataclasses import replace
import math

from hypothesis import given, settings, strategies as st

from flytrap.arena.core import (
    MAX_COORD, MIN_COORD, MOVEMENT_PER_TICK, Q, State, build_arena, generate_challenge, initial_state,
)
from flytrap.arena.sliding import _sweep, step_sliding
from flytrap.contracts import ControllerOutput

BOUNDED = st.floats(min_value=-1, max_value=1, allow_nan=False, allow_infinity=False)


def action(dx, dy):
    return ControllerOutput(schema_version="1", dx=dx, dy=dy, click=False, model_mode="fixture",
                            telemetry={"schema_version": "1", "sampled_neurons": 0,
                                       "spike_count": 0, "neural_ms": 0.0})


def assert_legal_path(world, path, delta):
    # Independent interval oracle: all exact breakpoints where a leg crosses a
    # rectangle coordinate, and a midpoint in every resulting interval. An
    # open interior crossing must contain one such midpoint.
    for start, end in zip(path, path[1:]):
        for axis in range(2):
            assert MIN_COORD * Q <= end[axis] <= MAX_COORD * Q
            assert (end[axis] - start[axis]) * delta[axis] >= 0
        for rect in world.scene.obstacles:
            times = {0, 1}
            for a, b, low, high in zip(start, end, (rect.x0 * Q, rect.y0 * Q),
                                      (rect.x1 * Q, rect.y1 * Q)):
                if b != a:
                    times.update(t for t in ((low - a) / (b - a), (high - a) / (b - a)) if 0 <= t <= 1)
            ordered = sorted(times)
            for low, high in zip(ordered, ordered[1:]):
                t = (low + high) / 2
                x, y = (a + (b - a) * t for a, b in zip(start, end))
                assert not rect.contains(x, y, interior=True)


@settings(max_examples=100, deadline=None)
@given(st.integers(0, 2**32 - 1), st.lists(st.tuples(BOUNDED, BOUNDED), min_size=1, max_size=80))
def test_replay_all_obstacles_no_tunneling_no_extra_or_reversed_motion(seed, vectors):
    world = build_arena(generate_challenge(seed=seed, distraction_count=3))
    state = replay = initial_state()
    for dx, dy in vectors:
        before = state
        command = action(dx, dy)
        delta = tuple(math.trunc(v * MOVEMENT_PER_TICK * Q) for v in (dx, dy))
        path, _ = _sweep(world, (before.x_q, before.y_q), delta)
        assert_legal_path(world, path, delta)
        state = step_sliding(world, state, command)
        replay = step_sliding(world, replay, command.model_copy(deep=True))
        assert state == replay
        assert state.tick == before.tick + 1
        for previous, current, requested in zip((before.x_q, before.y_q), (state.x_q, state.y_q), delta):
            assert abs(current - previous) <= abs(requested)
            assert (current - previous) * requested >= 0
        assert all(not r.contains(state.x_q, state.y_q, interior=True) for r in world.scene.obstacles)
        # Hidden cohort/scoring changes cannot alter motion before termination.
        other_side = "left" if world.target_side == "right" else "right"
        other = replace(world, target_side=other_side, target_texture=getattr(world.scene, other_side + "_texture"))
        other_after = step_sliding(other, before, command)
        assert (other_after.x_q, other_after.y_q) == (state.x_q, state.y_q)
        if state.outcome is not None:
            break


@settings(max_examples=300, deadline=None)
@given(st.integers(4 * Q, 92 * Q), st.integers(4 * Q, 92 * Q), BOUNDED, BOUNDED)
def test_arbitrary_legal_states_have_safe_swept_legs(x, y, dx, dy):
    world = build_arena(generate_challenge(seed=0, distraction_count=3))
    if any(r.contains(x, y, interior=True) for r in world.scene.obstacles):
        return
    if any(r.contains(x, y) for r in (world.scene.left_pad, world.scene.right_pad)):
        return
    delta = tuple(math.trunc(v * MOVEMENT_PER_TICK * Q) for v in (dx, dy))
    path, _ = _sweep(world, (x, y), delta)
    assert_legal_path(world, path, delta)
    after = step_sliding(world, State(x, y), action(dx, dy))
    assert all(not r.contains(after.x_q, after.y_q, interior=True) for r in world.scene.obstacles)


@given(st.sampled_from([0, 1]), st.sampled_from([MIN_COORD, MAX_COORD]), BOUNDED)
def test_each_wall_preserves_exact_quantized_tangent(axis, wall, tangent):
    start = [48 * Q, 76 * Q]
    start[axis] = wall * Q
    requested = [tangent, tangent]
    requested[axis] = -1 if wall == MIN_COORD else 1
    after = step_sliding(build_arena(generate_challenge(seed=0)), State(*start), action(*requested))
    actual = [after.x_q, after.y_q]
    assert actual[axis] == start[axis]
    assert actual[1 - axis] == start[1 - axis] + math.trunc(tangent * MOVEMENT_PER_TICK * Q)
