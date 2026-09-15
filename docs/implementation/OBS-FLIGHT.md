# OBS03 flight interface — motor-flight-v1

Frozen before implementation, 2026-09-15. This is a human-engineered flight
interface, with no learning or physiological flight claim. The decoder accepts
only typed `MotorRates` plus response/session identity and local timing; it has
no CPU adapter import and receives no pixels, labels, hashes or world targets.
Original raw actions/rates remain available unchanged in the neural sample.

## Mapping

Existing OBS02 safe-source measurements, `real/live-step-{0,1,2}.json`, contain
steering rates 50–450 Hz, forward rates 0–150 Hz, back 0–362.5 Hz and stop
75–100 Hz. These three historical samples justify engineering scales only;
no new model calls, seed selection or parameter search is used here.

Let `D(x,d) = sign(x) * max(abs(x)-d, 0)` and `C(x,a,b)` clamp to [a,b].
Rates are Hz; `F=(fwd_L+fwd_R)/2`, `A=(fwd_L+fwd_R+back)/3`.

- Yaw target rate: `1.2 * C(D(steer_L-steer_R,25)/400,-1,1)` rad/s.
  Positive yaw rotates from +x toward +y in the horizontal plane.
- Pitch target: `0.45 * C(D(F-back,25)/400,-1,1)` radians.
  Positive pitch points toward +z (altitude).
- Speed target: `C(4*max(A-5,0)/150,0,6)` world units/s.
  `back` contributes nonnegative activity to thrust and opposes pitch.
- `stop` and `click` remain raw telemetry and do not enter this flight mapping.
  No offsets balance the historical left bias. Zero mapped output freezes pose.

This bounded activity mapping may produce weak or biased input influence. OBS06
must measure raw rates and trajectory influence; these ranges prove no competence.

## Fixed-step authority and neutral policy

`flight-fixed20-v1`: Python owns state at exactly 20 ms/tick. State contains
position, velocity, yaw, pitch, yaw rate, tick and applied response ID. Targets
are smoothed with `alpha=1-exp(-0.02/0.25)`. Yaw acceleration is at most
3 rad/s² and yaw rate at most 1.2 rad/s. Pitch change is capped at 0.6 rad/s.
Velocity approaches the heading/pitch speed vector with a norm-limited
4 units/s² acceleration. Semi-implicit Euler position uses the new velocity.
Yaw wraps to [-pi,pi]; pitch stays within ±0.45 rad; speed stays within 6 units/s.

A command expires at input receipt + 2,000 ms, never completion + 2,000 ms.
Reject reversed/future timestamps and responses already too old at decode time.
A control applies only at/after its issuance time. Stop, source loss, lease loss,
missing/stale commands or zero mapped targets freeze pose and clear velocity and
yaw rate immediately; this safety stop intentionally overrides acceleration bounds.
There is no coasting, gravity, boundary, rescue, target attraction or random motion.
Coordinator catch-up ticks expire controls by tick time; newly arrived commands
are admitted after catch-up and cannot steer elapsed time retroactively.

Replay records control application ticks, initial full state and decoder/physics
identities. Reapplying the same events gives exact equality on the locked Python
runtime. Browser playback only interpolates Python snapshots; it has no physics
integrator. Float comparisons across runtimes use 1e-9 absolute tolerance for
snapshot interpolation; no cross-runtime physics equivalence is claimed.

## Early presentation

The local explicit synthetic preview contains safe invented motor vectors and
precomputed Python snapshots. It makes zero neural calls and saves no input or
session recording. Loading and playing it require explicit browser actions.
It is prominently labeled SYNTHETIC CONTROL REPLAY. This is the OBS03 visual
review; real source-to-browser wiring remains OBS04/OBS05.

The original procedural fly uses basic geometry. Renderer-only wings, banking,
camera follow and scenery are decorative; the fly root follows authoritative
snapshots. Display coordinates may subtract a nearby grid origin, applied equally
to fly, camera and scenery, without modifying physical state or steering.

## Replay and display details

The in-memory `obs-flight-trace-1` includes initial full state, origin time,
selected controls with application ticks, final tick and `terminal_tick`.
Immediate terminal neutralization overlays that tick's state after its completed
motion interval. This preserves both its final position and zero terminal velocity,
including Stop at tick zero or the 6,000-tick limit. A response selected for an
uncompleted interval is omitted from the exported trace. Serialization preserves
all velocity components; replay imports no neural backend and performs no inference.
Default recording remains off: these controls/ticks are bounded session memory,
not a persisted recording. Durable consented replay storage is OBS04.

The coordinator shortens control lifetime when the session config chooses a
response age below the default 2 seconds. Rate targets are recomputed only for
new accepted responses. Fixed tick smoothing remains independent of poll rate.
The 6,000-tick/120-second flight limit also freezes motion. Safety neutralization
in status reads does not integrate position; the owning session then terminates
or the stale command expires on its clock.

Rendering maps server `(x,y,z)` to `(x,z,-y)`. The fly stays at display origin;
landmarks repeat every 126 units and the grid every 4 units relative to physical
position. Altitude shifts the rendered ground. Camera offset is fixed at
`(-5.9,4,8)` relative to the fly, without camera steering input. The wings rotate
by `±(0.13 + 0.16*sin(0.035*t_ms))` radians using playback time only; pausing,
stopping or hiding the tab freezes decoration as well as travel. There is no
extra banking controller. Resizing redraws the same pose; there is one animation
loop, canceled on pause/unmount. GPU geometry/materials, context and observers
are released on disposal. Context loss disables playback until explicit graphics recreation or reload.
The OBS03 repair adds separate graphics/data readiness, local sanitized errors,
and one attempt per Retry graphics click (three retries per page). Successful
retry redraws the last successful pose and remains paused; only Play resumes.
The decoder, physics and procedural scene remain unchanged. See the
[repair report](milestones/OBS03.md).
