"""Explicit untrained FlyEye/FlyBrain adapter; evaluation input is pixels only."""
import hashlib
import json
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

import flyeye
import flysim
from flyeye import FlyEye, FlyPilot
from flysim import FlyBrain
from flytrap.contracts import CheckpointRef, ControllerOutput, Observation
from flytrap.data.bundle import DatasetSource, file_sha256, load_bundle

MAX_OBSERVATION_BYTES = 32_768
SEED_DOMAIN = b"FLYTRAP-step-seed-v1\0"


class ModelParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    schema_version: Literal["flytrap-model-1"] = "flytrap-model-1"
    v_rest: float = Field(default=-52.0, ge=-100, le=-1)
    v_thresh: float = Field(default=-45.0, ge=-99, le=0)
    v_reset: float = Field(default=-52.0, ge=-100, le=-1)
    tau_m: float = Field(default=20.0, ge=1, le=1000)
    refractory: float = Field(default=2.2, ge=0, le=100)
    dt: float = Field(default=0.2, ge=0.01, le=1)
    sim_steps: int = Field(default=100, ge=1, le=1000)

    @model_validator(mode="after")
    def threshold_order(self):
        if max(self.v_rest, self.v_reset) >= self.v_thresh:
            raise ValueError("rest and reset must be below threshold")
        return self


