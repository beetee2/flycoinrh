"""two_choice_v1: pure, quantized point motion with exact swept intersections.

Scoring stays outside Scene and outside the controller's observation envelope.
Coordinates are integer multiples of 1/256 pixel; positive y points down.
"""

from dataclasses import dataclass, replace
from fractions import Fraction
import math
import random
from typing import Literal

from flytrap.contracts import ChallengeSpec, ControllerOutput, create_challenge, verify_challenge_hash

Q = 256
MOVEMENT_PER_TICK = 8
MAX_TICKS = 256
MIN_COORD = 4
MAX_COORD = 92
Texture = Literal["stripes", "checkerboard"]
Side = Literal["left", "right"]
Outcome = Literal["success", "wrong_pad", "trial_timeout"]
TEXTURES = ("stripes", "checkerboard")
DISTRACTIONS = ("top", "middle", "bottom")


@dataclass(frozen=True)
class Rect:
    x0: int
    y0: int
    x1: int
    y1: int

    def __post_init__(self):
        if any(type(v) is not int for v in (self.x0, self.y0, self.x1, self.y1)):
            raise ValueError("Rectangle coordinates must be integers")
        if not (0 <= self.x0 < self.x1 <= 96 and 0 <= self.y0 < self.y1 <= 96):
            raise ValueError("Invalid bounded rectangle")

    def contains(self, x_q: int, y_q: int, *, interior: bool = False) -> bool:
        if interior:
            return self.x0 * Q < x_q < self.x1 * Q and self.y0 * Q < y_q < self.y1 * Q
        return self.x0 * Q <= x_q <= self.x1 * Q and self.y0 * Q <= y_q <= self.y1 * Q


LEFT_PAD = Rect(12, 12, 36, 28)
RIGHT_PAD = Rect(60, 12, 84, 28)
OBSTACLES = (Rect(44, 36, 52, 40), Rect(44, 48, 52, 52), Rect(44, 60, 52, 64))


@dataclass(frozen=True)
class Scene:
    left_texture: Texture
    right_texture: Texture
    obstacles: tuple[Rect, ...] = ()
    width: int = 96
    height: int = 96
    left_pad: Rect = LEFT_PAD
    right_pad: Rect = RIGHT_PAD

    def __post_init__(self):
        if type(self.width) is not int or type(self.height) is not int or (self.width, self.height) != (96, 96):
            raise ValueError("two_choice_v1 is exactly 96 by 96")
        if (type(self.left_pad) is not Rect or type(self.right_pad) is not Rect
                or self.left_pad != LEFT_PAD or self.right_pad != RIGHT_PAD):
            raise ValueError("Only fixed nonoverlapping reachable pads are legal")
        if (self.left_texture not in TEXTURES or self.right_texture not in TEXTURES
                or self.left_texture == self.right_texture):
            raise ValueError("Two distinct approved textures are required")
        if type(self.obstacles) is not tuple or any(type(r) is not Rect or r not in OBSTACLES for r in self.obstacles):
            raise ValueError("Only approved distraction obstacles are legal")
        if tuple(r for r in OBSTACLES if r in self.obstacles) != self.obstacles:
            raise ValueError("Distractions must be unique and in top/middle/bottom order")
        # The only accepted geometry leaves clear horizontal corridors at y=76
        # and vertical corridors at x=24 and x=72, each reaching one pad. All
        # geometry is >=8 pixels from the outer wall and each other pad. There is
        # no arbitrary geometry route that could bypass these reachability facts.


@dataclass(frozen=True)
class Arena:
    scene: Scene
    target_side: Side
    challenge_sha256: str
    target_texture: Texture

    def __post_init__(self):
        if type(self.scene) is not Scene:
            raise ValueError("Expected an exact Scene")
        replace(self.scene)
        if self.target_side not in ("left", "right") or self.target_texture not in TEXTURES:
            raise ValueError("Unknown scoring rule")
        if getattr(self.scene, self.target_side + "_texture") != self.target_texture:
            raise ValueError("Destination does not match the cohort's fixed cue mapping")
        if (type(self.challenge_sha256) is not str or len(self.challenge_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.challenge_sha256)):
            raise ValueError("Invalid challenge digest")


@dataclass(frozen=True)
class State:
    x_q: int
    y_q: int
    tick: int = 0
    outcome: Outcome | None = None

    def __post_init__(self):
        if any(type(v) is not int for v in (self.x_q, self.y_q, self.tick)):
            raise ValueError("State coordinates and tick must be integers")
        if not (MIN_COORD * Q <= self.x_q <= MAX_COORD * Q and MIN_COORD * Q <= self.y_q <= MAX_COORD * Q):
            raise ValueError("State lies outside the arena walls")
        if not 0 <= self.tick <= MAX_TICKS:
            raise ValueError("Invalid environment tick")
        if self.outcome not in (None, "success", "wrong_pad", "trial_timeout"):
            raise ValueError("Invalid arena outcome")
        if self.outcome == "trial_timeout" and self.tick != MAX_TICKS:
            raise ValueError("A trial timeout requires the tick limit")
        if self.outcome is None and self.tick == MAX_TICKS:
            raise ValueError("Tick limit must be terminal")
        if self.outcome is not None and self.tick == 0:
            raise ValueError("Initial state cannot be terminal")


