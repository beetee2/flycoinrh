"""SG01 safe art review: explicit synthetic Preview and existing measured replay.

No desktop source is discoverable and Start has no inference factory. All
mutable service state lives in a temporary directory. Original replay files are
verified on read and are exposed through an allowlist with no write methods.
"""
import argparse
from pathlib import Path
import tempfile

import uvicorn

from flytrap.live.api import create_live_app
from flytrap.live.capture import Capture
from flytrap.live.contracts import SourceCapability
from flytrap.live.recording import RecordingError, RecordingStore
from flytrap.live.service import LiveService, Unavailable

SAFE_REPLAY_ID = "8d4d624e6f4a4d3f8a9a7dbdc26d3d62"


def no_inference(*args, **kwargs):
    raise Unavailable("SG01 art review has no inference. Use synthetic movement or an existing recorded replay.")


def safe_capture(**kwargs):
    if kwargs.get("source_id") != "fixture-pattern":
        raise Unavailable("SG01 art review accepts only the explicitly selected synthetic fixture.")
    return Capture(**kwargs)


class SafeReplayStore:
    def __init__(self, root):
        self._store = RecordingStore(root)

    def read(self, recording_id):
        if recording_id != SAFE_REPLAY_ID:
            raise RecordingError("Replay is not allowlisted for SG01 art review.")
        replay = self._store.read(recording_id)
        if replay.manifest.source.source_id != "fixture-pattern":
            raise RecordingError("SG01 replay must contain the known safe synthetic stimulus.")
        return replay

    def list(self):
        if not (self._store.root / SAFE_REPLAY_ID).exists():
            return []
        return [{"recording_id": SAFE_REPLAY_ID, "manifest": self.read(SAFE_REPLAY_ID).manifest}]


def preview_service(root, replay_root):
    source = SourceCapability(schema_version="obs-source-1", source_id="fixture-pattern",
        evidence_kind="fixture", name="SG01 safe deterministic image sequence (synthetic)",
        driver=None, backend="synthetic", capabilities=None, formats=None,
        metadata_state="available", producer_detection="synthetic")
    return LiveService(repository_root=root, source_provider=lambda: [source],
        session_factory=no_inference, capture_factory=safe_capture,
        recording_store=SafeReplayStore(replay_root), execution_purpose="automated")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    replay_root = Path(__file__).resolve().parents[1] / "artifacts/live/recordings"
    with tempfile.TemporaryDirectory(prefix="flyjam-sg01-") as directory:
        service = preview_service(Path(directory), replay_root)
        uvicorn.run(create_live_app(service=service), host="127.0.0.1", port=args.port,
                    workers=1, timeout_keep_alive=5, log_level="warning")


if __name__ == "__main__":
    main()
