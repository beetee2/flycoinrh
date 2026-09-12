"""Passive, bounded development capture of the existing pilot's motor rates.

This helper keeps only the most recent sample. It does not add fields to the
controller input/output, change checkpoint source files, call the neural model,
or reconstruct actions. The original pilot receives the original arguments and
its return object is passed through unchanged. Use only around a serial local
development diagnostic, never concurrently on one controller.
"""

import math


MOTOR_POPULATIONS = {
    "steer_L": "DNa02 L",
    "steer_R": "DNa02 R",
    "fwd_L": "DNa01 L",
    "fwd_R": "DNa01 R",
    "back": "MDN",
    "stop": "DNp09",
}


class MotorRateDiagnostic:
    """Temporarily observe ``controller._pilot.step`` without changing actions.

    ``rates`` is a copied mapping in Hz, or None if no valid sample is available.
    Read it immediately after a successful controller step. A failed pilot call
    clears the previous sample; invalid telemetry is reported through ``error``
    without changing the original return value or exception.
    """

    def __init__(self, controller):
        self._pilot = controller._pilot
        self._active = False
        self._rates = None
        self.error = None
        self.calls = 0

    @property
    def rates(self):
        return None if self._rates is None else self._rates.copy()

    def __enter__(self):
        if self._active or getattr(self._pilot.step, "_motor_rate_diagnostic", False):
            raise RuntimeError("motor diagnostic is already active on this pilot")
        original = self._pilot.step
        self._had_instance_step = "step" in vars(self._pilot)
        self._instance_step = vars(self._pilot).get("step")
        self._rates = None
        self.error = None
        self.calls = 0

        def capture(*args, **kwargs):
            self._rates = None
            self.error = None
            self.calls += 1
            try:
                result = original(*args, **kwargs)
            except BaseException as exc:
                self.error = f"pilot raised {type(exc).__name__}"
                raise
            try:
                rates = {key: float(result[3][key]) for key in MOTOR_POPULATIONS}
                if not all(math.isfinite(rate) and rate >= 0 for rate in rates.values()):
                    raise ValueError("motor rates must be finite and nonnegative")
            except (IndexError, KeyError, TypeError, ValueError, OverflowError) as exc:
                self.error = f"invalid motor telemetry: {type(exc).__name__}"
            else:
                self._rates = rates
            return result

        capture._motor_rate_diagnostic = True
        self._pilot.step = capture
        self._active = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._had_instance_step:
            self._pilot.step = self._instance_step
        else:
            del self._pilot.step
        self._active = False
        return False
