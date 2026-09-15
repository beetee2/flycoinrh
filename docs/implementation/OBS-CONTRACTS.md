# Flyjam live v1 foundation and operating policy

## OBS02 neural session operations

`NeuralSession(config, purpose=...)` is an internal coordinator. Construction and
snapshots are idle; `start()` is explicit and idempotent. Each new session has a
new ID, one continuous reader and one persistent isolated model process. A caller
must renew its control lease while working. Terminal sessions never restart.
Real sources require an operator-confirmed device configuration and verified
producer health. Initial model validation explicitly uses `fixture-pattern` pixels
with the actual full graph; fixture-source identity does not imply a fixture model.

The coordinator acquires `artifacts/live/session.lock`, then the existing P00
model lock, without waiting. The worker inherits both open lock descriptors.
Linux parent-death guards are installed before exec for the model and FFmpeg.
Stop prevents new scheduling, clears applicable output, and reaps the model.
If capture cleanup exceeds its bound, status becomes failed and ownership remains
held until the actual reader/child terminates. A failed cleanup cannot admit a
second live session. Lock files are never replaced during normal ownership.

The worker compiles raw-annotation retinal indices once and checks them against
the independent P00 oracle at load. The passive live tap checks actual retinal
drive before each ordinary inference, retaining original pilot action, motor
rates, adapter output and statistics. Frame sequences and model step indices are
distinct; one request is in flight and each next request takes the latest frame.
It keeps the original 100 × 0.2 ms integration and internal step-seed sequence.

`SessionSnapshot.sample` is present only when applicable and fresh. Its separately
named `last_inferred` and `last_completed` are historical measurements, never
commands. Snapshots also report waiting state, completed/attempted calls, drops,
receipt age, last step wall time, completed neural milliseconds and observed
average model Hz since readiness. The final rate is frozen at termination.
Producer-to-consumer latency remains unknown for sources without producer timing.
Full graph/annotation payloads never enter IPC responses or snapshots; session
provenance is retrieved separately and hashed once during startup.

Each real call is charged and fsynced before execution. Automated calls use both
the fixed workstream ledger and a per-session ledger; human Start uses its own
bounded session ledger. A hash chain and durable checkpoint reject partial,
edited, missing or truncated accounting. Interrupted accounting fails closed.
Removing all accounting artifacts is outside this local corruption protection;
never reset them to obtain another allowance. Fixture model tests use disposable
roots and cannot satisfy real validation.

`make test-live-real LIVE_REAL_EVIDENCE=<new-directory>` runs the fixed nine-call
OBS02 gate under a 90-second process-group deadline: three safe-source live steps,
three untapped adapter references and three historical-tap references. It refuses
existing evidence directories and fails nonzero for missing data. It persists
synthetic input measurements only, with recording disabled. Do not rerun it simply
to obtain another demonstration; the workstream allowance persists across runs.
The OBS02 execution report is [OBS02](milestones/OBS02.md).

## Scope and executable boundary

OBS02 adds a supervised neural session, compiled retinal verification and separate
durable accounting. OBS01 adds explicit CLI source inspection/preview, continuous capture, a pure
encoder and driver/authenticated producer monitoring. See [OBS01](milestones/OBS01.md)
for actual hardware checks. OBS00 provides strict Pydantic contracts, generated JSON Schema and TypeScript,
AJV runtime parsing with shared synthetic positive/negative cases, metadata-only
device discovery, a prerequisite doctor and an idle local application. Neural
sessions run through the internal coordinator and the dedicated real-model gate.
Decoder execution, physics, browser session control, streaming and
replay execution are later numbered deliverables. The idle browser API explicitly reports
`capture_implemented: false` and `inference_implemented: false`.
Those flags describe its still-idle browser controls; source preview is currently
the separate explicit CLI operation below. Browser control API integration is OBS04.

Contracts live in `flytrap/live/contracts.py`; generated browser contracts are in
`web/src/live/generated/`. Run `make generate-live` after an intentional interface
change and `make check-live-generated` to detect drift. Every top-level wire type
has a literal version. Unknown fields/versions, nonfinite or out-of-range numbers,
unsafe JavaScript integers, arbitrary source paths/URLs, invalid epochs, foreign
stream identities and replay path traversal are rejected. Python additionally
distinguishes integer objects from floats; JSON/JavaScript has one number type.

