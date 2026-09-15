#!/usr/bin/env python3
"""OBS02 real-model gate on safe generated pixels; exactly nine planned attempts.

This executable never opens an OBS device or enables recording. Three live calls
are followed by their three original-adapter and three historical-tap references.
Every invocation consumes the fixed automated ledger; a failure never retries.
"""
import argparse
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import importlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
SEED = 20260915
LIVE_STEPS = 3
PLANNED_CALLS = 9


class Blocked(RuntimeError):
    """A required real-model prerequisite is unavailable."""


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def save(path, value):
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def checked(condition, message):
    if not condition:
        raise AssertionError(message)


def protected_paths(files):
    required = [files["annotations_path"], files["parameters_path"], files["calibration_path"],
                files["checkpoint_path"], files["graph_root"] / "graph.npz",
                files["graph_root"] / "manifest.json", REPO / "flysim.py", REPO / "flyeye.py",
                REPO / "flytrap/controllers/fly.py"]
    absent = [str(path.relative_to(REPO)) for path in required if not path.is_file()]
    if absent:
        raise Blocked("Missing real model prerequisites: " + ", ".join(absent))
    graph_files = list(files["graph_root"].rglob("*"))
    return sorted(set(required + [p for p in graph_files if p.is_file()] +
                      [REPO / "artifacts/milestones/P00/attempts.jsonl"]))


def identities(paths):
    return {str(path.relative_to(REPO)): digest(path) if path.is_file() else None for path in paths}


def snapshot_json(snapshot):
    value = asdict(snapshot)
    for key in ("status", "sample", "last_inferred", "last_completed", "flight"):
        model = getattr(snapshot, key)
        value[key] = None if model is None else model.model_dump(mode="json")
    return value


@contextmanager
def deadline(seconds):
    """Bound reference work in the command's main thread without changing seeds."""
    def expired(*_):
        raise TimeoutError("Real reference step exceeded its hard deadline; attempt remains charged")

    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def observe_live(output, report, config, files):
    from flytrap.live.session import NeuralSession

    session = NeuralSession(config, purpose="automated", repository_root=REPO, files=files)
    report["live_session_id"] = session.session_id
    save(output / "result.json", report)
    samples, results = {}, {}
    started = time.monotonic()
    try:
        session.start()
        while True:
            session.renew_lease()
            snapshot = session.snapshot()
            inferred, result = snapshot.last_inferred, snapshot.last_completed
            if result is not None and result.step_index not in results:
                checked(inferred is not None and inferred.step_index == result.step_index,
                        "Live result lost its exact admitted input identity")
                index = result.step_index
                samples[index], results[index] = inferred, result
                save(output / f"live-step-{index}.json", {
                    "source_evidence": "safe deterministic fixture pixels; actual real connectome",
                    "inferred": inferred.model_dump(mode="json"),
                    "result": result.model_dump(mode="json"),
                })
            if session.wait(.005):
                # Cleanup can complete between snapshot and wait. Read the final
                # historical sample even though applicable sample is now null.
                final = session.snapshot()
                if final.last_completed is not None:
                    index = final.last_completed.step_index
                    samples[index], results[index] = final.last_inferred, final.last_completed
                    save(output / f"live-step-{index}.json", {
                        "source_evidence": "safe deterministic fixture pixels; actual real connectome",
                        "inferred": final.last_inferred.model_dump(mode="json"),
                        "result": final.last_completed.model_dump(mode="json"),
                    })
                break
            if time.monotonic() - started > 55:
                raise TimeoutError("Real live validation exceeded its whole-session deadline")
    finally:
        session.stop()
        checked(session.wait(3), "Live worker/capture cleanup did not finish")
        report["live_final"] = snapshot_json(session.snapshot())
        report["live_provenance"] = session.provenance
        save(output / "result.json", report)
    final = session.snapshot()
    checked(final.status.state == "limit_reached", f"Live session ended {final.status.state}: {final.status.reason}")
    checked(final.completed_calls == LIVE_STEPS and final.status.attempted_calls == LIVE_STEPS,
            "Live session did not complete exactly three charged attempts")
    checked(set(results) == set(range(LIVE_STEPS)), "Polling missed a live sample; no automatic rerun allowed")
    checked(final.rejected_results == 0, "A real live result exceeded input-age admission")
    checked(final.model_kind == "real", "Fixture model cannot satisfy the real-model gate")
    checked(session.provenance["model"]["fixture"] is False, "Actual real graph required")
    checked(session.provenance["model_loads"] == 1 and session.provenance["controller_resets"] == 1,
            "Live session must load and reset its model once")
    for result in results.values():
        checked(result.model_file_reads == 0, "Live hot path repeatedly opened model input files")
        checked(result.output.model_mode == "windowed_reset", "Baseline numerical mode changed")
    return [samples[i] for i in range(LIVE_STEPS)], [results[i] for i in range(LIVE_STEPS)]


