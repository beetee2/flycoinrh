# OBS06 — technical validation and local handoff

**Subsequent human review:** CHANGES_REQUESTED for ground penetration at pushed
revision `3ee5b7247f2e4525bea60cb8fa3e3e260b33db8c`. OBS06 technical results below
remain accepted as recorded. The [focused ground repair](OBS06-ground.md) adds
new physics while preserving these v1 causal measurements; its implementation
passes local checks and awaits human re-review. The reviewed revision's hosted
workflow later finished FAILURE, as recorded in that repair report.

2026-09-15. **Technical validation PASS. Return for final human review.**
Reviewed starting revision: `a9688b39caaebb71a0c1058a6bf923ef86aab314`, initially
clean. OBS06 changes are local and uncommitted. No push or new hosted run occurred.
Evidence is under ignored `artifacts/milestones/OBS06/`.

| Required status | Result |
|---|---|
| implementation_status | **PASS** — CI integration, diagnostic tools, regression and lifecycle checks |
| real_model_status | **PASS** — CPU reference comparisons and actual model/browser/record/replay |
| real_obs_status | **PASS** — approved source, changed input, actual producer stop/restart, preview tab closure |
| causal_validation_status | **PASS for the frozen safe-stimulus diagnostic**; ordinary OBS visual influence remains **INCONCLUSIVE** |
| human_review | **Operator controls complete**; final product and causal-response approval **PENDING** |

## Prior handoff and operator evidence

