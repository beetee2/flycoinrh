# Flyjam OBS live specification

## 1. Scope and authority

Build the local OBS-to-flight workstream, OBS00 through OBS06, in the existing
repository. Read the current code and applicable repository instructions. The
explicit current assignment permits this new workstream despite the historical
P00 stop. Preserve prior results and do not relabel navigation as successful.

Resolve routine reversible implementation choices independently. Delegate
bounded, nonconflicting tasks when useful. Deliver functioning code and relevant
tests, not only design prose. Run one numbered milestone per instruction.

Public hosting/tunnels, remote pushes/PRs, tokens/wallets, paid services, unrelated
OS automation, audio ingestion, YouTube extraction, learning, fast weights, and
third-party game control are outside this assignment. Privileged installation or
kernel changes require explicit operator approval. Do not launch upstream wallet,
roaming, voice, or token services during tests. Preserve LICENSE and NOTICE.

## 2. Repository integration

Reviewed baseline: `a1af684f5dbcf88f75cc23da5b0df6621a7efd5a`.

Relevant existing code:
- `flytrap/controllers/fly.py`: explicit baseline, immutable gains/weights,
  internal step-seed derivation, pixels-only Observation, source-bound checkpoint.
- `flytrap/lab/runner.py`: independent A/A-repeat/B comparison jobs. Do not use
  that nine-call request loop as the streaming interface.
- `flytrap/lab/sensory.py`: raw-annotation sampling oracle and passive response
  interception. It currently reads/hashes annotations per inspection; avoid
  placing that file I/O inside every live step.
- `flytrap/lab/api.py`: local service, child work, P00 model lock.
- `web/`: React, TypeScript, AJV, Vitest, Testing Library, Playwright.
- `Makefile`: broad Python checks plus separately invoked lab frontend/schema
  checks. Preserve historical targets while integrating new fast checks.

Use new code under `flytrap/live/` and UI code under `web/src/live/` unless actual
checkout conventions justify a documented alternative. Keep `/lab` working.
Prefer a separate live app at `http://127.0.0.1:8767/live`, configurable on conflict;
never kill an unrelated service occupying the port. No automatic capture/inference
on app startup, page load, reconnect, or opening a replay.

Track progress in `docs/implementation/OBS-STATUS.md`, reports in
`docs/implementation/milestones/OBS00.md` ... `OBS06.md`, and evidence in
`artifacts/milestones/OBS00/` ... `OBS06/`. Session data lives separately under
ignored `artifacts/live/`. Add an active routing note to the top-level STATUS
without rewriting historical reports.

Keep model files and model semantics unchanged. A source-bound baseline may
reject even an otherwise harmless source edit; do not silently regenerate it.
Put the live adapter/tap outside the historical model files. Any unavoidable
baseline change requires a separately versioned descriptor and explicit report.

## 3. System shape

```text
Selected OBS virtual device
  -> continuously drained frame reader
  -> capacity-one latest-frame slot
  -> one persistent neural worker per active session
  -> raw responses -> fixed flight decoder
  -> authoritative fixed-step flight state
  -> local API/snapshot stream -> third-person renderer
```

The model is loaded once per active session, not once per frame. Capture and
inference cannot block the API event loop. No per-viewer brain instances or
unbounded work queues. Use one capture backend, not several speculative backends.
A maintained V4L2-capable library or a bounded FFmpeg subprocess is acceptable;
record the chosen backend/version and justify it briefly from verified support.
Do not write a kernel driver or vendor a large streaming platform.

A persistent process is not persistent neural state. Retain `windowed_reset`,
all-one gains, disabled learning, and the existing per-step seed sequence.
Reset the controller once at session start; call its step for each admitted
observation. Its numerical dynamics still reset internally as currently defined.
Do not shorten numerical integration to advertise a better latency.

## 4. Capture and pixel contracts

Enumerate device names, driver, capabilities and formats without opening camera
streams. The operator explicitly selects an OBS virtual device. Never choose
`/dev/video0` by assumption or switch to a physical webcam on error. Store only
an approved local source ID/configuration; browser requests cannot pass arbitrary
paths, URLs, shell fragments or FFmpeg arguments. Validate the actual resolved
character device, driver identity and format at opening and on any later start.

Preview is an explicit short operation without neural inference. Capture is
closed when preview/session ends. Streaming format changes terminate the active
session with a clear reason; reopening requires a new Start.

The frame envelope carries source ID, generation/epoch, sequence, dimensions,
format, local receipt monotonic timestamp, and source timestamp/sequence when
available and trustworthy. Missing producer timing is null/unknown, not invented.
A receipt timestamp is not the OBS render/capture time.

