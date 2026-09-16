"""Optional, batch-one CUDA inference for the verified windowed-reset baseline.

Selectively adapted from fruitflydev/flycoinrh flysim_gpu.py at
f2fdedf49bbd2712834c5404c690670af26c2028 (upstream LICENSE/NOTICE apply).
Retains host NumPy randomness and the upstream operation order, CSR device
operator and exact integer spike accumulator. No learning or carried state.
Torch is imported only when the owned worker constructs GPUInference.
"""
import ast
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import time

import numpy as np

UPSTREAM = "f2fdedf49bbd2712834c5404c690670af26c2028"


def require_qualified_gpu():
    """Check the tested engine/runtime without importing or initializing Torch."""
    path = Path(__file__).resolve().parents[2] / "config/gpu01-qualification.json"
    try:
        qualification = json.loads(path.read_text())
        source = Path(__file__).read_text()
        engine = "\n".join(ast.get_source_segment(source, node) for node in ast.parse(source).body
                           if getattr(node, "name", None) in {"GPUInference", "_drive_arrays"})
        if (qualification["status"] != "PASS" or
                hashlib.sha256(engine.encode()).hexdigest() != qualification["engine_sha256"] or
                platform.python_version() != qualification["python"] or
                any(version(name) != expected for name, expected in qualification["packages"].items())):
            raise ValueError("changed engine or runtime")
        return qualification
    except (OSError, KeyError, ValueError, ImportError) as error:
        raise ValueError("GPU01 CUDA qualification unavailable or stale; see docs/implementation/milestones/GPU01.md") from error


def _drive_arrays(drive, dt):
    indices, probabilities = [], []
    for key, rate in (drive or {}).items():
        ii, rr = np.asarray(key, dtype=np.int64), np.asarray(rate, dtype=np.float32)
        if rr.ndim == 0:
            rr = np.full(len(ii), float(rr), dtype=np.float32)
        elif len(rr) != len(ii):
            raise ValueError("drive rates do not match neurons")
        indices.append(ii)
        probabilities.append(np.clip(rr * dt / 1000.0, 0.0, 1.0))
    if not indices:
        return np.array([], dtype=np.int64), np.array([], dtype=np.float32)
    return np.concatenate(indices), np.concatenate(probabilities).astype(np.float32)