| Contract | Meaning |
|---|---|
| SourceCapability | Safe source ID, bounded metadata, driver/backend, known formats or null, producer detection and explicit real/fixture label |
| FrameIdentity | Source/session/generation/sequence, RGB dimensions and receipt/producer clock metadata |
| EncoderConfig | Versioned deterministic 16×16 whole-source letterbox encoding |
| NeuralSample | Frame identity, exact 256 uint8 input values, response ID, step, raw motor rates/actions and timing |
| FlightControls | Response/session/generation, finite bounded yaw rate, pitch and speed targets, issue/expiry times; no source pixels or targets |
| FlightSnapshot | Authoritative fixed tick, world position, yaw/pitch/speed, last applied response and neutral state |
| SessionConfig / SessionStatus | Explicit source/seed/recording choice, limits, lifecycle, counts and distinct freshness indicators |
| StreamEnvelope | Current status plus optional latest source, actual inferred input/response, and authoritative flight; matching session/epoch/evidence |
| ReplayManifest | Recording consent, fixed event filename/digest/size, source/config, initial state and model/runtime/source provenance |

The decoder's future input is the measured motor rates and explicit decoder state;
only the encoder sees raw source pixels. Frame and neural contracts are coordinator
records and must not be passed wholesale into the decoder. Replay hash verification,
sequence admission, source identity revalidation, state transitions and filesystem
publication remain runtime obligations in their numbered milestones. Structural
schema acceptance is not a passing replay or real-model gate.

## Encoder definition frozen for OBS01

`obs-rgb-letterbox16-v1`: decode into full-range RGB24 in top-to-bottom row order.
Convert YUV with declared BT.601 coefficients/range; opening must reject unsupported
or ambiguous color metadata rather than silently reinterpret it. RGB sources are
assumed full range. Grayscale is `(77*R + 150*G + 29*B + 128) // 256`, integer uint8.
Let `s = min(16/W, 16/H)`; resized dimensions are
`max(1, floor(W*s + 0.5))` and `max(1, floor(H*s + 0.5))` (half-up rounding).
Place at `(floor((16-w)/2), floor((16-h)/2))`; extra odd padding goes right/bottom.
Nearest-pixel-center resampling selects `floor((x+0.5)*W/w)` and
`floor((y+0.5)*H/h)`, clamped to the last source pixel. Pad with zero and normalize
each final byte by 255 for the existing float32 retinal mapping. No mirroring,
contrast normalization, content-selected crop or ROI. Black padding still drives
the baseline L2 population. OBS01 must implement golden/reference tests.

## Clocks, freshness and flight policy

Wire local times are monotonic milliseconds bounded to the JavaScript safe numeric
range, scoped to the server process/session. Receipt time is when a complete frame
arrives locally, not OBS render time. Producer timestamps/sequences are nullable;
unknown source clock requires a null timestamp. Non-null producer time requires an
explicit producer or local-monotonic clock label; do not subtract different clock
domains. Process restarts create new sessions/epochs. Old or foreign results cannot
be admitted by a new session. A response retains the exact frame/observation used;
the separately displayed latest preview can have a newer sequence.

Unchanged-content duration is independent of source/producer liveness. Static
images can be valid; repeated reads and ordinary black frames do not prove OBS
health or uniquely indicate a stop. OBS01 must test the installed driver's stop
behavior. If needed, verified mode uses authenticated, local, read-only OBS status
and a heartbeat deadline. No credential appears in browser data, command arguments,
traces or archives. Virtual-camera-active does not prove the source app is updating.

Default session bounds (configurable downward): 120 seconds, 512 attempted calls,
2,000 ms source/producer inactivity, 5,000 ms hard neural step deadline, 30,000 ms
startup deadline, 2,000 ms maximum response age from receipt, 3,000 ms browser lease
and 3,000 ms owned-process stop/reap grace. Recording cap is 32 MiB. Control expiry
is at most 2,000 ms and must not extend past input age or the session lease. Fixed
authoritative flight step is 20 ms; yaw is bounded ±π rad/s, pitch ±π/4 rad and
speed 0–10 world units/s. OBS03 freezes the actual fixed mapping, deadbands,
smoothing and acceleration limits before measurement; these schema limits are
interface ceilings, not measured performance or physiology.

