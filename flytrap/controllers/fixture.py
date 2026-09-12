"""Synthetic pixel response for infrastructure tests, never a real-model fallback."""
import hashlib
import random

from flytrap.contracts import CheckpointRef, ControllerOutput, Observation

FIXTURE_SHA256 = hashlib.sha256(b"FLYTRAP fixture controller v1").hexdigest()


def fixture_checkpoint() -> CheckpointRef:
    return CheckpointRef(
        schema_version="1", checkpoint_id="fixture-v1", sha256=FIXTURE_SHA256,
        graph_sha256=FIXTURE_SHA256, model_mode="fixture",
    )


class FixtureController:
    def __init__(self):
        self._rng = None

    def reset(self, *, run_seed: int, checkpoint: CheckpointRef) -> None:
        if type(run_seed) is not int or not 0 <= run_seed <= 2**32 - 1:
            raise ValueError("run_seed must be an unsigned 32-bit integer")
        if checkpoint != fixture_checkpoint():
            raise ValueError("fixture requires its explicit fixture checkpoint")
        self._rng = random.Random(run_seed)

    def step(self, observation: Observation) -> ControllerOutput:
        if self._rng is None:
            raise RuntimeError("reset must precede step")
        # Test-only movement. Zero neural telemetry truthfully identifies no simulation.
        brightness = sum(observation.pixels) / len(observation.pixels)
        return ControllerOutput(
            schema_version="1", dx=self._rng.uniform(-1.0, 1.0),
            dy=brightness * 2.0 - 1.0, click=False, model_mode="fixture",
            telemetry={"schema_version": "1", "sampled_neurons": 0, "spike_count": 0, "neural_ms": 0.0},
        )
