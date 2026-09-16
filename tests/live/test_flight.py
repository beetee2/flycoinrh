"""Synthetic motor vectors exercise the backend-independent OBS03 flight boundary."""
import inspect
import math
import subprocess
import sys
from typing import get_args

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from flytrap.live.contracts import FlightControls, MotorRates, State
from flytrap.live.flight import (
    ControlTick, FlightAuthority, FlightTrace, advance, decode, initial_state, replay, synthetic_preview,
)


def rates(**overrides):
    return MotorRates(**{**dict.fromkeys(MotorRates.model_fields, 0.), **overrides})


def command(motor=None, *, receipt=0., completed=None, now=None, response="fixture-0", **identity):
    return decode(motor or rates(fwd_L=150., fwd_R=150.), response_id=response,
                  session_id=identity.get("session_id", "fixture-flight"),
                  generation=identity.get("generation", 1),
                  evidence_kind=identity.get("evidence_kind", "fixture"),
                  receipt_ms=receipt, completed_ms=receipt if completed is None else completed,
                  now_ms=receipt if now is None else now)


def initial():
    return initial_state("fixture-flight", 1, "fixture")


def moving():
    state = initial()
    control = command(rates(steer_L=425., fwd_L=450., fwd_R=450.))
    for tick in range(1, 20):
        state = advance(state, control, tick_ms=tick*20.)
    assert state.snapshot.position != initial().snapshot.position
    assert state.yaw_rate > 0
    return state


@pytest.mark.parametrize("motor,expected", [
    (rates(), (0., 0., 0.)),
    (rates(steer_L=25., fwd_L=5., fwd_R=5., back=5.), (0., 0., 0.)),
    (rates(steer_L=225., fwd_L=150., fwd_R=150., back=50.), (.6, .084375, 134/45)),
    (rates(steer_R=225., back=150.), (-.6, -.140625, 1.2)),
    (rates(steer_L=1e12, fwd_L=1e12, fwd_R=1e12), (1.2, .45, 6.)),
    (rates(steer_R=1e12, back=1e12), (-1.2, -.45, 6.)),
])
def test_declared_formula_signs_deadbands_and_saturation(motor, expected):
    output = command(motor)
    assert (output.yaw_rate_rad_s, output.pitch_target_rad,
            output.speed_target_units_s) == pytest.approx(expected)


def test_unused_stop_click_are_telemetry_and_rates_are_preserved():
    motor = rates(steer_L=170., fwd_R=40.)
    before = motor.model_dump()
    assert command(motor) == command(motor.model_copy(update={"stop": 1e12, "click": 1e12}))
    assert motor.model_dump() == before


@given(st.lists(st.floats(min_value=0., max_value=1e12, allow_nan=False,
                         allow_infinity=False), min_size=7, max_size=7))
def test_finite_rate_property_has_bounded_targets(values):
    output = command(MotorRates(**dict(zip(MotorRates.model_fields, values, strict=True))))
    assert -1.2 <= output.yaw_rate_rad_s <= 1.2
    assert -.45 <= output.pitch_target_rad <= .45
    assert 0 <= output.speed_target_units_s <= 6


@pytest.mark.parametrize("field", list(MotorRates.model_fields))
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), -1., True, "4"])
def test_invalid_rates_rejected_at_typed_boundary(field, bad):
    with pytest.raises(ValidationError):
        MotorRates.model_validate({**rates().model_dump(), field: bad})


@pytest.mark.parametrize("field", list(MotorRates.model_fields))
def test_missing_rate_rejected(field):
    payload = rates().model_dump()
    del payload[field]
    with pytest.raises(ValidationError):
        MotorRates.model_validate(payload)


