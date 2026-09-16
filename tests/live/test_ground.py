"""Synthetic ground regression; no capture, neural calls or learned claims."""
import math

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from flytrap.live.contracts import GROUND_ENVIRONMENT, GroundFlightSnapshot
from flytrap.live.flight import (
    FlightAuthority, FlightState, FlightTrace, LEGACY_PHYSICS_ID,
    PHYSICS_ID, advance, initial_state, neutralize, replay, synthetic_preview,
)
from tests.live.test_flight import command, rates

FLOOR = GROUND_ENVIRONMENT.ground_z + GROUND_ENVIRONMENT.clearance


def initial(version=PHYSICS_ID):
    return initial_state("fixture-flight", 1, "fixture", physics_id=version)


def descending(tick, *, turning=True):
    return command(rates(back=900., steer_L=425. if turning else 0.), receipt=(tick-1)*20.)


def state_at(z, velocity, *, version=PHYSICS_ID, pitch=-.45):
    state = initial(version)
    data = {**state.snapshot.model_dump(), "position": [0., 0., z], "pitch_rad": pitch,
            "speed_units_s": math.hypot(*velocity), "neutral": False}
    if version == PHYSICS_ID:
        data["ground_contact"] = z == FLOOR
    return FlightState(physics_id=version, snapshot=type(state.snapshot)(**data), velocity=velocity)


def test_full_120_seconds_refreshed_descent_preserves_v1_defect_and_bounds_v2():
    old, new = initial(LEGACY_PHYSICS_ID), initial()
    contact_ticks = 0
    for tick in range(1, 6001):
        control = descending(tick)
        old = advance(old, control, tick_ms=tick*20.)
        before = new
        new = advance(new, control, tick_ms=tick*20.)
        assert new.snapshot.position[2] >= FLOOR
        assert not new.snapshot.neutral  # Contact is not neural silence.
        assert new.snapshot.applied_response_id == control.response_id
        assert new.snapshot.speed_units_s == math.hypot(*new.velocity)
        if new.snapshot.ground_contact:
            contact_ticks += 1
            assert new.velocity[2] == 0.
            assert new.snapshot.position[:2] != before.snapshot.position[:2]
            assert new.snapshot.yaw_rad != before.snapshot.yaw_rad
    assert contact_ticks > 5000
    assert old.snapshot.position[2] < -200.
    assert old.physics_id == LEGACY_PHYSICS_ID
    assert "environment" not in old.snapshot.model_dump()


@pytest.mark.parametrize("distance,velocity", [(1e-9, (0., 0., -6.)), (.01, (3., 0., -4.)),
                                              (.079, (0., 0., -4.))])
def test_fast_swept_crossing_cannot_tunnel_and_only_normal_velocity_is_removed(distance, velocity):
    new = state_at(FLOOR+distance, velocity)
    old = state_at(FLOOR+distance, velocity, version=LEGACY_PHYSICS_ID)
    control = descending(1)
    unconstrained = advance(old, control, tick_ms=20.)
    resolved = advance(new, control, tick_ms=20.)
    assert unconstrained.snapshot.position[2] < FLOOR
    assert resolved.snapshot.position[2] == FLOOR
    assert resolved.velocity == (*unconstrained.velocity[:2], 0.)
    assert resolved.snapshot.position[:2] == unconstrained.snapshot.position[:2]
    assert resolved.snapshot.yaw_rad == unconstrained.snapshot.yaw_rad
    assert resolved.snapshot.pitch_rad == unconstrained.snapshot.pitch_rad
    assert resolved.yaw_rate == unconstrained.yaw_rate
    assert math.hypot(*resolved.velocity) <= math.hypot(*unconstrained.velocity)
    assert resolved.snapshot.speed_units_s == math.hypot(*resolved.velocity)


def test_upward_controls_depart_but_zero_stop_and_stale_input_freeze_contact():
    contact = state_at(FLOOR, (3., 0., 0.))
    for status, control, time in [("running", command(rates()), 20.), ("stopped", descending(1), 20.),
                                  ("source_lost", descending(1), 20.), ("running", None, 20.),
                                  ("running", descending(1), 2000.)]:
        stopped = advance(contact, control, tick_ms=time, session_state=status)
        assert stopped.snapshot.position == contact.snapshot.position
        assert stopped.snapshot.ground_contact
        assert stopped.velocity == (0., 0., 0.)
        assert stopped.snapshot.neutral
    up = contact
    for tick in range(1, 101):
        up = advance(up, command(rates(fwd_L=500., fwd_R=500.), receipt=(tick-1)*20.), tick_ms=tick*20.)
    assert up.snapshot.position[2] > FLOOR+1
    assert up.velocity[2] > 0
    assert not up.snapshot.ground_contact


