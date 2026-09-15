"""Operator-coordinated OBS06 checks; retains no source pixels or previews on disk.

Requires a separately running automated local service and explicit content consent.
Only numeric comparisons and lifecycle metadata are persisted. Input bytes remain
in memory and never appear in assertions or exception messages.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import uuid

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8878")
    parser.add_argument("--approved-source", required=True, choices=["/dev/video0"])
    parser.add_argument("--safe-content-ready", required=True, choices=["yes"])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.url != "http://127.0.0.1:8878":
        parser.error("This bounded validation uses the separate local port 8878 service")
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {"status": "RUNNING", "source": args.approved_source,
              "consent": "Operator confirmed safe content and coordination in OBS06 conversation",
              "recording": False, "saved_inputs": False, "phases": []}
    client = httpx.Client(base_url=args.url, timeout=6)
    token = client.get("/api/live/control").json()["csrf_token"]
    client.headers.update({"origin": args.url, "x-live-csrf": token})
    active = None

    def save():
        (args.output / "result.json").write_text(json.dumps(report, indent=2))

    def checked(ok, message):
        if not ok:
            raise RuntimeError(message)

    def config():
        response = client.get("/api/live/config")
        response.raise_for_status()
        result = response.json()
        checked(result["execution_purpose"] == "automated", "Automated server accounting required")
        checked(result["obs_recording_allowed"] is False, "OBS recording guard must stay disabled")
        return result

    def current():
        response = client.get("/api/live/status")
        response.raise_for_status()
        return response.json()["current"]

    def command(text):
        print(text, flush=True)
        checked(sys.stdin.readline().strip() == "continue", "Explicit operator coordination required")

    def start(calls):
        nonlocal active
        cfg = config()
        checked(cfg["validation_remaining"] >= calls, "Insufficient actual remaining allowance")
        owner = uuid.uuid4().hex
        response = client.post("/api/live/sessions", json={"request_id": uuid.uuid4().hex,
            "owner_token": owner, "config": {"source_id": "v4l2-video0", "evidence_kind": "real",
            "seed": 20260915, "max_model_calls": calls, "duration_seconds": 120, "recording": False}})
        response.raise_for_status()
        snap = response.json()
        active = (snap["status"]["session_id"], {"generation": snap["status"]["generation"], "owner_token": owner})
        return snap

    def stop():
        nonlocal active
        if active:
            sid, owner = active
            response = client.post(f"/api/live/sessions/{sid}/stop", json=owner)
            response.raise_for_status()
            active = None

    def collect(*, signal=False):
        started = last_renew = time.monotonic()
        signaled = False
        health_ms, receipt_ms, step_ms, samples = [], [], [], {}
        while time.monotonic() - started < 125:
            now = time.monotonic()
            if now-last_renew > .5 and active:
                sid, owner = active
                reply = client.post(f"/api/live/sessions/{sid}/renew", json=owner)
                checked(reply.status_code in (200, 409), "Lease renewal failed")
                last_renew = now
            t = time.monotonic()
            health = client.get("/health/live")
            health.raise_for_status()
            health_ms.append((time.monotonic()-t)*1000)
            snap = current()
            sample = snap["last_inferred"]
            if sample:
                samples[sample["step_index"]] = sample
                if signal and not signaled:
                    print("STOP_OBS_NOW: first real response received; operator may stop Virtual Camera now", flush=True)
                    signaled = True
            if snap["source_receipt_age_ms"] is not None:
                receipt_ms.append(snap["source_receipt_age_ms"])
            if snap["last_step_wall_ms"] is not None:
                step_ms.append(snap["last_step_wall_ms"])
            if snap["status"]["state"] in {"stopped", "failed", "source_lost", "limit_reached"}:
                checked(snap["recording_state"] == "off", "OBS recording must remain off")
                numeric = {"status": snap["status"], "completed_calls": snap["completed_calls"],
                    "rejected_results": snap["rejected_results"], "flight": snap["flight"],
                    "health_max_ms": max(health_ms), "health_reads": len(health_ms),
                    "receipt_age_max_ms": max(receipt_ms, default=None),
                    "step_wall_max_ms": max(step_ms, default=None),
                    "elapsed_seconds": time.monotonic()-started,
                    "samples": [{"step_index": s["step_index"], "frame": s["frame"],
                                 "motor_rates_hz": s["motor_rates_hz"]} for s in samples.values()]}
                report["phases"].append(numeric)
                save()
                stop()
                return snap, samples
            time.sleep(.05)
        raise RuntimeError("Bounded OBS phase timed out")

    try:
        report["accounting_before"] = config()
        # Reuse the completed initial browser call's input only in memory.
        initial = current()
        checked(initial is not None and initial["last_inferred"] is not None,
                "Run the approved OBS browser gate first on this service")
        checked(initial["last_inferred"]["frame"]["source_id"] == "v4l2-video0", "Wrong initial source")
        before_pixels = initial["last_inferred"]["observation_u8"]
        report["initial_session_id"] = initial["status"]["session_id"]
        save()
        command("CHANGE_CONTENT: initial input retained in memory; change safe content within FLYJAM_INPUT, then send continue")
        start(2)
        changed, samples = collect()
        checked(changed["completed_calls"] == 2, "Changed-content phase needs two actual completed calls")
        report["changed_pixels_from_initial"] = [sum(a != b for a, b in zip(before_pixels, s["observation_u8"], strict=True))
                                                  for s in samples.values()]
        save()
        command("PREPARE_STOP: ready for bounded real inference producer-stop phase; send continue when operator is ready")
        start(64)
        stopped, _ = collect(signal=True)
        checked(stopped["status"]["state"] == "source_lost", "Actual producer stop must reach source_lost")
        checked(stopped["flight"]["neutral"], "Producer stop must neutralize flight")
        held = current()
        time.sleep(.4)
        checked(current()["flight"] == held["flight"], "Late result advanced stopped flight")
        report["producer_stop_pose_stable"] = True
        save()
        command("RESTART_OBS: producer-stop detected; manually restart Virtual Camera then send continue")
        checked(current()["status"]["state"] == "source_lost", "Producer restart auto-resumed inference")
        report["restart_requires_explicit_start"] = True
        start(2)
        restarted, _ = collect()
        checked(restarted["completed_calls"] == 2, "Explicit restart must complete real calls")
        checked(restarted["status"]["session_id"] != stopped["status"]["session_id"], "Restart must use new session")
        report["status"] = "PASS" if all(report["changed_pixels_from_initial"]) else "INCONCLUSIVE"
        report["scope"] = "Actual changed-input delivery and producer lifecycle; no causal-response or product approval"
        return 0 if report["status"] == "PASS" else 1
    except Exception as exc:
        report["status"] = "FAIL"
        report["reason"] = f"{type(exc).__name__}: coordinated check failed; inspect numeric phase statuses"
        return 1
    finally:
        stop()
        report["accounting_after"] = config()
        save()
        client.close()
        print(json.dumps({"status": report["status"], "evidence": str(args.output / "result.json")}), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
