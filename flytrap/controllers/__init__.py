"""Controller interfaces cannot import the arena, queue, or API."""
from typing import Protocol

from flytrap.contracts import CheckpointRef, ControllerOutput, Observation


class Controller(Protocol):
    def reset(self, *, run_seed: int, checkpoint: CheckpointRef) -> None: ...

    def step(self, observation: Observation) -> ControllerOutput: ...
