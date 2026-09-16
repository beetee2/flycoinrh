"""Fail-closed qualification checks without Torch or CUDA requirements."""
import json
from pathlib import Path
import sys

import pytest

from flytrap.live import gpu


def qualified_runtime(monkeypatch):
    qualification = json.loads((Path(gpu.__file__).resolve().parents[2] /
                                "config/gpu01-qualification.json").read_text())
    monkeypatch.setattr(gpu, "version", qualification["packages"].__getitem__)
    monkeypatch.setattr(gpu.platform, "python_version", lambda: qualification["python"])
    return qualification


def test_qualification_checks_without_importing_torch(monkeypatch):
    qualified_runtime(monkeypatch)
    before = "torch" in sys.modules
    assert gpu.require_qualified_gpu()["status"] == "PASS"
    assert ("torch" in sys.modules) == before


@pytest.mark.parametrize("change", ["package", "engine", "failure", "missing", "python"])
def test_stale_or_missing_qualification_blocks_gpu(monkeypatch, change):
    qualification = qualified_runtime(monkeypatch)
    read = Path.read_text

    def changed_read(path, *args, **kwargs):
        if path.name == "gpu01-qualification.json":
            if change == "missing":
                raise FileNotFoundError(path)
            value = dict(qualification)
            if change == "engine":
                value["engine_sha256"] = "0" * 64
            if change == "failure":
                value["status"] = "FAIL"
            return json.dumps(value)
        return read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", changed_read)
    if change == "package":
        monkeypatch.setattr(gpu, "version", lambda _: "unqualified-version")
    if change == "python":
        monkeypatch.setattr(gpu.platform, "python_version", lambda: "unqualified-version")
    with pytest.raises(ValueError, match="qualification unavailable or stale"):
        gpu.require_qualified_gpu()
