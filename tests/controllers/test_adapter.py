"""Actual FlyBrain/FlyPilot behavior on labeled synthetic graph bundles."""

import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from flytrap.contracts import ControllerOutput, Observation
from flytrap.controllers.fly import FlyController, write_baseline_checkpoint

pytestmark = pytest.mark.unit


def observation(value=0.5):
    return Observation(schema_version="1", pixels=[float(value)] * 256)


def trace(controller, seed=742):
    controller.reset(run_seed=seed, checkpoint=controller.checkpoint)
    return [controller.step(observation(value)) for value in (0.0, 1.0, 0.25, 0.75, 1.0, 0.0)]


def stable_trace(outputs):
    return [(out.dx, out.dy, out.click, out.model_mode, out.telemetry.sampled_neurons,
             out.telemetry.spike_count, out.telemetry.neural_ms) for out in outputs]


def test_real_engine_fixture_trace_is_bounded_and_repeatable(adapter_files):
    controller = FlyController(**adapter_files)
    first = trace(controller)
    assert stable_trace(first) == stable_trace(trace(controller))
    assert stable_trace(first) == stable_trace(trace(FlyController(**adapter_files)))
    assert sum(out.telemetry.spike_count for out in first) > 0
    assert any(out.dx != 0 or out.dy != 0 for out in first)
    assert all(out.model_mode == "fixture" for out in first)
    for out in first:
        assert -1 <= out.dx <= 1 and -1 <= out.dy <= 1
        assert out.telemetry.neural_ms == 20.0
        assert out.telemetry.sampled_neurons > 0
        assert ControllerOutput.model_validate_json(out.model_dump_json()) == out
    assert controller.provenance["fixture"] is True
    assert controller.provenance["neural_state_mode"] == "windowed_reset"


def test_pixels_change_actual_neural_trace(adapter_files):
    controller = FlyController(**adapter_files)
    controller.reset(run_seed=39, checkpoint=controller.checkpoint)
    dark = [controller.step(observation(0)) for _ in range(8)]
    controller.reset(run_seed=39, checkpoint=controller.checkpoint)
    bright = [controller.step(observation(1)) for _ in range(8)]
    assert stable_trace(dark) != stable_trace(bright)


def test_reset_isolates_interleaved_runs(adapter_files):
    controller = FlyController(**adapter_files)
    expected = stable_trace(trace(controller, 9))
    trace(controller, 98765)
    assert stable_trace(trace(controller, 9)) == expected
    assert stable_trace(trace(FlyController(**adapter_files), 9)) == expected


def test_seed_stream_depends_only_on_run_and_step(adapter_files, monkeypatch):
    from flysim import FlyBrain

    seeds = []
    original = FlyBrain.run

    def record_seed(self, *args, **kwargs):
        seeds.append(kwargs["seed"])
        return original(self, *args, **kwargs)

    monkeypatch.setattr(FlyBrain, "run", record_seed)
    controller = FlyController(**adapter_files)
    for pixels in (0.0, 1.0):
        controller.reset(run_seed=4294967295, checkpoint=controller.checkpoint)
        for _ in range(3):
            controller.step(observation(pixels))
    expected = [int.from_bytes(hashlib.sha256(
        b"FLYTRAP-step-seed-v1\0" + (4294967295).to_bytes(4, "big") + index.to_bytes(8, "big")
    ).digest()[:8], "big") for index in range(3)]
    assert seeds == expected + expected


def test_explicit_paths_survive_changed_working_directory(adapter_files, tmp_path, monkeypatch):
    expected = stable_trace(trace(FlyController(**adapter_files)))
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    assert stable_trace(trace(FlyController(**adapter_files))) == expected


def test_identity_survives_relocation(adapter_files, tmp_path):
    original = FlyController(**adapter_files)
    source = adapter_files["parameters_path"].parent
    moved = tmp_path / "relocated"
    shutil.copytree(source, moved)
    relocated = {key: moved / value.relative_to(source) if isinstance(value, Path) else value
                 for key, value in adapter_files.items()}
    restored = FlyController(**relocated)
    assert restored.checkpoint == original.checkpoint
    assert stable_trace(trace(restored)) == stable_trace(trace(original))


def test_step_requires_explicit_reset(adapter_files):
    with pytest.raises(RuntimeError, match="reset"):
        FlyController(**adapter_files).step(observation())