def compare_references(output, report, files, samples, results):
    from flytrap.contracts import Observation
    from flytrap.controllers.fly import FlyController
    from flytrap.lab.sensory import ResponseCapture, inspect_retina
    from flytrap.live.accounting import LiveLedger, LiveOwnership
    from flytrap.live.sensory import CompiledRetina

    global_ledger = LiveLedger.automated(REPO)
    observations = [Observation(schema_version="1", pixels=[p / 255 for p in s.observation_u8]) for s in samples]
    with LiveOwnership(REPO) as owner:
        with deadline(30):
            controller = FlyController(**files)
            checked(controller.provenance["fixture"] is False, "Reference must use the real connectome")
            retina = CompiledRetina(controller, annotations_path=files["annotations_path"])
        report["reference_provenance"] = controller.provenance
        report["retinal_comparisons"] = []
        for index, observation in enumerate(observations):
            actual = retina.inspect(observation)
            reference = inspect_retina(controller, observation, annotations_path=files["annotations_path"])
            checked(actual == reference, "Compiled mapping differs from raw-annotation oracle")
            report["retinal_comparisons"].append({
                "step_index": index, "equal": True, "sampled_pixel_count": actual["sampled_pixel_count"],
                "retina_sha256": hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest(),
            })
        save(output / "result.json", report)

        for mode in ("untapped", "historical-tap"):
            session_id = report["reference_session_ids"][mode]
            ledger = LiveLedger.session(REPO, session_id, cap=LIVE_STEPS, mode="automated")
            checked(ledger.attempted == 0, "Reference session already consumed calls")
            controller.reset(run_seed=SEED, checkpoint=controller.checkpoint)
            for index, observation in enumerate(observations):
                with deadline(5):
                    if mode == "historical-tap":
                        with ResponseCapture(controller, observation, annotations_path=files["annotations_path"]) as tap:
                            global_ledger.record_attempt(session_id=session_id, seed=SEED, step=index,
                                                         ownership=owner)
                            ledger.record_attempt(session_id=session_id, seed=SEED, step=index, ownership=owner)
                            ordinary = controller.step(observation)
                        rates_equal = tap.rates == results[index].motor_rates_hz.model_dump()
                        statistics_equal = tap.statistics == results[index].statistics.model_dump()
                        comparison = {"rates_equal": rates_equal, "statistics_equal": statistics_equal,
                                      "rates": tap.rates, "statistics": tap.statistics}
                    else:
                        global_ledger.record_attempt(session_id=session_id, seed=SEED, step=index,
                                                     ownership=owner)
                        ledger.record_attempt(session_id=session_id, seed=SEED, step=index, ownership=owner)
                        ordinary = controller.step(observation)
                        comparison = {}
                comparison.update(mode=mode, step_index=index, session_id=session_id,
                                  output=ordinary.model_dump(mode="json"),
                                  output_equal=ordinary == results[index].output)
                report["reference_comparisons"].append(comparison)
                save(output / f"reference-{mode}-{index}.json", comparison)
                save(output / "result.json", report)
                checked(comparison["output_equal"], f"Original adapter differs at {mode} step {index}")
                if mode == "historical-tap":
                    checked(comparison["rates_equal"] and comparison["statistics_equal"],
                            f"Live tap changes raw rates/statistics at step {index}")