@pytest.mark.parametrize("field", ["pixels", "observation_u8", "target", "goal_coordinates", "image_hash", "label"])
def test_no_source_or_world_metadata_can_enter_decoder(field):
    with pytest.raises(ValidationError):
        MotorRates.model_validate({**rates().model_dump(), field: [0, 1]})
    with pytest.raises(TypeError):
        decode(rates(), response_id="fixture", session_id="fixture-flight", generation=1,
               evidence_kind="fixture", receipt_ms=0., completed_ms=0., now_ms=0., **{field: [0, 1]})
    with pytest.raises(ValidationError):
        FlightControls.model_validate({**command().model_dump(), field: [0, 1]})


def test_decoder_revalidates_constructed_nonfinite_rates():
    with pytest.raises(ValidationError):
        command(rates().model_copy(update={"back": float("nan")}))


@pytest.mark.parametrize("receipt,completed,now", [
    (20., 10., 20.), (0., 21., 20.), (1., 1., 0.), (0., 0., 2000.),
    (-1., 0., 0.), (0., float("nan"), 0.), (0., 0., float("inf")),
])
def test_invalid_future_reversed_and_expired_response_timing(receipt, completed, now):
    with pytest.raises(ValueError):
        command(receipt=receipt, completed=completed, now=now)


def test_expiration_uses_receipt_and_excludes_exact_expiry():
    control = command(receipt=100., completed=1500., now=1501.)
    assert control.expires_monotonic_ms == 2100.
    assert advance(initial(), control, tick_ms=1520.).snapshot.neutral
    live = advance(initial(), control, tick_ms=1540.)
    assert not live.snapshot.neutral
    assert not advance(live, control, tick_ms=2099.).snapshot.neutral
    expired = advance(live, control, tick_ms=2100.)
    assert expired.snapshot.position == live.snapshot.position
    assert expired.velocity == (0., 0., 0.)
    assert expired.snapshot.applied_response_id is None


def test_zero_control_neutralizes_existing_momentum_and_freezes_pose():
    state = moving()
    stopped = advance(state, command(rates()), tick_ms=400.)
    assert stopped.snapshot.position == state.snapshot.position
    assert stopped.snapshot.yaw_rad == state.snapshot.yaw_rad
    assert stopped.snapshot.pitch_rad == state.snapshot.pitch_rad
    assert stopped.velocity == (0., 0., 0.)
    assert stopped.yaw_rate == 0
    for tick in range(21, 30):
        stopped = advance(stopped, command(rates()), tick_ms=tick*20.)
    assert stopped.snapshot.position == state.snapshot.position


@pytest.mark.parametrize("status", [s for s in get_args(State) if s != "running"])
def test_every_nonrunning_state_neutralizes_immediately(status):
    state = moving()
    stopped = advance(state, command(), tick_ms=400., session_state=status)
    assert stopped.snapshot.position == state.snapshot.position
    assert stopped.snapshot.yaw_rad == state.snapshot.yaw_rad
    assert stopped.snapshot.pitch_rad == state.snapshot.pitch_rad
    assert stopped.snapshot.neutral
    assert stopped.snapshot.speed_units_s == stopped.yaw_rate == 0.
    assert stopped.velocity == (0., 0., 0.)
    assert stopped.snapshot.applied_response_id is None


def test_missing_command_freezes_existing_motion():
    state = moving()
    stopped = advance(state, None, tick_ms=400.)
    assert stopped.snapshot.position == state.snapshot.position
    assert stopped.velocity == (0., 0., 0.)
    assert stopped.snapshot.neutral


def test_constant_saturated_controls_bound_acceleration_rotation_and_speed():
    state = initial()
    for tick in range(1, 501):
        # Refresh only the validity interval. Direction switches test deceleration as well.
        sign = 1 if tick <= 250 else -1
        control = command(rates(steer_L=1e12 if sign == 1 else 0.,
                                steer_R=1e12 if sign == -1 else 0.,
                                fwd_L=1e12 if sign == 1 else 0., back=1e12 if sign == -1 else 0.),
                          receipt=(tick-1)*20.)
        new = advance(state, control, tick_ms=tick*20.)
        assert math.dist(new.velocity, state.velocity) <= .08 + 1e-12
        assert abs(new.yaw_rate-state.yaw_rate) <= .06 + 1e-12
        assert abs(new.snapshot.pitch_rad-state.snapshot.pitch_rad) <= .012 + 1e-12
        assert abs(new.yaw_rate) <= 1.2
        assert abs(new.snapshot.pitch_rad) <= .45
        assert abs(new.snapshot.yaw_rad) <= math.pi
        assert math.hypot(*new.velocity) <= 6. + 1e-12
        assert new.snapshot.speed_units_s == math.hypot(*new.velocity)
        assert new.snapshot.position == pytest.approx([
            p+v*.02 for p, v in zip(state.snapshot.position, new.velocity, strict=True)])
        state = new
    assert math.dist(state.snapshot.position, initial().snapshot.position) > 1.


