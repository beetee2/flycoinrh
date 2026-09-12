"""Synthetic motor rates test the frozen readout without any neural calls."""

import copy
import hashlib
import json
import math

import pytest
from hypothesis import given, strategies as st

from flytrap.contracts import ControllerOutput
from scripts import feasibility_final_motor as motor
from scripts.feasibility_motor_telemetry import MOTOR_POPULATIONS


def action():
    return ControllerOutput(schema_version="1", dx=0.3, dy=-0.2, click=True, model_mode="fixture",
                            telemetry=dict(schema_version="1", sampled_neurons=12,
                                           spike_count=34, neural_ms=20.0))


def rates(**values):
    return dict.fromkeys(MOTOR_POPULATIONS, 0.0) | values


def test_hand_computed_population_balance_preserves_click_and_telemetry():
    original = action()
    # 815 left spikes balance 782 right; 1341 reverse balances 730 forward.
    hz = rates(steer_L=815.0, steer_R=1007.0, fwd_L=460.0, fwd_R=1000.0,
               back=1341.0, stop=225.0)
    result = motor.calibrate(original, hz, motor.MOTOR_VERSION)
    assert result.dx == 0.5
    assert result.dy == 0
    assert result.click == original.click
    assert result.telemetry == original.telemetry
    assert result.model_mode == "fixture"
    assert motor.STEER_LEFT_WEIGHT == 782 / 815
    assert motor.BACK_WEIGHT == 730 / 1341
    assert 0 < motor.STEER_LEFT_WEIGHT <= 1
    assert 0 < motor.BACK_WEIGHT <= 1


def test_silence_remains_still_and_original_comparison_is_identity():
    original = action()
    assert motor.calibrate(original, rates(), "upstream_pilot_v1") is original
    result = motor.calibrate(original, rates(), motor.MOTOR_VERSION)
    assert result.dx == result.dy == 0


def test_inputs_are_not_mutated_and_output_telemetry_is_independent():
    original, hz = action(), rates(back=100.0)
    before_action, before_rates = original.model_dump(), copy.deepcopy(hz)
    result = motor.calibrate(original, hz, motor.MOTOR_VERSION)
    assert original.model_dump() == before_action
    assert hz == before_rates
    assert result is not original
    assert result.telemetry is not original.telemetry


@pytest.mark.parametrize("stop", [450.0, 900.0, 1e308])
def test_stop_suppresses_vertical_motion_without_suppressing_steering(stop):
    result = motor.calibrate(action(), rates(steer_R=450.0, fwd_L=900.0, stop=stop), motor.MOTOR_VERSION)
    assert result.dx == 1
    assert result.dy == 0


@given(st.fixed_dictionaries({key: st.floats(min_value=0, max_value=1e308,
                                          allow_nan=False, allow_infinity=False)
                             for key in MOTOR_POPULATIONS}))
def test_all_finite_nonnegative_rates_produce_finite_bounded_motion(hz):
    result = motor.calibrate(action(), hz, motor.MOTOR_VERSION)
    assert math.isfinite(result.dx) and -1 <= result.dx <= 1
    assert math.isfinite(result.dy) and -1 <= result.dy <= 1


@given(st.floats(min_value=0, max_value=1000, allow_nan=False),
       st.floats(min_value=0, max_value=1000, allow_nan=False))
def test_rate_increases_keep_declared_axis_directions(base, increase):
    original = rates(steer_L=base, steer_R=base, fwd_L=base, fwd_R=base, back=base, stop=90.0)
    initial = motor.calibrate(action(), original, motor.MOTOR_VERSION)
    for key in ("steer_L", "steer_R", "fwd_L", "fwd_R", "back"):
        changed = original | {key: base + increase}
        result = motor.calibrate(action(), changed, motor.MOTOR_VERSION)
        if key == "steer_L":
            assert result.dx <= initial.dx
        elif key == "steer_R":
            assert result.dx >= initial.dx
        elif key == "back":
            assert result.dy >= initial.dy
        else:
            assert result.dy <= initial.dy


@pytest.mark.parametrize("version", ["upstream_pilot_v1", motor.MOTOR_VERSION])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf, -1, True, "12", None, 10**400])
def test_invalid_rate_values_fail_in_both_comparisons(version, invalid):
    with pytest.raises(ValueError, match="finite nonnegative"):
        motor.calibrate(action(), rates(stop=invalid), version)


@pytest.mark.parametrize("bad", [{}, rates() | {"goal_x": 0}, None, []])
def test_rates_require_exact_six_keys(bad):
    with pytest.raises(ValueError, match="six diagnostic populations"):
        motor.calibrate(action(), bad, motor.MOTOR_VERSION)


@pytest.mark.parametrize("version", ["unknown", None, 3, [], {}])
def test_unknown_mapping_fails(version):
    with pytest.raises(ValueError, match="unknown motor mapping"):
        motor.calibrate(action(), rates(), version)


def test_invalid_action_fails():
    with pytest.raises(ValueError, match="ControllerOutput"):
        motor.calibrate(action().model_dump(), rates(), motor.MOTOR_VERSION)
    broken = action().model_copy(update={"dx": math.nan})
    with pytest.raises(ValueError):
        motor.calibrate(broken, rates(), motor.MOTOR_VERSION)


def synthetic_basis(tmp_path, monkeypatch):
    # Two explicitly synthetic 96-window files reproduce only the arithmetic
    # totals. They are not simulations or substitutes for historical evidence.
    totals = dict(steer_L=40750.0, steer_R=39100.0, fwd_L=27250.0, fwd_R=9250.0,
                  back=33525.0, stop=21825.0)
    sources = {}
    for seed in (1, 2):
        rows = [dict(before={"tick": index}, observation_pixels=[0] * 256,
                     motor_rates={key: value / 2 for key, value in totals.items()} if index == 0 else rates())
                for index in range(96)]
        payload = "\n".join(json.dumps(row) for row in rows).encode()
        name = f"synthetic-{seed}.jsonl"
        (tmp_path / name).write_bytes(payload)
        sources[name] = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(motor, "_ROOT", tmp_path)
    monkeypatch.setattr(motor, "_DARK_SOURCES", sources)
    return sources


def test_basis_checks_sources_and_reconstructs_weights_without_neural_calls(tmp_path, monkeypatch):
    sources = synthetic_basis(tmp_path, monkeypatch)
    result = motor.calibration_basis()
    assert result["source_file_sha256"] == sources
    assert result["windows"] == 192
    assert result["weights"] == dict(steer_left=782 / 815, back=730 / 1341)
    assert result["mean_rates_hz"]["back"] == 33525 / 192
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("corruption", ["hash", "rows", "tick", "pixels", "rates"])
def test_basis_rejects_corrupt_or_changed_inputs(tmp_path, monkeypatch, corruption):
    sources = synthetic_basis(tmp_path, monkeypatch)
    name = next(iter(sources))
    path = tmp_path / name
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if corruption == "rows":
        rows.pop()
    elif corruption == "tick":
        rows[0]["before"]["tick"] = 1
    elif corruption == "pixels":
        rows[0]["observation_pixels"][0] = 255
    else:
        rows[0]["motor_rates"]["steer_L"] += 1
    payload = "\n".join(json.dumps(row) for row in rows).encode()
    path.write_bytes(payload)
    if corruption != "hash":
        sources[name] = hashlib.sha256(payload).hexdigest()
    with pytest.raises(ValueError):
        motor.calibration_basis()
