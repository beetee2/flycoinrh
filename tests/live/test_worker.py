"""Instrument the persistent worker with the actual tiny adapter and bounded IPC."""
import socket
import sys
import threading
import types

import pytest

from flytrap.controllers import fly
from flytrap.live.accounting import LiveOwnership
from flytrap.live.contracts import SessionConfig
from flytrap.live.neural import MAX_PACKET, StepRequest, receive_packet, send_packet
from flytrap.live.worker import execute
from tests.controllers import conftest as synthetic_fixtures

adapter_files = synthetic_fixtures.adapter_files
adapter_files_factory = synthetic_fixtures.adapter_files_factory


@pytest.mark.parametrize("backend", ["cpu", "cuda"])
def test_worker_loads_and_resets_exactly_once_for_multiple_frames(adapter_files, tmp_path, monkeypatch, backend):
    counts = {"loads": 0, "resets": 0, "steps": 0}
    original = fly.FlyController

    class CountedController(original):
        def __init__(self, **kwargs):
            counts["loads"] += 1
            super().__init__(**kwargs)

        def reset(self, **kwargs):
            counts["resets"] += 1
            return super().reset(**kwargs)

        def step(self, observation):
            counts["steps"] += 1
            return super().step(observation)

    monkeypatch.setattr(fly, "FlyController", CountedController)
    attached = []
    if backend == "cuda":
        from flytrap.live.worker import identity
        module = types.ModuleType("flytrap.live.gpu")

        def attach(controller):
            assert counts == {"loads": 1, "resets": 0, "steps": 0}
            attached.append(controller)
            descriptor = identity(controller, {})["neural_execution"]
            return {**descriptor, "backend": "cuda-torch-csr-v1", "device": "cuda:0",
                    "device_name": "synthetic test GPU"}

        module.attach_gpu = attach
        monkeypatch.setitem(sys.modules, "flytrap.live.gpu", module)
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    parent.settimeout(5)
    child.settimeout(5)
    errors = []
    with LiveOwnership(tmp_path) as owner:
        config = SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=23, max_model_calls=3)
        init = {"repository_root": str(tmp_path), "purpose": "fixture", "files": adapter_files,
                "lock_fds": owner.filenos, "config": config.model_dump(mode="json"),
                "session_id": "fixture-worker", "generation": 1, "backend": backend}

        def run():
            try:
                execute(child, init)
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=run)
        thread.start()
        try:
            ready = receive_packet(parent)
            assert ready["kind"] == "ready"
            assert ready["provenance"]["neural_execution"]["backend"] == (
                "cuda-torch-csr-v1" if backend == "cuda" else "cpu-numpy-csc-v1")
            assert ready["provenance"]["model"]["fixture"] is True
            assert ready["provenance"]["model_id"].startswith(
                "fixture-cuda-" if backend == "cuda" else "fixture-")
            for index in range(3):
                send_packet(parent, StepRequest(session_id="fixture-worker", generation=1, step_index=index,
                                               observation_u8=[index * 50] * 256).model_dump())
                assert receive_packet(parent) == {"kind": "attempt", "step_index": index}
                result = receive_packet(parent)
                assert result["step_index"] == index and result["model_file_reads"] == 0
            send_packet(parent, {"kind": "close"})
        finally:
            thread.join(5)
            parent.close()
            child.close()
        assert not thread.is_alive() and errors == []
    assert counts == {"loads": 1, "resets": 1, "steps": 3}
    assert len(attached) == int(backend == "cuda")


def test_ipc_rejects_metadata_and_oversized_packets():
    with pytest.raises(ValueError):
        StepRequest(session_id="fixture-worker", generation=1, step_index=0,
                    observation_u8=[0] * 256, target=[1, 2])
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        parent.send(b" " * (MAX_PACKET + 1))
        with pytest.raises(ValueError, match="exceeds"):
            receive_packet(child)
        with pytest.raises(ValueError, match="exceeds"):
            send_packet(parent, {"large": " " * MAX_PACKET})
    finally:
        parent.close()
        child.close()
