"""Real-data sampling gate. No neural dynamics or full-model calls are run."""

import json
import os
from pathlib import Path

import numpy as np
import pytest

from flytrap.contracts import Observation
from flytrap.controllers.fly import FlyController, write_baseline_checkpoint
from flytrap.lab.sensory import inspect_retina

pytestmark = [pytest.mark.real_model, pytest.mark.timeout(120)]


def test_real_annotation_oracle_matches_actual_retina_without_inference(tmp_path):
    repository = Path(__file__).resolve().parents[2]
    raw = Path(os.environ.get("FLYTRAP_RAW_ROOT", repository / "data"))
    files = dict(
        graph_root=Path(os.environ.get("FLYTRAP_GRAPH_ROOT", repository / "build/flytrap-v1")),
        annotations_path=raw / "body-annotations.feather",
        parameters_path=repository / "config/flytrap-model-v1.json",
        calibration_path=repository / "config/flytrap-visual-v1.json",
        checkpoint_path=tmp_path / "baseline.json",
    )
    write_baseline_checkpoint(**files)
    controller = FlyController(**files)

    def forbidden(*args, **kwargs):
        pytest.fail("Real retina coverage inspection must not run neural dynamics")

    controller._brain.run = forbidden
    observation = Observation(schema_version="1", pixels=[value / 255 for value in range(256)])
    retina = inspect_retina(controller, observation, annotations_path=files["annotations_path"])
    assert controller.provenance["fixture"] is False
    assert 0 < retina["sampled_pixel_count"] < 256
    assert len(retina["discarded_pixel_indices"]) + retina["sampled_pixel_count"] == 256
    for name, population in retina["populations"].items():
        assert len(population["drive_hz"]) == controller.provenance["populations"][name]
        assert population["missing_coordinates"] == controller.provenance["retinal_cells_without_coordinates"][name]
        assert sum(population["coverage_counts"]) == len(population["neuron_indices"])
        assert all(np.isfinite(population["drive_hz"]))
    # Changing only discarded pixels produces the exact same actual drive.
    discarded = observation.model_copy(deep=True)
    for index in retina["discarded_pixel_indices"]:
        discarded.pixels[index] = 1.0 - discarded.pixels[index]
    assert inspect_retina(controller, discarded, annotations_path=files["annotations_path"]) == retina
    print(json.dumps({"gate": "P00_real_raw_annotation_sampling", "fixture": False,
                      "new_full_model_calls": 0, "retina": retina,
                      "model_provenance": controller.provenance}, sort_keys=True))
