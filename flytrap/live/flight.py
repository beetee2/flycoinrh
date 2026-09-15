"""Backend-independent motor decoder and pure fixed-step flight authority.

Equations, coordinate system and safety exceptions: docs/implementation/OBS-FLIGHT.md.
No capture, controller, numerical-model or rendering dependencies belong here.
"""
from math import copysign, cos, exp, hypot, isfinite, pi, sin
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .contracts import (Contract, FlightControls, FlightSnapshot, MotorRates,
                        State, SyntheticFlightPreview)

DT_MS = 20
DT = DT_MS / 1000
PHYSICS_ID = "flight-fixed20-v1"
ALPHA = 1 - exp(-DT / .25)


def clamp(value, lower, upper):
    return min(upper, max(lower, value))


def deadband(value, width):
    return copysign(max(abs(value) - width, 0), value)


def decode(rates: MotorRates, *, response_id: str, session_id: str, generation: int,
           evidence_kind: str, receipt_ms: float, completed_ms: float, now_ms: float,
           max_age_ms: float = 2000.) -> FlightControls:
    """Accept typed rates and timing only. Raw actions remain with the caller."""
    rates = MotorRates.model_validate(rates.model_dump())
    if (not isfinite(max_age_ms) or not 0 < max_age_ms <= 2000
            or not all(isfinite(v) and 0 <= v <= 2**53-1 for v in (receipt_ms, completed_ms, now_ms))
            or not receipt_ms <= completed_ms <= now_ms < receipt_ms + max_age_ms):
        raise ValueError("invalid or stale neural response timing")
    forward = (rates.fwd_L + rates.fwd_R) / 2
    activity = (rates.fwd_L + rates.fwd_R + rates.back) / 3
    return FlightControls(schema_version="obs-controls-1", decoder_id="motor-flight-v1",
        response_id=response_id, session_id=session_id, generation=generation, evidence_kind=evidence_kind,
        issued_monotonic_ms=now_ms, expires_monotonic_ms=receipt_ms + max_age_ms,
        yaw_rate_rad_s=1.2 * clamp(deadband(rates.steer_L-rates.steer_R, 25)/400, -1, 1),
        pitch_target_rad=.45 * clamp(deadband(forward-rates.back, 25)/400, -1, 1),
        speed_target_units_s=clamp(4 * max(activity-5, 0)/150, 0, 6))


class FlightState(Contract):
    physics_id: Literal["flight-fixed20-v1"] = PHYSICS_ID
    snapshot: FlightSnapshot
    velocity: tuple[float, float, float] = (0., 0., 0.)
    yaw_rate: Annotated[float, Field(ge=-1.2, le=1.2)] = 0.

    @field_validator("velocity", mode="before")
    @classmethod
    def json_vector(cls, value):
        # JSON arrays carry this fixed tuple; scalar values remain strictly typed.
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def coherent(self):
        speed = hypot(*self.velocity)
        if (speed > 6 + 1e-12 or abs(speed-self.snapshot.speed_units_s) > 1e-9
                or abs(self.snapshot.pitch_rad) > .45 + 1e-12
                or (self.snapshot.neutral and (speed != 0 or self.yaw_rate != 0))):
            raise ValueError("inconsistent bounded flight state")
        return self


class ControlTick(Contract):
    """Control selected for the interval ending at tick; never a pixel record."""
    tick: Annotated[int, Field(ge=1, le=6000)]
    controls: FlightControls | None
    state: State = "running"


def initial_state(session_id: str, generation: int, evidence_kind: str) -> FlightState:
    return FlightState(snapshot=FlightSnapshot(schema_version="obs-flight-1", session_id=session_id,
        generation=generation, evidence_kind=evidence_kind, tick=0, position=[0., 0., 2.],
        yaw_rad=0., pitch_rad=0., speed_units_s=0., applied_response_id=None, neutral=True))


def neutralize(state: FlightState) -> FlightState:
    return FlightState(snapshot=FlightSnapshot(**{**state.snapshot.model_dump(),
        "speed_units_s": 0., "applied_response_id": None, "neutral": True}))


