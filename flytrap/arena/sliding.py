"""Development tangent_v2 physics; v1 remains the default in arena.core.

The requested quantized velocity is unchanged until swept contact. Only its
blocked normal components are removed for the remainder of that tick. There is
no speed renormalization, restoration of removed components, or target input.
"""

from dataclasses import replace
from fractions import Fraction
import math

from flytrap.arena.core import (
    Arena, MAX_COORD, MAX_TICKS, MIN_COORD, MOVEMENT_PER_TICK, Q, State,
)
from flytrap.contracts import ControllerOutput

PHYSICS_VERSION = "tangent_v2"


def _entry(start, delta, rect, *, interior=False):
    """Exact slab sweep, including the normal axes at entry into a solid."""
    entry, leave = Fraction(0), Fraction(1)
    for a, d, low, high in zip(start, delta, (rect.x0 * Q, rect.y0 * Q),
                               (rect.x1 * Q, rect.y1 * Q)):
        if d == 0:
            if not (low < a < high if interior else low <= a <= high):
                return None
        else:
            t0, t1 = sorted(((low - a) / d, (high - a) / d))
            entry, leave = max(entry, t0), min(leave, t1)
            if entry > leave:
                return None
    if interior and entry >= leave:
        return None
    normals = frozenset(
        axis for axis, (a, d, low, high) in enumerate(zip(
            start, delta, (rect.x0 * Q, rect.y0 * Q), (rect.x1 * Q, rect.y1 * Q),
        )) if (d > 0 and a + d * entry == low) or (d < 0 and a + d * entry == high)
    )
    return entry, normals


def _sweep(arena, start, delta):
    """Return exact piecewise path and terminal outcome for one bounded tick.

    The path is retained internally so tests can check every swept leg for
    penetration. At most two axes can be removed, followed by one free leg.
    """
    position = tuple(Fraction(a) for a in start)
    remaining = tuple(Fraction(d) for d in delta)
    path = [position]
    outcome = None
    for _ in range(3):
        events = []
        for axis, (a, d) in enumerate(zip(position, remaining)):
            if d > 0 and a + d >= MAX_COORD * Q:
                events.append(((MAX_COORD * Q - a) / d, 0, 0, None, frozenset({axis})))
            elif d < 0 and a + d <= MIN_COORD * Q:
                events.append(((MIN_COORD * Q - a) / d, 0, 0, None, frozenset({axis})))
        for rect in arena.scene.obstacles:
            hit = _entry(position, remaining, rect, interior=True)
            if hit is not None:
                events.append((hit[0], 0, 0, None, hit[1]))
        for index, (side, pad) in enumerate((("left", arena.scene.left_pad),
                                            ("right", arena.scene.right_pad))):
            hit = _entry(position, remaining, pad)
            if hit is not None:
                result = "success" if side == arena.target_side else "wrong_pad"
                events.append((hit[0], 1, index, result, frozenset()))
        event = min(events, key=lambda e: e[:3]) if events else (Fraction(1), 2, 0, None, frozenset())
        time, priority, _, outcome, _ = event
        position = tuple(a + d * time for a, d in zip(position, remaining))
        path.append(position)
        if priority != 0:
            break
        # Resolve all simultaneous solid normals uniformly. At a corner both
        # inward axes stop; an axis tangent to a contacted edge stays legal.
        blocked = frozenset().union(*(e[4] for e in events if e[0] == time and e[1] == 0))
        if not blocked:
            raise RuntimeError("Solid contact has no blocking normal")
        remaining = tuple(Fraction(0) if axis in blocked else d * (1 - time)
                          for axis, d in enumerate(remaining))
        if not any(remaining):
            break
    else:
        raise RuntimeError("Bounded sliding sweep exhausted its axis budget")
    return path, outcome


def step_sliding(arena: Arena, state: State, action: ControllerOutput) -> State:
    """Apply tangent_v2 explicitly, with v1 bounds, scoring and quantization.

    Solid contacts precede pads at equal time; left pad precedes right pad;
    pad outcomes precede timeout. Positive y still points down. Removed axes
    stay removed until the next action, even after passing an obstacle corner.
    """
    if type(arena) is not Arena or type(state) is not State or type(action) is not ControllerOutput:
        raise ValueError("Expected exact arena, state and controller output types")
    replace(arena)
    replace(state)
    action = ControllerOutput.model_validate(action.model_dump())
    if state.outcome is not None:
        raise ValueError("Cannot step a terminal state")
    if any(r.contains(state.x_q, state.y_q, interior=True) for r in arena.scene.obstacles):
        raise ValueError("State lies inside an obstacle")
    if any(r.contains(state.x_q, state.y_q) for r in (arena.scene.left_pad, arena.scene.right_pad)):
        raise ValueError("Active state already touches a terminal pad")
    start = (state.x_q, state.y_q)
    delta = tuple(math.trunc(d * MOVEMENT_PER_TICK * Q) for d in (action.dx, action.dy))
    path, outcome = _sweep(arena, start, delta)
    # One final quantization toward the original position avoids losing legal
    # tangential motion at intermediate rational contacts.
    x_q, y_q = (a + math.trunc(b - a) for a, b in zip(start, path[-1]))
    tick = state.tick + 1
    if outcome is None and tick == MAX_TICKS:
        outcome = "trial_timeout"
    return State(x_q, y_q, tick, outcome)
