"""One frozen, target-free motor readout calibration for the final diagnostic.

The two positive weights balance recorded black-input population means. They
change only the fixed readout, preserve silence and direction signs, and are
never fitted or updated during an episode. No neural model is called here.
"""

import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path

from flytrap.contracts import ControllerOutput
from scripts.feasibility_motor_telemetry import MOTOR_POPULATIONS

MOTOR_VERSION = "dark_balance_v3"
STEER_LEFT_WEIGHT = 782 / 815
BACK_WEIGHT = 730 / 1341
_ROOT = Path(__file__).resolve().parents[1]
_DARK_SOURCES = {
    "artifacts/milestones/05/revision/primary/"
    "tangent_v2-crop16_v1-51001-left-dark/trace.jsonl":
        "390f7d54ad2d6da2a8938bea3d3784847d810acc5a2d243caa1c7e1fc744db21",
    "artifacts/milestones/05/revision/primary/"
    "tangent_v2-crop16_v1-51002-left-dark/trace.jsonl":
        "22989a4e6a624a6c161b7555e3ef2222d4fd9291248e3b46fe387f4e3e96df28",
}


def _checked_rates(rates: dict) -> dict[str, float]:
    if type(rates) is not dict or set(rates) != set(MOTOR_POPULATIONS):
        raise ValueError("motor rates must contain exactly the six diagnostic populations")
    result = {}
    for key, value in rates.items():
        if type(value) not in (int, float):
            raise ValueError("motor rates must be finite nonnegative numbers")
        try:
            converted = float(value)
        except (ValueError, OverflowError) as exc:
            raise ValueError("motor rates must be finite nonnegative numbers") from exc
        if not math.isfinite(converted) or converted < 0:
            raise ValueError("motor rates must be finite nonnegative numbers")
        result[key] = converted
    return result


def calibrate(action: ControllerOutput, rates: dict, version: str) -> ControllerOutput:
    """Apply the selected frozen readout, retaining upstream click and telemetry."""
    if version not in ("upstream_pilot_v1", MOTOR_VERSION):
        raise ValueError("unknown motor mapping version")
    if type(action) is not ControllerOutput:
        raise ValueError("motor calibration requires a ControllerOutput")
    payload = action.model_dump()
    ControllerOutput.model_validate(payload)
    hz = _checked_rates(rates)
    if version == "upstream_pilot_v1":
        return action
    turn = (hz["steer_R"] - STEER_LEFT_WEIGHT * hz["steer_L"]) / 450
    # Divide before addition so all accepted finite rates remain bounded even
    # when their sum would overflow. The recorded rates are exact multiples of Hz.
    forward = hz["fwd_L"] / 2 + hz["fwd_R"] / 2
    speed = max(-1.0, min(1.0, (forward - BACK_WEIGHT * hz["back"]) / 450))
    speed *= 1 - min(1.0, hz["stop"] / 450)
    payload.update(dx=max(-1.0, min(1.0, turn)), dy=-speed)
    return ControllerOutput.model_validate(payload)


def calibration_basis() -> dict:
    """Verify and summarize the 192 existing, unique target-free dark windows."""
    totals = {key: Fraction(0) for key in MOTOR_POPULATIONS}
    windows = 0
    for relative, expected in _DARK_SOURCES.items():
        payload = (_ROOT / relative).read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected:
            raise ValueError(f"calibration source checksum mismatch: {relative}")
        rows = [json.loads(line) for line in payload.splitlines()]
        if len(rows) != 96:
            raise ValueError("each calibration source must contain 96 windows")
        for index, row in enumerate(rows):
            if row["before"]["tick"] != index or row["observation_pixels"] != [0] * 256:
                raise ValueError("calibration requires ordered target-free black windows")
            rates = _checked_rates(row["motor_rates"])
            for key, value in rates.items():
                totals[key] += Fraction(str(value))
            windows += 1
    if windows != 192 or not totals["steer_L"] or not totals["back"]:
        raise ValueError("calibration requires the declared 192 nondegenerate windows")
    steer = totals["steer_R"] / totals["steer_L"]
    back = (totals["fwd_L"] + totals["fwd_R"]) / (2 * totals["back"])
    if (steer != Fraction(782, 815) or back != Fraction(730, 1341)
            or float(steer) != STEER_LEFT_WEIGHT or float(back) != BACK_WEIGHT
            or not 0 < STEER_LEFT_WEIGHT <= 1 or not 0 < BACK_WEIGHT <= 1):
        raise ValueError("recorded rates do not reproduce the frozen motor weights")
    return {
        "source_file_sha256": dict(_DARK_SOURCES),
        "windows": windows,
        "mean_rates_hz": {key: float(value / windows) for key, value in totals.items()},
        "weights": {"steer_left": STEER_LEFT_WEIGHT, "back": BACK_WEIGHT},
        "derivation": {
            "steer_left": "mean(steer_R) / mean(steer_L) = 782/815",
            "back": "mean((fwd_L + fwd_R)/2) / mean(back) = 730/1341",
            "selection": "96 black windows per development seed 51001 and 51002; left layout only",
            "limitation": "Balances pre-stop means; does not guarantee zero final black motion or navigation.",
        },
    }
