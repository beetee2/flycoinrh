"""Read-only inspection of the unchanged baseline sensory boundary.

The milestone 05 retinal_coverage.py audit checked sampling against eye UVs.
This maintained oracle instead derives the mapping from checksum-verified raw
annotations, independently of FlyEye's masks, UVs and sampling implementation.
No function in this module calls FlyBrain.run or advances neural state.
"""

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd

from flytrap.contracts import Observation
from flytrap.data.bundle import file_sha256

MOTOR_NAMES = ("steer_L", "steer_R", "fwd_L", "fwd_R", "back", "stop", "click")
STATISTIC_NAMES = ("sampled_neurons", "spike_count", "firing", "spikes_per_sec", "mean_mv", "visual", "motor")


def _oracle(controller, annotations_path):
    path = Path(annotations_path) if annotations_path is not None else (
        Path(__file__).resolve().parents[2] / "data/body-annotations.feather")
    expected_hash = controller.provenance["annotations_sha256"]
    if file_sha256(path) != expected_hash:
        raise ValueError("sampling oracle annotations do not match the model")
    annotations = pd.read_feather(path, columns=["bodyId", "assignedOlHex1", "assignedOlHex2"])
    if file_sha256(path) != expected_hash:
        raise ValueError("sampling oracle annotations changed while reading")
    annotations = annotations.drop_duplicates()
    if annotations.bodyId.duplicated().any():
        raise ValueError("sampling oracle requires unambiguous body coordinates")
    brain = controller._brain
    aligned = annotations.set_index("bodyId").reindex(brain.bodies)
    h1 = aligned.assignedOlHex1.to_numpy(dtype=float)
    h2 = aligned.assignedOlHex2.to_numpy(dtype=float)
    finite = np.isfinite(h1) & np.isfinite(h2)
    selected = finite & np.isin(brain.types, ("L1", "L2"))
    if not selected.any():
        raise ValueError("sampling oracle requires finite retinal coordinates")

    # Preserve upstream arithmetic order and promotion exactly: x starts in
    # float32; y multiplies float32 coordinates by NumPy's float64 sqrt scalar.
    # Converting everything to float64 changes truncation at pixel boundaries.
    axial_1 = h1[selected].astype(np.float32)
    axial_2 = h2[selected].astype(np.float32)
    x = axial_1 + axial_2 * 0.5
    y = axial_2 * (np.sqrt(3) / 2)
    horizontal = np.clip((x - x.min()) / (x.max() - x.min() + 1e-9), 0, 1)
    vertical = np.clip((y - y.min()) / (y.max() - y.min() + 1e-9), 0, 1)
    # Center 8, field of view 16; int truncation then clipping is the adapter's
    # declared mapping. Derive flat indices without consulting eye UV arrays.
    columns = np.clip((horizontal * 16).astype(int), 0, 15)
    rows = np.clip((vertical * 16).astype(int), 0, 15)
    indices = np.flatnonzero(selected)
    mapping = {}
    for name in ("L1", "L2"):
        population = brain.types[indices] == name
        mapping[name] = (
            indices[population], (rows * 16 + columns)[population],
            int(np.sum((brain.types == name) & ~finite)),
        )
    return mapping


def _check_drive(actual, retina):
    expected_keys = {tuple(pop["neuron_indices"]) for pop in retina["populations"].values()}
    if set(actual) != expected_keys:
        raise ValueError("actual retinal population indices disagree with the raw-annotation oracle")
    for name, population in retina["populations"].items():
        observed = np.asarray(actual[tuple(population["neuron_indices"])])
        expected = np.asarray(population["drive_hz"], dtype=np.float32)
        if observed.shape != expected.shape or not np.array_equal(observed, expected):
            raise ValueError(f"actual {name} drive disagrees with the raw-annotation sampling oracle")


def inspect_retina(controller, observation: Observation, *, annotations_path=None) -> dict:
    """Return exact coverage, discarded pixels and verified input drive, in Hz.

    ``sampled_pixels_u8`` is the nearest uint8 representation of the normalized
    Observation; P00 inputs are uint8/255. The drive uses the actual float32
    Observation values, with no brightness normalization or retina reshaping.
    """
    if type(observation) is not Observation:
        raise ValueError("sensory inspection requires a validated Observation")
    observation = Observation.model_validate(observation.model_dump())
    flat = np.asarray(observation.pixels, dtype=np.float32)
    mapping = _oracle(controller, annotations_path)
    max_hz = controller.provenance["calibration"]["max_hz"]
    result = {"populations": {}}
    union = np.zeros(256, dtype=int)
    for name, (indices, pixels, missing) in mapping.items():
        samples = flat[pixels]
        drive = samples * max_hz if name == "L1" else (1.0 - samples) * max_hz * 0.6
        counts = np.bincount(pixels, minlength=256)
        union += counts
        result["populations"][name] = {
            "neuron_indices": indices.tolist(),
            "body_ids": controller._brain.bodies[indices].astype(int).tolist(),
            "pixel_indices": pixels.tolist(),
            "sampled_pixels_u8": np.rint(samples * 255).astype(int).tolist(),
            "drive_hz": drive.tolist(), "coverage_counts": counts.tolist(),
            "missing_coordinates": missing,
        }
    result.update(union_coverage_counts=union.tolist(), sampled_pixel_count=int(np.count_nonzero(union)),
                  discarded_pixel_indices=np.flatnonzero(union == 0).tolist())
    _check_drive(controller._eye.look(flat.reshape(16, 16), 8, 8), result)
    return result


class ResponseCapture:
    """Passively copy one controller window's raw rates, statistics and drive.

    Usage: ``with ResponseCapture(controller, observation) as capture:`` then
    ``controller.step(observation)``. The baseline adapter and reset semantics
    remain unchanged. The intercepted eye result is checked before brain.run.
    """

    def __init__(self, controller, observation: Observation, *, annotations_path=None):
        self.controller = controller
        self.observation = observation
        self.annotations_path = annotations_path
        self.rates = None
        self.statistics = None
        self.retina = None
        self._entered = False

    def __enter__(self):
        if self._entered:
            raise RuntimeError("response capture is already active")
        self.retina = inspect_retina(self.controller, self.observation, annotations_path=self.annotations_path)
        pilot, eye = self.controller._pilot, self.controller._eye
        self._original_step, self._original_look = pilot.step, eye.look
        expected_image = np.asarray(self.observation.pixels, dtype=np.float32).reshape(16, 16)

        def look(image, *args, **kwargs):
            if not np.array_equal(image, expected_image):
                raise ValueError("inference pixels differ from the inspected Observation")
            drive = self._original_look(image, *args, **kwargs)
            _check_drive(drive, self.retina)
            self._drive_seen = True
            return drive

        def step(*args, **kwargs):
            if self.rates is not None:
                raise RuntimeError("response capture permits only one controller step")
            self._drive_seen = False
            result = self._original_step(*args, **kwargs)
            if not self._drive_seen or len(result) != 5:
                raise ValueError("response capture requires actual retinal drive and detailed model outputs")
            _, _, _, rates, statistics = result
            if set(rates) != set(MOTOR_NAMES):
                raise ValueError("unexpected motor-population response schema")
            self.rates = {name: float(rates[name]) for name in MOTOR_NAMES}
            self.statistics = deepcopy({name: statistics[name] for name in STATISTIC_NAMES})
            return result

        eye.look, pilot.step = look, step
        self._entered = True
        return self

    def __exit__(self, *_):
        self.controller._pilot.step = self._original_step
        self.controller._eye.look = self._original_look
        self._entered = False
