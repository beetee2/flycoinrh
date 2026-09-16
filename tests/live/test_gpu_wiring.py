"""Server selection and owned-worker GPU attachment; synthetic graph only."""
import json
import subprocess
import sys
import types

import pytest
from pydantic import ValidationError

from flytrap.live.api_contracts import StartRequest
from flytrap.live.contracts import SessionConfig
from flytrap.live.service import LiveService
from scripts import sg01_dev


def gpu_module(monkeypatch, gate):
    module = types.ModuleType("flytrap.live.gpu")
    module.require_qualified_gpu = gate
    monkeypatch.setitem(sys.modules, "flytrap.live.gpu", module)
    return module


def test_cpu_startup_never_imports_torch():
    code = "from flytrap.live.service import LiveService; import sys, json; s=LiveService(); print(json.dumps({'torch': 'torch' in sys.modules, 'backend': s.capabilities.neural_backend}))"
    result = subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == {"torch": False, "backend": "cpu"}


def test_unqualified_gpu_refuses_startup_without_cpu_fallback(monkeypatch):
    def fail():
        raise ValueError("GPU qualification failed")
    gpu_module(monkeypatch, fail)
    with pytest.raises(ValueError, match="qualification failed"):
        LiveService(backend="cuda")
    with pytest.raises(ValueError, match="qualification failed"):
        with sg01_dev.profile_service("live", "cuda"):
            pytest.fail("unqualified service must never become available")


def test_gpu_label_and_launcher_selection_are_server_authoritative(monkeypatch):
    from flytrap.live import session
    checked = []
    gpu_module(monkeypatch, lambda: checked.append(True))
    calls = []
    monkeypatch.setattr(session, "NeuralSession", lambda config, **kwargs: calls.append(kwargs))
    with sg01_dev.profile_service("live", "cuda") as service:
        assert checked == [True]
        assert service.capabilities.neural_backend == "cuda"
        assert service.sessions == {} and service.current_id is None
        service.session_factory("fixture", repository_root="fixture", source=None,
                                expected_device=None, recording_store=None)
    assert calls[0]["backend"] == "cuda" and calls[0]["purpose"] == "human"
    with pytest.raises(ValidationError):
        SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=1, backend="cuda")
    with pytest.raises(ValidationError):
        StartRequest(request_id="a" * 32, owner_token="b" * 32,
            config=SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=1), backend="cuda")


def test_unknown_backend_and_review_cuda_rejected():
    with pytest.raises(ValueError, match="backend"):
        LiveService(backend="auto")
    with pytest.raises(ValueError, match="live profile"):
        with sg01_dev.profile_service("review", "cuda"):
            pytest.fail("review cannot select GPU inference")