Continuously drain the capture backend, including subprocess pipes if used.
Retain only the newest complete frame for inference. Measure actual overwritten
frames. Avoid bounded application storage hiding an unbounded decoder/kernel
backlog. A slow-consumer test must show that the next consumed source sequence
is recent, not an increasingly old frame. Partial frames, malformed sizes, EOF,
permissions, wrong formats and blocked reads must be bounded and recoverable.
Use argument arrays, no shell execution; bound and sanitize stderr handling.

Initial encoder: `obs-rgb-letterbox16-v1`. Preserve the whole selected source's
aspect ratio, letterbox to a 16x16 grayscale uint8 Observation, normalize by 255,
and use the current retinal mapping. Fix and document the grayscale formula,
resampler, rounding and padding value. Do not auto-normalize contrast, mirror,
move the crop, read text, or select regions from content. If padding is black,
remember it still stimulates the current L2 encoding. Declare format/color-range
conversion assumptions. Any explicit ROI is a later version, not needed now.

Show two different previews when useful: latest source preview and the exact
16x16 observation actually used for the displayed neural response. Never label
an unprocessed new source frame as the input for an older response. Frame/response
IDs tie every displayed quantity to its actual observation.

The decoder cannot read raw pixels, media labels, a URL, input hashes, image
features, or world targets. Only the sensory encoder sees source pixels.

## 5. Source freshness and lifecycle

Pixel equality is not proof of failure: a valid static scene can remain unchanged.
V4L2 loopback may duplicate frames, so successful reads are not always proof that
OBS is producing new frames. Report content-unchanged duration separately.

Verify the installed producer-stop behavior. Use reliable driver/producer
metadata if available. If the tested driver cannot reveal producer inactivity,
use an authenticated local, read-only OBS status monitor (GetVirtualCamStatus/
output events, with a poll/heartbeat deadline) for verified mode. It must never
start/stop streaming, alter scenes, or change OBS settings. Keep credentials out
of the browser, traces, command lines, errors and archives. Do not claim that
"virtual camera active" proves the underlying captured application is updating.
Unsupported producer detection may allow an explicitly labeled preview, but the
verified OBS-stop safety gate remains blocked until reliable signaling is set up.
Never treat an ordinary black image as the unique stop marker.

Proposed configurable defaults (engineering bounds, not performance promises):
- 120 seconds per explicitly started interactive session, maximum 512 model calls.
- Source receipt/producer inactivity deadline: 2 seconds.
- One neural step hard deadline: 5 seconds; model startup deadline: 30 seconds.
- Completed response older than 2 seconds from input receipt: not applied to flight.
- Browser control lease: expires within 3 seconds without renewal; hidden/closed
  control tab releases its lease and stops (with an explicit visible-tab resume).
- Stop acknowledged promptly; stop scheduling immediately and terminate/reap
  owned capture/model subprocesses within 3 seconds if cooperative stop fails.
- 32 MiB optional replay artifact cap per session; exceeding it stops recording/
  the session explicitly instead of dropping required trace events silently.

Use explicit state transitions: idle, previewing, starting, running, stopping,
stopped, source_lost, failed, limit_reached. Assign each session a unique ID and
generation; reject late frames/results from old generations. No automatic retry
or automatic resumed inference after a failure or reconnect. Start/Stop requests
are idempotent; one active session is enforced across processes. Respect the
existing P00 model lock so P00 and live jobs cannot concurrently use the protected
model resource. A documented reuse of the existing lock avoids changing P00.

Stale input, late inference, transport loss or expired ownership must neutralize
new movement commands. Model-driven pose advancement stops under the documented
neutral policy. Decorative idle wing motion is allowed only as clearly ordinary
animation; it must not look like continued autonomous flight after disconnection.

## 6. Flight implementation

Use a small third-person 3D scene. A procedural fly built from original basic
geometry is sufficient: head, thorax, abdomen, eyes, six legs and two visible wings.
Use one local rendering dependency if needed, pinned in the lockfile; no remote
CDNs or purchased assets. A minimal scene should be viewable early with a prominent
SYNTHETIC/REPLAY label while the real integration is under construction.

The flight decoder maps selected measured motor rates to bounded yaw, pitch and
thrust/speed targets. Choose one simple, explicit mapping with fixed scales,
deadbands, smoothing and limits. Explain each channel and its units. No parameter
sweep, unadvertised baseline balancing or action selected from pixels. Do not
inherit the unsuccessful arena's direct cursor-to-position movement or its walls.

It is acceptable to use a nonnegative activity readout for thrust and opponent
rates for turning: this is an engineered flight interface, not a physiological
claim. Neural silence must not produce translational flight or random maneuvers.
Keep the original raw actions and rates in recorded evidence. Wing flapping and
banking may be renderer animation; identify their rules separately.

