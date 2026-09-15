# Flyjam live v1 foundation and operating policy

## Scope and executable boundary

OBS00 provides strict Pydantic contracts, generated JSON Schema and TypeScript,
AJV runtime parsing with shared synthetic positive/negative cases, metadata-only
device discovery, a prerequisite doctor and an idle local application. Capture,
preview, model calls, decoder execution, physics, session writes, streaming and
replay execution are later numbered deliverables. The idle API explicitly reports
`capture_implemented: false` and `inference_implemented: false`.

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

One future active live session across processes; capture continuously drains into
a capacity-one latest-frame slot, and one persistent model worker loads once per
session. A persistent worker does not change the model's `windowed_reset` dynamics:
reset controller once at session start, preserve internal step-seed progression,
100 × 0.2 ms integration, all-one immutable gains/weights and disabled learning.
The live adapter/tap stays outside source-bound historical model files.

OBS02 must acquire the same exclusive flock at
`artifacts/milestones/P00/model.lock` for the full model-worker lifetime, together
with an independent live-session lock under `artifacts/live/`. Keep a consistent
lock acquisition order and fail busy rather than queue. Do not replace the lock
inode. P00's 256-call ledger stays separate and unchanged.

Automated validation across OBS00–OBS06 has a total ceiling of 1,024 full-model
attempts. OBS00 uses zero. Planned append-before-call/fsync ledger:
`artifacts/live/validation/attempts.jsonl`; hold model/accounting locks, fail closed
on corruption/exhaustion, count failures/restarts and never reset it when choosing
a new evidence directory. Fixture calls cannot satisfy a real gate. Explicit human
Start has separate 120-second/512-call session accounting, not unattended runs.

Operator source configuration will live under ignored
`artifacts/live/operator/source.json`, with a server-approved ID resolving to a
revalidated local character device/driver/format. OBS00 stores no source selection.
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