def test_yaw_and_pitch_change_actual_heading_with_declared_signs():
    positive = advance(initial(), command(rates(steer_L=425., fwd_L=450., fwd_R=450.)), tick_ms=20.)
    negative = advance(initial(), command(rates(steer_R=425., back=900.)), tick_ms=20.)
    assert positive.snapshot.position[0] > 0
    assert positive.snapshot.position[1] > 0 > negative.snapshot.position[1]
    assert positive.snapshot.position[2] > 2 > negative.snapshot.position[2]


def test_pure_step_dt_is_fixed_and_does_not_use_render_elapsed_time():
    control = command()
    assert "dt" not in inspect.signature(advance).parameters
    assert advance(initial(), control, tick_ms=20.) == advance(initial(), control, tick_ms=1980.)


@pytest.mark.parametrize("identity", [{"session_id": "foreign"}, {"generation": 2}, {"evidence_kind": "real"}])
def test_foreign_controls_rejected_by_step_and_authority(identity):
    control = command(**identity)
    with pytest.raises(ValueError, match="foreign"):
        advance(initial(), control, tick_ms=20.)
    with pytest.raises(ValueError, match="foreign"):
        FlightAuthority("fixture-flight", 1, "fixture", origin_ms=0.).apply(control, now_ms=0.)


def test_delayed_control_never_steers_elapsed_ticks():
    authority = FlightAuthority("fixture-flight", 1, "fixture", origin_ms=0.)
    control = command(receipt=0., completed=499., now=499.)
    authority.apply(control, now_ms=499.)
    assert authority.current.snapshot.tick == 24
    assert authority.current.snapshot.position == initial().snapshot.position
    assert authority.events[0].tick == 25
    assert authority.advance_to(500.).position == initial().snapshot.position
    assert authority.advance_to(520.).position != initial().snapshot.position


def test_authority_polling_cadence_and_replay_are_exactly_equal():
    dense = FlightAuthority("fixture-flight", 1, "fixture", origin_ms=0.)
    sparse = FlightAuthority("fixture-flight", 1, "fixture", origin_ms=0.)
    for authority in (dense, sparse):
        authority.apply(command(), now_ms=0.)
    for timestamp in range(1, 338):
        dense.advance_to(float(timestamp))
    second = command(rates(steer_L=425., fwd_L=500.), receipt=300., completed=335., now=337.,
                     response="fixture-1")
    for authority in (dense, sparse):
        authority.apply(second, now_ms=337.)
    for timestamp in range(338, 2501):
        dense.advance_to(float(timestamp))
    sparse.advance_to(2500.)
    assert dense.current == sparse.current
    assert dense.events == sparse.events
    assert dense.current == replay(dense.initial, dense.events, ticks=125, origin_ms=0.)[-1]
    assert dense.current.snapshot.neutral  # Latest input expired during catch-up.


def test_multiple_controls_in_same_interval_replay_final_selection():
    authority = FlightAuthority("fixture-flight", 1, "fixture", origin_ms=0.)
    authority.apply(command(), now_ms=0.)
    authority.apply(command(rates(back=150.), receipt=1., response="fixture-1"), now_ms=1.)
    assert len(authority.events) == 1
    authority.advance_to(100.)
    assert authority.current == replay(authority.initial, authority.events, ticks=5, origin_ms=0.)[-1]
    assert authority.current.snapshot.applied_response_id == "fixture-1"


