"""Isolated process limits with explicitly synthetic subprocess commands."""
import json
import subprocess
import sys

import pytest

from flytrap.lab import api
from flytrap.lab.contracts import LabRequest


def service(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'ARTIFACTS', tmp_path)
    instance = api.LabService()
    monkeypatch.setattr(instance, 'prerequisites', lambda: None)
    return instance


def test_actual_child_timeout_releases_model_slot(tmp_path, monkeypatch):
    instance = service(tmp_path, monkeypatch)
    original = subprocess.run
    monkeypatch.setattr(api, 'TIMEOUT_SECONDS', 0.1)
    captured = []

    def slow_child(command, **kwargs):
        try:
            return original([sys.executable, '-c', 'import time; time.sleep(10)'], **kwargs)
        except subprocess.TimeoutExpired as exc:
            captured.append(exc)
            raise

    monkeypatch.setattr(api.subprocess, 'run', slow_child)
    with pytest.raises(api.Unavailable, match='child stopped'):
        instance.compare(LabRequest(schema_version='flytrap-lab-request-1', a=[0]*256, b=[0]*256))
    assert len(captured) == 1
    with instance.slot():
        pass
    assert instance.budget.attempted == 0
    assert len(list((tmp_path/'results').glob('*.request.json'))) == 1


def test_actual_child_failure_preserves_log_and_request(tmp_path, monkeypatch):
    instance = service(tmp_path, monkeypatch)
    original = subprocess.run

    def failed_child(command, **kwargs):
        return original([sys.executable, '-c', 'import sys; print("SYNTHETIC FAILURE"); sys.exit(7)'], **kwargs)

    monkeypatch.setattr(api.subprocess, 'run', failed_child)
    request = LabRequest(schema_version='flytrap-lab-request-1', a=[0]*256, b=[255]*256)
    with pytest.raises(api.Unavailable, match='exit 7'):
        instance.compare(request)
    assert next((tmp_path/'results').glob('*.log')).read_text() == 'SYNTHETIC FAILURE\n'
    assert json.loads(next((tmp_path/'results').glob('*.request.json')).read_text())['request'] == request.model_dump()
    with instance.slot():
        pass
