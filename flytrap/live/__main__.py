"""Local live entry point: metadata discovery, environment checks, and idle API."""
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
    serve = commands.add_parser("serve", help="Serve the idle local live API")
    serve.add_argument("--port", type=_port, default=8767)
    args = parser.parse_args(argv)
    if args.command == "serve":
        import uvicorn
        uvicorn.run("flytrap.live.api:create_live_app", factory=True, host="127.0.0.1", port=args.port,
                    workers=1, limit_concurrency=16, timeout_keep_alive=5)
        return 0
    report = discover_devices() if args.command == "devices" else inspect_environment()
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
