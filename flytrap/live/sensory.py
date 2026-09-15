"""Compiled retinal verification and a passive tap outside the frozen model.

Construction reads verified raw annotations and checks a ramp against the P00
oracle. Live steps reuse only retinal index arrays and scalar calibration; they
never read or hash raw files, reset the controller, or alter its return value.
"""

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd

from flytrap.contracts import Observation
from flytrap.data.bundle import file_sha256
from flytrap.lab.sensory import MOTOR_NAMES, STATISTIC_NAMES, inspect_retina


class CompiledRetina:
    """Session-local, raw-annotation mapping independent of FlyEye's arrays."""

    def __init__(self, controller, *, annotations_path):
        self.controller = controller
        self._active = False
        path = Path(annotations_path)
        provenance = controller.provenance
        digest = provenance["annotations_sha256"]
        if file_sha256(path) != digest:
            raise ValueError("compiled retina annotations do not match the model")
        annotations = pd.read_feather(path, columns=["bodyId", "assignedOlHex1", "assignedOlHex2"])
        if file_sha256(path) != digest:
            raise ValueError("compiled retina annotations changed while reading")
        annotations = annotations.drop_duplicates()
        if annotations.bodyId.duplicated().any():
            raise ValueError("compiled retina requires unambiguous body coordinates")
        brain = controller._brain
        aligned = annotations.set_index("bodyId").reindex(brain.bodies)
        coords = aligned[["assignedOlHex1", "assignedOlHex2"]].to_numpy(dtype=float)
        finite = np.isfinite(coords).all(axis=1)
        selected = finite & np.isin(brain.types, ("L1", "L2"))
        if not selected.any():
            raise ValueError("compiled retina requires finite retinal coordinates")
        axial_1, axial_2 = coords[selected].astype(np.float32).T
        # Match the baseline's arithmetic promotion/order at truncation edges.
        horizontal = axial_1 + axial_2 * 0.5
        vertical = axial_2 * (np.sqrt(3) / 2)
        columns = np.clip((np.clip((horizontal - horizontal.min()) /
                          (horizontal.max() - horizontal.min() + 1e-9), 0, 1) * 16).astype(int), 0, 15)
        rows = np.clip((np.clip((vertical - vertical.min()) /
                       (vertical.max() - vertical.min() + 1e-9), 0, 1) * 16).astype(int), 0, 15)
        selected_indices = np.flatnonzero(selected)
        self._populations = {}
        self._max_hz = provenance["calibration"]["max_hz"]
        union = np.zeros(256, dtype=int)
        for name in ("L1", "L2"):
            mask = brain.types[selected_indices] == name
            indices = selected_indices[mask].copy()
            pixels = (rows * 16 + columns)[mask].copy()
            counts = np.bincount(pixels, minlength=256)
            union += counts
            for array in (indices, pixels, counts):
                array.flags.writeable = False
            self._populations[name] = {
                "indices": indices, "key": tuple(indices), "pixels": pixels,
                "bodies": brain.bodies[indices].astype(int).tolist(), "counts": counts,
                "missing": int(np.sum((brain.types == name) & ~finite)),
            }
        self._keys = {pop["key"] for pop in self._populations.values()}
        self._coverage = {
            "union_coverage_counts": union.tolist(),
            "sampled_pixel_count": int(np.count_nonzero(union)),
            "discarded_pixel_indices": np.flatnonzero(union == 0).tolist(),
        }
        ramp = Observation(schema_version="1", pixels=[value / 255 for value in range(256)])
        if self.inspect(ramp) != inspect_retina(controller, ramp, annotations_path=path):
            raise ValueError("compiled retina disagrees with independent raw-annotation oracle")

    @staticmethod
    def _pixels(observation):
        if type(observation) is not Observation:
            raise ValueError("compiled retina requires a validated Observation")
        checked = Observation.model_validate(observation.model_dump())
        return np.asarray(checked.pixels, dtype=np.float32)

    def _drives(self, flat):
        drives = {}
        for name, population in self._populations.items():
            samples = flat[population["pixels"]]
            drives[population["key"]] = (samples * self._max_hz if name == "L1" else
                                          (1.0 - samples) * self._max_hz * 0.6)
        return drives

    def check_drive(self, actual, expected):
        """Verify the actual eye result before the ordinary brain call."""
        if set(actual) != self._keys:
            raise ValueError("actual retinal population indices disagree with compiled mapping")
        for key, drive in expected.items():
            if not np.array_equal(np.asarray(actual[key]), drive):
                raise ValueError("actual retinal drive disagrees with compiled raw-annotation mapping")

    def inspect(self, observation: Observation) -> dict:
        """Explicit diagnostic evidence; full retinal arrays are not live packets."""
        flat = self._pixels(observation)
        drives = self._drives(flat)
        result = {"populations": {}, **deepcopy(self._coverage)}
        for name, population in self._populations.items():
            samples = flat[population["pixels"]]
            result["populations"][name] = {
                "neuron_indices": population["indices"].tolist(),
                "body_ids": list(population["bodies"]),
                "pixel_indices": population["pixels"].tolist(),
                "sampled_pixels_u8": np.rint(samples * 255).astype(int).tolist(),
                "drive_hz": drives[population["key"]].tolist(),
                "coverage_counts": population["counts"].tolist(),
                "missing_coordinates": population["missing"],
            }
        return result


class LiveResponseCapture:
    """Copy a single ordinary step's rates, original pilot action and statistics.

    Call ``controller.step(observation)`` inside this context. The caller retains
    that original ControllerOutput; this tap does not derive any flight command.
    The worker must own its controller exclusively for the lifetime of the tap.
    """

    def __init__(self, controller, observation: Observation, *, retina: CompiledRetina):
        if retina.controller is not controller:
            raise ValueError("compiled retina belongs to a different controller")
        self.controller = controller
        self.retina = retina
        self._image = retina._pixels(observation).reshape(16, 16)
        self._expected = retina._drives(self._image.reshape(256))
        self.rates = self.statistics = self.raw_action = None
        self._used = self._entered = False

    def __enter__(self):
        if self._entered or self._used or self.retina._active:
            raise RuntimeError("live response capture is already active or consumed")
        eye, pilot = self.controller._eye, self.controller._pilot
        self._original_look, self._original_step = eye.look, pilot.step

        def look(image, *args, **kwargs):
            if not np.array_equal(image, self._image):
                raise ValueError("inference pixels differ from the admitted Observation")
            drive = self._original_look(image, *args, **kwargs)
            self.retina.check_drive(drive, self._expected)
            self._drive_seen = True
            return drive

        def step(*args, **kwargs):
            if self._used:
                raise RuntimeError("live response capture permits only one controller step")
            self._used = True
            self._drive_seen = False
            result = self._original_step(*args, **kwargs)
            if not self._drive_seen or len(result) != 5:
                raise ValueError("live response capture requires actual drive and detailed model outputs")
            dx, dy, click, rates, statistics = result
            if set(rates) != set(MOTOR_NAMES):
                raise ValueError("unexpected motor-population response schema")
            self.rates = {name: float(rates[name]) for name in MOTOR_NAMES}
            self.raw_action = {"dx": float(dx), "dy": float(dy), "click": bool(click)}
            self.statistics = deepcopy({name: statistics[name] for name in STATISTIC_NAMES})
            return result

        eye.look, pilot.step = look, step
        self._entered = self.retina._active = True
        return self

    def __exit__(self, *_):
        self.controller._eye.look = self._original_look
        self.controller._pilot.step = self._original_step
        self._entered = self.retina._active = False