Stale input/results, transport loss and expired ownership neutralize commands and
stop model-driven pose advancement immediately under the future coordinator.
Neutral policy freezes pose and sets translational speed to zero; it never invents
wandering. Silence must produce zero translation. Browser interpolation is display
only. Any decorative wing animation must be labeled ordinary animation.

Lifecycle states: idle, previewing, starting, running, stopping, stopped,
source_lost, failed, limit_reached. Start/Stop will be idempotent and require
same-origin authenticated control ownership, explicit operator source selection,
and visible-tab lease renewal. Failure/reconnect/replay never auto-starts work.
Health/config reads never capture, discover devices, inspect model data or infer.
The OBS00 service has no mutation routes and no CORS allowance.
Its security header blocks remote resources and framing; `unsafe-eval` is needed
by the existing AJV compiler for trusted bundled schemas. Client-supplied schemas
or executable code are never accepted.

## Ownership, compute and storage

One active live session across processes; capture continuously drains into
a capacity-one latest-frame slot, and one persistent model worker loads once per
session. A persistent worker does not change the model's `windowed_reset` dynamics:
reset controller once at session start, preserve internal step-seed progression,
100 × 0.2 ms integration, all-one immutable gains/weights and disabled learning.
The live adapter/tap stays outside source-bound historical model files.

OBS02 acquires the same exclusive flock at
`artifacts/milestones/P00/model.lock` for the full model-worker lifetime, together
with an independent live-session lock under `artifacts/live/`. Keep a consistent
lock acquisition order and fail busy rather than queue. Do not replace the lock
inode. P00's 256-call ledger stays separate and unchanged.

Automated validation across OBS00–OBS06 has a total ceiling of 1,024 full-model
attempts. OBS00/OBS01 use zero; OBS02 validation used nine. Append-before-call/fsync ledger:
`artifacts/live/validation/attempts.jsonl`; hold model/accounting locks, fail closed
on corruption/exhaustion, count failures/restarts and never reset it when choosing
a new evidence directory. Fixture calls cannot satisfy a real gate. Explicit human
Start has separate 120-second/512-call session accounting, not unattended runs.

Future browser operator source configuration will live under ignored
`artifacts/live/operator/source.json`, with a server-approved ID resolving to a
revalidated local character device/driver/format. OBS01's CLI requires an explicit
source ID for each inspection or preview; it stores no selection or desktop pixels.
Session IDs are server generated; private manifests/events will be under
`artifacts/live/sessions/<id>/`. Recording is opt-in/off by default. Save no raw
full-resolution frames; even recorded 16×16 observations can contain private data.
Persist complete provenance once per session and lightweight IDs in packets.
Use atomic manifests, bounded event files and corruption-aware replay validation.

Milestone evidence is separately under `artifacts/milestones/OBSNN/` (ignored).
Fast CI uses synthetic inputs and stores only test reports. Never upload private
previews, credentials or sessions to CI. A review bundle needs operator-approved
test content. No new database is needed.

## Backend and operator commands

Chosen backend: bounded **FFmpeg V4L2 subprocess**, argument arrays and no shell.
Installed FFmpeg `n9.0.1` advertises the `video4linux2,v4l2` demuxer in `-devices`
and documents its options in `-h demuxer=v4l2`; the actual output is saved in the
OBS00 environment evidence. This avoids a new Python binding and uses the installed
Linux video backend. OBS01 must continuously drain stdout/stderr, cap diagnostics,
bound partial/blocked reads, terminate/reap owned children, and test freshness
through backend buffering. OBS00's metadata subprocess runner already bounds
output and time; it does not implement a capture reader.

- `make live-devices`: sysfs names/driver and character-device/access metadata.
  Never opens device nodes. Capabilities/formats are explicitly unknown until an
  operator selects a source for ioctl inspection. No source is selected by default.