def advance(state: FlightState, controls: FlightControls | None, *, tick_ms: float,
            session_state: str = "running") -> FlightState:
    """Exactly one 20 ms step. tick_ms is the end of this interval, not browser dt."""
    if not isfinite(tick_ms) or tick_ms < 0:
        raise ValueError("invalid flight tick time")
    s = state.snapshot
    if controls is not None:
        controls = FlightControls.model_validate(controls.model_dump())
        if (controls.session_id, controls.generation, controls.evidence_kind) != (
                s.session_id, s.generation, s.evidence_kind):
            raise ValueError("foreign flight control")
    active = (session_state == "running" and controls is not None
              and controls.issued_monotonic_ms <= tick_ms - DT_MS
              and tick_ms < controls.expires_monotonic_ms
              and any((controls.yaw_rate_rad_s, controls.pitch_target_rad, controls.speed_target_units_s)))
    if not active:
        stopped = neutralize(state)
        return FlightState(snapshot=FlightSnapshot(**{**stopped.snapshot.model_dump(), "tick": s.tick+1}))
    yaw_target = clamp(controls.yaw_rate_rad_s, -1.2, 1.2)
    yaw_rate = state.yaw_rate + clamp(ALPHA*(yaw_target-state.yaw_rate), -3*DT, 3*DT)
    yaw = (s.yaw_rad + yaw_rate*DT + pi) % (2*pi) - pi
    pitch = s.pitch_rad + clamp(ALPHA*(clamp(controls.pitch_target_rad, -.45, .45)-s.pitch_rad),
                               -.6*DT, .6*DT)
    speed = s.speed_units_s + ALPHA*(min(6., controls.speed_target_units_s)-s.speed_units_s)
    target = (cos(yaw)*cos(pitch)*speed, sin(yaw)*cos(pitch)*speed, sin(pitch)*speed)
    delta = tuple(t-v for t, v in zip(target, state.velocity, strict=True))
    factor = min(1., 4*DT/hypot(*delta)) if any(delta) else 1.
    velocity = tuple(v+d*factor for v, d in zip(state.velocity, delta, strict=True))
    position = [p+v*DT for p, v in zip(s.position, velocity, strict=True)]
    snapshot = FlightSnapshot(**{**s.model_dump(), "tick": s.tick+1, "position": position,
        "yaw_rad": yaw, "pitch_rad": pitch, "speed_units_s": hypot(*velocity),
        "neutral": False, "applied_response_id": controls.response_id})
    return FlightState(snapshot=snapshot, velocity=velocity, yaw_rate=yaw_rate)


def replay(initial: FlightState, events: list[ControlTick], *, ticks: int, origin_ms: float,
           terminal_tick: int | None = None) -> list[FlightState]:
    """In-memory deterministic replay; recording/storage consent is a later boundary."""
    if type(ticks) is not int or not 0 <= ticks <= 6000 or initial.snapshot.tick != 0:
        raise ValueError("replay requires tick-zero initial state and bounded duration")
    if not isfinite(origin_ms) or origin_ms < 0:
        raise ValueError("invalid replay origin")
    if terminal_tick is not None and (type(terminal_tick) is not int or not 0 <= terminal_tick <= ticks):
        raise ValueError("invalid terminal tick")
    if any(a.tick >= b.tick for a, b in zip(events, events[1:])) or any(e.tick > ticks for e in events):
        raise ValueError("unordered or out-of-range control application ticks")
    by_tick = {e.tick: e for e in events}
    if terminal_tick is not None and any(e.tick > terminal_tick for e in events):
        raise ValueError("control application after terminal tick")
    states, control, status = [neutralize(initial) if terminal_tick == 0 else initial], None, "running"
    for tick in range(1, ticks+1):
        if tick in by_tick:
            event = by_tick[tick]
            if status != "running" and event.state == "running":
                raise ValueError("terminal flight replay cannot resume")
            control, status = event.controls, event.state
        if terminal_tick is not None and tick > terminal_tick:
            status = "stopped"
        state = advance(states[-1], control, tick_ms=origin_ms+tick*DT_MS, session_state=status)
        states.append(neutralize(state) if tick == terminal_tick else state)
    return states