def test_floor_only_contact_never_adds_upward_velocity_or_pitch_correction():
    current = state_at(FLOOR, (3., 0., 0.))
    for tick in range(1, 151):
        previous = current
        current = advance(current, descending(tick, turning=False), tick_ms=tick*20.)
        assert current.velocity[2] == 0.
        assert current.snapshot.position[2] == FLOOR
        assert current.snapshot.pitch_rad == previous.snapshot.pitch_rad
        assert current.snapshot.yaw_rad == previous.snapshot.yaw_rad == 0.
        assert current.yaw_rate == 0.


@given(st.lists(st.tuples(st.floats(0, 1000), st.floats(0, 1000), st.floats(0, 1000)),
                min_size=1, max_size=100))
@settings(max_examples=30)
def test_freeflight_is_exactly_old_physics_for_varied_controls(values):
    old = state_at(100., (0., 0., 0.), version=LEGACY_PHYSICS_ID, pitch=0.)
    new = state_at(100., (0., 0., 0.), pitch=0.)
    for tick, (forward, back, steer) in enumerate(values, 1):
        control = command(rates(fwd_L=forward, fwd_R=forward, back=back, steer_L=steer),
                          receipt=(tick-1)*20.)
        old = advance(old, control, tick_ms=tick*20.)
        new = advance(new, control, tick_ms=tick*20.)
        assert new.velocity == old.velocity
        assert new.yaw_rate == old.yaw_rate
        assert {k: getattr(new.snapshot, k) for k in type(old.snapshot).model_fields if k != "schema_version"} == {
            k: v for k, v in old.snapshot.model_dump().items() if k != "schema_version"}


def test_live_serialization_replay_and_every_seek_exactly_agree_at_contact_departure():
    authority = FlightAuthority("fixture-flight", 1, "fixture", origin_ms=0.)
    states = [authority.current]
    for tick in range(1, 601):
        if tick % 50 == 1:
            motor = rates(back=900., steer_L=225.) if tick <= 400 else rates(fwd_L=500., fwd_R=500.)
            control = command(motor, receipt=(tick-1)*20., response=f"synthetic-{tick}")
            authority.apply(control, now_ms=(tick-1)*20.)
        authority.advance_to(tick*20.)
        states.append(authority.current)
    trace = FlightTrace.model_validate_json(authority.trace().model_dump_json())
    assert any(state.snapshot.ground_contact for state in states)
    assert not states[-1].snapshot.ground_contact
    assert replay(trace.initial, trace.events, ticks=trace.ticks, origin_ms=trace.origin_ms) == states
    for tick in (0, 150, 200, 250, 399, 450, 600):
        selected = [event for event in trace.events if event.tick <= tick]
        assert replay(trace.initial, selected, ticks=tick, origin_ms=trace.origin_ms)[-1] == states[tick]
        assert FlightState.model_validate_json(states[tick].model_dump_json()) == states[tick]
    authority.stop()
    assert authority.current == neutralize(states[-1])


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(physics_id="unknown"),
    lambda d: d.update(physics_id=LEGACY_PHYSICS_ID),
    lambda d: d["snapshot"].update(physics_id="unknown"),
    lambda d: d["snapshot"]["environment"].update(ground_z=-8.),
    lambda d: d["snapshot"]["environment"].update(clearance=0.),
    lambda d: d["snapshot"]["environment"].update(environment_id="unknown"),
    lambda d: d["snapshot"]["environment"].update(collision_proxy="unknown"),
    lambda d: d["snapshot"].update(ground_contact=True),
    lambda d: d["snapshot"].update(position=[0., 0., -100.]),
])
def test_unknown_or_inconsistent_physics_environment_and_contact_rejected(mutate):
    data = initial().model_dump()
    mutate(data)
    with pytest.raises(ValidationError):
        FlightState.model_validate(data)


def test_legacy_below_ground_initial_is_still_readable_unclamped_and_serializes_unchanged():
    old = state_at(-8.14, (0., 0., 0.), version=LEGACY_PHYSICS_ID)
    data = old.model_dump()
    restored = FlightState.model_validate_json(old.model_dump_json())
    assert restored.model_dump() == data
    assert advance(restored, None, tick_ms=20.).snapshot.position[2] == -8.14
    assert "ground_contact" not in data["snapshot"]
    assert "physics_id" not in data["snapshot"]


def test_synthetic_preview_has_descent_contact_and_departure():
    frames = synthetic_preview().snapshots
    assert all(isinstance(frame, GroundFlightSnapshot) for frame in frames)
    assert frames[50].position[2] < frames[0].position[2]
    assert frames[300].ground_contact and frames[399].ground_contact
    assert not frames[-1].ground_contact
    assert frames[-1].position[2] > FLOOR
