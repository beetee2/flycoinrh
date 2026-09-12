"""Independent physics oracles; scripted actions are fixtures, not model competence."""

from dataclasses import FrozenInstanceError
from fractions import Fraction

import pytest

from flytrap.arena.core import (
    MAX_TICKS, Q, Rect, State, build_arena, generate_challenge, initial_state,
    segment_entry, step,
)
from flytrap.contracts import ControllerOutput, create_challenge


def action(dx=0.0, dy=0.0, *, click=False):
    return ControllerOutput(
        schema_version="1", dx=dx, dy=dy, click=click, model_mode="fixture",
        telemetry={"schema_version": "1", "sampled_neurons": 0, "spike_count": 0, "neural_ms": 0.0},
    )


def arena(*, distractions=0):
    return build_arena(generate_challenge(seed=17, distraction_count=distractions))


def test_stationary_fixture_has_no_goal_attraction_and_state_is_immutable():
    world = arena()
    before = initial_state()
    after = step(world, before, action(click=True))
    assert (before.x_q, before.y_q, before.tick, before.outcome) == (48 * Q, 76 * Q, 0, None)
    assert (after.x_q, after.y_q, after.tick, after.outcome) == (48 * Q, 76 * Q, 1, None)
    with pytest.raises(FrozenInstanceError):
        before.x_q = 0


@pytest.mark.parametrize("dx,dy,expected", [
    (1.0, -1.0, (56 * Q, 68 * Q)),
    (-1.0, 1.0, (40 * Q, 84 * Q)),
    (0.1234, -0.1234, (48 * Q + 252, 76 * Q - 252)),
    (0.0001, -0.0001, (48 * Q, 76 * Q)),
])
def test_movement_has_fixed_scale_and_truncates_toward_start(dx, dy, expected):
    after = step(arena(), initial_state(), action(dx, dy))
    assert (after.x_q, after.y_q) == expected


@pytest.mark.parametrize("start,delta,expected", [
    ((6, 76), (-1.0, -1.0), (4, 74)),
    ((90, 76), (1.0, -1.0), (92, 74)),
    ((48, 90), (1.0, 1.0), (50, 92)),
    ((48, 6), (1.0, -1.0), (50, 4)),
    ((4, 76), (-1.0, -1.0), (4, 76)),
    ((4, 76), (0.0, -1.0), (4, 68)),
    ((4, 76), (1.0, 0.0), (12, 76)),
])
def test_wall_stops_whole_segment_without_sliding(start, delta, expected):
    after = step(arena(), State(start[0] * Q, start[1] * Q), action(*delta))
    assert (after.x_q, after.y_q) == (expected[0] * Q, expected[1] * Q)
    assert after.outcome is None


def test_rational_wall_contact_truncates_secondary_axis_toward_start():
    # 511/2048 of the x movement reaches the wall; y travels -614 * 511/2048 q.
    after = step(arena(), State(90 * Q + 1, 76 * Q), action(1.0, -0.3))
    assert (after.x_q, after.y_q) == (92 * Q, 76 * Q - 153)


@pytest.mark.parametrize("start,delta,expected", [
    ((48, 66), (0.0, -1.0), (48, 64)),  # Would cross the entire thin obstacle.
    ((40, 62), (1.0, 0.0), (44, 62)),
    ((40, 66), (1.0, -1.0), (44, 62)),
    ((44, 64), (1.0, 0.0), (52, 64)),  # Tangent contact may move along the edge.
    ((48, 64), (0.0, 1.0), (48, 72)),  # Moving away is permitted.
    ((48, 64), (0.0, -1.0), (48, 64)),
])
def test_swept_obstacle_collision_prevents_tunneling(start, delta, expected):
    after = step(arena(distractions=3), State(start[0] * Q, start[1] * Q), action(*delta))
    assert (after.x_q, after.y_q) == (expected[0] * Q, expected[1] * Q)
    assert after.outcome is None


@pytest.mark.parametrize("side,x", [("left", 24), ("right", 72)])
@pytest.mark.parametrize("click", [False, True])
def test_closed_pad_contact_scores_without_click_requirement(side, x, click):
    world = arena()
    after = step(world, State(x * Q, 32 * Q), action(0.0, -1.0, click=click))
    assert (after.x_q, after.y_q) == (x * Q, 28 * Q)
    assert after.outcome == ("success" if world.target_side == side else "wrong_pad")
    with pytest.raises(ValueError):
        step(world, after, action())


def test_pad_corner_touch_is_terminal_even_without_entering_pad_interior():
    world = arena()
    after = step(world, State(40 * Q, 24 * Q), action(-1.0, 1.0))
    assert (after.x_q, after.y_q) == (36 * Q, 28 * Q)
    assert after.outcome == ("success" if world.target_side == "left" else "wrong_pad")


def test_timeout_uses_environment_ticks_and_terminal_state_cannot_advance():
    world, state = arena(), initial_state()
    for tick in range(1, MAX_TICKS + 1):
        state = step(world, state, action())
        assert state.tick == tick
        assert state.outcome == ("trial_timeout" if tick == MAX_TICKS else None)
    with pytest.raises(ValueError):
        step(world, state, action())


