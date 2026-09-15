# OBS05 — usable OBS-to-flight browser experience

2026-09-15. **Implementation and required local validation PASS / COMPLETE. Human real-flight review PENDING.** OBS05 only
was authorized. OBS06 remains stopped pending the operator's hands-on review.
The initial checkout was clean at reviewed revision
`2bc0c675c62b5aeaaa5393697f02406d53a7b195`; changes remain local. Historical evidence,
both kits, notices, and newer work were preserved.

## Prior approval and hosted result

The operator's OBS03 approval of repaired synthetic appearance/motion remains
**APPROVED**. It is not approval of real neural-driven flight. The original failure
and repair evidence remain in OBS03. Read-only `gh run view` confirmed
[workflow 34995107755](https://github.com/beetee2/flycoinrh/actions/runs/34995107755)
completed successfully for the exact reviewed revision, including the scoped
sandbox prerequisite, repository verification, and live verification. The OBS04
report now has an appended revalidation note. This does not claim hosted validation
of the new local OBS05 changes. Evidence: `artifacts/milestones/OBS05/hosted-workflow.json`.

## Implemented experience and boundaries

`/live` connects the actual service and SessionClient to the approved procedural
fly renderer. Explicit modes distinguish synthetic demonstration, capture-only
preview, actual neural model, fixture model, and recorded playback. The source is
never automatically selected. Controls provide Preview, Start, Stop, duration,
call limit, seed, per-Start recording consent, input inspection, and recording
list/load/play/pause/seek/download. `/lab` remains the separate diagnostic service
at port 8766. A failed live session never substitutes synthetic movement.

Runtime schemas validate responses and nested identities. The client pins source,
session, generation and event ordering, rejects regressing flight ticks, binds
recording IDs to listed manifests, and checks sample/input/raw-value consistency.
Seek results must match the loaded recording and requested tick. An invalid Start
acknowledgement cannot reattach after ownership was released. Newest source input
and the exact last-inferred input have separate identities and displays. The inspection
pane includes an ephemeral RGB source thumbnail and separately labeled processed
16×16 pixels; thumbnails are never exported or recorded. Capture,
neural and rendering rates are separate; render rate measures actual draws over
500 ms windows. Producer health, unchanged-content duration and input/response
ages remain visible. Receipt timing is not presented as an OBS capture timestamp.

The server remains the fixed 20 ms flight authority. Display interpolation runs
only between accepted poses for at most 100 ms; it cannot extrapolate. Local Stop,
hide, page exit, connection loss and graphics failure freeze the displayed position
and release ownership. Later status polls cannot move a locally frozen fly. The
existing maximum three-second owner lease and resource cleanup remain enforced.
Retry graphics preserves diagnostics, recreates one renderer and leaves playback
paused. Recovery requires explicit user action. Pending Start, seek and download
responses are fenced against mode changes and tab hiding.

The service defaults to **automated** execution accounting, including Playwright
POSTs. Execution purpose is configured only on the server, through
`--execution-purpose`; browser config cannot select it. `--safe-source` exposes the
existing deterministic fixture image generator with the actual CPU model. Source
fixture labels remain separate from model provenance. The default operator command
also charges the automated allowance; the UI displays this purpose and remaining
budget. Human purpose requires an explicit server invocation, never a browser flag.

Recording stays off by default. This workstream disables OBS/monitor recording in
both UI and API. Safe-source recording remains opt-in. Replay reads verified private
artifacts and uses recorded control ticks; it opens no capture device, performs no
inference, and leaves ledgers unchanged. Downloads preserve the original validated
server JSON text, including signed zero in raw neural values. Full-resolution
source video is never saved.

## Actual validation

Evidence root: ignored `artifacts/milestones/OBS05/`. Per-command records include
argv, cwd, exit, elapsed time and source hashes. XML/browser reports contain actual
counts; overlapping suites are not additive. The final counts table is populated
from executed reports. No missing real-data or hardware gate is treated as a skip.

| Check | Result and evidence |
|---|---|
| Repository verification and upstream tests | **PASS**, `foundation-fixed/`: `make verify test-upstream EVIDENCE=artifacts/milestones/OBS05/foundation-fixed/checks`, exit 0; 2,979 Python, 150 upstream, 89 web contracts, 9 UI, 2 browser; all zero failures/skips |
| Live checks | **PASS**, `final-checks/`: `make verify-live LIVE_EVIDENCE=artifacts/milestones/OBS05/final-checks/checks`, exit 0; 597 live Python, 222 UI/contracts, 124 lab Python, 15 lab UI, 18 desktop/mobile browsers; zero failures/errors/skips |
| Actual TCP HTTP and storage boundaries | **PASS**, included in Python suites; focused backend `backend-service/` has 256 passes, zero failures/errors/skips |
| CPU real-model reference gate | **PASS**, `real-reference-fixed/`: nine calls, independent original-output/historical-telemetry comparisons and retinal oracle; exit 0 |
| Real-model browser journey | **PASS**, `real-browser-final/`: `make test-live-real-browser LIVE_EVIDENCE=artifacts/milestones/OBS05/real-browser-final/checks`, exit 0, one browser test, two actual CPU calls; exact inputs/retinal fixture oracle, displayed neural values and rendered authoritative pose, opt-in recording, replay and original JSON download. Prior `real-browser/` failed at signed-zero download; preserved separately. |
| Existing real recording after repair | **PASS**, `real-replay-repair-final/`: one browser test, exit 0; exact download, trace-applied input/neural values, pose/seek, only GET requests, idle service and byte-identical ledgers |
| Approved actual OBS browser | **PASS** bounded Preview/Stop + two real calls, `actual-obs-run/`: one browser test, exit 0; exact displayed input bytes, source/response IDs, raw motor rates, authoritative/rendered final pose; recording off |

Development failures are retained: the old real-gate serializer did not include
`SessionSnapshot.flight`, causing report serialization failure after three charged
calls and before references. A non-model regression test covers the repair. The
first foundation run had 2,978 passes and one obsolete CLI-string expectation;
the updated test checks the constructed app's idle state, loopback and automated
purpose. Browser development failures included Node ESM imports, retained-session
label expectations, and the signed-zero download defect. The replay repair's first
assertion assumed the last completed sample had been applied, but the final call
limit stops before applying that result for a tick; the corrected test uses the
recorded control-application ID. Two intermediate aggregate live runs also exposed separate initial/reload assertions
that still expected the older retained-session label. Both assertions were corrected;
the final complete 18-browser run passed. UI lifecycle failures/repairs remain in the
`ui-agent-*.xml` reports. No seed selection, model tuning or discarded attempt was used.

## Approved OBS evidence and limits

The operator selected `/dev/video0`, **OBS Virtual Camera**, fixed **FLYJAM_INPUT**,
confirmed displayed content ready before new capture, and explicitly approved two
processed inputs. Metadata inspection confirmed v4l2loopback, 1920×1080 YUYV at
60 fps, `keep_format=0`; the capture opener revalidates identity. No other device,
scene modification, streaming command, privileged host change or desktop recording
was used. Approval is recorded in `capture-authorization.json`.

Actual session `cbc42ec586a24e5783af3b770b454a64`, generation 1, admitted source
sequences **247** and **277**. Both calls completed; zero responses were rejected.
The accepted final pose was tick **333**, position
**[0.8133997017796482, 0.2323433995648195, 1.9806413933992493]**,
yaw **0.5287348642493965**, speed **0**, neutral **true**. The last measured motor
rates were steer L/R **50/50 Hz**, forward L/R **50/0 Hz**, back **0 Hz**,
stop **100 Hz**, click **0 Hz**. These historical rates are distinct from the
terminal neutral command. The observed neural rate was about **1.395 Hz**, with
last step wall time about **800 ms**; this is a small validation sample, not a
performance guarantee. Numeric evidence is in `actual-obs/numeric-evidence.json`.

Exactly two 16×16 grayscale PNGs and identity sidecars are in
`actual-obs/approved-inputs/`; `view-inputs.html` displays those same PNGs enlarged
with CSS. Both images were opened and inspected. Their bytes are identical:
**0/256 pixels changed**. This validates the fixed-scene path, not changing-content
responsiveness. Current producer-stop/unplug behavior was not manually exercised;
OBS01 hardware history is preserved and not presented as a fresh test. Changing
OBS content, stopping its virtual camera, and real motion/framing/responsiveness
remain explicit hands-on checklist items. OBS06's causal experiment was not run.

No OBS screenshots, source thumbnails, videos, browser traces or failure accessibility
dumps were saved. Approved images are ignored by Git and remain private local evidence.
The actual-OBS browser configuration disables Playwright failure page snapshots as
well as screenshot/trace/video recording. Session recording remained off. The final
RGB thumbnail presentation addition was validated with fixture browser and pixel-mapping
tests; the actual-OBS run above inspected the processed preview before that addition.
No additional desktop capture was made for this presentation change.

## Browser and visual inspection

Tested browser: bundled Chromium **153.0.8010.12**, disposable headless Playwright
profile, sandbox enabled, WebGL2 through ANGLE/Vulkan **SwiftShader Device (Subzero)**.
`--enable-unsafe-swiftshader` is explicitly omitted. No driver/browser host policy
was changed. Browser/context diagnostics and Retry evidence are retained. This is
separate from the operator's previously approved hardware-accelerated personal Chrome.

The parent opened desktop/mobile fixture captures and the safe real-model capture.
The approved dark body, head/eyes, veined paired wings, legs and repeated landmarks
remain recognizable; the main stage retains scale and depth. Controls fit the
mobile width, labels remain legible, and input inspection is separate from the
primary stage. Axe WCAG checks reported no violations on desktop/mobile fixture
journeys. These inspections do not approve product taste on the operator's behalf.

## Accounting and preservation

| Execution | Additional full-model attempts |
|---|---:|
| Real reference run interrupted by reporting defect | 3 |
| Repaired nine-call reference gate | 9 |
| Initial safe real-model browser flight and recording | 2 |
| Reopening the same recording after download repair | 0 |
| Approved OBS browser flight | 2 |
| Final complete safe-model browser/replay journey after download repair | 2 |
| Total agent validation | **18** |
| Independently started browser session during handoff | **34** |
| Total added during OBS05 | **52** |

After agent validation finished at 27 attempts, a separate browser-controlled
preview and live session were observed on the handoff service. The preview made
zero neural calls; session `ca8aa9d3b58742d3af935425da5a8a9a` ended at its bound
with 34 calls, charged by the default automated server policy. No additional
images or neural samples from that session were saved by the agent. This activity
does not establish human appearance/motion approval. Final metadata is in
`local-service/handoff-state.json`.

OBS automated ledger: **61 / 1,024**, **963 remaining**. P00 remains **144 attempts**;
its bytes match the prior identity. `protected-check.json` confirms **59/59**
protected model/checkpoint/notice/kit/P00 identities unchanged; OBS accounting is
intentionally checked separately. CPU baseline, windowed reset, internal step seeds,
100 integration steps, all-one gains, disabled learning, encoder, fixed flight
mapping and authoritative physics are unchanged. No GPU integration, upstream merge,
database/token feature, push, deployment, paid service or publication occurred.

## Boundary handoff status

| Boundary | Status |
|---|---|
| OBS05 implementation / unit / contract / HTTP / UI / fixture browser | **PASS / COMPLETE** |
| Actual CPU model through browser and recording | **PASS** |
| Actual OBS Preview/Stop and bounded real flight | **PASS**; content-change and current producer-stop checks still require operator action |
| Recorded playback / exact download / zero-call isolation | **PASS** |
| Causal input-influence experiment | **NOT_RUN**, OBS06 remains unauthorized |
| Human real-flight appearance/motion/framing/responsiveness | **PENDING**, no approval inferred |
| OBS03 repaired synthetic appearance/motion | **APPROVED**, preserved operator confirmation |

## Handoff

Verified startup: **`make serve-live`**, **http://127.0.0.1:8767/live**.
The service was restarted and verified running idle, with no capture/model child
processes or open video descriptors and initial status `current: null`. The later
independent browser session finished at its bound. The final resource check
confirmed no capture/model children or open video devices; its terminal state was
preserved for review. Read-only
startup/final resource checks are under `local-service/`.

1. Open `/live`; check **Graphics: Ready**. Select **Live source**, then
   **OBS Virtual Camera · v4l2-video0**. Keep FLYJAM_INPUT fixed and exclude Flyjam output.
2. Enable **Inspect input**, press **Preview source**, verify the intended feed,
   then **Stop session**. Recording must remain disabled for this source.
3. Choose a short duration/call bound and seed; press **Start live flight**.
   Change content within the selected OBS input and compare newest-source versus
   last-inferred IDs, neural values, the three rates, and visible motion.
4. Test Stop and tab hiding. Separately stop OBS Virtual Camera and check source loss;
   recovery must require explicit Start. Use Retry graphics only if needed.
5. Use **Recorded playback** for the saved safe-source recording. Play/Pause/seek and
   download should leave the model allowance unchanged. Judge real motion, framing,
   responsiveness and appearance before authorizing anything further.

**Stop after OBS05. Human real-flight review remains PENDING; OBS06 is not started.**