Implement a pure deterministic flight-state update at a fixed time step. The
server/session coordinator owns authoritative position/orientation/state; the
browser interpolates snapshots and never integrates movement at variable browser
frame intervals as the authority. Replay uses recorded control-application ticks,
seed/config and initial state. Test tolerances explicitly across numerical runtimes.

An open/repeating visual space with a following spectator camera avoids trapping
at artificial boundaries. Specify any visual world rebasing; it must not change
physical state or choose a target. No invisible goal attraction, forced successful
path, rescue teleport, or autonomous wandering when the model is unavailable.
This source is independent of the fly's world; do not call it closed-loop game
control. Do not feed the third-person output back into the input by default.

## 7. Local API, records, and privacy

Use strict, versioned Pydantic schemas and generated TypeScript/runtime validation.
Implement device metadata, preview control, session start/stop/status, live
snapshots, and opt-in recorded replay listing/read. Choose one transport (SSE is
adequate) with bounded per-client buffering. Reconnect returns a current snapshot;
it must not launch a job or replay an unbounded backlog. Terminal state remains
queryable. Stale/out-of-order/foreign-session messages are rejected.

Loopback bind and trusted hosts; same-origin writes; explicit control ownership;
no permissive CORS. Mutations need an origin/token/session check appropriate to
a local app so a hostile website cannot start desktop capture. Validate sizes,
IDs, formats, finite numbers and limits. Serve only approved assets; never expose
arbitrary files from the checkout. Distinguish 409 busy, 4xx validation, and 503
unavailable. Status/health reads do not capture or run the model.

Use local manifests, bounded event files and append-before-call ledgers; no new
database or database server is needed. Persist manifests atomically, fsync where
needed, detect corruption, and distinguish partial/aborted recordings from complete
ones. Replays reject inconsistent hashes/versions and never execute inference.
Artifact paths derive from server-generated IDs under a fixed private root.

Recording is explicit and off by default. Raw full-resolution desktop frames are
never saved in this scope. With recording consent, save exact processed 16x16
inputs, raw responses, applied controls/ticks, flight snapshots or verifiable state,
source/encoder/decoder/model identities and timing needed for replay. Those inputs
can still be sensitive: treat them as private data. Session counters/status may
persist without recording. Include full provenance once per session, not every
frame; use bounded lightweight identifiers in live packets.

Do not publish private input previews, screen recordings, OBS credentials, or
session archives in GitHub Actions artifacts. Fixture evidence is safe when labeled.
Prepare a sanitized review bundle only from operator-approved test content.

## 8. Compute authorization in the copied implementation prompts

The new workstream permits up to 1,024 additional full-model attempts TOTAL for
automated implementation validation across OBS00–OBS06. This is a ceiling, not a
target. Count before invocation and persist across failures/restarts; no hidden
reruns or relabeling automated calls as manual to evade it. Fixture graphs do not
count as real calls and cannot satisfy real gates. Run only the tests justified
by affected boundaries, then proceed.

Manual browser sessions require a human's explicit Start and have their own
120-second / 512-call per-session bounds and usage records. No unattended repeating
sessions. This is a new scoped allowance, not permission to reset or edit the P00
256-call ledger. Store all new live accounting separately. Show remaining validation
allowance when running agent-driven validation.

## 9. Required operator commands

Implement actual commands/targets, with help and meaningful nonzero failures:
- `make live-devices` — metadata only.
- `make live-doctor` — runtime/data/backend checks; hardware check only for an
  explicitly selected device. Explain missing prerequisites.
- `make serve-live` — start local app idle; report the verified URL.
- `make test-live` — unit/property/contract/local integration, no hardware required.
- `make test-live-ui` and `make test-live-e2e` — routine fixture UI/browser checks.
- `make test-live-real` — real connectome with a declared replay/test frame source.
- `make test-live-obs` — actual approved OBS source plus real model/browser gate.
- `make verify-live` — complete fast checks plus current relevant lab checks.
- `make verify-live-real` — aggregate required real-source/model evidence; fails
  nonzero if data, hardware, permission or evidence is missing.

Allow an evidence-directory override to avoid overwriting historical evidence.
Scripts for the operator's PC must be checked-in `.sh` files when shell is needed,
with contents and path shown in the handoff. Do not pipe remote scripts into a shell.

## 10. Exit criteria and reporting

The deliverable is usable: select and preview the source, Start, see a recognizable
fly receiving real neural-driven controls, change OBS content, Stop, and replay an
opt-in recorded session without recomputation. Inspect desktop/mobile captures.

Report implementation, real-model, real-OBS, causal-control, and human product
review separately. A missing device can block the final real gate while independent
implementation continues. A hard-coded fixture animation cannot count as real.
Weak input influence is reported as such; do not invent competence, silently tune
until a flattering example appears, or abandon completed integration for a new pivot.
Human taste review asks about appearance, movement, framing and responsiveness.