def run(output, report):
    for package in ("numpy", "scipy", "pandas", "pyarrow"):
        try:
            importlib.import_module(package)
        except ImportError as exc:
            raise Blocked(f"Missing required model dependency: {package}") from exc
    from flytrap.live.accounting import LiveLedger
    from flytrap.live.contracts import SessionConfig
    from flytrap.live.worker import model_files

    files = model_files(REPO)
    paths = protected_paths(files)
    report["protected_before"] = identities(paths)
    report["source_identity"] = {
        "source_id": "fixture-pattern", "source_evidence_kind": "fixture", "model_evidence_kind": "real",
        "generator_path": "flytrap/live/fixture.py", "generator_sha256": digest(REPO / "flytrap/live/fixture.py"),
        "capture": "in-process deterministic 30 Hz generated test pattern; no device access",
        "timing": "Admitted source sequences depend on runtime; exact received inputs are saved for paired references.",
    }
    config = SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=SEED,
                           max_model_calls=LIVE_STEPS, duration_seconds=50, recording=False)
    report["config"] = config.model_dump(mode="json")
    ledger = LiveLedger.automated(REPO)
    report["automated_attempts_before"] = ledger.attempted
    report["automated_remaining_before"] = ledger.remaining
    save(output / "result.json", report)
    if ledger.remaining < PLANNED_CALLS:
        raise Blocked("Fewer than nine authorized automated attempts remain; validation cannot start")
    print(f"OBS02 validation allowance: {ledger.remaining} / 1024 remaining; exactly 9 planned attempts", flush=True)
    try:
        samples, results = observe_live(output, report, config, files)
        compare_references(output, report, files, samples, results)
        checked(ledger.attempted - report["automated_attempts_before"] == PLANNED_CALLS,
                "Expected exactly nine charged full-model attempts")
        checked(len(report["reference_comparisons"]) == 6, "All six independent reference comparisons required")
        report["checks"] = {
            "three_real_live_steps": True, "three_untapped_output_comparisons": True,
            "three_historical_rates_statistics_comparisons": True,
            "compiled_mapping_equals_independent_actual_data_oracle": True,
            "zero_model_input_opens_in_live_hot_path": True,
            "baseline_windowed_reset_100_steps_0_2_ms": (
                report["live_provenance"]["model"]["parameters"]["sim_steps"] == 100 and
                report["live_provenance"]["model"]["parameters"]["dt"] == .2),
        }
        checked(all(report["checks"].values()), "A required real-model invariant failed")
    finally:
        report["protected_after"] = identities(paths)
        report["protected_unchanged"] = report["protected_before"] == report["protected_after"]
        report["automated_attempts_after"] = ledger.attempted
        report["automated_remaining_after"] = ledger.remaining
        report["automated_attempts_consumed"] = ledger.attempted - report["automated_attempts_before"]
        save(output / "result.json", report)
        checked(report["protected_unchanged"], "Protected model/checkpoint/graph/P00 bytes changed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path,
                        help="new private evidence directory; existing paths are refused")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    try:
        output.mkdir(parents=True, exist_ok=False, mode=0o700)
    except FileExistsError:
        parser.error("evidence output already exists; choose a new directory")
    # Match the isolated worker's numerical thread environment before NumPy loads.
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    started = time.monotonic()
    report = {
        "schema_version": "obs02-real-validation-1", "status": "RUNNING", "seed": SEED,
        "planned_calls": {"live": 3, "original_untapped": 3, "historical_tap": 3, "total": PLANNED_CALLS},
        "declared_step_seeds": [int.from_bytes(hashlib.sha256(
            b"FLYTRAP-step-seed-v1\0" + SEED.to_bytes(4, "big") + index.to_bytes(8, "big")
        ).digest()[:8], "big") for index in range(LIVE_STEPS)],
        "automatic_retries": 0, "recording": False, "desktop_capture": False,
        "command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, check=True,
                                   capture_output=True, text=True).stdout.strip(),
        "validation_script_sha256": digest(Path(__file__).resolve()),
        "reference_session_ids": {mode: f"obs02-{mode}-{uuid.uuid4().hex[:16]}"
                                  for mode in ("untapped", "historical-tap")},
        "reference_comparisons": [],
        "scope": "Actual model on safe generated inputs; no real-OBS, browser, recording, or flight gate.",
    }
    save(output / "result.json", report)
    try:
        run(output, report)
        report["status"], code = "PASS", 0
    except Blocked as exc:
        report["status"], report["reason"], code = "BLOCKED", str(exc), 2
    except Exception as exc:
        report["status"], report["reason"], code = "FAIL", f"{type(exc).__name__}: {exc}", 1
    report["command_exit"] = code
    report["elapsed_seconds"] = time.monotonic() - started
    save(output / "result.json", report)
    print(json.dumps({"status": report["status"], "exit": code, "evidence": str(output / "result.json"),
                      "attempts_consumed": report.get("automated_attempts_consumed"),
                      "remaining": report.get("automated_remaining_after", report.get("automated_remaining_before"))}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
