# OBS06 ground-contact repair — return for human review

2026-09-15 (US/Central). Focused repair of the final human review defect at
`3ee5b7247f2e4525bea60cb8fa3e3e260b33db8c`. Initial checkout was clean at that
revision. Changes remain local and uncommitted. Evidence is under ignored
`artifacts/milestones/OBS06-ground/`. The original [OBS06 report](OBS06.md) and
its accepted technical/causal results remain historical evidence.

## Defect and resolution

Human review is **CHANGES_REQUESTED**: v1 can descend through the visible ground
and take the spectator camera beneath it. The operator reported altitude about
-8.14; a read of the already-terminal manual session found altitude -12.8847.
That status read did not capture or infer. Product approval remains withheld
until the operator reviews this repair.

New sessions use **flight-fixed20-ground-v2**, **obs-flight-2** snapshots and the
required **flat-ground-v1** environment. The original floor remains at world
z=-4. Python's strict `GroundEnvironment` contract supplies the ground and
`fly-clearance-v1` clearance of **1.5**; generated schema supplies the renderer's
legacy/empty-scene ground definition. New root altitude must be **>= -2.5**.
See [OBS-FLIGHT](../OBS-FLIGHT.md) for the equations and proxy justification.

The original decoder and free-flight integration compute each requested step.
Single-plane projection resolves a crossing within that tick, preserves full
horizontal displacement and turning, and removes only inward vertical velocity.
Reported speed uses the resolved velocity. The inelastic collision impulse is
separate from the ordinary acceleration limit. Upward commands depart normally;
contact supplies no bounce, upward thrust, pitch correction or steering.
Stop, stale/zero input, source loss and lease loss retain immediate neutralization.
Ground contact has a small explicit UI indicator and does not mark a session
failed, stopped or neurally silent. Raw controls/rates remain separate.

The clearance is conservative over supported pitch ±0.45, arbitrary yaw and
all decorative flap phases. Leg support is bounded by **1.4586264**, leaving
**0.0413736** units of margin. Body and wing bounds are smaller. Actual mesh
vertices are tested over 80 orientation/decoration combinations; analytic bounds
cover the continuous ranges. The constant proxy leaves a gap at some poses.
There is no landing animation or landmark collision. The fixed camera remains
at least **5.5** units above the plane for v2. Linear interpolation stays in the
legal half-space, without a display-only clamp or a moving world floor.

## Replay and provenance

Old **flight-fixed20-v1** dispatch, `obs-flight-1` fields, initial-state rules and
manifest hashing remain unchanged. A sealed synthetic fixture was generated
directly with the reviewed revision's original algorithm, clearly labeled with
fabricated neural metadata. Its original below-ground final altitude
**-27.02247197** and sealed file hashes remain unchanged through read/replay/seek.
The pre-existing browser fixture is also byte-for-byte unchanged.

New manifests carry the required physics/environment in initial snapshots;
trace, final state and manifest must agree. Strict schemas and generated
TypeScript validators reject unknown or inconsistent identities/parameters.
AJV treats Pydantic's discriminator as an annotation and validates every `oneOf`
branch normally; no version validation is bypassed. Live authority, JSON
serialization, replay and all 601 seeks in the 12-second recording test match
exactly in the locked Python runtime. Browser interpolation retains its 1e-9
absolute comparison guarantee.

The existing safe actual-model recording `8d4d624e6f4a4d3f8a9a7dbdc26d3d62`
also replays exactly under v1, with all original bytes preserved. A separate
120-second **replay of its two saved safe neural responses under new physics**
uses 120 synthetic timestamp refreshes and zero model calls. It repeats exactly;
these upward-biased responses do not contact the floor (minimum z=2, final
z=15.83072574). This is not a new neural observation or an OBS06 measurement.

OBS06 causal results remain measurements of v1; its frozen diagnostic explicitly
selects v1. Model/checkpoint, CPU execution, neural provenance, encoder, decoder,
raw rates, timestep, learning state, usage ledgers and consent remain preserved.

## Executed checks

All passing suites below have zero failures, errors and skips. Full commands,
exits and logs are in `commands.jsonl`, `physics/command.json`,
`recording-regression-final.json`, and the named renderer logs.

