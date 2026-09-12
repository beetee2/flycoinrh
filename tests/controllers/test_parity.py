"""Independent retinal/motor oracles and validation of operator model settings."""
import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st

from flyeye import FlyEye
from flytrap.contracts import Observation
from flytrap.controllers.fly import (FlyController, ModelParameters, VisualCalibration,
                                     write_baseline_checkpoint)


def test_centered_crop_matches_upstream_and_scalar_pixel_oracle(adapter_files):
    controller = FlyController(**adapter_files)
    image = np.arange(256, dtype=np.float32).reshape(16, 16) / 255
    original = FlyEye(controller._brain, annotations_path=adapter_files["annotations_path"])
    upstream = original.look(image, 8, 8, fov_w=16, fov_h=16, max_hz=180)
    actual = controller._eye.look(image, 8, 8)
    assert actual.keys() == upstream.keys()
    for group, uv, off in ((original.on_idx, original.on_uv, False),
                           (original.off_idx, original.off_uv, True)):
        sampled = np.array([image[min(15, max(0, int(float(v) * 16))),
                                  min(15, max(0, int(float(u) * 16)))] for u, v in zip(*uv)])
        rates = (1 - sampled) * 180 * 0.6 if off else sampled * 180
        np.testing.assert_array_equal(actual[tuple(group)], rates)
        np.testing.assert_array_equal(actual[tuple(group)], upstream[tuple(group)])
    assert any(not np.array_equal(actual[k], original.look(image, 8, 8)[k]) for k in actual)


def test_full_screen_integer_crop_sampling_parity(adapter_files):
    controller = FlyController(**adapter_files)
    eye = FlyEye(controller._brain, annotations_path=adapter_files["annotations_path"])
    world = np.random.default_rng(5).random((64, 64)).astype(np.float32)
    # An interior 16-pixel egocentric crop; duplicate its final edge because the
    # upstream u/v=1 endpoint requests the 17th pixel before raster clipping.
    # Padding the full scene's boundary makes it match the explicitly clipped crop.
    crop = world[16:32, 16:32].copy()
    screen = np.pad(crop, 16, mode="edge")
    expected = eye.look(screen, 24, 24, fov_w=16, fov_h=16)
    actual = controller._eye.look(crop, 8, 8)
    for key in actual:
        np.testing.assert_array_equal(actual[key], expected[key])


def test_motor_mapping_and_exact_spikes_match_recorded_neurons(adapter_files):
    controller = FlyController(**adapter_files)
    controller.reset(run_seed=0, checkpoint=controller.checkpoint)
    image = np.arange(256, dtype=np.float32).reshape(16, 16) / 255
    import hashlib
    seed = int.from_bytes(hashlib.sha256(b"FLYTRAP-step-seed-v1\0" + bytes(12)).digest()[:8], "big")
    raw = controller._brain.run(controller._eye.look(image, 8, 8), steps=100, seed=seed,
                                gains=np.ones(controller._brain.n_types, dtype=np.float32),
                                record=controller._pilot.motor, spike_log=True)
    rates = {name: float(raw[name].mean()) for name in controller._pilot.motor}
    turn = max(-1, min(1, (rates["steer_R"] - rates["steer_L"]) / 450))
    forward = (rates["fwd_L"] + rates["fwd_R"]) / 900
    speed = max(-1, min(1, forward - rates["back"] / 450)) * (1 - max(0, min(1, rates["stop"] / 450)))
    output = controller.step(Observation(schema_version="1", pixels=image.ravel().tolist()))
    assert output.dx == pytest.approx(turn)
    assert output.dy == pytest.approx(-speed)
    assert output.click == (rates["stop"] >= 330 and speed < 0.25)
    assert output.telemetry.spike_count == sum(len(spikes) for spikes in raw["_spikes"])
    assert output.telemetry.sampled_neurons == controller._brain.n


def test_hidden_scoring_information_cannot_change_serialized_response(adapter_files):
    controller = FlyController(**adapter_files)
    output = []
    envelopes = []
    for hidden in ({"goal": [0, 0], "target": "left", "score": 20},
                   {"goal": [900, 300], "target": "right", "score": -20}):
        scene = {"observation": Observation(schema_version="1", pixels=[0.5] * 256), **hidden}
        envelope = scene["observation"].model_dump_json().encode()
        assert set(json.loads(envelope)) == {"schema_version", "pixels"}
        envelopes.append(envelope)
        controller.reset(run_seed=991, checkpoint=controller.checkpoint)
        output.append(controller.step_serialized(envelope))
    assert envelopes[0] == envelopes[1]
    assert output[0] == output[1]