def initial_state() -> State:
    return State(48 * Q, 76 * Q)


def build_arena(challenge: ChallengeSpec, *, target_texture: Texture = "stripes") -> Arena:
    """Validate wire content and the explicit cohort rule before simulation."""
    if type(challenge) is not ChallengeSpec:
        raise ValueError("Expected an exact ChallengeSpec")
    checked = ChallengeSpec.model_validate(challenge.model_dump())
    verify_challenge_hash(checked)
    if checked.distractions != [d for d in DISTRACTIONS if d in checked.distractions]:
        raise ValueError("Distractions must be unique and canonically ordered")
    scene = Scene(checked.left_texture, checked.right_texture,
                  tuple(OBSTACLES[DISTRACTIONS.index(d)] for d in checked.distractions))
    return Arena(scene, checked.destination_side, checked.content_sha256, target_texture)


def generate_challenge(*, seed: int, target_texture: Texture = "stripes", distraction_count: int = 0) -> ChallengeSpec:
    """Development preset generation; this seed never feeds the controller.

    Evaluation cohorts must explicitly enumerate and counterbalance both sides;
    random sampling alone does not guarantee equal side counts.
    """
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("seed must be an unsigned 32-bit integer")
    if target_texture not in TEXTURES:
        raise ValueError("Unknown target texture")
    if type(distraction_count) is not int or not 0 <= distraction_count <= 3:
        raise ValueError("distraction_count must be between zero and three")
    rng = random.Random(seed)
    side = rng.choice(("left", "right"))
    other = next(t for t in TEXTURES if t != target_texture)
    selected = rng.sample(DISTRACTIONS, distraction_count)
    return create_challenge(dict(
        schema_version="1", preset_version="two_choice_v1", renderer_version="grayscale_v1",
        destination_side=side, left_texture=target_texture if side == "left" else other,
        right_texture=target_texture if side == "right" else other,
        distractions=[d for d in DISTRACTIONS if d in selected],
    ))


def segment_entry(start: tuple[int, int], end: tuple[int, int], rect: Rect, *, interior: bool = False) -> Fraction | None:
    """Exact slab intersection of a q-coordinate segment and pixel rectangle.

    Closed pads count tangency. Obstacles block only entry into their open
    interior, allowing motion along a contacted edge or away from it.
    """
    if (type(start) is not tuple or type(end) is not tuple or len(start) != 2 or len(end) != 2
            or any(type(v) is not int for v in (*start, *end)) or type(rect) is not Rect
            or type(interior) is not bool):
        raise ValueError("Invalid segment geometry")
    replace(rect)
    entry, leave = Fraction(0), Fraction(1)
    for a, b, low, high in zip(start, end, (rect.x0 * Q, rect.y0 * Q), (rect.x1 * Q, rect.y1 * Q)):
        delta = b - a
        if delta == 0:
            if not (low < a < high if interior else low <= a <= high):
                return None
        else:
            t0, t1 = sorted((Fraction(low - a, delta), Fraction(high - a, delta)))
            entry, leave = max(entry, t0), min(leave, t1)
            if entry > leave:
                return None
    if interior and entry >= leave:
        return None
    return entry


def step(arena: Arena, state: State, action: ControllerOutput) -> State:
    """Apply one action, stopping both axes at the first swept contact.

    No wall clock, controller, random source or neural time enters physics.
    Ties: solid boundary before pad; left pad before right; pad before timeout.
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
    delta = (math.trunc(action.dx * MOVEMENT_PER_TICK * Q), math.trunc(action.dy * MOVEMENT_PER_TICK * Q))
    end = (start[0] + delta[0], start[1] + delta[1])
    # Events compare rational time first. Second/third fields freeze tie policy.
    events: list[tuple[Fraction, int, int, str | None]] = []
    for a, d in zip(start, delta):
        if d > 0 and a + d >= MAX_COORD * Q:
            events.append((Fraction(MAX_COORD * Q - a, d), 0, 0, None))
        elif d < 0 and a + d <= MIN_COORD * Q:
            events.append((Fraction(MIN_COORD * Q - a, d), 0, 0, None))
    for rect in arena.scene.obstacles:
        entry = segment_entry(start, end, rect, interior=True)
        if entry is not None:
            events.append((entry, 0, 0, None))
    for index, (side, pad) in enumerate((("left", arena.scene.left_pad), ("right", arena.scene.right_pad))):
        entry = segment_entry(start, end, pad)
        if entry is not None:
            result = "success" if side == arena.target_side else "wrong_pad"
            events.append((entry, 1, index, result))
    time, _, _, outcome = min(events) if events else (Fraction(1), 2, 0, None)
    # Quantize toward the previous position, never through the contacted solid.
    x_q, y_q = (a + math.trunc(d * time) for a, d in zip(start, delta))
    tick = state.tick + 1
    if outcome is None and tick == MAX_TICKS:
        outcome = "trial_timeout"
    return State(x_q, y_q, tick, outcome)
