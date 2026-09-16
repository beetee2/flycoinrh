#!/usr/bin/env python3
"""Frozen OBS06 safe-stimulus diagnostic; preparation performs zero neural calls.

Prepare first, inspect plan.json, then explicitly execute the same plan. The
diagnostic is outside the live service and frozen model. It cannot open hardware,
change accounting purpose, retry a failed call, or change the fixed comparison.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

SEED = 20260915
STEPS = 8
PLANNED_CALLS = 32
CONDITIONS = ("changing", "frozen", "disconnected", "changing-repeat")
INTERVAL_MS = 500


def safe_stimuli():
    """Generated full-range grayscale RGB, then the unchanged production encoder."""
    from flytrap.live.contracts import FrameIdentity
    from flytrap.live.encoding import RGBFrame, encode_frame

    patterns = [
        ("dark", lambda x, y: 32), ("bright", lambda x, y: 224),
        ("left", lambda x, y: 224 if x < 8 else 32),
        ("right", lambda x, y: 32 if x < 8 else 224),
        ("top", lambda x, y: 224 if y < 8 else 32),
        ("bottom", lambda x, y: 32 if y < 8 else 224),
        ("checker", lambda x, y: 224 if (x//4+y//4) % 2 else 32),
        ("inverse-checker", lambda x, y: 32 if (x//4+y//4) % 2 else 224),
    ]
    samples = []
    for index, (name, pattern) in enumerate(patterns):
        identity = FrameIdentity(schema_version="obs-frame-1", source_id="safe-causal-pattern", session_id="causal-playback",
            generation=1, sequence=index, evidence_kind="fixture", width=16, height=16,
            pixel_format="RGB24", receipt_monotonic_ms=float(index*INTERVAL_MS),
            source_timestamp_ms=None, source_sequence=None, source_clock="unknown")
        rgb = bytes(v for y in range(16) for x in range(16) for v in [pattern(x, y)]*3)
        encoded = encode_frame(RGBFrame(identity, rgb))
        samples.append({"name": name, "observation_u8": list(encoded.u8),
                        "sha256": encoded.sha256, "frame": identity.model_dump(mode="json")})
    return samples


@contextmanager
def diagnostic_drive(controller, *, disconnected):
    """Observe actual brain input; ablation replaces rates with exact zero arrays.

    Retain neuron indices and RNG draw count. The ordinary eye and its oracle tap
    still execute unchanged. Only this explicitly labeled diagnostic intercepts
    the subsequent brain.run argument. Restore the instance method on all exits.
    """
    import numpy as np

    brain = controller._brain
    original = brain.run
    evidence = {}

    def run(drive, *args, **kwargs):
        if evidence:
            raise RuntimeError("diagnostic hook permits exactly one neural invocation")
        submitted = {key: np.zeros_like(value) for key, value in drive.items()} if disconnected else drive
        evidence.update({"diagnostic_disconnected": disconnected, "step_seed": kwargs["seed"],
            "ordinary_drive_hz": [{"indices": [int(i) for i in key],
                                    "rates": np.asarray(value).tolist()} for key, value in drive.items()],
            "submitted_drive_hz": [{"indices": [int(i) for i in key],
                                     "rates": np.asarray(value).tolist()} for key, value in submitted.items()]})
        return original(submitted, *args, **kwargs)

    brain.run = run
    try:
        yield evidence
    finally:
        brain.run = original


def fixed_flight(rates):
    """Apply each measured response for 25 ordinary 20 ms physics ticks."""
    from flytrap.live.contracts import MotorRates
    from flytrap.live.flight import ControlTick, decode, initial_state, replay

    # OBS06's frozen diagnostic and its historical measurements use v1.
    initial = initial_state("causal-playback", 1, "fixture", physics_id="flight-fixed20-v1")
    events, controls = [], []
    for index, vector in enumerate(rates):
        now = float(index*INTERVAL_MS)
        control = decode(MotorRates(**vector), response_id=f"causal-response-{index}",
            session_id="causal-playback", generation=1, evidence_kind="fixture",
            receipt_ms=now, completed_ms=now, now_ms=now)
        controls.append(control.model_dump(mode="json"))
        events.append(ControlTick(tick=index*25+1, controls=control))
    states = replay(initial, events, ticks=len(rates)*25, origin_ms=0.)
    return {"controls": controls, "states": [state.model_dump(mode="json") for state in states]}


def specification():
    from scripts.live_real import digest

    paths = ["scripts/live_causal.py", "flytrap/live/encoding.py", "flytrap/live/sensory.py",
             "flytrap/live/flight.py", "flytrap/live/accounting.py", "flysim.py", "flyeye.py",
             "flytrap/controllers/fly.py"]
    return {"schema_version": "obs06-causal-plan-1", "seed": SEED, "steps_per_condition": STEPS,
        "conditions": list(CONDITIONS), "planned_calls": PLANNED_CALLS, "automatic_retries": 0,
        "execution_purpose": "automated", "source_evidence": "safe generated deterministic fixture",
        "model_evidence": "actual full connectome; disconnected condition is a diagnostic ablation",
        "desktop_capture": False, "obs_recording": False, "samples": safe_stimuli(),
        "playback_interval_ms": INTERVAL_MS, "flight_dt_ms": 20,
        "initial_pose": {"position": [0., 0., 2.], "yaw": 0., "pitch": 0., "speed": 0.},
        "timing": "Fixed diagnostic playback; actual model latency separately measured, not live receipt timing.",
        "source_sha256": {path: digest(REPO/path) for path in paths},
        "decision_rule": "Report all paired input/rate/control/trajectory differences and exact repeat; no seed or mapping tuning."}


def comparisons(runs):
    import numpy as np

    def difference(a, b):
        delta = np.abs(np.asarray(a, dtype=float)-np.asarray(b, dtype=float))
        return {"max_absolute": float(delta.max()), "mean_absolute": float(delta.mean()),
                "different_values": int(np.count_nonzero(delta)), "values_compared": int(delta.size)}

    def vectors(run, field, names):
        return [[entry[field][name] for name in names] for entry in run["steps"]]

    output = {}
    for other in CONDITIONS[1:]:
        a, b = runs["changing"], runs[other]
        rate_names = list(a["steps"][0]["rates"])
        control_names = ["yaw_rate_rad_s", "pitch_target_rad", "speed_target_units_s"]
        pair = {"observation_u8": difference([s["observation_u8"] for s in a["steps"]],
                                             [s["observation_u8"] for s in b["steps"]]),
                "rates_hz": {name: difference([s["rates"][name] for s in a["steps"]],
                                                [s["rates"][name] for s in b["steps"]]) for name in rate_names},
                "all_rates_hz": difference(vectors(a, "rates", rate_names), vectors(b, "rates", rate_names)),
                "controls": {name: difference([c[name] for c in a["flight"]["controls"]],
                                                [c[name] for c in b["flight"]["controls"]]) for name in control_names},
                "positions": difference([s["snapshot"]["position"] for s in a["flight"]["states"]],
                                          [s["snapshot"]["position"] for s in b["flight"]["states"]])}
        separation = np.asarray([s["snapshot"]["position"] for s in a["flight"]["states"]])-np.asarray(
            [s["snapshot"]["position"] for s in b["flight"]["states"]])
        pair["trajectory"] = {"max_separation_units": float(np.linalg.norm(separation, axis=1).max()),
                              "final_separation_units": float(np.linalg.norm(separation[-1])),
                              "final_position_difference": separation[-1].tolist()}
        output[f"changing_vs_{other}"] = pair
    return output


def execute(output, report):
    from flytrap.contracts import Observation
    from flytrap.controllers.fly import FlyController
    from flytrap.live.accounting import LiveLedger, LiveOwnership
    from flytrap.live.sensory import CompiledRetina, LiveResponseCapture
    from flytrap.live.worker import model_files
    from scripts.live_real import Blocked, checked, deadline, identities, protected_paths, save

    files = model_files(REPO)
    paths = protected_paths(files)
    before = identities(paths)
    ledger = LiveLedger.automated(REPO)
    report.update(protected_before=before, automated_attempts_before=ledger.attempted,
                  automated_remaining_before=ledger.remaining, runs={})
    save(output/"result.json", report)
    if ledger.remaining < PLANNED_CALLS:
        raise Blocked("Insufficient remaining automated allowance for the frozen 32-call comparison")
    print(f"Automated allowance: {ledger.remaining}/1024 remaining; 32 fixed attempts", flush=True)
    try:
        with LiveOwnership(REPO) as owner:
            started = time.monotonic()
            with deadline(30):
                controller = FlyController(**files)
                retina = CompiledRetina(controller, annotations_path=files["annotations_path"])
            checked(controller.provenance["fixture"] is False, "Real model is required")
            report.update(model_load_ms=(time.monotonic()-started)*1000,
                          model_provenance=controller.provenance)
            samples = report["plan"]["specification"]["samples"]
            for condition in CONDITIONS:
                session_id = f"obs06-causal-{uuid.uuid4().hex[:20]}"
                session_ledger = LiveLedger.session(REPO, session_id, cap=STEPS, mode="automated")
                controller.reset(run_seed=SEED, checkpoint=controller.checkpoint)
                run = report["runs"][condition] = {"session_id": session_id, "steps": []}
                for index in range(STEPS):
                    sample = samples[0 if condition == "frozen" else index]
                    observation = Observation(schema_version="1", pixels=[p/255 for p in sample["observation_u8"]])
                    retinal = retina.inspect(observation)
                    with deadline(5), diagnostic_drive(controller, disconnected=condition == "disconnected") as drive:
                        with LiveResponseCapture(controller, observation, retina=retina) as tap:
                            ledger.record_attempt(session_id=session_id, seed=SEED, step=index, ownership=owner)
                            session_ledger.record_attempt(session_id=session_id, seed=SEED, step=index, ownership=owner)
                            started = time.monotonic()
                            result = controller.step(observation)
                            model_step_ms = (time.monotonic()-started)*1000
                    expected_seed = int.from_bytes(hashlib.sha256(b"FLYTRAP-step-seed-v1\0"+
                        SEED.to_bytes(4, "big")+index.to_bytes(8, "big")).digest()[:8], "big")
                    checked(drive["step_seed"] == expected_seed, "Step seed changed")
                    run["steps"].append({"index": index, "input_name": sample["name"],
                        "observation_u8": sample["observation_u8"], "observation_sha256": sample["sha256"],
                        "retinal": retinal, "drive": drive, "rates": tap.rates, "raw_action": tap.raw_action,
                        "statistics": tap.statistics, "output": result.model_dump(mode="json"),
                        "model_step_ms": model_step_ms})
                    save(output/"result.json", report)
                run["flight"] = fixed_flight([step["rates"] for step in run["steps"]])
                save(output/"result.json", report)
            report["comparisons"] = comparisons(report["runs"])
            changing, repeat = report["runs"]["changing"], report["runs"]["changing-repeat"]
            exact_fields = ("observation_u8", "retinal", "drive", "rates", "raw_action", "statistics", "output")
            report["exact_repeat"] = all(all(a[k] == b[k] for k in exact_fields)
                for a, b in zip(changing["steps"], repeat["steps"], strict=True)) and changing["flight"] == repeat["flight"]
            checked(report["exact_repeat"], "Exact repeat failed; no automatic rerun")
            disconnected = report["runs"]["disconnected"]
            checked(all(value == 0 for step in disconnected["steps"]
                for group in step["drive"]["submitted_drive_hz"] for value in group["rates"]), "Drive not disconnected")
            checked(len({tuple(step["observation_u8"]) for step in changing["steps"]}) == STEPS,
                    "Changing condition requires eight distinct actual observations")
            report["interpretation"] = (
                "Bounded diagnostic evidence only. Inspect changing-versus-frozen control and trajectory deltas; "
                "motion or a difference from disconnected drive alone does not prove strong visual responsiveness.")
    finally:
        report.update(protected_after=identities(paths), automated_attempts_after=ledger.attempted,
                      automated_remaining_after=ledger.remaining,
                      automated_attempts_consumed=ledger.attempted-report["automated_attempts_before"])
        report["protected_unchanged"] = report["protected_after"] == before
        save(output/"result.json", report)
        checked(report["protected_unchanged"], "Protected model or historical ledger changed")
    checked(report["automated_attempts_consumed"] == PLANNED_CALLS, "Unexpected attempt count")


def main(argv=None):
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    from flytrap.live.accounting import LiveLedger
    from scripts.live_real import Blocked, digest, save

    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", type=Path, help="new private evidence directory")
    mode.add_argument("--execute-plan", type=Path, help="previously frozen plan.json")
    args = parser.parse_args(argv)
    if args.prepare:
        output = args.prepare.resolve()
        output.mkdir(parents=True, exist_ok=False, mode=0o700)
        ledger = LiveLedger.automated(REPO)
        plan = {"specification": specification(), "automated_attempts_at_preparation": ledger.attempted,
                "automated_remaining_at_preparation": ledger.remaining,
                "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
                "git_status": subprocess.check_output(["git", "status", "--short"], cwd=REPO, text=True),
                "prepared_unix_ns": time.time_ns()}
        save(output/"plan.json", plan)
        print(json.dumps({"status": "PREPARED", "planned_calls": PLANNED_CALLS,
                          "remaining": ledger.remaining, "plan": str(output/"plan.json")}))
        return 0
    path = args.execute_plan.resolve()
    output = path.parent
    if (output/"result.json").exists():
        parser.error("execution evidence already exists; automatic repeats are prohibited")
    plan = json.loads(path.read_text())
    if plan["specification"] != specification():
        parser.error("frozen plan differs from current schedule/source; do not run")
    report = {"schema_version": "obs06-causal-result-1", "status": "RUNNING", "plan": plan,
              "plan_sha256": digest(path), "command": [sys.executable, str(Path(__file__).resolve()),
                  *(argv if argv is not None else sys.argv[1:])], "started_unix_ns": time.time_ns()}
    started = time.monotonic()
    try:
        execute(output, report)
        report["status"], code = "PASS", 0
    except Blocked as exc:
        report["status"], report["reason"], code = "BLOCKED", str(exc), 2
    except Exception as exc:
        report["status"], report["reason"], code = "FAIL", f"{type(exc).__name__}: {exc}", 1
    report.update(command_exit=code, elapsed_seconds=time.monotonic()-started)
    save(output/"result.json", report)
    print(json.dumps({"status": report["status"], "exit": code, "result": str(output/"result.json"),
                      "attempts": report.get("automated_attempts_consumed"),
                      "remaining": report.get("automated_remaining_after")}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
