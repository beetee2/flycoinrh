"""Fixture process factory. Durable queue/leases/supervision belong to milestone 07."""
import json
import multiprocessing as mp
import os

from flytrap.config import Settings
from flytrap.contracts import ControllerOutput, Observation
from flytrap.controllers.fixture import FixtureController, fixture_checkpoint

MAX_MESSAGE_BYTES = 32_768


def _fixture_process(channel):
    controller = FixtureController()
    controller.reset(run_seed=0, checkpoint=fixture_checkpoint())
    channel.send_bytes(json.dumps({"pid": os.getpid(), "fixture": True}).encode())
    try:
        while True:
            message = channel.recv_bytes(MAX_MESSAGE_BYTES)
            if message == b"stop":
                return
            observation = Observation.model_validate_json(message)
            output = controller.step(observation)
            channel.send_bytes(output.model_dump_json().encode())
    except (EOFError, OSError):
        return
    finally:
        channel.close()


class FixtureWorker:
    def __init__(self):
        self._context = mp.get_context("spawn")
        self._channel = None
        self._process = None

    @property
    def pid(self):
        return self._process.pid if self._process else None

    @property
    def alive(self):
        return self._process is not None and self._process.is_alive()

    def start(self):
        if self._process is not None:
            raise RuntimeError("worker already started")
        self._channel, child = self._context.Pipe(duplex=True)
        self._process = self._context.Process(target=_fixture_process, args=(child,), daemon=True)
        self._process.start()
        child.close()
        try:
            if not self._channel.poll(5):
                raise RuntimeError("fixture worker startup timed out")
            ready = json.loads(self._channel.recv_bytes(MAX_MESSAGE_BYTES))
            if ready != {"pid": self.pid, "fixture": True}:
                raise RuntimeError("invalid worker handshake")
        except BaseException:
            self.close()
            raise

    def step(self, observation: Observation) -> ControllerOutput:
        if not self.alive:
            raise RuntimeError("fixture worker is not running")
        encoded = observation.model_dump_json().encode()
        if len(encoded) > MAX_MESSAGE_BYTES:
            raise ValueError("observation exceeds IPC limit")
        self._channel.send_bytes(encoded)
        if not self._channel.poll(5):
            self.close()
            raise RuntimeError("fixture worker response timed out")
        return ControllerOutput.model_validate_json(self._channel.recv_bytes(MAX_MESSAGE_BYTES))

    def close(self):
        if self._process is not None:
            if self.alive:
                try:
                    self._channel.send_bytes(b"stop")
                except (BrokenPipeError, OSError):
                    pass
                self._process.join(timeout=2)
            if self.alive:
                self._process.terminate()
                self._process.join(timeout=2)
            if self.alive:
                self._process.kill()
                self._process.join(timeout=2)
        if self._channel is not None:
            self._channel.close()


def create_worker(settings: Settings) -> FixtureWorker:
    if settings.profile != "fixture" or settings.production:
        raise RuntimeError("real model worker is not implemented; no fixture fallback")
    return FixtureWorker()
