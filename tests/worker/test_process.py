import os

import pytest

from flytrap.config import Settings
from flytrap.contracts import Observation
from flytrap.worker import create_worker


def test_fixture_boundary_crosses_real_process_and_stops(settings):
    worker = create_worker(settings)
    try:
        worker.start()
        assert worker.alive and worker.pid != os.getpid()
        output = worker.step(Observation(schema_version="1", pixels=[0.0] * 256))
        assert output.model_mode == "fixture"
        assert output.telemetry.sampled_neurons == 0
        assert output.dy == -1.0
    finally:
        worker.close()
    assert not worker.alive
    with pytest.raises(RuntimeError, match="not running"):
        worker.step(Observation(schema_version="1", pixels=[0.0] * 256))


def test_real_worker_never_falls_back():
    with pytest.raises(RuntimeError, match="no fixture fallback"):
        create_worker(Settings())
