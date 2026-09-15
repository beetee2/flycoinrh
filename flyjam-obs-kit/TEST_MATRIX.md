# Boundary validation matrix

Tests should detect plausible defects, not restate implementation constants.
Reuse valid existing tests. Counts and evidence must be actual and scoped.

| Boundary | Validation | Release evidence / defect detected |
|---|---|---|
| Source selection -> device | Unit + actual V4L2 inspection | No automatic webcam fallback, arbitrary path/URL rejection, identity/capability validation, no capture during discovery. |
| Device -> frame reader | Backend integration + approved OBS | Known color/orientation marker, correct format/stride, partial-read/EOF handling, format change, missing permissions, bounded blocked read. |
| Reader -> latest-frame slot | Concurrent integration + stress | Capacity one; slow inference consumes recent sequence numbers; decoder/pipe buffers do not accumulate; old source epochs rejected. |
| Producer -> freshness monitor | Integration + hardware fault injection | Static valid image stays valid; actual virtual-camera stop detected; duplication does not masquerade as proven producer health; status credentials private. |
| RGB -> Observation | Golden/reference unit + property | Aspect-preserving letterbox, defined color conversion, finite normalized 256 values, no mirroring, matching source/observation IDs. |
| Observation -> retinal drive | Cached-map oracle tests + real data | Compiled live mapping agrees with independent raw-annotation oracle; unavailable/missing cells handled identically; file reads/hashes removed from hot path without changing values. |
| Observation -> model response | Unit + actual connectome | One load per session; correct step-seed progression; same observations/config/seed reproduce; telemetry interception does not alter outputs; no neural mutation. |
| Session -> subprocess lifecycle | Multiprocess faults | Concurrent Start, cooperative stop, hung model/capture, worker crash, ownership loss, no orphan process, late response cannot revive old session. |
| Model ownership -> P00 | Shared-lock integration | Live and P00 cannot simultaneously claim the shared model resource; P00 behavior and counters preserved. |
| Real calls -> ledger | Filesystem integration | Append/fsync before call, failed attempt counted, corruption and exhausted budget fail closed, no reset on restart. |
| Raw rates -> flight decoder | Unit + property | Known vectors yield expected signed bounded controls, zero output stays neutral, no input pixels/labels accepted, timestamps and nonfinite data rejected. |
| Controls -> flight state | Fixed-step unit + property + replay | Frame-rate-independent authority, bounded acceleration/rotation, stale commands expire, deterministic replay from applied control ticks, visual rebasing doesn't steer. |
| Files -> replay | Filesystem crash/corruption tests | Partial write not published complete, traversal rejection, manifest/event hashes checked, unknown versions rejected, replay makes zero neural calls. |
| API -> clients | HTTP integration + schema drift | Responsive health during inference, schema rejection, origin/ownership protection, idempotent stop/start, bounded responses/streams, no API-triggered arbitrary capture. |
| Stream -> browser | Actual HTTP/browser tests | Reconnect snapshot, old/foreign epoch rejection, no duplicate application, terminal recovery, hidden-tab lease behavior and transport failure. |
| Browser -> renderer | Vitest/Testing Library + Playwright | Start/Stop behavior, keyboard access, stale labels, active input IDs, frame count/neural Hz distinction, one renderer/timer loop, cleanup. |
| Whole local pipeline with fixture | Playwright real services | UI through actual API/worker/artifact store using an explicitly synthetic controller/source. Source ID, pixels, pose and state asserted. |
| Replay source -> real model -> UI | Real-model integration + Playwright | Safe known frame sequence, true graph, no mocked model/API, exact observation and displayed controls, recording and replay agree. |
| OBS -> real model -> UI | Real hardware + Playwright/manual | Approved OBS feed is visible, changing source reaches model, start/stop/unplug are safe, source/accepted-frame IDs and real output evidence preserved. |
| Input influence | Matched recorded-input experiment | Changing vs frozen vs genuinely disconnected drive under fixed seeds; compare raw rates AND decoder controls/trajectories, not only screenshots or spike totals. |
| CI -> maintained product | CI config review + executed checks | Lab + live schemas/components/fixture journeys included; real gates separate; no missing-data-as-skip-success; no privileged hardware work on hosted PR CI. |

## Three evidence tiers

1. **Fast CI:** fake/test video source and explicitly synthetic graph/controller,
   actual local API/processes/filesystem/browser. No host camera, raw dataset, or sudo.
2. **Real-model:** actual full graph using a deterministic safe source. Real neural
   failures or missing data fail the dedicated command. This is not an OBS pass.
3. **Real-OBS:** explicitly selected virtual device, actual feed, real graph, actual
   browser. Manual OBS setup may be necessary. Unavailable hardware yields BLOCKED,
   nonzero verification, and a usable development handoff—not a fabricated pass.

## Input-influence experiment

Use a small declared neutral test sequence that substantially changes sampled
regions. Run the same frame schedule under changing input, first-frame-frozen
input, and actually zero sensory drive with matched step seeds. Include one exact
repeat. A black frame is not zero drive in the baseline; disconnect only through
an explicit diagnostic hook and label it outside the ordinary baseline input mode.
No change to model files/checkpoint, training or seed hunting is authorized.

Freeze the comparison and budget before running. Record no more than 32 steps per
condition and two seeds unless a documented defect requires a smaller repair run.
Count any replay-based neural recomputation in the new validation ledger.
Quantify changes in raw motor rates, decoded controls and flight state with the
same starting pose; don't require that every channel responds monotonically.
All-zero and constant-response decoder controls also need deterministic tests.
If inputs affect rates but the decoder saturates identically, report that finding
rather than claim a responsive fly. Finish the bridge and request a bounded
mapping revision instead of initiating a new product pivot.

## Manual review checklist

- The approved source, not my private desktop or another webcam, is captured.
- The main stage shows an identifiable fly, with enough scenery to perceive motion.
- I can change OBS content and see the accepted observation update.
- Latest source preview and last inferred observation are not confused.
- I can tell capture rate, inference rate, render rate, and delayed/stopped state apart.
- Stop stops neural-driven flight promptly. Stopping OBS does not leave it falsely Live.
- Closing/hiding the controller tab releases control within the lease bound.
- Replay is labeled and does not consume model calls; recording required consent.
- No session or recording starts on page load or reconnect.
- I find the actual motion and framing engaging enough for another iteration.

Record my actual answers; do not approve product taste on my behalf.
