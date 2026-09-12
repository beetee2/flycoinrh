"""Synthetic retinal boundary mechanics; these are not real-model evidence."""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from flytrap.contracts import Observation
from flytrap.controllers.fly import _CenteredEye
from flytrap.data.bundle import file_sha256
from flytrap.lab.sensory import MOTOR_NAMES, ResponseCapture, inspect_retina


@pytest.fixture
def synthetic_retina(tmp_path):
    path = tmp_path / "synthetic-annotations.feather"
    annotations = pd.DataFrame({
        "bodyId": [1, 2, 3, 4, 5, 6],
        "assignedOlHex1": [0.0, 2.0, float("nan"), 0.0, 2.0, 2.0],
        "assignedOlHex2": [0.0, 0.0, float("nan"), 2.0, 2.0, 2.0],
    })
    annotations.to_feather(path)
    brain = SimpleNamespace(bodies=np.arange(1, 7), types=np.array(["L1"] * 3 + ["L2"] * 3))
    eye = _CenteredEye(brain, annotations, 180.0)
    controller = SimpleNamespace(_brain=brain, _eye=eye, provenance={
        "annotations_sha256": file_sha256(path), "calibration": {"max_hz": 180.0}})
    return controller, path


def ramp():
    return Observation(schema_version="1", pixels=[value / 255 for value in range(256)])


def test_synthetic_oracle_coverage_drive_and_json_round_trip(synthetic_retina):
    controller, path = synthetic_retina
    retina = inspect_retina(controller, ramp(), annotations_path=path)
    on, off = retina["populations"]["L1"], retina["populations"]["L2"]
    assert on["neuron_indices"] == [0, 1]
    assert on["body_ids"] == [1, 2]
    assert on["pixel_indices"] == [0, 10]
    assert off["pixel_indices"] == [245, 255, 255]
    assert on["sampled_pixels_u8"] == [0, 10]
    assert off["sampled_pixels_u8"] == [245, 255, 255]
    assert on["missing_coordinates"] == 1
    assert off["missing_coordinates"] == 0
    assert retina["sampled_pixel_count"] == 4
    assert len(retina["discarded_pixel_indices"]) == 252
    assert retina["union_coverage_counts"][255] == 2
    assert sum(on["coverage_counts"]) == 2
    assert sum(off["coverage_counts"]) == 3
    assert off["drive_hz"][1:] == [0.0, 0.0]
    assert on["drive_hz"][1] == float(np.float32(10 / 255) * 180)
    assert json.loads(json.dumps(retina, allow_nan=False)) == retina


def test_synthetic_oracle_detects_eye_uv_tampering(synthetic_retina):
    controller, path = synthetic_retina
    controller._eye.on_uv[0][1] = 0.0
    with pytest.raises(ValueError, match="raw-annotation sampling oracle"):
        inspect_retina(controller, ramp(), annotations_path=path)


def test_synthetic_oracle_detects_population_tampering(synthetic_retina):
    controller, path = synthetic_retina
    controller._eye.on_idx[1] = 2
    with pytest.raises(ValueError, match="population indices"):
        inspect_retina(controller, ramp(), annotations_path=path)


def test_synthetic_oracle_rejects_changed_annotation_source(synthetic_retina):
    controller, path = synthetic_retina
    with path.open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="annotations do not match"):
        inspect_retina(controller, ramp(), annotations_path=path)


def test_synthetic_oracle_reports_discarded_pixel_changes(synthetic_retina):
    controller, path = synthetic_retina
    first = ramp()
    second = first.model_copy(deep=True)
    second.pixels[1] = 1.0
    assert inspect_retina(controller, first, annotations_path=path) == inspect_retina(
        controller, second, annotations_path=path)


def test_synthetic_capture_copies_actual_rates_and_restores_methods(synthetic_retina):
    controller, path = synthetic_retina
    rates = {name: float(index) for index, name in enumerate(MOTOR_NAMES)}
    statistics = dict(sampled_neurons=6, spike_count=9, firing=3, spikes_per_sec=450.0,
                      mean_mv=-51.0, visual=2, motor=1)
    calls = []

    def synthetic_step(image, cx, cy, **kwargs):
        calls.append(controller._eye.look(image, cx, cy))
        return 0.0, 0.0, False, rates, statistics

    controller._pilot = SimpleNamespace(step=synthetic_step)
    original_look = controller._eye.look
    observation = ramp()
    with ResponseCapture(controller, observation, annotations_path=path) as capture:
        result = controller._pilot.step(np.asarray(observation.pixels, dtype=np.float32).reshape(16, 16),
                                        8, 8, detail=True)
        assert result[3] is rates
        assert capture.rates == rates
        assert capture.statistics == statistics
        assert capture.retina["sampled_pixel_count"] == 4
        with pytest.raises(RuntimeError, match="only one"):
            controller._pilot.step(None, 8, 8)
    assert len(calls) == 1
    rates["click"] = 999.0
    statistics["spike_count"] = 999
    assert capture.rates["click"] == 6.0
    assert capture.statistics["spike_count"] == 9
    assert controller._pilot.step is synthetic_step
    assert controller._eye.look == original_look


def test_synthetic_capture_rejects_other_input_and_restores_on_error(synthetic_retina):
    controller, path = synthetic_retina
    controller._pilot = SimpleNamespace(step=lambda *args: controller._eye.look(*args))
    original = controller._pilot.step
    with pytest.raises(ValueError, match="inference pixels differ"):
        with ResponseCapture(controller, ramp(), annotations_path=path):
            controller._pilot.step(np.zeros((16, 16), dtype=np.float32), 8, 8)
    assert controller._pilot.step is original


def test_synthetic_oracle_requires_valid_observation(synthetic_retina):
    controller, path = synthetic_retina
    with pytest.raises(ValueError, match="validated Observation"):
        inspect_retina(controller, {"pixels": [0] * 256}, annotations_path=path)