def test_authority_rejects_future_expired_duplicate_and_out_of_order_controls():
    authority = FlightAuthority("fixture-flight", 1, "fixture", origin_ms=0.)
    with pytest.raises(ValueError, match="future"):
        authority.apply(command(receipt=10.), now_ms=0.)
    authority.apply(command(receipt=20., response="fixture-1"), now_ms=20.)
    for stale in (command(receipt=10.), command(receipt=20., response="duplicate")):
        with pytest.raises(ValueError, match="out-of-order"):
            authority.apply(stale, now_ms=20.)
    with pytest.raises(ValueError, match="expired"):
        authority.apply(command(), now_ms=2000.)
    with pytest.raises(ValueError, match="monotonically"):
        authority.advance_to(1999.)


def test_stop_immediately_freezes_and_late_controls_cannot_resume():
    authority = FlightAuthority("fixture-flight", 1, "fixture", origin_ms=0.)
    authority.apply(command(), now_ms=0.)
    authority.advance_to(100.)
    pose = authority.current.snapshot.position
    authority.stop()
    assert authority.current.velocity == (0., 0., 0.)
    assert authority.current.snapshot.neutral
    assert authority.current.snapshot.position == pose
    assert not authority.apply(command(receipt=100.), now_ms=100.)
    authority.stop()
    authority.advance_to(1000.)
    assert authority.current.snapshot.position == pose
    assert authority.current == replay(authority.initial, authority.events, ticks=50, origin_ms=0.,
                                       terminal_tick=authority.terminal_tick)[-1]


@pytest.mark.parametrize("stop_ms", [0., 100., 120000.])
def test_immediate_stop_full_state_replays_at_zero_nonzero_and_maximum_tick(stop_ms):
    authority = FlightAuthority("fixture-flight", 1, "fixture", origin_ms=0.)
    authority.apply(command(), now_ms=0.)
    if stop_ms == 120000.:
        authority.apply(command(receipt=119980., response="fixture-last"), now_ms=119980.)
    authority.advance_to(stop_ms)
    before = authority.current.snapshot
    authority.stop()
    assert authority.terminal_tick == int(stop_ms/20.)
    assert authority.current.snapshot.tick == before.tick
    assert authority.current.snapshot.position == before.position
    assert authority.current.velocity == (0., 0., 0.)
    assert all(event.tick <= before.tick for event in authority.events)
    assert authority.current == replay(authority.initial, authority.events, ticks=before.tick,
                                       origin_ms=0., terminal_tick=authority.terminal_tick)[-1]


def test_stop_discards_unapplied_control_and_preserves_terminal_tick_after_later_polls():
    authority = FlightAuthority("fixture-flight", 1, "fixture", origin_ms=0.)
    authority.apply(command(), now_ms=0.)
    authority.apply(command(receipt=101., response="fixture-pending"), now_ms=101.)
    assert authority.events[-1].tick == 6
    authority.stop()
    assert authority.terminal_tick == 5
    assert all(event.controls.response_id != "fixture-pending" for event in authority.events)
    pose = authority.current.snapshot.position
    authority.advance_to(1000.)
    authority.stop()
    assert authority.terminal_tick == 5
    assert authority.current.snapshot.position == pose
    assert authority.current == replay(authority.initial, authority.events, ticks=50, origin_ms=0.,
                                       terminal_tick=5)[-1]


@pytest.mark.parametrize("stop", [False, True])
def test_full_trace_json_roundtrip_replays_current_state_and_omits_pending_control(stop):
    authority = FlightAuthority("fixture-flight", 1, "fixture", origin_ms=100.)
    authority.apply(command(receipt=100.), now_ms=100.)
    authority.apply(command(receipt=201., response="fixture-pending"), now_ms=201.)
    if stop:
        authority.stop()
    trace = FlightTrace.model_validate_json(authority.trace().model_dump_json())
    assert trace == authority.trace()
    assert trace.initial.physics_id == "flight-fixed20-ground-v2"
    assert trace.decoder_id == "motor-flight-v1"
    assert len(trace.events) == 1
    assert trace.events[0].controls.response_id == "fixture-0"
    assert replay(trace.initial, trace.events, ticks=trace.ticks, origin_ms=trace.origin_ms,
                  terminal_tick=trace.terminal_tick)[-1] == authority.current