| Check | Actual result / evidence |
|---|---|
| Focused flight/property/ground | 148 PASS; `physics/pytest.xml` |
| Recording and ground recording regression | 65 PASS; `recording-regression-final.log` |
| 120-second synthetic descent, refreshed every 20 ms | v1 min **-201.6504886**, v2 min **-2.5**, **5,843** v2 contact ticks; `saved-response-reuse.json` |
| Swept high-speed/within-tick contact, horizontal turning, upward departure, no added energy/steering, neutral policies, exact free flight | PASS; `tests/live/test_ground.py`, focused and broad suite logs |
| Actual HTTP replay/list/download/seek, v1 and v2, subprocesses forbidden | PASS; `tests/live/test_ground_recording.py` |
| UI/contracts/geometry | 242 PASS; `renderer/ui-02.xml`, `renderer/geometry-bound.json` |
| Actual HTTP/browser descent/contact/departure/Pause/Stop, desktop and mobile | 2 PASS; `renderer/browser-01/report.json`, six inspected screenshots and interpolated-frame attachments; zero non-GET requests |
| No-source local preview guard | PASS; `preview-guard-03.log`; valid Start/Preview requests receive unavailable-source 503, no subprocesses or ledgers |
| `make verify test-upstream EVIDENCE=artifacts/milestones/OBS06-ground/foundation-confirmed` | Exit **0**: **3,031 Python**, **150 upstream**, **89 web contracts**, **9 UI**, **2 fixture browsers**; schema drift, lint, package/web builds and dependencies PASS; `foundation-03.log` |
| `make verify-live LIVE_EVIDENCE=artifacts/milestones/OBS06-ground/live-final` | Exit **0**: **649 live Python**, **242 live UI/contracts**, **124 lab Python**, **15 lab UI**, **2 lab + 20 live fixture browsers**; generated schemas/types, lint and build PASS; `verify-live-final.log` |

The parent opened all six descent/contact/departure captures. The complete fly,
legs and wings remain framed at desktop/mobile sizes, with the camera above the
ground during contact and departure. Decorative cones can overlap the fly; they
remain outside this repair's collision scope. Screenshots are synthetic scene
renders, not desktop or OBS source captures.

Development evidence is retained. Initial broad runs found two old assertions
expecting default v1 in new authorities (611 live / 2 failures; 2,993 repository /
2 failures). The new identity assertion was corrected; historical v1 tests remain.
Initial UI compilation failed on AJV's unrecognized discriminator annotation
(five failed suites, nine passing tests); the annotation registration repaired
it while preserving full branch validation. The preview guard was strengthened
from malformed requests to valid requests, then corrected its expected rejection
from 404 to the service's existing 503. One repository command's tool session
reported exit 143 despite complete passing constituent logs; a fresh aggregate
was run to obtain an unambiguous command result.

Evidence-preservation limitation: an initial delegated Vitest command omitted
`VITEST_JUNIT_PATH` and wrote the repository's default ignored
`artifacts/milestones/01/ui-junit.xml`. Its previous contents were not snapshotted
and may have been overwritten. The failure log is preserved in this repair's
directory; subsequent commands use isolated evidence paths. Original OBS06
causal evidence, ledgers, recordings and protected model files are separately
hash-checked. No claim is made that the older default JUnit file was preserved.

## Hosted result and review handoff

The reviewed revision's [hosted workflow 35005380470](https://github.com/beetee2/flycoinrh/actions/runs/35005380470)
finished **FAILURE**, updated 2026-09-15 18:12:08 UTC. Foundation checks passed;
the live browser suite had **16 passes and 2 mobile failures**: a 409 resource
console error in the private replay journey, and reload yielding `failed` where
the test expected `stopped`. `hosted-workflow.json` and `hosted-failed.log`
preserve the actual result. This ground repair makes no hosted-pass claim and
does not modify or dispatch the remote workflow.

Local synthetic preview: **http://127.0.0.1:8769/live**. Choose **Load synthetic
preview**, then **Play synthetic preview**. It descends, contacts at 2.64 seconds,
continues horizontal turning, and departs after the upward command at 8 seconds
(last contact snapshot at 8.74 seconds). Pause/Stop freeze; Reset returns to the
initial pose. This server offers no capture/inference sources. To restart it:
`.venv/bin/python -m scripts.live_ground_preview --port 8769`.

The previous manual service process had already exited when its restart was
checked. A fresh service was started with the same human-purpose command on
**http://127.0.0.1:8767/live**; HTTP confirms no current session, OBS recording
disabled, and a v2 preview. No historical terminal pose was clamped or migrated.

Capture and inference remain stopped; OBS recording remains disabled. Automated
accounting remains **219/1,024**, **805 remaining**, with P00 **144** unchanged.
No full-connectome calls, desktop capture, allowance reset, GPU/learning work,
host/browser changes, commit, push, merge or deployment is part of this repair.
Final product approval remains **CHANGES_REQUESTED / awaiting human re-review**.

**implementation_status: PASS.** Original OBS06 real_model_status,
real_obs_status and causal_validation_status remain accepted as recorded; those
gates were **not rerun** in this zero-call repair. **human_review: PENDING** for
this repair, with the prior CHANGES_REQUESTED decision preserved.


## Operator confirmation during SG01 authorization

2026-09-15: the operator explicitly confirms ground contact works at the supplied
last-reviewed revision `e08dad056077db96d825fb7c4a950833f7e141ac`. This is operator
confirmation, not a new agent-executed real-OBS check. The original repair evidence
and CHANGES_REQUESTED history remain intact. Overall product approval is still
pending. SG01 separately authorizes the Screen Gremlin presentation candidate;
see [SG01](SG01.md).
