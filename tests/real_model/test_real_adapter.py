"""Actual connectome adapter gate: unavailable data fails, never skips or substitutes."""

import hashlib
import json
import os
from pathlib import Path
from time import perf_counter

import pytest

from flytrap.contracts import ControllerOutput, Observation
from flytrap.controllers.fly import (
    FlyController,
    ModelParameters,
    VisualCalibration,
    write_baseline_checkpoint,
)
from flytrap.data.bundle import file_sha256

pytestmark = [pytest.mark.real_model, pytest.mark.timeout(120)]


@pytest.fixture
def real_controller(tmp_path):
    repository = Path(__file__).resolve().parents[2]
    graph_root = Path(os.environ.get("FLYTRAP_GRAPH_ROOT", repository / "build/flytrap-v1")).resolve()
    raw_root = Path(os.environ.get("FLYTRAP_RAW_ROOT", repository / "data")).resolve()
    annotations_path = raw_root / "body-annotations.feather"
    required = [graph_root / "graph.npz", graph_root / "manifest.json", annotations_path]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        pytest.fail("Real adapter gate requires the pinned graph and annotations: " + ", ".join(missing))

    parameters_path = tmp_path / "parameters.json"
    calibration_path = tmp_path / "calibration.json"
    checkpoint_path = tmp_path / "baseline.json"
    parameters_path.write_text(ModelParameters().model_dump_json())
    calibration_path.write_text(VisualCalibration().model_dump_json())
    inputs = {
        "graph_root": graph_root,
        "annotations_path": annotations_path,
        "parameters_path": parameters_path,
        "calibration_path": calibration_path,
        "checkpoint_path": checkpoint_path,
    }
    started = perf_counter()
    checkpoint = write_baseline_checkpoint(**inputs)
    checkpoint_seconds = perf_counter() - started
    started = perf_counter()
    controller = FlyController(**inputs)
    loading_seconds = perf_counter() - started
    provenance = controller.provenance
    assert provenance["fixture"] is False
    assert provenance["learning_enabled"] is False
    assert provenance["neural_state_mode"] == "windowed_reset"
    assert provenance["gains"] == "all-one-float32"
    assert controller.checkpoint == checkpoint
    assert checkpoint.sha256 == file_sha256(checkpoint_path)
    assert checkpoint.graph_sha256 == file_sha256(graph_root / "graph.npz")
    assert provenance["annotations_sha256"] == file_sha256(annotations_path)
    assert provenance["parameters_sha256"] == file_sha256(parameters_path)
    assert provenance["calibration_sha256"] == file_sha256(calibration_path)
    assert all(count > 0 for count in provenance["populations"].values())
    assert provenance["neurons"] > 0
    print(json.dumps({
        "gate": "real_adapter", "fixture": False,
        "checkpoint_preparation_seconds": checkpoint_seconds,
        "controller_loading_seconds": loading_seconds,
        "provenance": provenance,
    }, sort_keys=True))
    return controller, checkpoint_path


def test_real_windows_repeat_after_reset_with_explicit_provenance(real_controller, tmp_path, monkeypatch):
    controller, checkpoint_path = real_controller
    provenance_before = controller.provenance
    checkpoint_hash = file_sha256(checkpoint_path)
    observations = [
        Observation(schema_version="1", pixels=[0.0] * 256),
        Observation(schema_version="1", pixels=[float((x // 2 + y // 2) % 2)
                                                for y in range(16) for x in range(16)]),
    ]
    payloads = [observation.model_dump_json().encode() for observation in observations]
    observation_hashes = [hashlib.sha256(payload).hexdigest() for payload in payloads]
    assert len(set(observation_hashes)) == 2

    # Step and reset must retain their explicit sources after moving outside the checkout.
    unrelated = tmp_path / "unrelated-working-directory"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    traces = []
    run_seed = 20260911
    for repetition in range(2):
        controller.reset(run_seed=run_seed, checkpoint=controller.checkpoint)
        trace = []
        for step_index, payload in enumerate(payloads):
            started = perf_counter()
            serialized_output = controller.step_serialized(payload)
            wall_seconds = perf_counter() - started
            output = ControllerOutput.model_validate_json(serialized_output)
            assert output.model_mode == "windowed_reset"
            assert output.telemetry.sampled_neurons == provenance_before["neurons"]
            assert output.telemetry.spike_count > 0
            parameters = provenance_before["parameters"]
            assert output.telemetry.neural_ms == parameters["dt"] * parameters["sim_steps"]
            assert -1 <= output.dx <= 1 and -1 <= output.dy <= 1
            trace.append(serialized_output)
            print(json.dumps({
                "gate": "real_adapter_window", "fixture": False,
                "repetition": repetition, "step_index": step_index, "run_seed": run_seed,
                "observation_sha256": observation_hashes[step_index],
                "output_sha256": hashlib.sha256(serialized_output).hexdigest(),
                "wall_seconds": wall_seconds, "output": output.model_dump(),
            }, sort_keys=True))
        traces.append(trace)

    assert traces[0] == traces[1]
    assert controller.provenance == provenance_before
    assert file_sha256(checkpoint_path) == checkpoint_hash
