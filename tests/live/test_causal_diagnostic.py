"""Fixture-only checks of the OBS06 diagnostic intervention and fixed playback."""
import numpy as np
import pytest

from flytrap.contracts import Observation
from flytrap.controllers.fly import FlyController
from flytrap.live.sensory import CompiledRetina, LiveResponseCapture
from scripts.live_causal import diagnostic_drive, fixed_flight, safe_stimuli
from tests.controllers import conftest as synthetic_fixtures

adapter_files = synthetic_fixtures.adapter_files
adapter_files_factory = synthetic_fixtures.adapter_files_factory


def test_safe_sequence_changes_every_sampled_region(adapter_files):
    controller = FlyController(**adapter_files)
    retina = CompiledRetina(controller, annotations_path=adapter_files["annotations_path"])
    samples = safe_stimuli()
    assert len({s["sha256"] for s in samples}) == 8
    arrays = np.array([s["observation_u8"] for s in samples])
    assert np.all(np.ptp(arrays, axis=0) == 192)
    inspected = [retina.inspect(Observation(schema_version="1", pixels=[v/255 for v in s["observation_u8"]]))
                 for s in samples]
    for name in ("L1", "L2"):
        drives = np.array([s["populations"][name]["drive_hz"] for s in inspected])
        assert np.all(np.ptp(drives, axis=0) > 0)


def test_disconnection_reaches_brain_as_zero_while_black_eye_is_active(adapter_files, monkeypatch):
    controller = FlyController(**adapter_files)
    retina = CompiledRetina(controller, annotations_path=adapter_files["annotations_path"])
    controller.reset(run_seed=42, checkpoint=controller.checkpoint)
    black = Observation(schema_version="1", pixels=[0.]*256)
    original = controller._brain.run
    calls = []

    def inspect(drive, *args, **kwargs):
        calls.append({k: np.asarray(v).copy() for k, v in drive.items()})
        return original(drive, *args, **kwargs)

    monkeypatch.setattr(controller._brain, "run", inspect)
    weights, gains = controller._brain.wdata.copy(), controller._gains.copy()
    with diagnostic_drive(controller, disconnected=True) as evidence:
        with LiveResponseCapture(controller, black, retina=retina) as tap:
            controller.step(black)
    assert len(calls) == 1
    assert all(np.count_nonzero(v) == 0 for v in calls[0].values())
    assert any(v > 0 for group in evidence["ordinary_drive_hz"] for v in group["rates"])
    assert all(v == 0 for group in evidence["submitted_drive_hz"] for v in group["rates"])
    assert all(rate == 0 for rate in tap.rates.values())
    assert controller._brain.run is inspect
    np.testing.assert_array_equal(controller._brain.wdata, weights)
    np.testing.assert_array_equal(controller._gains, gains)


def test_hook_restores_brain_method_on_failed_attempt(adapter_files, monkeypatch):
    controller = FlyController(**adapter_files)

    def fail(*args, **kwargs):
        raise RuntimeError("deliberate model failure")

    monkeypatch.setattr(controller._brain, "run", fail)
    with pytest.raises(RuntimeError, match="deliberate model failure"):
        with diagnostic_drive(controller, disconnected=True):
            controller._brain.run({(0,): np.array([100.])}, seed=1)
    assert controller._brain.run is fail


def test_ordinary_diagnostic_preserves_fixture_result_and_matched_seed(adapter_files):
    controller = FlyController(**adapter_files)
    sample = safe_stimuli()[1]
    observation = Observation(schema_version="1", pixels=[v/255 for v in sample["observation_u8"]])
    controller.reset(run_seed=42, checkpoint=controller.checkpoint)
    expected = controller.step(observation)
    controller.reset(run_seed=42, checkpoint=controller.checkpoint)
    with diagnostic_drive(controller, disconnected=False) as evidence:
        actual = controller.step(observation)
    assert actual == expected
    assert evidence["ordinary_drive_hz"] == evidence["submitted_drive_hz"]


def test_zero_response_never_translates_and_repeat_is_exact():
    zero = dict(steer_L=0., steer_R=0., fwd_L=0., fwd_R=0., back=0., stop=0., click=0.)
    result = fixed_flight([zero]*8)
    assert len(result["states"]) == 201
    assert all(state["snapshot"]["position"] == [0., 0., 2.] for state in result["states"])
    assert all(state["snapshot"]["neutral"] for state in result["states"])
    assert result == fixed_flight([zero]*8)


def test_constant_rates_give_constant_controls_and_fixed_reproducible_motion():
    constant = dict(steer_L=200., steer_R=50., fwd_L=140., fwd_R=140., back=80., stop=0., click=0.)
    result = fixed_flight([constant]*8)
    for field in ("yaw_rate_rad_s", "pitch_target_rad", "speed_target_units_s"):
        assert len({control[field] for control in result["controls"]}) == 1
    assert result["states"][-1]["snapshot"]["position"] != [0., 0., 2.]
    assert result == fixed_flight([constant]*8)
