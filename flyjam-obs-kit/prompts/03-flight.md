# OBS03 — neural flight decoder and an early third-person fly

Read `flyjam-obs-kit/SPEC.md`, `flyjam-obs-kit/TEST_MATRIX.md`, applicable
`AGENTS.md`, actual git status, `docs/implementation/OBS-STATUS.md` if present,
and the latest relevant milestone report. Read the relevant implementation before
editing. Perform the actual work, run appropriate tests, and update the handoff.
Preserve user changes and existing evidence. Execute only this milestone.

Deliver visible movement without changing the neural model.

1. Define one explicit decoder version mapping raw motor-rate channels to yaw,
   pitch and thrust/speed targets. Write the formula, scales, deadbands, smoothing,
   units and caps first. Use a simple fixed mapping justified from existing
   recorded ranges, not a new parameter search. Preserve raw upstream actions.
   No direct source/image/hash/text access. Zero rates must produce neutral motion.
   This mapping is a human-engineered interface, not learned flight physiology.

2. Implement pure fixed-time-step flight physics and authoritative FlightState:
   orientation, position, velocity and sequence/tick. Bound acceleration/rotation;
   handle stale controls, Stop and source loss as SPEC requires. Keep control
   application ticks in the record. No arena goal/wall logic or invisible rescue.
   Use an open/repeating visual space and document any display-only rebasing.

3. Add a minimal third-person browser stage now. Prefer original procedural fly
   geometry with recognizable head/body/eyes/legs/wings and a simple scene that
   makes translation and turns visible. Use locally bundled assets/dependencies.
   Consume typed server/replay snapshots; frontend frame rate is not authoritative
   physics time. A clearly labeled synthetic control sequence may drive this
   early development preview and must never be labeled actual neural behavior.

4. Keep decorative wing cycles, bank animation and camera follow distinct from
   substantive neural movement. Stop must not leave the fly autonomously traveling.
   Do not replace absent neural output with random motion or a successful scripted
   performance. Provide renderer cleanup, reset and unavailable-WebGL behavior.

Validation: known rate-vector signs/bounds, nonfinite/missing schema rejection,
zero/saturated/constant controls, dt/replay invariance, delayed controls and
terminal states, neutralization, display-rebasing invariance, render-loop cleanup
and an actual browser smoke test. Record and open a screenshot or short local
capture of the recognizable fly. Hardware/model absence does not prevent this
explicitly synthetic presentation check.

Handoff: show the preview and the fixed mapping. Flag appearance/motion questions
for the human without pretending the real source is integrated. Continue toward
OBS04 when instructed; do not start an additional model experiment. Stop.