@pytest.mark.parametrize("terminal_tick", [-1, 3, True, 1.5])
def test_replay_rejects_invalid_terminal_tick(terminal_tick):
    with pytest.raises(ValueError, match="terminal tick"):
        replay(initial(), [], ticks=2, origin_ms=0., terminal_tick=terminal_tick)


def test_replay_rejects_control_after_immediate_terminal_tick():
    with pytest.raises(ValueError, match="after terminal tick"):
        replay(initial(), [ControlTick(tick=2, controls=command())], ticks=2, origin_ms=0., terminal_tick=1)


@pytest.mark.parametrize("path,value", [
    (("schema_version",), "obs-flight-trace-unknown"),
    (("decoder_id",), "unknown-decoder"),
    (("initial", "physics_id"), "unknown-physics"),
])
def test_trace_rejects_unknown_contract_decoder_and_physics_versions(path, value):
    authority = FlightAuthority("fixture-flight", 1, "fixture", origin_ms=0.)
    payload = authority.trace().model_dump()
    target = payload
    for field in path[:-1]:
        target = target[field]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        FlightTrace.model_validate(payload)


@pytest.mark.parametrize("velocity", [
    (0., 0.), (0., 0., 0., 0.), (float("nan"), 0., 0.),
    (float("inf"), 0., 0.), ("0", 0., 0.), (True, 0., 0.),
])
def test_trace_initial_velocity_rejects_invalid_numbers_and_dimensions(velocity):
    payload = FlightAuthority("fixture-flight", 1, "fixture", origin_ms=0.).trace().model_dump()
    payload["initial"]["velocity"] = velocity
    with pytest.raises(ValidationError):
        FlightTrace.model_validate(payload)


@pytest.mark.parametrize("status", [s for s in get_args(State) if s != "running"])
def test_terminal_replay_cannot_resume(status):
    events = [ControlTick(tick=1, controls=None, state=status), ControlTick(tick=2, controls=command())]
    with pytest.raises(ValueError, match="cannot resume"):
        replay(initial(), events, ticks=2, origin_ms=0.)


@pytest.mark.parametrize("events,ticks", [
    ([ControlTick(tick=2, controls=None), ControlTick(tick=1, controls=None)], 2),
    ([ControlTick(tick=1, controls=None), ControlTick(tick=1, controls=None)], 2),
    ([ControlTick(tick=3, controls=None)], 2), ([], 6001), ([], -1), ([], True),
])
def test_replay_rejects_invalid_application_ticks(events, ticks):
    with pytest.raises(ValueError):
        replay(initial(), events, ticks=ticks, origin_ms=0.)


def test_preview_is_explicit_synthetic_deterministic_and_moves():
    preview = synthetic_preview()
    assert preview.evidence_kind == "synthetic"
    assert all(s.evidence_kind == "fixture" for s in preview.snapshots)
    assert preview == synthetic_preview()
    assert preview.snapshots[-1].position != preview.snapshots[0].position
    assert [s.tick for s in preview.snapshots] == list(range(601))


def test_backend_independence_import_and_preview_without_numerical_or_cpu_modules():
    script = """
import importlib.abc
import sys
class NoBackend(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'flysim', 'flyeye', 'numpy', 'scipy', 'torch', 'cupy'} or fullname.startswith('flytrap.controllers'):
            raise AssertionError('flight imported a model backend: ' + fullname)
sys.meta_path.insert(0, NoBackend())
from flytrap.live.flight import synthetic_preview
assert synthetic_preview().snapshots[-1].tick == 600
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
