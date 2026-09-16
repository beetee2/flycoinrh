# OBS flight interface — motor-flight-v1

## Ground-contact repair after OBS06 human review

Human review requested changes at `3ee5b7247f2e4525bea60cb8fa3e3e260b33db8c`:
v1 has no ground boundary, so descending flight can cross the visible world
plane at z = -4 and leave the spectator camera beneath it. The operator observed
altitude approximately -8.14. The repair preserves that ground location.

New sessions use **`flight-fixed20-ground-v2`**, with `obs-flight-2` snapshots.
The required environment is **`flat-ground-v1`**, `ground_z=-4.0`,
`collision_proxy="fly-clearance-v1"`, `clearance=1.5`. Python's
`GroundEnvironment` contract is the single definition; the renderer uses the
snapshot environment and its generated schema for legacy/empty-scene ground.
The permitted root altitude is therefore **z >= -2.5**. Unknown identities,
inconsistent parameters, incompatible state/snapshot identities and invalid v2
initial states are rejected.

The constant vertical-clearance proxy covers the existing geometry over the
supported yaw range, pitch ±0.45 radians and decorative wing flap range
[-0.03,0.29] radians. The rear leg endpoint at local (-1.12,-1.04,±1.15),
including maximum cylinder radius 0.035, has downward support at most
`1.04*cos(.45)+1.12*sin(.45)+.035 = 1.4586264` units. Body support is smaller;
wing support stays below 1.0 unit after flap and pitch. Yaw does not change
vertical support. Tests inspect the actual mesh vertices over these poses and
the analytic bounds cover the continuous ranges. A constant clearance leaves
a small visible gap at some orientations; this is a documented collision proxy,
not a foot placement or landing animation. Decorative landmarks have no collision.

Each ordinary 20 ms integration step first computes exactly the v1 requested
velocity and straight swept displacement. If its endpoint crosses the permitted
half-space, project only z to -2.5 and set only negative vertical velocity to
zero. This equals swept inelastic contact against a single horizontal plane for
the fixed-step integrator. Horizontal displacement uses the entire interval;
yaw, yaw rate and pitch retain their ordinary values. Speed is recomputed from
the resolved velocity. At the floor, positive vertical velocity leaves normally.
There is no bounce, gravity, added thrust or orientation correction.

The contact impulse is a separate constraint from the normal 4 units/s² motor
acceleration limit. It can remove downward velocity faster than that limit,
never add vertical kinetic energy, and never alter horizontal velocity. The
existing immediate neutralization for Stop, stale/zero controls, source loss and
lease loss still clears velocity/yaw rate and freezes position. Contact itself
is neither terminal nor neutral: requested controls and raw neural samples
retain their original values and response identity. The UI displays **Ground
contact** alongside authoritative pose telemetry.

Linear position interpolation stays inside this convex half-space. Interpolated
pitch remains within the validated clearance range, and fixed camera y = 4
relative to the fly stays at least 5.5 units above the floor. Rendering performs
no pose clamp, ground chase, physical correction or extrapolation.

Historical **`flight-fixed20-v1`** states retain `obs-flight-1`, their original
field shape, original integration and unrestricted altitude. Old manifests,
hashes and initial-state rules remain unchanged, including below-ground paths.
Replay dispatch uses the trace initial state's physics identity; manifest initial
snapshot, trace and final state must agree. New recordings carry the required
environment in their snapshots and use the same physics for verification and
seek. Same-runtime Python replay remains exact; browser interpolation retains
the existing 1e-9 absolute comparison tolerance. This physics identity does not
change the model, checkpoint, encoder, decoder, raw rates or neural provenance.

OBS06's accepted causal results remain measurements of v1. Its frozen diagnostic
explicitly selects v1; none of those trajectory measurements are evidence of v2.
The repair preview is an invented, zero-neural-call descent/contact/departure
sequence computed by v2 and labeled **SYNTHETIC CONTROL REPLAY**.

The following original specification remains historical context.

---

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