- `make live-doctor`: installed runtime/tool support, disk, model/raw/checkpoint
  byte identities and device metadata. Nonzero if required prerequisites are missing.
  It does not load the graph into a model or run a real-model gate.
- `make serve-live`: idle service at `http://127.0.0.1:8767/live`; use
  `make serve-live LIVE_PORT=8877` if occupied. Never stop an unrelated listener.
  Build UI first with `npm --prefix web run build`. CLI help:
  `.venv/bin/python -m flytrap.live --help` (also per-subcommand help).
- `make test-live`, `make test-live-ui`, `make test-live-e2e`, `make verify-live`: hardware-free
  foundation contracts/API/metadata and current lab regressions/types/build.
  Override `LIVE_EVIDENCE` to a fresh path for test reports. Metadata reports can
  be saved using `devices|doctor --evidence-dir <new-directory>`; existing report
  files are refused to preserve evidence.

No new dependencies or shell scripts are needed. The maintained browser check
tests the actual idle service on desktop/mobile, including reload and page errors.
Source/session browser E2E, real-model, real-OBS and aggregate real gate targets
belong to subsequent implementation; the OBS00 fast pass does not imply their
existence or success.

## OBS01 capture operations

- `.venv/bin/python -m flytrap.live inspect-source --source v4l2-videoN` performs
  bounded read-only ioctls on exactly the operator-selected device. It does not
  start capture. `doctor --source v4l2-videoN` adds that selected inspection.
- `.venv/bin/python -m flytrap.live preview --source fixture-pattern --seconds 15`
  explicitly starts a synthetic preview and prints its private loopback URL.
  `--port` changes the default 8768 if occupied. It expires within 30 seconds,
  closes capture and discards the slot. No model calls or recording occur.
- With real-source selection, replace the source ID with the selected
  `v4l2-videoN`. Without reliable producer status it says **UNVERIFIED OBS PREVIEW**.
  `--verified` requires reliable driver status or an authenticated monitor.
  The verified v4l2loopback configuration uses exclusive capture/output
  capabilities and `keep_format=0`; loss of that condition terminates capture.
  Add `--obs-monitor --verified` to use authenticated local OBS status;
  the password is entered through a private terminal prompt, never an argument.
  `--obs-port` changes the local default 4455. Enable authenticated OBS WebSocket
  v5 through OBS settings. The monitor only identifies and calls GetVirtualCamStatus.
- Original harmless scene: [obs-test.html](../../flytrap/live/assets/obs-test.html).
  Add that file as an OBS local Browser Source, 960 × 540, or use the local app's
  `/live/obs-test` URL. OBS setup and Virtual Camera Start are operator actions.

The single backend is FFmpeg V4L2 → full-range RGB24 PPM frames on a continuously
drained pipe. PPM headers expose dimension changes. Read/partial-frame deadlines
and a separate device metadata watcher catch loss or format/identity changes;
one-slot replacement counts unconsumed frames. Source timestamps/sequences are
unknown/null for this backend. Local receipt times never stand in for OBS time.
The CLI preview only shows current source/encoded pairs with a common frame ID;
the later neural response must retain its own encoded input independently.

Accepted real input is progressive, tightly packed RGB3/BGR3/YUYV/NV12, 1–60 fps,
dimensions ≤8192 per side and at most 32 MiB decoded RGB. RGB requires sRGB/JPEG
full-range metadata. YUV requires SMPTE170M, JPEG or sRGB BT.601 metadata and known range.
Extended metadata is used only with the V4L2 capability and private magic marker;
legacy drivers use documented colorspace defaults and ignore undefined extension
bytes. Ambiguous color, compressed input, padded stride and interlacing fail closed.
The adapter never silently reformats OBS or substitutes another source.

FFmpeg queue size one, passthrough frame timing, prompt packet flushing and
continuous pipe draining are exercised with actual FFmpeg indexed fixtures.
That fixture evidence alone cannot establish installed V4L2/kernel/OBS buffer latency
or stop behavior. The selected-device stop/restart and real preview passed; see the
milestone report for the separate patterned-source result. The authenticated monitor
indicates OBS virtual-camera state, not whether its underlying application updates.
