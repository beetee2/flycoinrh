"""Passive development telemetry on labeled synthetic adapter fixtures."""

import hashlib
import random
from types import SimpleNamespace

import numpy as np
import pytest

from flytrap.contracts import Observation
from flytrap.controllers.fly import FlyController, SEED_DOMAIN
from scripts.feasibility_motor_telemetry import MOTOR_POPULATIONS, MotorRateDiagnostic

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("seed", [0, 39, 4294967295])
def test_matched_pixels_and_seed_preserve_outputs_and_neural_calls(adapter_files, monkeypatch, seed):
    from flysim import FlyBrain

    controller = FlyController(**adapter_files)
    observations = [Observation(schema_version="1", pixels=[float(value)] * 256)
                    for value in (0, 1, 0.25, 0.75)]
    calls = []
    original_run = FlyBrain.run

    def record_run(self, *args, **kwargs):
        calls.append(kwargs["seed"])
        return original_run(self, *args, **kwargs)

    monkeypatch.setattr(FlyBrain, "run", record_run)
    controller.reset(run_seed=seed, checkpoint=controller.checkpoint)
    expected = [controller.step(observation) for observation in observations]
    controller.reset(run_seed=seed, checkpoint=controller.checkpoint)
    original_step = controller._pilot.step
    captured = []
    with MotorRateDiagnostic(controller) as diagnostic:
        assert diagnostic.rates is None
        observed = []
        for observation in observations:
            observed.append(controller.step(observation))
            captured.append(diagnostic.rates)
            assert diagnostic.error is None
        assert diagnostic.calls == len(observations)
    assert observed == expected
    assert controller._pilot.step == original_step
    assert "step" not in vars(controller._pilot)
    expected_seeds = [int.from_bytes(hashlib.sha256(
        SEED_DOMAIN + seed.to_bytes(4, "big") + index.to_bytes(8, "big")
    ).digest()[:8], "big") for index in range(len(observations))]
    assert calls == expected_seeds * 2
    for output, rates in zip(observed, captured, strict=True):
        assert set(rates) == set(MOTOR_POPULATIONS)
        assert all(np.isfinite(value) and value >= 0 for value in rates.values())
        # These equations reproduce the inspected upstream mapping, with the
        # adapter's division by 90 included; positive y remains downward.
        turn = np.clip((rates["steer_R"] - rates["steer_L"]) / 450, -1, 1)
        speed = np.clip(((rates["fwd_L"] + rates["fwd_R"]) / 2 - rates["back"]) / 450, -1, 1)
        speed *= 1 - np.clip(rates["stop"] / 450, 0, 1)
        assert output.dx == pytest.approx(turn, abs=1e-15)
        assert output.dy == pytest.approx(-speed, abs=1e-15)


def test_exact_passthrough_defensive_copy_and_rng_preservation():
    hz = dict.fromkeys(MOTOR_POPULATIONS, 12.0)
    result = (1.0, -2.0, False, hz, {"untouched": object()})
    args_seen = []

    def step(*args, **kwargs):
        args_seen.append((args, kwargs))
        return result

    pilot = SimpleNamespace(step=step)
    controller = SimpleNamespace(_pilot=pilot)
    pixels, gains = object(), object()
    python_rng = random.getstate()
    numpy_rng = np.random.get_state()
    with MotorRateDiagnostic(controller) as diagnostic:
        assert pilot.step(pixels, 8, 8, gains=gains, seed=7, detail=True) is result
        assert args_seen == [((pixels, 8, 8), {"gains": gains, "seed": 7, "detail": True})]
        exposed = diagnostic.rates
        exposed["stop"] = 999
        hz["back"] = 888
        assert diagnostic.rates == dict.fromkeys(MOTOR_POPULATIONS, 12.0)
    assert pilot.step is step
    assert random.getstate() == python_rng
    after_rng = np.random.get_state()
    assert numpy_rng[0] == after_rng[0]
    np.testing.assert_array_equal(numpy_rng[1], after_rng[1])
    assert numpy_rng[2:] == after_rng[2:]


def test_failed_pilot_clears_sample_propagates_same_exception_and_restores():
    failure = RuntimeError("injected simulator failure")
    count = 0

    def step():
        nonlocal count
        count += 1
        if count == 2:
            raise failure
        return (0, 0, False, dict.fromkeys(MOTOR_POPULATIONS, 1), {})

    controller = SimpleNamespace(_pilot=SimpleNamespace(step=step))
    with pytest.raises(RuntimeError) as caught:
        with MotorRateDiagnostic(controller) as diagnostic:
            controller._pilot.step()
            assert diagnostic.rates is not None
            controller._pilot.step()
    assert caught.value is failure
    assert diagnostic.rates is None
    assert diagnostic.error == "pilot raised RuntimeError"
    assert diagnostic.calls == 2
    assert controller._pilot.step is step


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -1, None, "invalid"])
def test_invalid_capture_preserves_original_return(invalid):
    rates = dict.fromkeys(MOTOR_POPULATIONS, 0)
    rates["stop"] = invalid
    result = (0, 0, False, rates, {})
    controller = SimpleNamespace(_pilot=SimpleNamespace(step=lambda: result))
    with MotorRateDiagnostic(controller) as diagnostic:
        assert controller._pilot.step() is result
        assert diagnostic.rates is None
        assert diagnostic.error.startswith("invalid motor telemetry:")


def test_nested_context_rejected_and_outer_binding_restored():
    def original():
        return (0, 0, False, dict.fromkeys(MOTOR_POPULATIONS, 0))

    controller = SimpleNamespace(_pilot=SimpleNamespace(step=original))
    diagnostic = MotorRateDiagnostic(controller)
    with diagnostic:
        wrapped = controller._pilot.step
        with pytest.raises(RuntimeError, match="already active"):
            with MotorRateDiagnostic(controller):
                pytest.fail("nested capture must not install")
        with pytest.raises(RuntimeError, match="already active"):
            diagnostic.__enter__()
        assert controller._pilot.step is wrapped
    assert controller._pilot.step is original
    with diagnostic:
        controller._pilot.step()
        assert diagnostic.calls == 1
