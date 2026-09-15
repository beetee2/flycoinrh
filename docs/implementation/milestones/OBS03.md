# OBS03 browser compatibility and diagnostics repair

2026-09-15. **Repair implementation and automated checks PASS; human review BLOCKED.**
Focused repair of reviewed/pushed revision
`58fbfd275821eb31c8a37df0cd55bde6e0a1676e`. The initial tracked worktree was clean.
Repair changes remain local and uncommitted. **Stop after this repair; OBS04 is
not authorized.** The original implementation report and passing evidence below
are historical and do not certify the operator's normal browser.

## Actual environment difference and operator confirmation

The operator originally reported “Loaded · idle” with disabled Play, failed
WebGL context creation, GL_VENDOR/GL_RENDERER `Disabled`, and
`BindToCurrentSequence failed`. That browser session was not automated or copied.
During this repair the operator enabled graphics acceleration and confirmed:
“i can click load and play and see the fly move.” This confirms normal-browser
playback of the previously served preview, before the repaired build was ready.
It does not constitute appearance/motion approval of this repair.

The supplied GPU export is dated `2026-09-15T15:29:15.383Z`: Chrome
153.0.8010.36, Linux 7.2.4-arch1-2, Hyprland/Wayland, hardware WebGL,
NVIDIA RTX 3080 / driver 610.57.04, ANGLE OpenGL, GPU sandbox true.
GL_VENDOR is `Google Inc. (NVIDIA Corporation)`; GL_RENDERER is
`ANGLE (NVIDIA Corporation, NVIDIA GeForce RTX 3080/PCIe/SSE2, OpenGL ES 3.2 NVIDIA 610.57.04)`.
GL_VERSION is `OpenGL ES 3.0 (ANGLE 2.1.28650 git hash: fca5efdfeff5)`.
Its command line includes `--ozone-platform=wayland` and
`--render-node-override=/dev/dri/renderD128`. The export reports a Wayland/Vulkan
compatibility message and disabled accelerated video encoding while WebGL works.
Those messages do not establish the cause of the original WebGL failure.

| Environment | Executable, version, mode | Context diagnostics |
|---|---|---|
| Independent installed Chrome | `/opt/google/chrome/chrome`, 153.0.8010.36, headed, disposable profile | Minimal WebGL2 and exact scene attributes PASS; RTX 3080 through ANGLE/OpenGL; GPU sandbox true |
| Independent CI browser | Playwright revision 1243 `chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell`, 153.0.8010.12, headless; desktop/mobile emulation | Both context probes PASS; SwiftShader software Vulkan; GPU diagnostics report sandbox false despite requested Chromium sandbox true and no `--no-sandbox` flag |
| Operator normal browser | Chrome 153.0.8010.36, personal session, user-supplied diagnostics only | Playback works after operator enabled acceleration; original failing configuration was not independently reproduced |

Prior Playwright configuration had no custom launch options and inherited
headless mode, `--no-sandbox`, and `--enable-unsafe-swiftshader`. The repair's
ordinary and opt-in checks request `chromiumSandbox: true` and remove the unsafe
SwiftShader opt-in. Actual final launch arguments and GPU information are saved.
The installed direct binary avoids the system wrapper that sources user flags;
no private flags file or browsing profile was accessed. Default Playwright launch
options still differ from the operator's normal session.

Four independent context probes cleared/read back pixels successfully with GL
error 0. The exact context attributes match pinned three.js r186, including its
internal `alpha:true` even when renderer output uses `alpha:false`: depth,
antialias and premultipliedAlpha true; stencil, preserveDrawingBuffer and
failIfMajorPerformanceCaveat false; powerPreference default. Both minimal and
requested contexts work, so no attribute fallback or scene rewrite is justified.

The operator's successful configuration change supports a browser-configuration
explanation for the original availability failure. No particular driver or
extension fault is established. No further host/browser change is proposed.

## Application repair

- Request WebGL2 explicitly and capture `webglcontextcreationerror` before scene
  construction; distinguish context creation, renderer/scene failure and context
  loss. Retain up to four sanitized messages of at most 600 characters in page
  memory, including after successful retry. Omit URLs, paths, controls and stacks.
- Display graphics readiness and preview-data readiness separately. Loaded data
  cannot enable Play without a successfully initialized/drawn renderer.
- **Retry graphics** makes one attempt per click, up to three retries per page.
  It releases the previous canvas/context, resources, observer and animation loop,
  recreates the last successful pose, and leaves playback paused. Reload resets
  the attempt budget. Loading data, Reset and context restoration do not retry.
- Context loss and render/resize exceptions stop playback and show a frozen state.
  Failed draws do not advance stored playback time. Old callbacks cannot alter a
  remounted stage. Disposal is idempotent and covers partial initialization,
  geometry/materials including the grid helper, listeners, context and canvas.

Installed Chrome also exposed an implicit `/favicon.ico` 404. A small original
SVG favicon is now linked and bundled locally; no console error is suppressed.
Physics, original geometry, model boundary and dependencies are unchanged.
This work fixes diagnostics and lifecycle behavior; it does not claim to repair
a driver or make WebGL available when the browser cannot supply it.

## Validation and review gates

Repair evidence is under ignored `artifacts/milestones/OBS03/browser-repair/`.
Previous OBS03 passing evidence remains in its original locations. Exact command
arguments, exits, counts, browser launch diagnostics and source identities are
recorded with the new evidence. Counts below overlap and must not be summed.