@pytest.mark.parametrize("seed", [-1, 2**32, True, 2.5, "12", None])
def test_invalid_seed_fails(adapter_files, seed):
    controller = FlyController(**adapter_files)
    with pytest.raises((ValueError, TypeError)):
        controller.reset(run_seed=seed, checkpoint=controller.checkpoint)


def test_checkpoint_reference_cannot_be_substituted(adapter_files):
    controller = FlyController(**adapter_files)
    for field, value in (("sha256", "0" * 64), ("graph_sha256", "0" * 64),
                         ("model_mode", "windowed_reset"), ("checkpoint_id", "other-model")):
        substituted = controller.checkpoint.model_copy(update={field: value})
        with pytest.raises(ValueError):
            controller.reset(run_seed=0, checkpoint=substituted)


def test_failed_reset_invalidates_previous_run(adapter_files):
    controller = FlyController(**adapter_files)
    controller.reset(run_seed=0, checkpoint=controller.checkpoint)
    controller.step(observation())
    with pytest.raises(ValueError):
        controller.reset(run_seed=-1, checkpoint=controller.checkpoint)
    with pytest.raises(RuntimeError, match="reset"):
        controller.step(observation())


def test_provenance_cannot_be_mutated_by_caller(adapter_files):
    controller = FlyController(**adapter_files)
    original = controller.provenance
    changed = controller.provenance
    changed["fixture"] = False
    for value in changed.values():
        if isinstance(value, dict):
            value.clear()
    assert controller.provenance == original


def test_checkpoint_reference_is_defensive(adapter_files):
    controller = FlyController(**adapter_files)
    original = controller.checkpoint
    exposed = controller.checkpoint
    exposed.sha256 = "0" * 64
    assert controller.checkpoint == original
    controller.reset(run_seed=1, checkpoint=original)
    assert controller.step(observation()).telemetry.spike_count >= 0


def test_checkpoint_creation_never_overwrites(adapter_files):
    original = adapter_files["checkpoint_path"].read_bytes()
    with pytest.raises(FileExistsError):
        write_baseline_checkpoint(**adapter_files)
    assert adapter_files["checkpoint_path"].read_bytes() == original


@pytest.mark.parametrize("component", ["graph_root", "annotations_path", "parameters_path",
                                        "calibration_path", "checkpoint_path"])
def test_missing_explicit_input_has_no_fallback(adapter_files, component, tmp_path):
    broken = {**adapter_files, component: tmp_path / "missing"}
    with pytest.raises((ValueError, OSError)):
        FlyController(**broken)


def test_fixture_requires_explicit_opt_in(adapter_files):
    with pytest.raises(ValueError, match="fixture"):
        FlyController(**{**adapter_files, "allow_fixture": False})


@pytest.mark.parametrize("population", [("L1", None), ("L2", None), ("DNa02", "L"),
                                       ("DNa02", "R"), ("DNa01", "L"), ("DNa01", "R"),
                                       ("MDN", None), ("DNp09", None), ("MN9", None)])
def test_missing_neural_population_fails(adapter_files_factory, population):
    files = adapter_files_factory(missing_population=population)
    with pytest.raises(ValueError):
        write_baseline_checkpoint(**files)
        FlyController(**files)


@pytest.mark.parametrize("component", ["annotations_path", "parameters_path", "calibration_path",
                                        "checkpoint_path"])
def test_modified_explicit_input_cannot_inherit_baseline_identity(adapter_files, component):
    path = adapter_files[component]
    if component == "annotations_path":
        import pandas as pd
        frame = pd.read_feather(path)
        frame.loc[0, "assignedOlHex1"] = 1.0
        frame.to_feather(path)
    else:
        payload = json.loads(path.read_text())
        if component == "parameters_path":
            payload["sim_steps"] = 101
        elif component == "calibration_path":
            payload["max_hz"] = 179.0
        else:
            payload["inherited_gains"] = [8.0]
        path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        FlyController(**adapter_files)


def test_unrelated_trained_files_are_not_loaded(adapter_files, tmp_path, monkeypatch):
    expected = stable_trace(trace(FlyController(**adapter_files)))
    unrelated = tmp_path / "upstream-state"
    unrelated.mkdir()
    for relative in ("build/gains.npz", "build/mb_gains.npz", "data/mb_state.npz",
                     "mushroom_state.npz", "trained_gains.npz"):
        path = unrelated / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"intentionally corrupt inherited state")
    monkeypatch.setenv("FLY_STATE_DIR", str(unrelated / "build"))
    monkeypatch.chdir(unrelated)
    assert stable_trace(trace(FlyController(**adapter_files))) == expected


