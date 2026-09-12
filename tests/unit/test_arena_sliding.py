"""Labeled scripted physics fixtures; these do not measure neural competence."""

import pytest

from flytrap.arena.core import MAX_TICKS, Q, State, build_arena, generate_challenge, initial_state, step
from flytrap.arena.sliding import PHYSICS_VERSION, step_sliding
from flytrap.contracts import ControllerOutput


def action(dx=0.0, dy=0.0):
    return ControllerOutput(schema_version="1", dx=dx, dy=dy, click=False, model_mode="fixture",
                            telemetry={"schema_version": "1", "sampled_neurons": 0,
                                       "spike_count": 0, "neural_ms": 0.0})


def arena(distractions=0):
    return build_arena(generate_challenge(seed=17, distraction_count=distractions))


@pytest.mark.parametrize("start,command,expected", [
    ((4, 76), (-1, -1), (4, 68)), ((92, 76), (1, -1), (92, 68)),
    ((48, 4), (1, -1), (56, 4)), ((48, 92), (1, 1), (56, 92)),
    ((6, 76), (-1, -1), (4, 68)), ((90, 76), (1, -1), (92, 68)),
    ((48, 6), (1, -1), (56, 4)), ((48, 90), (1, 1), (56, 92)),
])
def test_v1_whole_segment_stop_is_preserved_and_v2_retains_full_tangent(start, command, expected):
    world, before = arena(), State(*(v * Q for v in start))
    after = step_sliding(world, before, action(*command))
    assert PHYSICS_VERSION == "tangent_v2"
    assert (after.x_q, after.y_q) == tuple(v * Q for v in expected)
    assert step(world, before, action(*command)) != after


@pytest.mark.parametrize("x,sx", [(4, -1), (92, 1)])
@pytest.mark.parametrize("y,sy", [(4, -1), (92, 1)])
def test_all_corners_block_two_normals_and_allow_leaving_either_axis(x, sx, y, sy):
    before, world = State(x * Q, y * Q), arena()
    both_blocked = step_sliding(world, before, action(sx, sy))
    assert (both_blocked.x_q, both_blocked.y_q) == (before.x_q, before.y_q)
    along_x = step_sliding(world, before, action(-sx, sy))
    along_y = step_sliding(world, before, action(sx, -sy))
    leaving = step_sliding(world, before, action(-sx, -sy))
    assert (along_x.x_q, along_x.y_q) == ((x - 8 * sx) * Q, y * Q)
    assert (along_y.x_q, along_y.y_q) == (x * Q, (y - 8 * sy) * Q)
    assert (leaving.x_q, leaving.y_q) == ((x - 8 * sx) * Q, (y - 8 * sy) * Q)


@pytest.mark.parametrize("start,command,expected", [
    ((90, 90), (1, 0.5), (92, 92)), ((6, 6), (-1, -0.5), (4, 4)),
    ((90, 6), (1, -1), (92, 4)), ((6, 90), (-1, 1), (4, 92)),
])
def test_swept_sequential_and_simultaneous_outer_contacts(start, command, expected):
    after = step_sliding(arena(), State(*(v * Q for v in start)), action(*command))
    assert (after.x_q, after.y_q) == tuple(v * Q for v in expected)


@pytest.mark.parametrize("start,command,expected", [
    ((44, 62), (1, 0.125), (44, 63)), ((52, 62), (-1, 0.125), (52, 63)),
    ((48, 60), (0.125, 1), (49, 60)), ((48, 64), (0.125, -1), (49, 64)),
    ((40, 62), (1, 0.125), (44, 63)), ((56, 62), (-1, 0.125), (52, 63)),
    ((48, 56), (0.125, 1), (49, 60)), ((48, 68), (0.125, -1), (49, 64)),
    ((48, 66), (0, -1), (48, 64)),  # Sweeps through full 4-pixel obstacle.
    ((40, 68), (1, -1), (44, 64)),  # Two inward normals at corner stop both.
    ((44, 64), (1, -1), (44, 64)),
    ((44, 64), (1, 0), (52, 64)), ((44, 64), (1, 1), (52, 72)),
    ((48, 64), (0, 1), (48, 72)), ((48, 60), (0, -1), (48, 52)),
    ((44, 62), (-1, 0), (36, 62)), ((52, 62), (1, 0), (60, 62)),
    # Removed normal does not resume after leaving the end of the edge.
    ((44, 62), (1, 1), (44, 70)),
])
def test_obstacle_faces_corners_swept_contacts_and_leaving(start, command, expected):
    after = step_sliding(arena(3), State(*(v * Q for v in start)), action(*command))
    assert (after.x_q, after.y_q) == tuple(v * Q for v in expected)
    assert after.outcome is None


def test_fractional_contact_does_not_discard_legal_tangential_quantum():
    before = State(90 * Q + 1, 76 * Q)
    after = step_sliding(arena(), before, action(1, -0.3))
    assert (after.x_q, after.y_q) == (92 * Q, 76 * Q - 614)
    assert step(arena(), before, action(1, -0.3)).y_q == 76 * Q - 153


@pytest.mark.parametrize("x,side", [(24, "left"), (72, "right")])
@pytest.mark.parametrize("tick", [0, MAX_TICKS - 1])
def test_swept_pad_outcomes_precede_timeout_and_terminal_restep_is_rejected(x, side, tick):
    world = arena()
    after = step_sliding(world, State(x * Q, 32 * Q, tick), action(0, -1))
    assert (after.x_q, after.y_q) == (x * Q, 28 * Q)
    assert after.outcome == ("success" if side == world.target_side else "wrong_pad")
    with pytest.raises(ValueError, match="terminal state"):
        step_sliding(world, after, action())


def test_closed_pad_corner_scores_and_stationary_timeout_has_no_rescue():
    world = arena()
    after = step_sliding(world, State(40 * Q, 24 * Q), action(-1, 1))
    assert (after.x_q, after.y_q) == (36 * Q, 28 * Q)
    assert after.outcome is not None
    before = State(48 * Q, 92 * Q, MAX_TICKS - 1)
    stopped = step_sliding(world, before, action(0, 1))
    assert (stopped.x_q, stopped.y_q, stopped.outcome) == (48 * Q, 92 * Q, "trial_timeout")


def test_zero_and_quantized_zero_actions_are_stationary():
    for command in (action(), action(0.0001, -0.0001)):
        after = step_sliding(arena(), initial_state(), command)
        assert (after.x_q, after.y_q) == (48 * Q, 76 * Q)


@pytest.mark.parametrize("state", [State(24 * Q, 20 * Q), State(48 * Q, 62 * Q)])
def test_illegal_active_contact_states_rejected(state):
    with pytest.raises(ValueError):
        step_sliding(arena(3), state, action())


@pytest.mark.parametrize("field,value", [("dx", float("nan")), ("dy", 1.001)])
def test_action_is_revalidated(field, value):
    with pytest.raises(ValueError):
        step_sliding(arena(), initial_state(), action().model_copy(update={field: value}))