Read-only `gh run view 35000589668 --repo beetee2/flycoinrh` confirmed completed /
success for the exact reviewed revision, updated 2026-09-15 17:24:38 UTC.
[Hosted result](https://github.com/beetee2/flycoinrh/actions/runs/35000589668).
`hosted-workflow-verified.json` preserves its jobs and commit identity. The first
lookup selected the upstream repository and returned 404; the explicit fork
lookup succeeded. An append-only update in [OBS05](OBS05.md) resolves its pending
handoff without rewriting its historical checks or allowance snapshot.

The operator confirmed Start/Stop. They reported switching from videos to static
content and seeing the exact last-inferred input update appropriately. They could
not clearly tell whether the flight path changed and lacked enough evidence to
contradict a response. Start/Stop controls appeared to function correctly. These
are operator observations, separate from the agent's independent checks.
Unreported rate-label comprehension, personal-browser tab hiding, replay, and
product taste are not marked approved. OBS03 synthetic appearance approval remains
historical approval of that experience.

## Implementation and preservation

Reviewed OBS00–OBS05, SPEC/TEST_MATRIX, the historical boundaries, and applicable
implementation. No application model or presentation change was needed. Changes:

- Ordinary CI adds a separate lab fixture HTTP/browser journey alongside the
  live fixture journey, schema drift, components, and historical foundation checks.
  The lab fixture honestly returns model unavailable after validated submission;
  its real-only result contract is preserved. It covers editing, exact request
  pixels, error recovery and reload; it is not a successful real lab result.
- Lab/live evidence targets now support isolated paths outside historical
  milestones. `verify-live-real` invokes the real reference, safe-model browser,
  and approved OBS gates; missing explicit OBS readiness fails before calls.
- `scripts/live_causal.py` supplies a frozen, separately labeled diagnostic;
  six tests verify actual zero-drive submission, restored interception, unchanged
  ordinary output, sampled stimulus changes, silence and deterministic controls.
- `scripts/live_performance.py` runs a bounded synthetic slow-consumer/failure
  soak. `scripts/live_obs_coordination.py` coordinates explicit operator actions
  and persists numeric summaries only. The actual OBS browser gate adds a
  zero-call preview tab-closure check.

CPU, model/checkpoint, all-one gains, disabled learning, `windowed_reset`, 100
integration steps at 0.2 ms, internal seed progression, encoder, decoder, physics,
renderer, notices, kits, P00 and protected evidence remain preserved. Diagnostic
disconnection is unavailable to normal live sessions. The recording guard remains
unchanged and rejects OBS recording. No model experiment, tuning, GPU integration,
learning change, allowance reset, privileged host action or upstream merge occurred.

## Actual validation

Commands and evidence paths below are relative to the repository unless noted.
Passing test suites have zero failures, errors and skips.

| Command / gate | Actual result and evidence |
|---|---|
| `make verify test-upstream EVIDENCE=artifacts/milestones/OBS06/ci-regression/foundation/checks` | Exit 0: 2,979 Python, 150 upstream, 89 web contracts, 9 UI, 2 fixture browsers; `ci-regression/foundation/` |
| `make verify-live LIVE_EVIDENCE=artifacts/milestones/OBS06/ci-regression/final/checks` | Exit 0: 603 live Python, 222 live UI/contracts, 124 lab Python, 15 lab UI, 2 lab and 18 live fixture browsers; schemas/lint/build PASS |
| `make test-live-real LIVE_REAL_EVIDENCE=artifacts/milestones/OBS06/real-reference` | Exit 0: nine actual attempts; original-output/historical-tap comparisons, independent retinal oracle, one model load/reset; `real-reference/` |
| `make test-live-real-browser LIVE_EVIDENCE=artifacts/milestones/OBS06/safe-browser` | Exit 0: one browser test, two actual calls, exact input/rate/pose identity, safe recording, zero-call replay/seek/download |
| `make test-live-obs LIVE_EVIDENCE=artifacts/milestones/OBS06/approved-obs` with approved device/readiness and automated URL `http://127.0.0.1:8878` | Exit 0: one initial browser test, two actual calls; preview/Stop and rendered input/rate/pose checks; recording off |
| `.venv/bin/python -m scripts.live_obs_coordination --approved-source /dev/video0 --safe-content-ready yes --output artifacts/milestones/OBS06/coordinated-obs` | Exit 0: changed-input two calls, producer-stop 28 attempts/27 completions, restart two calls; actual operator actions recorded in conversation |
| OBS browser config, `-g 'closing the approved'`, approved URL and fresh `obs-tab-close-fixed` evidence | Exit 0: one actual-source preview/close test; zero neural calls; no pixel persistence |
| Frozen causal prepare/execute commands in `causal/commands.json` | Exit 0: 32 actual attempts, exact repeat and paired analysis; six diagnostic fixture tests PASS |
| Performance command in `lifecycle/commands.json` | Exit 0: 32 synthetic responses, no full-model calls; measured bounds and cleanup |
| `.venv/bin/python -m flytrap.live doctor --source v4l2-video0 --evidence-dir artifacts/milestones/OBS06/doctor` | Exit 0: selected-device and runtime checks, no stream or inference |
| `node artifacts/milestones/OBS06/review/capture.mjs 8d4d624e6f4a4d3f8a9a7dbdc26d3d62` against idle safe service | Exit 0: original-time safe real recording replay, exact final pose, no mutating requests, unchanged allowance, screenshot/video |
| `make verify-live-real` without readiness variables | Expected BLOCKED, exit 2; zero calls. Constituents executed separately above; aggregate successful invocation was not rerun redundantly |

The foundation run preceded the six new diagnostic tests; final `verify-live`
includes them. The later added OBS preview-closure test was executed separately.
Historical navigation `verify-real` / `verify-release` definitions remain unchanged.
Hosted CI validates the pushed OBS05 revision only; new CI wiring has local results.

Development failures remain preserved: the new lab browser initially refused an
occupied port, then moved to configurable default 8898. An overlapping causal run
changed the durable ledger during a browser zero-call assertion; that run had
16/18 passes and a subsequent mobile timeout. The final exclusive, model-idle run
passed without weakening assertions. The performance harness initially treated a
terminal renewal 409 as an error; terminal handling was repaired. The causal fixture
probe initially used an incomplete frame schema. A new preview-close assertion
initially read the previous terminal session before the new preview acknowledgement;
waiting explicitly for `previewing` repaired the test. Its error-context artifact
contains test source/error details, **no page snapshot or source pixels**. No failed
full-model attempts were refunded or silently retried.

## Actual OBS source and lifecycle

Before capture, metadata confirmed `/dev/video0` / `v4l2-video0`, **OBS Virtual
Camera**, driver **v4l2 loopback**, 1920×1080 YUYV, 60 fps, stride 3840,
`keep_format=0`. The operator confirmed safe content, fixed FLYJAM_INPUT, and
excluded Flyjam output. The server revalidates device identity and producer
capabilities on Start. No other source or scene was selected by the agent.

The operator changed content on request. Both new inferred observations differed
from the initial sample in **143/256 pixels**. Comparison occurred only in memory;
no additional processed screen inputs were saved. The operator then stopped
Virtual Camera after the first real response. Session entered `source_lost`,
neutralized flight, reaped the in-flight worker, and retained its stationary pose.
The interrupted 28th attempt remains charged. Manual producer restart did not
resume inference; explicit Start created a new session and completed two calls.
Preview tab closure separately stopped actual capture in **539 ms** without model calls.

Source timestamps/sequences remain unknown for FFmpeg V4L2 receipt; local receipt
sequence is not a producer sequence. Equal pixels were never used as source-health
proof. Exact latency from the human's producer-stop click was not instrumented;
the measured total producer-stop phase is not reported as detection latency.
Software deadlines, format/EOF/partial-read errors, stale/foreign responses,
worker crash/hang, lease expiry, active Stop, shared locks, and actual FFmpeg
slow-consumer behavior are covered by the passing boundary regression suite.

## Causal comparison

Before inference, `causal/plan.json` froze seed **20260915**, eight generated safe
stimuli, four conditions and **32** calls. Changing, first-frame-frozen, genuinely
disconnected drive, and an exact changing repeat each use eight steps. Every
response gets 500 ms of playback at 20 ms/tick, starting at (0,0,2) with zero
yaw/pitch/speed. The identical OBS05 saved inputs cannot serve as changing input
and were excluded. No additional OBS recording was needed.

The diagnostic intercepts the submitted sensory arrays after the ordinary eye and
oracle inspection, replacing every rate with zero for disconnection while keeping
indices and random draw count. An ordinary black frame is never called silence.

| Changing versus frozen | Measured difference |
|---|---|
| Input | 1,024/2,048 bytes differ; mean absolute difference 96 |
| Motor rates | 37/56 values differ; mean absolute difference 107.366 Hz |
| Yaw / pitch / speed targets | 7/8, 6/8, 7/8 responses differ |
| Final/max trajectory separation | 9.172079 world units after fixed 4-second playback |
| Exact changing repeat | Inputs, drive, rates, raw outputs, controls and all 201 states identical |
| Disconnected condition | Submitted drive, motor rates and controls zero; pose remains (0,0,2) |

This demonstrates influence for the predefined high-contrast safe sequence.
Frozen input also produces variation because step seeds advance. Motion alone
does not establish visual influence. Ordinary OBS perceptual responsiveness remains
inconclusive; one seed/eight stimuli do not establish broad responsiveness or
human causal approval. No tuning or additional seed search followed the result.

## Performance and inspected visual evidence

- Actual CPU model construction plus compiled retina: **4,742.537 ms**. Ordinary
  changing-step wall times: **478.464–665.577 ms**, median **528.366 ms**. These
  exclude ledger writes; numerical simulation remains 20 ms per window.
- Coordinated OBS health HTTP maxima: **6.03 / 9.10 / 6.87 ms** by phase; local
  receipt-age maxima **78.30 / 64.90 / 121.80 ms**; largest step **833.05 ms**.
  Unknown source capture age is not replaced with receipt age.
- Safe 5.84-second soak: **172 captured, 139 overwritten**, 32 synthetic responses,
  **16 stale results rejected**. Recent consumed sequences advanced 20→164.
  Health/session HTTP p95 **2.18/2.95 ms**; receipt age p95 **32.04 ms**.
- Encoder p95 over 100 samples: **0.066 ms** at 320×180 and **0.068 ms** at 1280×720.
  Synthetic parent/worker RSS peaks **169,412/154,484 KiB**. Actual OBS restart
  process samples separately show service **99,516 KiB**, largest model-sized
  child **747,908 KiB**, capture-sized child **197,840 KiB**; per-PID maxima are
  not summed as simultaneous memory. The first RSS probe missed thread children
  and is preserved as service-only evidence; the corrected probe enumerated all
  thread descendants. No causal-process RSS is retroactively claimed.
- Recorded browser replay showed 86 flight-canvas clears through 6.569 seconds
  of sampled playback (~13.1 draws/s overall; variable 500 ms intervals) and no
  new clears after terminal freeze. This is instrumented headless SwiftShader
  playback with video enabled, not the operator's Chrome performance or neural Hz.

The parent opened the safe real-model screenshot, final fixture mobile capture,
causal figure, and video frames at 6 and 7.5 seconds. The fly's body, eyes, wings,
legs and surrounding landmarks remain identifiable; mobile controls and separate
input panels fit the page. Video shows labeled recorded playback, an initially
stationary load interval, then the recorded displacement and terminal freeze.
It is original-time playback of two real safe-source calls, not OBS footage or a
long responsiveness demonstration. The causal plot includes fixed-scale paths
and all prescribed conditions; exact repeat overlays changing.

## Accounting, cleanup and next handoff

OBS06 started at **142**, not the old handoff's 61. The intervening 81 charges
remain unchanged; their three sessions are listed in the OBS05 append. OBS06 adds
**77** attempts: reference 9, safe browser 2, initial OBS browser 2, causal 32,
changed input 2, producer-stop 28, restart 2. Final total **219/1,024**, **805
remaining**. Human sessions use their separate server-selected usage records.
P00 remains **144** and its protected bytes remain unchanged.

Final preservation/cleanup evidence checks the original 142-row ledger prefix,
protected identities, free model ownership, terminal human service, no Flyjam video
descriptors, and stopped validation services. The operator-restarted OBS producer
still holds its own device descriptor; Flyjam capture/inference are off. OBS recording and monitor recording
remained disabled; no new private source previews, screenshots, traces, or raw
desktop files were retained. The review bundle contains only allowlisted safe
generated-input visual evidence and numeric/technical reports.

Read [OBS-LIVE-HANDOFF](../OBS-LIVE-HANDOFF.md). Stop with capture and inference
off. Return for final product and causal-response review. No further model,
mapping, public release or remote work is implicitly authorized.
