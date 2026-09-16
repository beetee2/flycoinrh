"""Local live metadata, explicit bounded source preview, and idle API."""
import argparse
import json
from pathlib import Path

from .environment import discover_devices, inspect_environment


def _port(value: str) -> int:
    number = int(value)
    if not 1024 <= number <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1024 and 65535")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, description in (("devices", "List device metadata without opening streams"),
                              ("doctor", "Inspect local prerequisites without capture or inference")):
        command = commands.add_parser(name, help=description)
        command.add_argument("--evidence-dir", type=Path,
                             help="Write a new JSON report here; existing report files are never overwritten")
        if name == "doctor":
            command.add_argument("--source", help="Explicitly selected v4l2-videoN to inspect using read-only ioctls")
    inspect = commands.add_parser("inspect-source", help="Inspect only the explicitly selected OBS device; no capture")
    inspect.add_argument("--source", required=True)
    preview = commands.add_parser("preview", help="Explicitly start an ephemeral preview, without inference or recording")
    preview.add_argument("--source", required=True, help="v4l2-videoN, or explicitly synthetic fixture-pattern")
    preview.add_argument("--seconds", type=float, default=15, help="Positive duration, at most 30 seconds")
    preview.add_argument("--port", type=_port, default=8768)
    preview.add_argument("--obs-monitor", action="store_true", help="Privately prompt for local OBS WebSocket password")
    preview.add_argument("--obs-port", type=_port, default=4455)
    preview.add_argument("--verified", action="store_true", help="Require reliable driver or authenticated OBS producer status")
    serve = commands.add_parser("serve", help="Serve the idle local live API")
    serve.add_argument("--port", type=_port, default=8767)
    serve.add_argument("--safe-source", action="store_true",
                       help="Offer only deterministic safe imagery to the actual neural model")
    serve.add_argument("--execution-purpose", choices=("automated", "human"), default="automated",
                       help="Server accounting policy; automated includes every API/browser test call")
    serve.add_argument("--backend", choices=("cpu", "cuda"), default="cpu",
                       help="Explicit neural implementation; CUDA requires completed qualification")
    args = parser.parse_args(argv)
    if args.command in ("inspect-source", "preview"):
        from dataclasses import asdict
        from .device import SourceError, inspect_selected
        try:
            if args.command == "inspect-source":
                print(json.dumps(asdict(inspect_selected(args.source)), indent=2))
                return 0
            from .preview import run_preview
            monitor = None
            if args.obs_monitor:
                import getpass
                import sys
                if not sys.stdin.isatty():
                    raise SourceError("OBS credentials require a private interactive terminal prompt.")
                from .producer import ObsProducerMonitor
                monitor = ObsProducerMonitor(password=getpass.getpass("Local OBS WebSocket password: "), port=args.obs_port)
            return run_preview(source_id=args.source, duration_s=args.seconds, port=args.port,
                               monitor=monitor, verified=args.verified)
        except SourceError as exc:
            print(str(exc))
            return 2
        except (OSError, ValueError):
            # Device/backend exceptions are not allowed to expose private diagnostics.
            print("Preview/inspection unavailable: check the explicit source ID, OBS format/access, local port, "
                  "and authenticated monitor if required. Run inspect-source for selected-device setup.")
            return 2
    if args.command == "serve":
        import uvicorn
        from .api import create_live_app
        from .service import LiveService, safe_source_metadata, source_metadata
        service = LiveService(execution_purpose=args.execution_purpose, backend=args.backend,
                              source_provider=safe_source_metadata if args.safe_source else source_metadata)
        uvicorn.run(create_live_app(service=service), host="127.0.0.1", port=args.port,
                    workers=1, limit_concurrency=16, timeout_keep_alive=5)
        return 0
    report = discover_devices() if args.command == "devices" else inspect_environment()
    if args.command == "doctor" and args.source:
        from dataclasses import asdict
        from .device import SourceError, inspect_selected
        try:
            report["selected_device"] = asdict(inspect_selected(args.source))
        except SourceError as exc:
            report["selected_device"] = None
            report["blockers"].append(str(exc))
            report["status"] = "blocked"
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.evidence_dir is not None:
        args.evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            with (args.evidence_dir / f"{args.command}.json").open("x") as stream:
                stream.write(payload)
        except FileExistsError:
            parser.error("evidence report exists; use a new --evidence-dir to preserve it")
    print(payload, end="")
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
