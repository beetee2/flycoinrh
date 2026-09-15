"""Playwright-only local service: safe pixels and an attributed tiny fixture graph.

Uses the actual API, capture slot, persistent neural subprocess, fixed-step flight,
private recording store and ledgers. It cannot discover or open host devices.
"""
import argparse
from pathlib import Path
import tempfile

import uvicorn

from flytrap.controllers.fly import write_baseline_checkpoint
from flytrap.live.api import create_live_app
from flytrap.live.contracts import SourceCapability
from flytrap.live.service import LiveService
from flytrap.live.session import NeuralSession
from tests.controllers.conftest import adapter_files_factory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8876)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    args.state.mkdir(parents=True, exist_ok=True)
    # The temporary directory lives through ASGI shutdown, allowing all children
    # to finish before removal. Its location is recorded only for ledger checks.
    with tempfile.TemporaryDirectory(prefix="obs05-fixture-") as temporary:
        root = Path(temporary)
        (args.state / "fixture-root.txt").write_text(str(root))
        files = adapter_files_factory.__wrapped__(root)()
        write_baseline_checkpoint(**files)
        source = SourceCapability(schema_version="obs-source-1", source_id="fixture-pattern",
            evidence_kind="fixture", name="Safe deterministic source (synthetic)", driver=None,
            backend="synthetic", capabilities=None, formats=None, metadata_state="available",
            producer_detection="synthetic")

        def factory(config, **kwargs):
            return NeuralSession(config, purpose="fixture", repository_root=root, files=files,
                source=kwargs["source"], recording_store=kwargs["recording_store"])

        service = LiveService(repository_root=root, session_factory=factory, source_provider=lambda: [source])
        uvicorn.run(create_live_app(service=service), host="127.0.0.1", port=args.port,
                    workers=1, timeout_keep_alive=5, log_level="warning")


if __name__ == "__main__":
    main()