class VisualCalibration(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    schema_version: Literal["flytrap-calibration-1"] = "flytrap-calibration-1"
    calibration_id: Literal["untrained-visual-v1"] = "untrained-visual-v1"
    max_hz: float = Field(default=180.0, ge=0, le=1000)
    click_hz: float = Field(default=330.0, ge=0, le=1000)
    gain: float = Field(default=1.0, ge=1, le=1)


def _json_bytes(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _read_config(path, model):
    payload = Path(path).resolve().read_bytes()
    if len(payload) > 16_384:
        raise ValueError("model configuration exceeds size limit")
    return model.model_validate_json(payload), hashlib.sha256(payload).hexdigest()


def _load_inputs(*, graph_root, annotations_path, parameters_path, calibration_path, allow_fixture):
    graph_root, annotations_path = Path(graph_root).resolve(), Path(annotations_path).resolve()
    graph, manifest = load_bundle(graph_root, allow_fixture=allow_fixture)
    if not manifest.source.fixture:
        catalog = Path(__file__).resolve().parents[1] / "data/sources.json"
        if manifest.source != DatasetSource.model_validate_json(catalog.read_bytes()):
            raise ValueError("real graph must use the pinned public source")
    expected_annotations = next(
        (f.sha256 for f in manifest.source.files if f.filename == "body-annotations.feather"), None)
    annotations_hash = file_sha256(annotations_path)
    if annotations_hash != expected_annotations:
        raise ValueError("annotations checksum does not match graph source")
    parameters, parameters_hash = _read_config(parameters_path, ModelParameters)
    calibration, calibration_hash = _read_config(calibration_path, VisualCalibration)
    descriptor = {
        "schema_version": "flytrap-baseline-1", "checkpoint_id": "fly-baseline-v1",
        "graph_sha256": manifest.graph_sha256, "annotations_sha256": annotations_hash,
        "parameters_sha256": parameters_hash, "calibration_sha256": calibration_hash,
        "parameters": parameters.model_dump(), "calibration": calibration.model_dump(),
        "fixture": manifest.source.fixture, "neural_state_mode": "windowed_reset",
        "gains": "all-one-float32", "learning_enabled": False,
        "seed_stream": "sha256-domain-u32be-run-u64be-step-first-u64be-v1",
        "observation_mapping": "16x16-float32-center-8-fov-16-truncate-clip-v1",
        "action_mapping": "upstream-pilot-divide-90-v1",
        "upstream_revision": manifest.builder["upstream_revision"],
        "model_source_sha256": {
            "flysim": file_sha256(Path(flysim.__file__)),
            "flyeye": file_sha256(Path(flyeye.__file__)),
            "adapter": file_sha256(Path(__file__)),
        },
    }
    return graph, manifest, parameters, calibration, descriptor


def _checkpoint(descriptor, payload):
    return CheckpointRef(schema_version="1", checkpoint_id="fly-baseline-v1",
                         sha256=hashlib.sha256(payload).hexdigest(),
                         graph_sha256=descriptor["graph_sha256"],
                         model_mode="fixture" if descriptor["fixture"] else "windowed_reset")


def write_baseline_checkpoint(*, graph_root, annotations_path, parameters_path,
                              calibration_path, checkpoint_path, allow_fixture=False) -> CheckpointRef:
    """Operator-only creation of a new descriptor; never overwrite a checkpoint."""
    *_, descriptor = _load_inputs(graph_root=graph_root, annotations_path=annotations_path,
                                  parameters_path=parameters_path, calibration_path=calibration_path,
                                  allow_fixture=allow_fixture)
    payload = _json_bytes(descriptor)
    with Path(checkpoint_path).resolve().open("xb") as stream:
        stream.write(payload)
    return _checkpoint(descriptor, payload)


class _CenteredEye(FlyEye):
    def __init__(self, brain, annotations, max_hz):
        super().__init__(brain, annotations=annotations)
        self._max_hz = max_hz

    def look(self, img, cx, cy):
        # Coordinates are fixed adapter constants; task/world coordinates never enter.
        return super().look(img, 8, 8, fov_w=16, fov_h=16, max_hz=self._max_hz)


class FlyController:
    def __init__(self, *, graph_root: Path, annotations_path: Path, parameters_path: Path,
                 calibration_path: Path, checkpoint_path: Path, allow_fixture: bool = False):
        graph_root, annotations_path = Path(graph_root).resolve(), Path(annotations_path).resolve()
        graph, manifest, params, calibration, descriptor = _load_inputs(
            graph_root=graph_root, annotations_path=annotations_path,
            parameters_path=parameters_path, calibration_path=calibration_path,
            allow_fixture=allow_fixture)
        payload = Path(checkpoint_path).resolve().read_bytes()
        if payload != _json_bytes(descriptor):
            raise ValueError("checkpoint is corrupt or does not match the explicit baseline configuration")
        self._checkpoint = _checkpoint(descriptor, payload)
        self._params = params
        self._descriptor = descriptor
        self._brain = FlyBrain(graph_path=graph_root / "graph.npz", p=params)
        # Guard the second upstream file read and validate its correspondence to the bundle.
        if file_sha256(graph_root / "graph.npz") != manifest.graph_sha256:
            raise ValueError("graph changed during adapter construction")
        if (self._brain.W != graph.W).nnz or not np.array_equal(self._brain.bodies, graph.bodies):
            raise ValueError("upstream graph loader disagrees with verified bundle")
        annotations = pd.read_feather(annotations_path, columns=[
            "bodyId", "assignedOlHex1", "assignedOlHex2", "somaSide"])
        if file_sha256(annotations_path) != descriptor["annotations_sha256"]:
            raise ValueError("annotations changed during adapter construction")
        unique = annotations.drop_duplicates()
        if unique.bodyId.duplicated().any():
            raise ValueError("conflicting duplicate retina/motor annotations")
        aligned = unique.set_index("bodyId").reindex(self._brain.bodies)
        coords = aligned[["assignedOlHex1", "assignedOlHex2"]].to_numpy(dtype=float)
        if np.isinf(coords).any():
            raise ValueError("retinal coordinates must be finite or missing")
        for population in ("L1", "L2"):
            selected = self._brain.types == population
            # Upstream excludes cells whose retinotopic assignment is missing.
            # Require a usable population, while preserving that explicit mask.
            if not np.isfinite(coords[selected]).all(axis=1).any():
                raise ValueError(f"required retinal population {population} missing finite coordinates")
        if np.any(np.abs(coords[np.isfinite(coords)]) > 1_000_000):
            raise ValueError("retinal coordinates exceed supported bounds")
        self._eye = _CenteredEye(self._brain, unique, calibration.max_hz)
        self._pilot = FlyPilot(self._brain, eye=self._eye, sim_steps=params.sim_steps,
                               click_hz=calibration.click_hz, annotations=unique)
        missing = [name for name, indices in self._pilot.motor.items() if not len(indices)]
        if missing:
            raise ValueError(f"required motor populations are missing: {missing}")
        self._gains = np.ones(self._brain.n_types, dtype=np.float32)
        self._gains.flags.writeable = False
        for array in (self._brain.wdata, self._brain.W.data, self._brain.indices, self._brain.indptr):
            array.flags.writeable = False
        self._run_seed = None
        self._step_index = 0

    @property
    def checkpoint(self) -> CheckpointRef:
        return self._checkpoint.model_copy(deep=True)

    @property
    def provenance(self) -> dict:
        return json.loads(_json_bytes({**self._descriptor, "checkpoint": self._checkpoint.model_dump(),
                                      "populations": {"L1": len(self._eye.on_idx),
                                                      "L2": len(self._eye.off_idx),
                                                      **{k: len(v) for k, v in self._pilot.motor.items()}},
                                      "retinal_cells_without_coordinates": {
                                          "L1": int((self._brain.types == "L1").sum()) - len(self._eye.on_idx),
                                          "L2": int((self._brain.types == "L2").sum()) - len(self._eye.off_idx)},
                                      "neurons": self._brain.n}))

    def reset(self, *, run_seed: int, checkpoint: CheckpointRef) -> None:
        self._run_seed = None
        self._step_index = 0
        if type(run_seed) is not int or not 0 <= run_seed <= 2**32 - 1:
            raise ValueError("run_seed must be an unsigned 32-bit integer")
        if type(checkpoint) is not CheckpointRef or checkpoint != self._checkpoint:
            raise ValueError("checkpoint must match the loaded explicit baseline")
        self._gains = np.ones(self._brain.n_types, dtype=np.float32)
        self._gains.flags.writeable = False
        self._run_seed = run_seed

    def step(self, observation: Observation) -> ControllerOutput:
        if self._run_seed is None:
            raise RuntimeError("reset must precede step, including after a model error")
        if type(observation) is not Observation or set(vars(observation)) != {"schema_version", "pixels"}:
            raise ValueError("controller requires only the declared Observation fields")
        observation = Observation.model_validate(observation.model_dump())
        seed = int.from_bytes(hashlib.sha256(
            SEED_DOMAIN + self._run_seed.to_bytes(4, "big") + self._step_index.to_bytes(8, "big")
        ).digest()[:8], "big")
        image = np.asarray(observation.pixels, dtype=np.float32).reshape(16, 16)
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                dx, dy, click, hz, info = self._pilot.step(
                    image, 8, 8, gains=self._gains, seed=seed, detail=True)
            values = [dx, dy, *hz.values(), info["mean_mv"], info["spikes_per_sec"]]
            if not np.isfinite(values).all() or any(rate < 0 for rate in hz.values()):
                raise ValueError("nonfinite or negative neural output")
            output = ControllerOutput(
                schema_version="1", dx=float(dx / 90.0), dy=float(dy / 90.0), click=bool(click),
                model_mode=self._checkpoint.model_mode,
                telemetry={"schema_version": "1", "sampled_neurons": info["sampled_neurons"],
                           "spike_count": info["spike_count"],
                           "neural_ms": self._params.sim_steps * self._params.dt})
        except Exception:
            self._run_seed = None
            raise
        self._step_index += 1
        return output

    def step_serialized(self, payload: bytes) -> bytes:
        """Bounded observation JSON envelope for the later simulator IPC boundary."""
        if type(payload) is not bytes or len(payload) > MAX_OBSERVATION_BYTES:
            raise ValueError("observation envelope exceeds byte limit or is not bytes")
        return self.step(Observation.model_validate_json(payload)).model_dump_json().encode()