class FlightTrace(Contract):
    """Bounded in-memory state/control record, with an immediate terminal overlay."""
    schema_version: Literal["obs-flight-trace-1"] = "obs-flight-trace-1"
    decoder_id: Literal["motor-flight-v1"] = "motor-flight-v1"
    initial: FlightState
    origin_ms: Annotated[float, Field(ge=0, le=2**53-1)]
    events: Annotated[list[ControlTick], Field(max_length=512)]
    ticks: Annotated[int, Field(ge=0, le=6000)]
    terminal_tick: Annotated[int, Field(ge=0, le=6000)] | None


class FlightAuthority:
    """Session-owned clock. Poll cadence changes no physics or application time."""
    def __init__(self, session_id: str, generation: int, evidence_kind: str, *, origin_ms: float):
        if not isfinite(origin_ms) or origin_ms < 0:
            raise ValueError("invalid flight origin")
        self.initial = self.current = initial_state(session_id, generation, evidence_kind)
        self.origin_ms = origin_ms
        self.controls = None
        self.events: list[ControlTick] = []
        self.terminal = False
        self.terminal_tick = None
        self._last_now = origin_ms

    def advance_to(self, now_ms: float):
        if not isfinite(now_ms) or now_ms < self._last_now:
            raise ValueError("flight clock must advance monotonically")
        self._last_now = now_ms
        target = min(6000, int((now_ms-self.origin_ms)/DT_MS))
        while self.current.snapshot.tick < target:
            tick = self.current.snapshot.tick+1
            self.current = advance(self.current, self.controls, tick_ms=self.origin_ms+tick*DT_MS,
                                   session_state="stopped" if self.terminal else "running")
        if target == 6000:
            self.stop()
        return self.current.snapshot

    def apply(self, controls: FlightControls, *, now_ms: float):
        # Catch up BEFORE installing a response. It cannot steer elapsed intervals.
        self.advance_to(now_ms)
        if self.terminal:
            return False
        s = self.current.snapshot
        if (controls.session_id, controls.generation, controls.evidence_kind) != (
                s.session_id, s.generation, s.evidence_kind):
            raise ValueError("foreign flight control")
        if not controls.issued_monotonic_ms <= now_ms < controls.expires_monotonic_ms:
            raise ValueError("control is future or expired")
        if self.controls is not None and controls.issued_monotonic_ms <= self.controls.issued_monotonic_ms:
            raise ValueError("duplicate or out-of-order control")
        if len(self.events) >= 512 or s.tick >= 6000:
            raise ValueError("flight application limit reached")
        event = ControlTick(tick=s.tick+1, controls=controls)
        # Multiple responses in one physics interval retain only its final selection.
        if self.events and self.events[-1].tick == event.tick:
            self.events[-1] = event
        else:
            self.events.append(event)
        self.controls = controls
        return True

    def stop(self):
        # Immediate safety neutralization: no catch-up movement after a stop signal.
        if not self.terminal:
            self.terminal_tick = self.current.snapshot.tick
            self.events = [event for event in self.events if event.tick <= self.terminal_tick]
        self.terminal = True
        self.controls = None
        self.current = neutralize(self.current)

    def trace(self) -> FlightTrace:
        # A selected control for the next interval has not yet been applied.
        return FlightTrace(initial=self.initial, origin_ms=self.origin_ms,
            events=[e for e in self.events if e.tick <= self.current.snapshot.tick],
            ticks=self.current.snapshot.tick, terminal_tick=self.terminal_tick)


def synthetic_preview() -> SyntheticFlightPreview:
    """Fixed safe test vectors, not a neural experiment or recording."""
    initial = initial_state("synthetic-flight-preview", 1, "fixture")
    events = []
    for second in range(12):
        rates = MotorRates(steer_L=200. if second < 5 else 50., steer_R=50. if second < 5 else 200.,
                           fwd_L=140., fwd_R=140., back=80., stop=0., click=0.)
        controls = decode(rates, response_id=f"synthetic-{second}", session_id=initial.snapshot.session_id,
            generation=1, evidence_kind="fixture", receipt_ms=float(second*1000),
            completed_ms=float(second*1000), now_ms=float(second*1000))
        events.append(ControlTick(tick=second*50+1, controls=controls))
    states = replay(initial, events, ticks=600, origin_ms=0.)
    return SyntheticFlightPreview(schema_version="obs-flight-preview-1", evidence_kind="synthetic",
                                  dt_ms=20, snapshots=[s.snapshot for s in states])
