"""GPU01 predefined safe comparison. Every full-graph invocation is precharged.

No desktop capture, automatic retries, human accounting, or gate promotion.
CPU profiling precedes CUDA construction. Outputs retain every raw population
rate and fired index; a failed comparison remains a failure.
"""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import time
import uuid

import numpy as np

from scripts.live_real import save

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (17, 29, 43)
BASE_ATTEMPTS = 219
TASK_CAP = 384


def plan():
    patterns = [
        ("black", lambda x, y: 0), ("white", lambda x, y: 255),
        ("gray", lambda x, y: 128), ("ramp", lambda x, y: x * 17),
        ("checker", lambda x, y: 255 * ((x//2+y//2) % 2)),
        ("bar", lambda x, y: 255 if 5 <= x < 9 else 0)]
    return {"schema": "gpu01-plan-1", "seeds": list(SEEDS), "attempts": 54,
        "task_initial_automated_attempts": BASE_ATTEMPTS, "task_cap": TASK_CAP,
        "stimuli": [{"name": name, "pixels": [f(x, y) for y in range(16) for x in range(16)]}
                    for name, f in patterns],
        "order": ["cpu", "cuda", "cuda-repeat"], "batch_size": 1, "steps": 100, "dt_ms": .2,
        "gate": {"integer_spikes": "exact", "population_rates": "exact", "fired_indices": "exact",
                 "raw_actions": "exact", "statistics_except_mean": "exact", "decoded_controls": "exact",
                 "mean_mv_absolute_tolerance": .0001, "relative_tolerance": 0., "gpu_repeat": "exact"},
        "rationale": "Conservative deterministic substitution: discrete spikes and motor thresholds must agree; "
                     "only final mean permits float32 reduction error, far below the 7 mV threshold gap.",
        "timing": "identical 500 ms application intervals; original 20 ms physics; first call per backend cold",
        "source": "generated safe pixels only", "recording": False}


def serial(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    return value


def summary(values):
    return {"n": len(values), "median": float(np.median(values)),
            "p95": float(np.percentile(values, 95)), "min": min(values), "max": max(values)}


def compare(a, b, *, repeat=False):
    differences = {}
    for name in a["raw"]:
        left, right = a["raw"][name], b["raw"][name]
        if name == "_fired":
            differences[name] = {"symmetric_difference": len(set(left) ^ set(right)),
                                  "cpu_count": len(left), "other_count": len(right)}
        else:
            delta = np.abs(np.asarray(left)-np.asarray(right))
            differences[name] = {"max_absolute": float(delta.max(initial=0)),
                                 "different_values": int(np.count_nonzero(delta))}
    mean_ok = differences["_mean_mv"]["max_absolute"] <= (0 if repeat else .0001)
    exact = all(v.get("symmetric_difference", v.get("different_values", 0)) == 0
                for k, v in differences.items() if k != "_mean_mv")
    fields = {name: a[name] == b[name] for name in ("rates", "action", "controls", "output", "types")}
    # Statistics mean is the raw mean above; every other field must match.
    fields["statistics"] = all(a["statistics"][k] == b["statistics"][k]
                               for k in a["statistics"] if k != "mean_mv")
    return {"pass": mean_ok and exact and all(fields.values()), "raw_differences": differences,
            "equal_fields": fields}


def execute(output):
    from flytrap.contracts import Observation
    from flytrap.controllers.fly import FlyController
    from flytrap.live.accounting import LiveLedger, LiveOwnership
    from flytrap.live.contracts import FrameIdentity, MotorRates
    from flytrap.live.encoding import RGBFrame, encode_frame
    from flytrap.live.flight import decode
    from flytrap.live.gpu import GPUInference
    from flytrap.live.sensory import CompiledRetina, LiveResponseCapture
    from flytrap.live.worker import identity, model_files

    specification = plan()
    if json.loads((output / "plan.json").read_text()) != specification:
        raise ValueError("prepared specification does not match; do not overwrite a confirmation plan")
    if (output / "result.json").exists():
        raise ValueError("results exist; automatic retries forbidden")
    ledger = LiveLedger.automated(ROOT)
    session_id = "gpu01-" + uuid.uuid4().hex
    session = LiveLedger.session(ROOT, session_id, cap=54, mode="automated")
    report = {"status": "RUNNING", "session_id": session_id, "plan_sha256": hashlib.sha256(
        (output / "plan.json").read_bytes()).hexdigest(), "runs": {}, "attempted": 0}
    save(output / "result.json", report)
    with LiveOwnership(ROOT) as owner:
        if min(ledger.remaining, BASE_ATTEMPTS+TASK_CAP-ledger.attempted) < 54:
            raise ValueError("insufficient remaining GPU01/global attempt allowance")
        began = time.perf_counter()
        controller = FlyController(**model_files())
        retina = CompiledRetina(controller, annotations_path=model_files()["annotations_path"])
        report["cpu_startup_graph_retina_seconds"] = time.perf_counter()-began
        report["cpu_provenance"] = identity(controller, {"purpose": "gpu01-fixed-input"})
        cpu_run = controller._brain.run
        for backend in specification["order"]:
            if backend == "cuda":
                began = time.perf_counter()
                # Explicit diagnostic construction can test an unqualified engine;
                # the normal live worker must instead use qualified attach_gpu.
                controller._gpu_inference = GPUInference(controller._brain)
                report["gpu_execution"] = controller._gpu_inference.descriptor()
                report["gpu_import_device_load_seconds"] = time.perf_counter()-began
            native_run = cpu_run if backend == "cpu" else controller._gpu_inference.run
            rows = report["runs"][backend] = []
            for seed in SEEDS:
                controller.reset(run_seed=seed, checkpoint=controller.checkpoint)
                for index, stimulus in enumerate(specification["stimuli"]):
                    raw, neural = {}, {}

                    def measured(*args, **kwargs):
                        tick = time.perf_counter()
                        value = native_run(*args, **kwargs)
                        neural["wall_ms"] = (time.perf_counter()-tick)*1000
                        raw.update(value)
                        return value

                    controller._brain.run = measured
                    tick = time.perf_counter()
                    frame = FrameIdentity(schema_version="obs-frame-1", source_id="gpu01-safe",
                        session_id=session_id, generation=1, sequence=index, evidence_kind="fixture",
                        width=16, height=16, pixel_format="RGB24", receipt_monotonic_ms=float(index*500),
                        source_timestamp_ms=None, source_sequence=None, source_clock="unknown")
                    encoded = encode_frame(RGBFrame(frame, bytes(v for pixel in stimulus["pixels"] for v in [pixel]*3)))
                    observation = Observation(schema_version="1", pixels=[v/255 for v in encoded.u8])
                    encoding_ms = (time.perf_counter()-tick)*1000
                    tick = time.perf_counter()
                    if ledger.attempted >= BASE_ATTEMPTS+TASK_CAP:
                        raise ValueError("GPU01 task allowance exhausted")
                    ledger.record_attempt(session_id=session_id, seed=seed, step=index, ownership=owner)
                    session.record_attempt(session_id=session_id, seed=seed, step=len(rows), ownership=owner)
                    ledger_ms = (time.perf_counter()-tick)*1000
                    report["attempted"] += 1
                    save(output / "result.json", report)
                    tick, cpu = time.perf_counter(), time.process_time()
                    with LiveResponseCapture(controller, observation, retina=retina) as tap:
                        result = controller.step(observation)
                    step_ms = (time.perf_counter()-tick)*1000
                    cpu_ms = (time.process_time()-cpu)*1000
                    control = decode(MotorRates(**tap.rates), response_id=f"response-{index}", session_id="gpu01-fixed",
                        generation=1, evidence_kind="fixture", receipt_ms=float(index*500),
                        completed_ms=float(index*500), now_ms=float(index*500)).model_dump(mode="json")
                    row = {"seed": seed, "index": index, "stimulus": stimulus["name"],
                        "raw": serial(raw), "types": {k: str(v.dtype) if isinstance(v, np.ndarray) else
                                                      type(v).__name__ for k, v in raw.items()},
                        "rates": tap.rates, "action": tap.raw_action, "statistics": tap.statistics,
                        "output": result.model_dump(mode="json"), "controls": control,
                        "timing": {"encoding_ms": encoding_ms, "ledger_ms": ledger_ms,
                            "neural_ms": neural["wall_ms"], "step_ms": step_ms, "cpu_ms": cpu_ms,
                            "adapter_other_ms": step_ms-neural["wall_ms"],
                            "total_ms": encoding_ms+ledger_ms+step_ms},
                        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
                    if backend != "cpu":
                        row["gpu_timing"] = controller._gpu_inference.last_timing
                    rows.append(row)
                    save(output / "result.json", report)
            report.setdefault("warm_timing", {})[backend] = {
                k: summary([row["timing"][k] for row in rows[1:]]) for k in rows[0]["timing"]}
        report["comparisons"] = [compare(a, b) for a, b in zip(report["runs"]["cpu"], report["runs"]["cuda"], strict=True)]
        report["repeatability"] = [compare(a, b, repeat=True) for a, b in zip(
            report["runs"]["cuda"], report["runs"]["cuda-repeat"], strict=True)]
        report["status"] = "PASS" if all(r["pass"] for r in report["comparisons"]+report["repeatability"]) else "FAIL"
        report["automated_attempted"], report["automated_remaining"] = ledger.attempted, ledger.remaining
        save(output / "result.json", report)
    print(json.dumps({k: report[k] for k in ("status", "attempted", "warm_timing", "automated_remaining")}, indent=2))
    return 0 if report["status"] == "PASS" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "execute"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.phase == "prepare":
        args.output.mkdir(parents=True, exist_ok=False)
        save(args.output / "plan.json", plan())
        return 0
    return execute(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