@pytest.mark.parametrize("mutation", ["short", "long", "nan", "infinity", "negative", "overbright", "bool"])
def test_mutated_observation_is_revalidated(adapter_files, mutation):
    controller = FlyController(**adapter_files)
    controller.reset(run_seed=12, checkpoint=controller.checkpoint)
    invalid = observation()
    if mutation == "short":
        invalid.pixels.pop()
    elif mutation == "long":
        invalid.pixels.append(0.0)
    else:
        invalid.pixels[0] = {"nan": float("nan"), "infinity": float("inf"),
                             "negative": -0.01, "overbright": 1.01, "bool": True}[mutation]
    with pytest.raises((ValueError, TypeError)):
        controller.step(invalid)


@pytest.mark.parametrize("field", ["goal", "goal_coordinates", "challenge", "destination_side",
                                  "reward", "target_label", "dom", "distance_to_goal", "run_seed"])
def test_serialized_envelope_rejects_privileged_fields(adapter_files, field):
    controller = FlyController(**adapter_files)
    controller.reset(run_seed=0, checkpoint=controller.checkpoint)
    payload = {**observation().model_dump(), field: {"hidden": 1}}
    with pytest.raises((ValueError, TypeError)):
        controller.step_serialized(json.dumps(payload).encode())


def test_serialized_roundtrip_matches_direct_execution(adapter_files):
    direct = FlyController(**adapter_files)
    serialized = FlyController(**adapter_files)
    direct.reset(run_seed=42, checkpoint=direct.checkpoint)
    serialized.reset(run_seed=42, checkpoint=serialized.checkpoint)
    for value in (0.0, 0.5, 1.0):
        image = observation(value)
        response = serialized.step_serialized(image.model_dump_json().encode())
        assert isinstance(response, bytes)
        assert ControllerOutput.model_validate_json(response) == direct.step(image)


@pytest.mark.parametrize("payload", [b"{}", b"{", b"[]", b"null", b"\xff", b" " * 32769,
                                    b'{"schema_version":"1","pixels":[NaN]}', "not bytes"])
def test_invalid_serialized_payload_is_rejected(adapter_files, payload):
    controller = FlyController(**adapter_files)
    controller.reset(run_seed=0, checkpoint=controller.checkpoint)
    with pytest.raises((ValueError, TypeError)):
        controller.step_serialized(payload)


def test_object_boundary_rejects_metadata_even_when_schema_bypassed(adapter_files):
    controller = FlyController(**adapter_files)
    controller.reset(run_seed=0, checkpoint=controller.checkpoint)
    image = observation()
    object.__setattr__(image, "goal_coordinates", [2, 3])
    with pytest.raises(ValueError):
        controller.step(image)


def test_observation_subclass_cannot_expand_input_contract(adapter_files):
    class PrivilegedObservation(Observation):
        destination_side: str

    controller = FlyController(**adapter_files)
    controller.reset(run_seed=0, checkpoint=controller.checkpoint)
    with pytest.raises(ValueError):
        controller.step(PrivilegedObservation(**observation().model_dump(), destination_side="left"))


def test_simulator_exception_propagates_without_fallback(adapter_files, monkeypatch):
    from flysim import FlyBrain

    controller = FlyController(**adapter_files)
    controller.reset(run_seed=0, checkpoint=controller.checkpoint)

    def unavailable(*args, **kwargs):
        raise RuntimeError("injected simulator failure")

    monkeypatch.setattr(FlyBrain, "run", unavailable)
    with pytest.raises(RuntimeError, match="injected simulator failure"):
        controller.step(observation())
    with pytest.raises(RuntimeError, match="reset"):
        controller.step(observation())


@pytest.mark.parametrize("corrupted_key", ["steer_L", "stop", "_spikes_per_sec", "_mean_mv"])
def test_nonfinite_neural_results_fail_without_fallback(adapter_files, monkeypatch, corrupted_key):
    from flysim import FlyBrain

    original = FlyBrain.run

    def corrupted(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        result[corrupted_key] = np.array([np.nan]) if corrupted_key in ("steer_L", "stop") else np.nan
        return result

    monkeypatch.setattr(FlyBrain, "run", corrupted)
    controller = FlyController(**adapter_files)
    controller.reset(run_seed=0, checkpoint=controller.checkpoint)
    with pytest.raises((ValueError, RuntimeError)):
        controller.step(observation())
