"""Local foundation commands; no public deployment or upstream service launch."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess

from flytrap.config import Settings
from flytrap.persistence import require_sqlite


def doctor(settings: Settings) -> dict:
    require_sqlite()
    report = {
        "schema_version": "1", "profile": settings.profile,
        "fixture": settings.profile == "fixture", "python": platform.python_version(),
        "sqlite_linked": sqlite3.sqlite_version,
        "data_root": str(settings.data_root), "artifact_root": str(settings.artifact_root),
        "database_path": str(settings.database_path), "real_model_available": False,
        "admission": "closed" if settings.profile == "fixture" else "unavailable",
        "learning_claim_status": "NOT_RUN", "checks": {},
    }
    report["checks"]["python_runtime"] = platform.python_version() == "3.14.7"
    try:
        node = subprocess.check_output(["node", "--version"], text=True, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        node = None
    report["node"] = node
    report["checks"]["node_runtime"] = node == "v26.8.2"
    report["dependencies"] = {name: importlib.metadata.version(name) for name in ("fastapi", "pydantic", "uvicorn")}
    report["lock_sha256"] = {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        for path in (Path("uv.lock"), Path("web/package-lock.json"))
    }
    report["checks"]["locks_present"] = all(report["lock_sha256"].values())
    report["disk_free_bytes"] = shutil.disk_usage(Path.cwd()).free
    # These are explicitly upstream checkout probes, not operator storage-root paths.
    report["upstream_checkout_model_files"] = {
        str(p): p.is_file() for p in (Path("build/graph.npz"), Path("data/body-annotations.feather"))
    }
    if settings.profile == "real":
        report["checks"]["real_model_integration"] = False
        report["blockers"] = ["Real worker and end-to-end release integration are not implemented."]
        report["data_gate_command"] = "make data-doctor (RAW_ROOT/GRAPH_ROOT configurable)"
        report["adapter_gate_command"] = "make test-controller-real (RAW_ROOT/GRAPH_ROOT configurable)"
    report["status"] = "PASS" if all(report["checks"].values()) else "BLOCKED"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["serve", "doctor", "worker", "verify-real", "verify-release",
                                            "data-fetch", "data-build", "data-doctor",
                                            "controller-baseline", "controller-doctor"])
    parser.add_argument("--profile", choices=["real", "fixture"], default="real")
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--data-root", type=Path, default=Path("artifacts/local/data"))
    parser.add_argument("--artifact-root", type=Path, default=Path("artifacts/local/runs"))
    parser.add_argument("--raw-root", type=Path, default=Path("data"))
    parser.add_argument("--graph-root", type=Path, default=Path("build/flytrap-v1"))
    parser.add_argument("--annotations-path", type=Path)
    parser.add_argument("--parameters-path", type=Path)
    parser.add_argument("--calibration-path", type=Path)
    parser.add_argument("--checkpoint-path", type=Path)
    parser.add_argument("--min-syn", type=int, default=3)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if args.command.startswith("controller-"):
        if any(getattr(args, field) is None for field in (
            "annotations_path", "parameters_path", "calibration_path", "checkpoint_path"
        )):
            parser.error("controller commands require explicit annotation, parameter, calibration and checkpoint paths")
        try:
            from flytrap.model_tools import run_command
            result = run_command(args.command, graph_root=args.graph_root,
                                 annotations_path=args.annotations_path, parameters_path=args.parameters_path,
                                 calibration_path=args.calibration_path, checkpoint_path=args.checkpoint_path)
            print(json.dumps(result, indent=2))
            return 0
        except (OSError, ValueError, RuntimeError) as error:
            print(json.dumps({"status": "BLOCKED", "error": str(error), "learning_enabled": False}))
            return 1
    if args.command.startswith("data-"):
        from flytrap.data.prepare import run_command
        return run_command(args.command, args.raw_root, args.graph_root, args.min_syn)
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    try:
        settings = Settings(args.profile, args.production, args.data_root, args.artifact_root)
        if args.command in {"verify-real", "verify-release"}:
            settings = Settings("real", args.production, args.data_root, args.artifact_root)
        if args.command in {"doctor", "verify-real", "verify-release"}:
            report = doctor(settings)
            print(json.dumps(report, indent=2))
            return 0 if report["status"] == "PASS" else 1
        if args.command == "worker":
            from flytrap.contracts import Observation
            from flytrap.worker import create_worker
            worker = create_worker(settings)
            try:
                worker.start()
                result = worker.step(Observation(schema_version="1", pixels=[0.0] * 256))
                print(json.dumps({"fixture": True, "pid": worker.pid, "output": result.model_dump()}))
            finally:
                worker.close()
            return 0
        from flytrap.api import create_app
        import uvicorn
        uvicorn.run(create_app(settings), host="127.0.0.1", port=args.port, log_level="info")
        return 0
    except (ValueError, RuntimeError) as error:
        print(json.dumps({"status": "BLOCKED", "error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
