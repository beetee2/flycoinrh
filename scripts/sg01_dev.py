"""Own a loopback API and matching Vite process for either SG01 launch profile."""
import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "review": "Art review — capture-only demo and saved replays.",
    "live": "Live flight — human execution mode. Select a source and Preview or Start explicitly.",
}


def port(value):
    number = int(value)
    if not 1024 <= number <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1024 and 65535")
    return number


@contextmanager
def profile_service(profile, backend="cpu"):
    if profile == "review" and backend != "cpu":
        raise ValueError("CUDA requires the live profile")
    if profile == "review":
        from scripts.sg01_preview import preview_service
        with tempfile.TemporaryDirectory(prefix="flyjam-sg01-") as directory:
            yield preview_service(Path(directory), ROOT / "artifacts/live/recordings")
    else:
        from flytrap.live.service import LiveService, source_metadata
        yield LiveService(repository_root=ROOT, execution_purpose="human", source_provider=source_metadata, backend=backend)


def serve_api(profile, fd, backend="cpu"):
    import uvicorn
    from flytrap.live.api import create_live_app
    with socket.socket(fileno=fd) as listener, profile_service(profile, backend) as service:
        server = uvicorn.Server(uvicorn.Config(create_live_app(service=service),
            host="127.0.0.1", workers=1, limit_concurrency=16, timeout_keep_alive=5,
            timeout_graceful_shutdown=5, log_level="warning"))
        server.run(sockets=[listener])


def reserve_port(number):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # No SO_REUSEPORT: only our API child may inherit this reservation.
        # SO_REUSEADDR permits relaunch after closed connections reach TIME_WAIT;
        # it cannot replace an active listening socket.
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", number))
        listener.listen(128)
        return listener
    except OSError:
        listener.close()
        raise RuntimeError(f"Port {number} is unavailable. Stop its owner yourself or choose another port.") from None


def stop_owned(process):
    """A private session contains only this child and its descendants (including Vite)."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        pass
    # npm may exit before Vite; reap every descendant in our private group.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=3)


def wait_api(process, api_port, timeout=15):
    # The supervisor retains the listening socket throughout its lifetime. A
    # different backend cannot bind it, even if our child exits during readiness.
    deadline = time.monotonic() + timeout
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("SG01 API exited during startup. Check the local server output.")
        try:
            with opener.open(f"http://127.0.0.1:{api_port}/health/live", timeout=.25) as response:
                if response.status == 200 and process.poll() is None:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(.05)
    raise RuntimeError("SG01 API did not become ready. Check the local server output and retry.")


def run(profile, api_port, ui_port, backend="cpu"):
    if api_port == ui_port:
        raise RuntimeError("API and frontend ports must be different.")
    children = []
    with reserve_port(api_port) as api_socket, reserve_port(ui_port) as ui_socket:
        try:
            api = subprocess.Popen([sys.executable, "-m", "scripts.sg01_dev", "--profile", profile,
                "--api-fd", str(api_socket.fileno()), "--backend", backend], cwd=ROOT,
                pass_fds=(api_socket.fileno(),), start_new_session=True)
            children.append(api)
            wait_api(api, api_port)
            # Vite owns its socket and fails closed on a bind race via strictPort.
            ui_socket.close()
            frontend = subprocess.Popen(["npm", "--prefix", "web", "run", "dev", "--",
                "--port", str(ui_port), "--strictPort"], cwd=ROOT,
                env={**os.environ, "FLYJAM_API_PORT": str(api_port)}, start_new_session=True)
            children.append(frontend)
            print(f"{LABELS[profile]}\nNeural backend: {backend if profile == 'live' else 'none'}.\nhttp://127.0.0.1:{ui_port}/live\n"
                  "Startup is idle. Ctrl+C stops this launcher's processes.", flush=True)
            while True:
                if api.poll() is not None:
                    raise RuntimeError("SG01 API stopped; closing its frontend. Relaunch to reconnect.")
                result = frontend.poll()
                if result is not None:
                    return result
                time.sleep(.1)
        finally:
            # A second Ctrl+C must not interrupt cleanup and orphan a child.
            handlers = {sig: signal.signal(sig, signal.SIG_IGN)
                        for sig in (signal.SIGINT, signal.SIGTERM)}
            try:
                for child in reversed(children):
                    stop_owned(child)
            finally:
                for sig, handler in handlers.items():
                    signal.signal(sig, handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=LABELS, required=True)
    parser.add_argument("--api-port", type=port)
    parser.add_argument("--ui-port", type=port, default=5173)
    parser.add_argument("--api-fd", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--backend", choices=("cpu", "cuda"), default="cpu",
                        help="Explicit live neural implementation (CPU remains the default)")
    args = parser.parse_args(argv)
    if args.profile == "review" and args.backend != "cpu":
        parser.error("CUDA requires --profile live")
    if args.api_fd is not None:
        serve_api(args.profile, args.api_fd, args.backend)
        return 0

    def interrupted(signum, frame):
        raise KeyboardInterrupt

    old_handlers = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        return run(args.profile, args.api_port or (8770 if args.profile == "review" else 8767), args.ui_port, args.backend)
    except KeyboardInterrupt:
        return 130
    except (RuntimeError, OSError) as exc:
        message = str(exc) if isinstance(exc, RuntimeError) else "Unable to launch SG01. Check Python, npm and local access."
        print(message, file=sys.stderr)
        return 1
    finally:
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    raise SystemExit(main())