| Check | Result |
|---|---|
| Live contracts, components, renderer lifecycle and lab UI | PASS: 150 tests, 6 files, zero failures/skips |
| Live Python boundaries and synthetic integration | PASS: 473 tests, zero failures/skips |
| Lab Python regression | PASS: 124 tests, zero failures/skips |
| Live/lab generated schemas, Ruff, TypeScript and production build | PASS, exit 0; existing bundle-size advisory retained |
| Independent minimal WebGL2/scene-attribute probes | PASS: four probes, pixel readback, zero GL/console/page errors |
| Automated scene rendering, desktop/mobile | PASS: 8 tests, exit 0, zero failures/skips; `automated-complete/report.json` |
| Actual installed-browser headed scene compatibility | PASS: 4 tests in Chrome 153.0.8010.36, exit 0, zero failures/skips; `installed-headed-complete/report.json` |
| Operator normal-browser playback | Prior served build PASS by operator confirmation after enabling acceleration; repaired-build check BLOCKED pending reload/retest |
| Human appearance/motion/framing approval | BLOCKED pending operator review; no approval inferred from visible movement |

Regression coverage includes initialization details, successful/failed bounded
retry, real browser context loss, idle recreation, partial-init cleanup and
StrictMode/remount. Browser playback captures actual rendered scene pixels across
Play, Pause, Stop, Reset and reload. Console errors and uncaught page errors are
retained per test; forced failure evidence is separate from normal playback.
No error messages are blanket-suppressed. Final normal and forced-failure
attachments each contain zero console errors and zero uncaught page errors.
Final invocations (cwd `web/`; `command.json` records absolute evidence paths):

- `FLYJAM_LIVE_EVIDENCE=artifacts/milestones/OBS03/browser-repair/automated-complete npx playwright test --config playwright.live.config.ts`: 8/8, exit 0.
- `FLYJAM_COMPAT_BROWSER=/opt/google/chrome/chrome FLYJAM_LIVE_EVIDENCE=artifacts/milestones/OBS03/browser-repair/installed-headed-complete npx playwright test --config playwright.live.config.ts --project installed-headed`: 4/4, exit 0.

Each directory contains `command.json`, `command.log`, `report.json`, graphics
JSON, error attachments and screenshots. Installed-browser tests retain its
native Linux user agent; desktop/mobile CI intentionally uses emulated devices.
The parent opened final installed `rendered-initial-pose0.png`,
`rendered-paused-pose0.png`, `rendered-reset-pose0.png` and the mobile full-page
capture. The body rotates, landmark positions shift, and Reset restores the
initial composition. Head/body/copper eyes, two veined wings and legs are visible;
mobile controls/readiness fit. NVIDIA draws the ground grid much more visibly
than SwiftShader, so no pixel-identical appearance across browsers is claimed.
These observations do not replace operator appearance approval.

Development evidence is retained. The first focused run had 19 passes/1 failure:
the new resource registry initially omitted GridHelper's internally created
resources, found and corrected by the existing disposal test. The first browser
run had 6 passes/2 failures: auto-scrolling shifted screenshot capture by one row
on Reset. Later captures also isolated overlay text and mobile sampling differences.
A test-only attempt to hide text with injected screenshot CSS hit the existing
CSP and was discarded; errors are retained in its failed run. The final checks require pixel changes on Play and Reset, byte-stable captures
on Pause/Stop, initial telemetry on repeated Reset, and an idle visible
scene on reload. They do not require byte equality across differently scrolled
initial/Reset captures. Reload before loading data uses the existing default
pose (altitude 0), whereas loaded synthetic tick 0 has altitude 2; those images
are not expected to match. No CSS injection or error suppression remains.
Full UI captures and manually inspected initial/reset scene pairs are retained.
The first installed run failed four checks: three on the confirmed favicon 404,
one on repeated Reset screenshot byte equality. The final assertion uses the
initial authoritative pose plus inspected Reset images, while retaining actual
pixel-change and Pause/Stop pixel-freeze checks. All failed command reports remain. Independent
review also caught stale “Playing” text and premature elapsed-time commitment on
draw failure; both now have regression assertions. Earlier diagnostic launches
and their discovered default-flag differences remain recorded honestly.

## Handoff and scope

The prior local service was no longer listening during handoff. `make serve-live`
was started without capture/model activity; `/live` and `/health/live` return 200,
and the served HTML matches the repaired production build. The process remains
running (no exit yet); evidence is `local-service-final.json`.

Open `http://127.0.0.1:8767/live` and reload to receive the repaired build. Confirm
**Graphics: Ready**, then Load synthetic preview, Play, Pause, Stop and Reset.
Review the fly's appearance, motion and framing. If graphics fails, expand
**Graphics diagnostics (local to this page)** and use **Retry graphics** once;
report its message and the new GPU-page sections. Do not infer graphics readiness
from **Preview data: Loaded**.

The opt-in headed check uses an exact installed Chromium-family executable:
from `web/`, run `FLYJAM_COMPAT_BROWSER=/opt/google/chrome/chrome FLYJAM_LIVE_EVIDENCE=artifacts/milestones/OBS03/browser-repair/installed-headed npx --no-install playwright test --config=playwright.live.config.ts --project=installed-headed`
after `npm --prefix web run build` from the repository root. It opens a disposable
profile, preserves browser security checks, and fails when graphics is unavailable;
a passing bundled headless run cannot substitute for this check.

Zero new neural calls, capture/recording, OBS/device changes, GPU-model
integration, host changes, remote pushes or deployment. OBS ledger stays 9/1,024
(1,015 remaining); P00 stays 144 attempts. Baseline/checkpoint, protected files,
ledgers, notices and both implementation kits match saved hashes: 60/60 protected and kit identities, exit 0.
`source-identity.json` records the final tracked and new source hashes;
`repair.diff` preserves the local tracked patch.
**Return for human review. Do not start OBS04.**

---

## Historical OBS03 implementation report (before browser repair)

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