def test_pad_outcome_precedes_timeout_on_last_allowed_tick():
    world = arena()
    x = 24 if world.target_side == "left" else 72
    after = step(world, State(x * Q, 32 * Q, MAX_TICKS - 1), action(0.0, -1.0))
    assert (after.tick, after.outcome) == (MAX_TICKS, "success")


def test_neural_duration_does_not_change_environment_motion_or_ticks():
    command = action(0.2, -0.4)
    long_window = command.model_copy(deep=True)
    long_window.telemetry.neural_ms = 1_000_000.0
    assert step(arena(), initial_state(), command) == step(arena(), initial_state(), long_window)


@pytest.mark.parametrize("seed", range(8))
@pytest.mark.parametrize("side,x_direction", [("left", -1.0), ("right", 1.0)])
def test_both_pads_reachable_with_all_distractions_using_labeled_script_fixture(seed, side, x_direction):
    world = build_arena(generate_challenge(seed=seed, distraction_count=3))
    state = initial_state()
    # Explicit TEST FIXTURE route: lower horizontal corridor, then outside obstacle column.
    for fixture_action in [action(x_direction, 0.0)] * 3 + [action(0.0, -1.0)] * 6:
        state = step(world, state, fixture_action)
    assert state.tick == 9
    assert state.outcome == ("success" if side == world.target_side else "wrong_pad")


@pytest.mark.parametrize("start,end,rect,interior,expected", [
    ((0, 20), (96, 20), Rect(12, 12, 36, 28), False, Fraction(1, 8)),
    ((96, 20), (0, 20), Rect(12, 12, 36, 28), False, Fraction(5, 8)),
    ((48, 96), (48, 0), Rect(44, 60, 52, 64), True, Fraction(1, 3)),
    ((0, 28), (96, 28), Rect(12, 12, 36, 28), False, Fraction(1, 8)),
    ((0, 28), (96, 28), Rect(12, 12, 36, 28), True, None),
    ((40, 24), (32, 32), Rect(12, 12, 36, 28), False, Fraction(1, 2)),
    ((40, 24), (32, 32), Rect(12, 12, 36, 28), True, None),
    ((48, 64), (48, 72), Rect(44, 60, 52, 64), True, None),
    ((48, 64), (48, 56), Rect(44, 60, 52, 64), True, Fraction(0)),
    ((48, 70), (48, 64), Rect(44, 60, 52, 64), True, None),
    ((20, 20), (20, 20), Rect(12, 12, 36, 28), False, Fraction(0)),
    ((48, 70), (48, 70), Rect(44, 60, 52, 64), True, None),
])
def test_large_segment_exact_intersection_oracles(start, end, rect, interior, expected):
    assert segment_entry(
        tuple(value * Q for value in start), tuple(value * Q for value in end), rect,
        interior=interior,
    ) == expected


@pytest.mark.parametrize("start,end,first", [((0, 20), (96, 20), "left"), ((96, 20), (0, 20), "right")])
def test_large_sweep_across_both_disjoint_pads_has_unambiguous_first_contact(start, end, first):
    scene = arena().scene
    times = {
        side: segment_entry(tuple(v * Q for v in start), tuple(v * Q for v in end), pad)
        for side, pad in (("left", scene.left_pad), ("right", scene.right_pad))
    }
    assert set(times.values()) == {Fraction(1, 8), Fraction(5, 8)}
    assert min(times, key=times.get) == first


@pytest.mark.parametrize("update", [
    {"left_texture": "stripes", "right_texture": "stripes"},
    {"distractions": ["middle", "top"]},
    {"distractions": ["top", "top"]},
])
def test_schema_valid_but_illegal_challenge_is_rejected(update):
    payload = generate_challenge(seed=17).model_dump(exclude={"content_sha256"})
    with pytest.raises(ValueError):
        build_arena(create_challenge({**payload, **update}))


def test_challenge_content_hash_and_cue_mapping_are_verified():
    challenge = generate_challenge(seed=17)
    with pytest.raises(ValueError):
        build_arena(challenge.model_copy(update={"content_sha256": "0" * 64}))
    payload = challenge.model_dump(exclude={"content_sha256"})
    payload["destination_side"] = "right" if challenge.destination_side == "left" else "left"
    with pytest.raises(ValueError):
        build_arena(create_challenge(payload))


@pytest.mark.parametrize("state_args", [
    (3 * Q, 76 * Q), (93 * Q, 76 * Q), (48 * Q, 3 * Q),
    (48 * Q, 93 * Q), (48 * Q, 76 * Q, -1), (48 * Q, 76 * Q, MAX_TICKS),
    (24 * Q, 20 * Q), (48 * Q, 62 * Q),
])
def test_illegal_active_states_are_rejected(state_args):
    with pytest.raises(ValueError):
        step(arena(distractions=3), State(*state_args), action())


@pytest.mark.parametrize("updates", [
    {"x_q": float("nan")}, {"y_q": float("inf")}, {"tick": True},
    {"tick": MAX_TICKS + 1}, {"outcome": "infrastructure_failure"},
    {"outcome": "trial_timeout", "tick": 2}, {"outcome": "success", "tick": 0},
])
def test_state_rejects_nonfinite_values_invalid_types_and_impossible_lifecycle(updates):
    with pytest.raises(ValueError):
        State(**{"x_q": 48 * Q, "y_q": 76 * Q, **updates})
