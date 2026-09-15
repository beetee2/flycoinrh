# OBS03 — authoritative flight and early third-person preview

2026-09-15. **Implementation PASS / COMPLETE** after the checks recorded below.
Starting worktree was clean at `7c35af0299d918f6294e2ba64452ec89108372d8`.
The first saved file-hash record followed the frontend dependency installation;
its two package-file changes were this milestone's concurrent work, not user edits.
Only OBS03 was executed. Changes remain local and uncommitted.

## Upstream disposition and model boundary

Read the [upstream review](../OBS-UPSTREAM-REVIEW.md) and
[fixed mapping/physics specification](../OBS-FLIGHT.md).
The review records the fork/upstream/common-ancestor identities, inspected patches,
GPU result-contract gap and deferred learning/reset/sensory changes. Hosted run
[34982619140](https://github.com/beetee2/flycoinrh/actions/runs/34982619140)
was freshly verified completed/success for the reviewed fork commit; the old
pending prerequisite is resolved. This does not certify the new local OBS03 work.

CPU `windowed_reset`, 100 × 0.2 ms, all-one gains, learning disabled, checkpoint
and seed progression are preserved. No GPU backend was installed or activated.
No upstream files were merged or adapted. All 20 checked protected identities,
including graph, model, checkpoint, notices and accounting, match their recorded
baseline; see `artifacts/milestones/OBS03/protected-check.json`.
OBS accounting stays **9 / 1,024**, **1,015 remaining**; P00 stays **144 attempts**.
This milestone performed **zero additional full-model calls**.

## Flight implementation

`flytrap/live/flight.py` imports typed contracts and standard Python mathematics,
with no CPU model/adapter dependency. It accepts `MotorRates` plus response/session
identity and timing; raw actions and rates remain in the original neural sample.
The mapping was written before implementation, using the three existing OBS02
safe-source recorded ranges, without a parameter search or new experiment.

For `D(x,d)=sign(x)*max(abs(x)-d,0)` and clamp `C`, rates in Hz:

- Yaw: `1.2*C(D(steer_L-steer_R,25)/400,-1,1)` rad/s.
- Pitch: `0.45*C(D((fwd_L+fwd_R)/2-back,25)/400,-1,1)` rad.
- Speed: `C(4*max((fwd_L+fwd_R+back)/3-5,0)/150,0,6)` units/s.
- Stop/click channels remain raw telemetry. This is an engineered interface;
  no learned flight physiology or responsiveness claim follows from it.

Python advances full position/velocity/orientation at **20 ms/tick**, with a
0.25-second target smoothing constant, 4 units/s² vector acceleration cap,
3 rad/s² yaw acceleration cap, 1.2 rad/s yaw and 0.6 rad/s pitch-rate caps.
The session owns this clock; browser render timing never drives physics.
Receipt-based expiry, missing commands, silence and terminal states freeze pose
and clear velocity. Safety stops intentionally override acceleration bounds.
New responses are installed after catch-up and never steer elapsed intervals.

The bounded in-memory trace contains initial full state, origin, applied controls
and ticks, final tick and immediate terminal tick. Replay reproduces final full
state exactly, including terminal velocity, without inference. JSON roundtrip,
unknown-version rejection and differing polling cadences are tested. This is the
flight replay foundation; consented durable session storage remains OBS04.

Actual synthetic subprocess integration checks typed worker outputs through the
session decoder into moving flight, raw-action preservation, explicit Stop,
producer loss and lease expiry, then exact terminal replay. Stale results remain
historical and produce no flight event. Recording remains disabled.

## Early visual preview

Open `http://127.0.0.1:8767/live`, then **Load synthetic preview** and
**Play synthetic preview**. The maintained launch command is `make serve-live`. The idle local service was
left running on port 8767; HTTP 200 and its 205,855-byte synthetic payload were
verified in `local-service-check.json`.
The page starts idle. `GET /api/live/flight-preview` supplies 601 bounded,
strictly validated Python snapshots of a fixed synthetic sequence. It opens no
capture/model process and writes no session data. The page prominently says
**SYNTHETIC CONTROL REPLAY**; real source-to-browser wiring remains OBS04/OBS05.

The original procedural fly has head, thorax, abdomen, eyes, six legs and two
veined wings. Repeating landmarks and a following camera provide visible motion.
Display-only rebasing leaves authoritative position unchanged. Wings follow
playback time only; Pause/Stop/hidden-tab freeze it. Reset returns to the first
pose. Unmount releases the single animation loop, observer, GPU resources and
canvas; missing/lost WebGL disables playback with a visible explanation.

One local rendering dependency, **three 0.186.0**, is pinned in package/lock files,
with **@types/three 0.186.0** for development. Geometry is original; no upstream
`backrooms.html` code or assets were used. The three.js MIT notice is copied from
the installed package into `web/src/live/three-LICENSE.txt`, emitted as a local
asset and linked in the UI. LICENSE, NOTICE and data attribution are unchanged.
The stage loads separately so `/lab` does not load the rendering dependency.
Vite reports a 546 kB stage-chunk advisory; build and dependency audit pass.

Opened both desktop and mobile browser captures. The body/head, copper eyes,
legs and translucent veined wings are recognizable; scenery gives depth and
parallax. Mobile controls and the synthetic label fit without horizontal overflow.
These are implementation observations. **Human appearance/motion/framing review
remains PENDING**; no approval is inferred on the operator's behalf.

## Actual validation and evidence

Evidence root: ignored `artifacts/milestones/OBS03/`. Final command records include
exact argv, cwd, exit and elapsed time; XML/browser reports contain actual counts.
Counts overlap and must not be summed as unique tests. All final suites have zero
failures, errors and skips.

| Command | Actual result |
|---|---|
| `make verify test-upstream EVIDENCE=artifacts/milestones/OBS03/final/foundation` | Exit 0; **2,855 Python**, **150 upstream**, **89 web contracts**, **9 UI**, **2 browser** passes; lint/generated/build/dependency checks pass |
| `make verify-live LIVE_EVIDENCE=artifacts/milestones/OBS03/final/live` | Exit 0; **473 live Python**, **125 live UI/contracts**, **124 lab Python**, **15 lab UI**, **4 browser** passes; schemas/lint/build pass |
| Focused `pytest tests/live/test_flight.py -q` | Exit 0; **129 passed**, including motion/property/timing/replay/backend boundaries |
| Early actual HTTP desktop/mobile preview and WebGL fallback | Exit 0; **4 passed**, screenshots opened; final aggregate reruns this journey |

Opened final [desktop](../../../artifacts/milestones/OBS03/preview-desktop.png) and
[mobile](../../../artifacts/milestones/OBS03/preview-mobile.png) screenshots are
also copied to the evidence root. Final screenshots are under
`final/live/browser/results/`; early captures also
remain under `frontend-browser/results/`. Source/runtime/protected-file identities
and the sanitized synthetic preview payload are retained with the evidence.
No private desktop inputs, OBS credentials or session recording were produced.

Development failures are retained: trace JSON arrays initially failed strict tuple
validation (two cases), and a new source-loss test used an invalid producer-state
string (`lost` instead of `inactive`, one failure plus teardown error). Both were
fixed before the final passing suites. The first broad run collected 2,844 tests:
2,841 passed, three failed, one teardown error. The independent review also found
an immediate Stop replay mismatch; the terminal overlay and tick 0/5/6000
regressions fix it. A browser test-helper TypeScript annotation was corrected
before its passing build. Existing AnyIO deprecation and build-size advisories
remain visible in logs.

## Gates and next handoff

| Gate | Status |
|---|---|
| OBS03 implementation, motion, replay, boundaries and browser preview | **PASS / COMPLETE** |
| Hosted OBS01/OBS02 prerequisite at reviewed commit | **PASS**, verified |
| OBS03 additional real-model / real-OBS execution | **NOT_RUN**, zero calls/capture; not required for synthetic presentation |
| Real source → neural flight → interactive browser | **NOT_RUN**, OBS04/OBS05 integration pending |
| Causal input-influence experiment | **NOT_RUN**, OBS06 |
| Human appearance/motion/framing/responsiveness review | **PENDING** |

Selected source remains `/dev/video0`, OBS Virtual Camera, scene `FLYJAM_INPUT`,
1920×1080 YUYV at 60 fps. Prior hardware evidence is historical; this milestone
extends no capture consent. Recording stays off, checkpoint/accounting stay intact,
and there is no remote push or public deployment.

**Stop after OBS03.** Next authorized invocation may select
`flyjam-obs-kit/prompts/04-api-and-replay.md`
for ownership/control API, bounded stream and consented replay storage. Preserve
the backend-independent decoder, terminal replay semantics and upstream deferrals.