class GPUInference:
    """Immutable device operator attached to an already verified CPU brain."""

    def __init__(self, brain, device="cuda:0"):
        import torch

        if device != "cuda:0" or not torch.cuda.is_available():
            raise RuntimeError("GPU01 requires available CUDA device cuda:0; no fallback")
        self.torch, self.brain, self.device = torch, brain, torch.device(device)
        matrix = brain.W.tocsr(copy=True)
        self.operator = torch.sparse_csr_tensor(
            torch.from_numpy(matrix.indptr.astype(np.int32)).to(self.device),
            torch.from_numpy(matrix.indices.astype(np.int32)).to(self.device),
            torch.from_numpy(matrix.data.astype(np.float32)).to(self.device),
            size=matrix.shape, device=self.device)
        torch.cuda.synchronize(self.device)
        self.last_timing = {}

    def descriptor(self):
        torch, brain = self.torch, self.brain
        return {"backend": "cuda-torch-csr-v1", "source": "flytrap/live/gpu.py",
                "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "upstream_revision": UPSTREAM, "device": str(self.device),
                "device_name": torch.cuda.get_device_name(self.device), "dtype": "float32",
                "library_versions": {"torch": torch.__version__, "numpy": np.__version__,
                                     "cuda": torch.version.cuda},
                "effective_configuration": {"batch_size": 1, "steps": 100, "dt_ms": brain.p.dt,
                    "neural_state_mode": "windowed_reset", "gains": "all-one", "learning_enabled": False,
                    "synaptic_accumulation": "float32-cusparse"}}

    def run(self, drive, steps, gains=None, record=None, seed=0, spike_log=False):
        torch, brain, dev = self.torch, self.brain, self.device
        if gains is not None and (np.shape(gains) != (brain.n_types,) or not np.all(np.asarray(gains) == 1)):
            raise ValueError("GPU01 requires all-one gains")
        if type(steps) is not int or steps < 1:
            raise ValueError("positive integer steps required")
        p, n = brain.p, brain.n
        torch.cuda.synchronize(dev)
        began = time.perf_counter()
        rng = np.random.default_rng(seed)
        ext_idx, ext_p = _drive_arrays(drive, p.dt)
        # Same RNG calls and order as CPU, staged once per observation, never
        # across observations. This transfers input randomness, not video batches.
        masks = np.asarray([rng.random(len(ext_idx)) < ext_p for _ in range(steps)], dtype=bool)
        prepared = time.perf_counter()
        events = [torch.cuda.Event(enable_timing=True) for _ in range(4)]
        events[0].record()
        rows = torch.from_numpy(ext_idx).to(dev)
        masks_dev = torch.from_numpy(masks).to(dev)
        duplicate = len(np.unique(ext_idx)) != len(ext_idx)
        hit = torch.zeros(n, dtype=torch.int32, device=dev) if duplicate else None
        record = record or {}
        selections = {k: torch.from_numpy(np.asarray(v, dtype=np.int64)).to(dev) for k, v in record.items()}
        counts = {k: torch.zeros(len(v), dtype=torch.int64, device=dev) for k, v in record.items()}
        v = torch.full((n,), p.v_rest, dtype=torch.float32, device=dev)
        refr = torch.zeros(n, dtype=torch.int32, device=dev)
        total = torch.zeros((), dtype=torch.int64, device=dev)
        ever = torch.zeros(n, dtype=torch.bool, device=dev)
        logs = torch.empty((steps, n), dtype=torch.bool, device=dev) if spike_log else None
        events[1].record()
        for index in range(steps):
            v.sub_(p.v_rest).mul_(float(brain.decay)).add_(p.v_rest)
            if len(ext_idx):
                mask = masks_dev[index]
                if duplicate:
                    hit.zero_().index_put_((rows,), mask.to(torch.int32), accumulate=True)
                    v.masked_fill_(hit > 0, p.v_thresh + 1.)
                else:
                    v.index_put_((rows,), torch.where(mask, p.v_thresh + 1., v[rows]))
            v.masked_fill_(refr > 0, p.v_reset)
            fired = (v >= p.v_thresh) & (refr <= 0)
            if logs is not None:
                logs[index].copy_(fired)
            refr.masked_fill_(fired, brain.refr_steps)
            v.masked_fill_(fired, p.v_reset)
            v.add_(torch.sparse.mm(self.operator, fired.to(torch.float32)[:, None])[:, 0])
            total.add_(fired.sum())
            ever.logical_or_(fired)
            for name, selection in selections.items():
                counts[name].add_(fired.index_select(0, selection).to(torch.int64))
            refr.sub_(1)
        events[2].record()
        # Required outputs are all materialized before completed-work timing ends.
        count_host = {k: value.cpu().numpy() for k, value in counts.items()}
        total_host = int(total.cpu().item())
        ever_host, voltage_host = ever.cpu().numpy(), v.cpu().numpy()
        log_host = logs.cpu().numpy() if logs is not None else None
        events[3].record()
        torch.cuda.synchronize(dev)
        secs = steps * p.dt / 1000.0
        out = {k: value / secs for k, value in count_host.items()}
        out.update(_total_spikes=total_host, _total_hz=total_host / secs / n,
                   _spikes_per_sec=total_host / secs, _fired=np.flatnonzero(ever_host),
                   _mean_mv=float(voltage_host.mean()))
        if log_host is not None:
            out["_spikes"] = [np.flatnonzero(row).astype(np.int32) for row in log_host]
        self.last_timing = {"host_prepare_ms": (prepared-began)*1000,
            "device_setup_h2d_ms": events[0].elapsed_time(events[1]),
            "neural_cuda_ms": events[1].elapsed_time(events[2]),
            "d2h_ms": events[2].elapsed_time(events[3]),
            "wall_ms": (time.perf_counter()-began)*1000,
            "allocated_bytes": torch.cuda.memory_allocated(dev),
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(dev)}
        return out


def attach_gpu(controller):
    qualification = require_qualified_gpu()
    if controller._params.sim_steps != 100 or controller._params.dt != .2:
        raise ValueError("GPU01 requires 100 steps at dt=0.2 ms")
    if (controller.checkpoint.graph_sha256 != qualification["graph_sha256"] or
            controller.checkpoint.sha256 != qualification["checkpoint_sha256"]):
        raise ValueError("GPU01 requires the qualified graph and historical checkpoint")
    inference = GPUInference(controller._brain)
    if (inference.torch.cuda.get_device_name(0) != qualification["device_name"] or
            inference.torch.version.cuda != qualification["cuda_runtime"]):
        raise ValueError("GPU01 requires the qualified GPU and CUDA runtime")
    driver = subprocess.check_output(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader",
                                      "--id=0"], text=True, timeout=5).strip()
    if driver != qualification["driver"]:
        raise ValueError("GPU01 requires the qualified NVIDIA driver")
    controller._brain.run = inference.run
    controller._gpu_inference = inference
    descriptor = inference.descriptor()
    descriptor["library_versions"].update(driver=driver, python=platform.python_version(),
        cusparse=version("nvidia-cusparse-cu12"), cuda_runtime=version("nvidia-cuda-runtime-cu12"),
        nvjitlink=version("nvidia-nvjitlink-cu12"))
    return descriptor
