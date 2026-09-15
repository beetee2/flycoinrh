"""One guarded persistent neural process. The model itself receives pixels only."""
import builtins
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time

from .neural import StepRequest, StepResult, receive_packet, send_packet
from .contracts import SessionConfig

REPOSITORY = Path(__file__).resolve().parents[2]


def model_files(root=REPOSITORY):
    return dict(graph_root=root / "build/flytrap-v1",
                annotations_path=root / "data/body-annotations.feather",
                parameters_path=root / "config/flytrap-model-v1.json",
                calibration_path=root / "config/flytrap-visual-v1.json",
                checkpoint_path=root / "artifacts/milestones/05/trials/baseline.json")


@contextmanager
def count_model_reads(files):
    """Instrument Python file opens of model inputs; ledger writes stay permitted."""
    inputs = [Path(value).resolve() for key, value in files.items() if key != "allow_fixture"]
    reads = [0]
    originals = builtins.open, io.open, os.open

    def wrapper(original):
        def opened(file, *args, **kwargs):
            if isinstance(file, (str, bytes, os.PathLike)):
                path = Path(os.fsdecode(file)).resolve()
                if any(path == target or target in path.parents for target in inputs):
                    reads[0] += 1
            return original(file, *args, **kwargs)
        return opened

    builtins.open, io.open, os.open = (wrapper(original) for original in originals)
    try:
        yield reads
    finally:
        builtins.open, io.open, os.open = originals


def identity(controller, config):
    import numpy
    import scipy

    paths = sorted((REPOSITORY / "flytrap/live").glob("*.py"))
    hashes = {str(p.relative_to(REPOSITORY)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    model = controller.provenance
    payload = {"model": model, "live_sources": hashes, "config": config,
               "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPOSITORY,
                                                        text=True, timeout=2).strip(),
               "runtime": {"python": platform.python_version(), "numpy": numpy.__version__,
                           "scipy": scipy.__version__}}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return {**payload, "identity_sha256": digest,
            "model_id": ("fixture-" if model["fixture"] else "baseline-") + digest[:24],
            "model_loads": 1, "controller_resets": 1}


def execute(channel, init):
    # Imports and large data reads are bounded by the parent's startup deadline.
    from flytrap.contracts import Observation
    from flytrap.controllers.fly import FlyController
    from .accounting import LiveLedger, LiveOwnership
    from .sensory import CompiledRetina, LiveResponseCapture

    root = Path(init["repository_root"])
    purpose = init["purpose"]
    if purpose not in {"automated", "human", "fixture"}:
        raise ValueError("unknown execution purpose")
    files = {key: Path(value) if key != "allow_fixture" else value for key, value in init["files"].items()}
    ownership = LiveOwnership.from_inherited(root, tuple(init["lock_fds"]))
    controller = FlyController(**files)
    fixture = controller.provenance["fixture"]
    if fixture != (purpose == "fixture"):
        raise ValueError("fixture and real execution authority disagree")
    if not fixture and root.resolve() != REPOSITORY:
        raise ValueError("real accounting must use the fixed repository ledger")
    config = SessionConfig.model_validate(init["config"]).model_dump(mode="json")
    session_id, generation = init["session_id"], init["generation"]
    controller.reset(run_seed=config["seed"], checkpoint=controller.checkpoint)
    retina = CompiledRetina(controller, annotations_path=files["annotations_path"])
    provenance = identity(controller, config)
    global_ledger = LiveLedger.automated(root) if purpose == "automated" else None
    ledger = LiveLedger.session(root, session_id, cap=config["max_model_calls"],
                               mode="human" if purpose == "human" else "automated")
    # Validate existing ledgers before announcing readiness. Never reset them.
    if ledger.attempted or (global_ledger is not None and not global_ledger.remaining):
        raise ValueError("session already used or validation budget exhausted")
    send_packet(channel, {"kind": "ready", "provenance": provenance})
    for step in range(config["max_model_calls"]):
        request = StepRequest.model_validate(receive_packet(channel))
        if (request.session_id, request.generation, request.step_index) != (session_id, generation, step):
            raise ValueError("foreign or out-of-order neural request")
        observation = Observation(schema_version="1", pixels=[p / 255 for p in request.observation_u8])
        with count_model_reads(files) as reads:
            with LiveResponseCapture(controller, observation, retina=retina) as tap:
                if not ledger.remaining:
                    raise ValueError("session call limit reached")
                if global_ledger is not None:
                    global_ledger.record_attempt(session_id=session_id, seed=config["seed"], step=step,
                                                 ownership=ownership)
                ledger.record_attempt(session_id=session_id, seed=config["seed"], step=step,
                                      ownership=ownership)
                send_packet(channel, {"kind": "attempt", "step_index": step})
                output = controller.step(observation)
        if output.telemetry.neural_ms != 20.:
            raise ValueError("live baseline requires the unchanged 20 ms window")
        result = StepResult(session_id=session_id, generation=generation, step_index=step,
                            completed_monotonic_ms=time.monotonic() * 1000,
                            output=output, motor_rates_hz=tap.rates, raw_action=tap.raw_action,
                            statistics=tap.statistics, model_file_reads=reads[0])
        send_packet(channel, result.model_dump(mode="json"))
    # Parent consumes the last result before terminating/reaping us.
    receive_packet(channel)


def main():
    with socket.socket(fileno=int(sys.argv[1])) as channel:
        channel.settimeout(125)
        try:
            execute(channel, receive_packet(channel))
        except (EOFError, BrokenPipeError, ConnectionResetError):
            return 0
        except Exception:
            # Arbitrary model exceptions may contain local paths/private data.
            try:
                send_packet(channel, {"kind": "failed", "reason": "Neural worker failed; attempts remain counted."})
            except OSError:
                pass
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
