"""Bounded subprocess inference; no navigation or candidate calibration."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
from datetime import datetime, timezone

from flytrap.contracts import Observation
from flytrap.controllers.fly import FlyController
from flytrap.data.bundle import file_sha256
from .budget import CallBudget
from .contracts import LabRequest, LabResult, MOTORS, SEEDS
from .sensory import ResponseCapture

REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "artifacts/milestones/P00"
BASELINE = REPO / "artifacts/milestones/05/trials/baseline.json"


def controller_files():
    return dict(graph_root=REPO / "build/flytrap-v1",
                annotations_path=REPO / "data/body-annotations.feather",
                parameters_path=REPO / "config/flytrap-model-v1.json",
                calibration_path=REPO / "config/flytrap-visual-v1.json",
                checkpoint_path=BASELINE)


def summarize(request, samples):
    indexed = {(s["seed"], s["side"]): s for s in samples}
    metrics = {}
    for name in MOTORS:
        a = [indexed[seed, "A"]["motor_rates_hz"][name] for seed in SEEDS]
        b = [indexed[seed, "B"]["motor_rates_hz"][name] for seed in SEEDS]
        delta = [bv-av for av, bv in zip(a, b)]
        metrics[name] = dict(a_mean=statistics.mean(a), b_mean=statistics.mean(b),
                             a_sd=statistics.stdev(a), b_sd=statistics.stdev(b),
                             delta_mean=statistics.mean(delta), delta_sd=statistics.stdev(delta),
                             paired_deltas=delta)
    repeatable = all(all(indexed[seed, "A"][key] == indexed[seed, "A_repeat"][key]
                         for key in ("motor_rates_hz", "statistics", "neural_ms")) for seed in SEEDS)
    return dict(same_image=request.a == request.b, equal_brightness=sum(request.a) == sum(request.b),
                mean_brightness_u8=dict(A=statistics.mean(request.a), B=statistics.mean(request.b)),
                same_seed_repeatable=repeatable, motor_rates_hz=metrics)


def identities(controller, request):
    sources = [REPO / "flyeye.py", REPO / "flysim.py", REPO / "pyproject.toml", REPO / "uv.lock"]
    sources += sorted((REPO / "flytrap").rglob("*.py"))
    sources += sorted((REPO / "web/src").rglob("*.tsx")) + sorted((REPO / "web/src").rglob("*.ts"))
    sources += sorted((REPO / "web/src").rglob("*.json")) + sorted((REPO / "web/src").rglob("*.css"))
    hashes = {str(p.relative_to(REPO)): file_sha256(p) for p in sources}
    return dict(model=controller.provenance,
                graph_manifest_sha256=file_sha256(REPO / "build/flytrap-v1/manifest.json"),
                source_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
                source_sha256=hashes,
                source_tree_sha256=hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
                runtime=dict(python=platform.python_version(), platform=platform.platform(),
                             pid=os.getpid(), parent_pid=os.getppid(),
                             packages={p: importlib.metadata.version(p) for p in
                                       ("numpy", "scipy", "pandas", "pydantic", "fastapi")},
                             threads={p: os.environ.get(p) for p in
                                      ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}),
                input_sha256={"A": hashlib.sha256(bytes(request.a)).hexdigest(),
                              "B": hashlib.sha256(bytes(request.b)).hexdigest()},
                encoding="uint8 / 255 → Observation → float32 16×16; center 8,8; FOV 16×16; truncate and clip",
                comparison="3 matched seeds; A, A repeat, B independently reset; sample SD (ddof=1); delta B minus A",
                statistics="spike_count over 20 ms; spikes_per_sec whole graph spikes/s; mean_mv final mV; firing/visual/motor distinct active neuron counts over the window",
                limitations="Input drive is not neuron firing. Motor summaries do not identify whole-brain activity. No perception, preference, recognition or learning claim.")


def execute(request, result_id):
    controller = FlyController(**controller_files())
    if controller.checkpoint.model_mode != "windowed_reset" or controller.provenance["fixture"]:
        raise ValueError("explicit real untrained windowed_reset baseline required")
    budget = CallBudget(ARTIFACTS / "attempts.jsonl")
    samples, retina = [], {}
    for seed in SEEDS:
        for side in ("A", "A_repeat", "B"):
            pixels = request.b if side == "B" else request.a
            observation = Observation(schema_version="1", pixels=[p / 255 for p in pixels])
            controller.reset(run_seed=seed, checkpoint=controller.checkpoint)
            with ResponseCapture(controller, observation,
                                 annotations_path=controller_files()["annotations_path"]) as capture:
                budget.record_attempt(result_id=result_id, seed=seed, side=side)
                output = controller.step(observation)
            samples.append(dict(side=side, seed=seed, motor_rates_hz=capture.rates,
                                statistics=capture.statistics, neural_ms=output.telemetry.neural_ms))
            if side != "A_repeat":
                if side in retina and retina[side] != capture.retina:
                    raise ValueError("retinal drive changed across seeds")
                retina[side] = capture.retina
    return LabResult.model_validate(dict(
        schema_version="flytrap-lab-result-1", result_id=result_id,
        created_at=datetime.now(timezone.utc).isoformat(), cached=False, fixture=False,
        request=request.model_dump(), seeds=list(SEEDS), samples=samples, retina=retina,
        comparison=summarize(request, samples), identities=identities(controller, request),
        attempted_calls=budget.attempted))


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    envelope = json.loads(sys.stdin.buffer.read(32769))
    request = LabRequest.model_validate(envelope["request"])
    result = execute(request, envelope["result_id"])
    target = ARTIFACTS / "results" / f"{result.result_id}.json"
    with target.open("x") as stream:
        stream.write(result.model_dump_json(indent=2) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


if __name__ == "__main__":
    main()
