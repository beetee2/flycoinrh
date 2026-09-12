"""Synthetic fixtures verify diagnosis independently from historical outcomes."""
from dataclasses import asdict
from hashlib import sha256

import pytest

from flytrap.arena.core import Q, State, build_arena, generate_challenge, step
from flytrap.arena.render import observation_sha256, render
from flytrap.contracts import ControllerOutput
from scripts.feasibility_trace_diagnostics import diagnose_rows


def command(dx, dy):
    return ControllerOutput(schema_version="1", dx=dx, dy=dy, click=False, model_mode="fixture",
                            telemetry=dict(schema_version="1", sampled_neurons=0, spike_count=0, neural_ms=0.0))


def fixture_trace(position, commands, *, blank=False):
    arena = build_arena(generate_challenge(seed=17))
    raster = render(arena.scene)
    state = State(*[v * Q for v in position])
    rows = []
    for action in commands:
        after = step(arena, state, action)
        rows.append(dict(before=asdict(state), after=asdict(after), action=action.model_dump(),
                         raw_action=action.model_dump(), step_wall_seconds=0.25,
                         observation_sha256=sha256(bytes(256)).hexdigest() if blank else
                         observation_sha256(raster, x_q=state.x_q, y_q=state.y_q)))
        state = after
    return arena, rows


def test_distinguishes_motor_zero_quantization_collision_and_canceled_legal_tangent():
    arena, rows = fixture_trace((48, 90), [command(0, 0), command(0.0001, 0.0001),
                               command(1, 1), command(1, 1), command(0, -1)])
    result = diagnose_rows(rows, arena)
    assert result["stationary_causes"] == dict(zero_motor=1, quantization=1, collision=1)
    assert result["first_wall_contact_tick"] == 3
    assert result["controller_seconds_through_first_contact"] == 0.75
    assert result["contact_dwell"]["bottom"] == dict(ticks=2, controller_wall_seconds=0.5)
    assert result["canceled_legal_tangent_ticks"] == [4]
    assert result["rows"][2]["quantized_requested_q"] == [8 * Q, 8 * Q]
    assert result["rows"][2]["actual_q"] == [2 * Q, 2 * Q]
    assert result["motion"]["actual_displacement_pixels"] == [2, -6]
    assert result["vertical_drift"]["after_first_contact"]["mean_actual_vertical_pixels"] == -4


def test_corner_dwell_counts_both_walls_but_outward_both_axes_is_not_legal_tangent():
    arena, rows = fixture_trace((90, 90), [command(1, 1), command(1, 1), command(1, -1)])
    result = diagnose_rows(rows, arena)
    assert result["contact_dwell"]["right_bottom"]["ticks"] == 2
    assert result["contact_dwell"]["right"]["ticks"] == 2
    assert result["contact_dwell"]["bottom"]["ticks"] == 2
    assert result["canceled_legal_tangent_ticks"] == [3]


def test_black_control_has_geometric_pad_samples_but_no_controller_pad_pixels():
    arena, rows = fixture_trace((48, 76), [command(0, 1), command(0, 1), command(0, 0)], blank=True)
    result = diagnose_rows(rows, arena, blank=True)
    assert result["unique_observation_count"] == 1
    assert result["geometric_pad_visible_observation_count"] == 2
    assert result["controller_pad_visible_observation_count"] == 0
    assert result["first_geometric_pad_loss_state_tick"] == 2
    assert result["geometric_visibility_transitions"] == [dict(state_tick=0, visible=True), dict(state_tick=2, visible=False)]


@pytest.mark.parametrize("corruption", ["state", "observation", "multiplier"])
def test_diagnosis_rejects_traces_that_cannot_be_reconstructed(corruption):
    arena, rows = fixture_trace((48, 76), [command(0.5, 0.5)])
    if corruption == "state":
        rows[0]["after"]["x_q"] += 1
    elif corruption == "observation":
        rows[0]["observation_sha256"] = "0" * 64
    else:
        rows[0]["raw_action"]["dx"] = 0.25
    with pytest.raises(ValueError):
        diagnose_rows(rows, arena)