@pytest.mark.parametrize("field,value", [
    ("dt", 0), ("dt", float("nan")), ("tau_m", 0), ("refractory", -1),
    ("sim_steps", 0), ("sim_steps", 1001), ("sim_steps", True),
    ("v_reset", -40), ("v_rest", -40), ("v_thresh", float("inf")), ("reward", 1),
])
def test_invalid_model_settings(field, value):
    with pytest.raises(ValueError):
        ModelParameters(**{field: value})


@pytest.mark.parametrize("field,value", [("max_hz", float("nan")), ("max_hz", 1001),
                                        ("click_hz", -1), ("gain", 2.0), ("gain", True)])
def test_invalid_or_trained_calibration(field, value):
    with pytest.raises(ValueError):
        VisualCalibration(**{field: value})


@pytest.mark.parametrize("coordinate", [float("inf"), float("nan"), 1e10])
def test_invalid_retinal_metadata_fails(adapter_files_factory, coordinate):
    files = adapter_files_factory(annotation_edit=lambda frame: frame.__setitem__("assignedOlHex1", coordinate))
    write_baseline_checkpoint(**files)
    with pytest.raises(ValueError):
        FlyController(**files)


def test_partial_missing_retina_matches_upstream_mask(adapter_files_factory):
    def missing(frame):
        frame.loc[[0, 4], "assignedOlHex1"] = np.nan
    files = adapter_files_factory(annotation_edit=missing)
    write_baseline_checkpoint(**files)
    controller = FlyController(**files)
    upstream = FlyEye(controller._brain, annotations_path=files["annotations_path"])
    np.testing.assert_array_equal(controller._eye.on_idx, upstream.on_idx)
    np.testing.assert_array_equal(controller._eye.off_idx, upstream.off_idx)
    assert controller.provenance["retinal_cells_without_coordinates"] == {"L1": 1, "L2": 1}
    assert len(controller._eye.on_idx) == len(controller._eye.off_idx) == 3


def test_annotations_read_once_and_parameters_snapshot(adapter_files, monkeypatch):
    original = pd.read_feather
    reads = []
    def read(path, **kwargs):
        reads.append(path)
        return original(path, **kwargs)
    monkeypatch.setattr(pd, "read_feather", read)
    controller = FlyController(**adapter_files)
    assert len(reads) == 1
    provenance = controller.provenance
    adapter_files["parameters_path"].write_text('{"sim_steps":10}')
    controller.reset(run_seed=2, checkpoint=controller.checkpoint)
    for _ in range(2):
        assert controller.step(Observation(schema_version="1", pixels=[1.0] * 256)).telemetry.neural_ms == 20
    assert len(reads) == 1
    assert controller.provenance == provenance
    assert np.all(controller._gains == 1)
    with pytest.raises(ValueError):
        controller._brain.wdata[0] = 99


def test_import_closure_has_no_privileged_services(tmp_path):
    code = """
import sys, pathlib, json
from flytrap.controllers.fly import FlyController
print(json.dumps({'modules': sorted(sys.modules), 'files': list(map(str, pathlib.Path('.').iterdir()))}))
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    loaded = json.loads(result.stdout)
    forbidden = {"roam", "rhwallet", "rhlive", "rhprovider", "voice", "xpost", "envcfg",
                 "mushroom", "calibration", "flytrap.arena", "flytrap.api", "flytrap.worker"}
    assert not forbidden.intersection(loaded["modules"])
    assert loaded["files"] == []


@settings(max_examples=20, deadline=None)
@given(pixels=st.lists(st.floats(min_value=0, max_value=1, allow_nan=False), min_size=256, max_size=256))
def test_float32_raster_preserves_normalized_bounds(pixels):
    # Raster conversion cannot introduce nonfinite/negative/superunit input.
    observation = Observation(schema_version="1", pixels=pixels)
    raster = np.asarray(observation.pixels, dtype=np.float32).reshape(16, 16)
    assert np.isfinite(raster).all() and (raster >= 0).all() and (raster <= 1).all()
