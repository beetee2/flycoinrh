"""Bounded internal model IPC and typed coordinator snapshots."""
from dataclasses import dataclass
import json
import socket
from typing import Literal

from pydantic import Field

from flytrap.contracts import ControllerOutput
from flytrap.lab.contracts import Statistics
from .contracts import (AnyFlightSnapshot, Contract, Count, Epoch, Id, Millis, MotorRates,
                        NeuralSample, Pixels, RawAction, SessionStatus)

MAX_PACKET = 65536


class StepRequest(Contract):
    kind: Literal["step"] = "step"
    session_id: Id
    generation: Epoch
    step_index: int = Field(ge=0, le=511)
    observation_u8: Pixels


class StepResult(Contract):
    kind: Literal["result"] = "result"
    session_id: Id
    generation: Epoch
    step_index: int = Field(ge=0, le=511)
    completed_monotonic_ms: Millis
    output: ControllerOutput
    motor_rates_hz: MotorRates
    raw_action: RawAction
    statistics: Statistics
    model_file_reads: Count


def send_packet(channel, payload):
    data = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()
    if len(data) > MAX_PACKET:
        raise ValueError("model packet exceeds limit")
    if channel.send(data) != len(data):
        raise OSError("incomplete model packet")


def receive_packet(channel):
    data, _, flags, _ = channel.recvmsg(MAX_PACKET)
    if not data:
        raise EOFError("model channel closed")
    if flags & socket.MSG_TRUNC:
        raise ValueError("model packet exceeds limit")
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError("model packet must be an object")
    return value


@dataclass(frozen=True)
class SessionSnapshot:
    status: SessionStatus
    sample: NeuralSample | None  # Fresh, applicable only while running.
    last_inferred: NeuralSample | None  # Historical input/response, may be stale.
    last_completed: StepResult | None  # Historical measurement, never an active control.
    waiting_for_sample: bool
    completed_calls: int
    rejected_results: int
    neural_ms: float
    model_hz: float
    last_step_wall_ms: float | None
    source_receipt_age_ms: float | None
    model_kind: str
    flight: AnyFlightSnapshot
