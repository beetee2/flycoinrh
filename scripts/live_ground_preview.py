"""Local ground-contact preview with no available capture or inference source.

Run after `npm --prefix web run build`, then open /live and Load/Play the
synthetic preview. The server has no neural session or capture factory.
"""
import argparse
from pathlib import Path
import tempfile

import uvicorn

from flytrap.live.api import create_live_app
from flytrap.live.service import LiveService, Unavailable


def disabled_session(*args, **kwargs):
    raise Unavailable("This synthetic ground preview cannot capture or infer.")


def preview_service(root):
    return LiveService(repository_root=root, source_provider=lambda: [],
                       session_factory=disabled_session, capture_factory=disabled_session)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8769)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    with tempfile.TemporaryDirectory(prefix="flyjam-ground-preview-") as directory:
        service = preview_service(Path(directory))
        uvicorn.run(create_live_app(service=service), host="127.0.0.1", port=args.port,
                    workers=1, timeout_keep_alive=5)


if __name__ == "__main__":
    main()
