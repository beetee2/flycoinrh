# OBS04 — local session API and private opt-in replay

2026-09-15. **Implementation and local validation PASS / COMPLETE. Stop before
OBS05.** Starting checkout was clean at
`d07841cfe426c36e01c5c805a790d6448f420c64`. The first saved hash snapshot followed
concurrent task-owned edits; its nonempty status is explained in
`artifacts/milestones/OBS04/initial-status-observation.json`. No newer user work
was present or replaced. The separate CI-fix worktree was preserved.

## Approval and hosted prerequisite

The operator explicitly approved repaired-build Load, Play, Pause, Stop, Reset,
synthetic playback, and current appearance/motion at the starting revision, after
enabling hardware acceleration in their normal browser. This is **operator
confirmation, not an independently executed agent test**. The approval is appended
to [OBS03](OBS03.md); its original failure, repair and pending-review evidence remain.
It authorized OBS04 only and added no desktop recording or capture consent.

Hosted run [34991210953](https://github.com/beetee2/flycoinrh/actions/runs/34991210953)
for that exact revision finished **FAILURE**. Foundation checks passed, as did live
Python/UI/schema/build checks. All eight live browser tests failed before browser
startup: Ubuntu 24.04 AppArmor denied Chromium's user-namespace sandbox. This was
a runner prerequisite failure, not evidence against the operator's browser result.

The workflow now installs the pinned browser under the runner's temporary directory
and loads an AppArmor rule for that exact headless-shell executable. Chromium's
sandbox stays requested; no global sysctl or local host policy was changed.
Actionlint 1.7.7, extracted Bash syntax/profile construction, AppArmor compilation
in an unprivileged Ubuntu 24.04 container without kernel policy loading, and local
browser startup all **PASS**. Exact commands and earlier validation errors are in
`ci-prerequisite/summary.json` under the evidence root. **Hosted validation of the
repair is NOT_RUN**: no push or workflow dispatch was authorized or performed.
The historical failed run is never used as a passing prerequisite.

## Implemented service and ownership

`flytrap/live/api.py`, `api_contracts.py` and `service.py` connect the existing
capture, neural-session and flight modules through an actual local FastAPI service.
Startup creates no capture, model worker or recording. Default source discovery
uses metadata; explicit inspection validates the selected V4L2 source and reports
its current format. Start rechecks the OBS device identity and reliable producer
detection; an unavailable source fails closed, without webcam or fixture fallback.
Synthetic session factories are injected only by tests, not selected by production
browser requests. P00 remains available through its existing separate `/lab` service.

| Endpoint | Behavior |
|---|---|
| `GET /health/live`, `/api/live/config` | Passive availability/capability reads, reporting OBS04 |
| `GET /api/live/control` | Browser CSRF bootstrap and explicit recording privacy notice |
| `GET /api/live/sources` | Bounded source metadata, no capture |
| `POST /api/live/sources/inspect` | Explicit selected-source metadata inspection, no capture |
| `POST /api/live/preview` | Explicit capture-only preview, at most 30 seconds |
| `POST /api/live/sessions` | Explicit session Start; strict config and per-Start recording consent |
| `GET /api/live/status`, `/api/live/sessions/{id}` | Current status and authoritative snapshot, including terminal state |
| `POST /api/live/sessions/{id}/renew`, `/stop` | Owner-token and generation checked lease/Stop |
| `GET /api/live/sessions/{id}/preview` | Passive newest-source thumbnail and processed pixels; never starts capture |
| `GET /api/live/sessions/{id}/events?generation=1` | Current-snapshot SSE with bounded clients and buffering |
| `GET /api/live/replays`, `/api/live/replays/{id}` | Private recording listing and verified read |
| `GET /api/live/replays/{id}/seek?tick=N` | Deterministic flight state at a bounded recorded tick |

Control POSTs require exact same origin, a signed HttpOnly/SameSite cookie plus
matching CSRF header, JSON, and an 8,192-byte body completed within two seconds.
Trusted hosts are loopback only. There is no permissive CORS, arbitrary file/path,
command, URL or upload input. Validation, ownership conflicts, spectator capacity,
and unavailable prerequisites produce distinct 4xx/503 responses.

Each explicit Start/Preview supplies a random per-tab owner secret and request ID.
Identical retries return the same session, including after it becomes terminal;
changed parameters conflict. Only that owner can renew or stop. The existing
cross-process live/P00 locks enforce exclusive capture/model ownership, including
failed cleanup. Each new session has a server UUID and generation; stale generations
cannot renew or reconnect. The service retains the latest 32 sessions and remembers
256 request IDs for its process lifetime; retired IDs cannot revive work. Exhausting
that admission bound requires an explicit idle service restart.

The lease expires within the configured maximum three seconds without renewal.
The browser transport in `web/src/live/session-client.ts` renews at most once per
second, has an independent local expiry timer, and releases on hide, pagehide,
dispose or transport failure. It subtracts request elapsed time from the server's
remaining duration; it never compares Python and browser clock origins. Spectators
cannot acquire or extend ownership. Complete operator controls and renderer wiring
remain the separately selected OBS05 work; the existing `/live` stage stays a
clearly labeled synthetic preview, with a visible recording privacy explanation.

SSE admits at most four clients, including pending subscriptions, with one queued
snapshot per client. Slow clients overwrite old snapshots and cannot block inference.
Reconnect returns current state, without replaying historical events or scheduling
work. Packets include session/generation, sequence, authoritative flight tick,
source/response identity, timing ages, lifecycle and recording state. The client
rejects malformed, foreign, duplicate and out-of-order packets. Newest-source
preview, fresh applicable neural sample, and historical last-inferred input are
separate fields. Blocking snapshot acquisition runs outside the API event loop.

## Recording and replay

Recording defaults off. Both config opt-in and matching consent are required on
every Start. No real desktop recording was performed. All storage tests used safe
synthetic inputs and private temporary directories; no private inputs or archives
were added to CI artifacts or Git.

`recording.py` reserves a private server-generated recording ID before capture.
Unknown startup provenance is represented by a partial reservation, never invented.
Once the existing worker supplies its identity, the recorder saves provenance once,
exact processed 16×16 inputs before dispatch, every raw worker response, neural
samples, applied controls/ticks, initial state and the verified terminal flight trace.
It saves no full-resolution RGB video, OBS credentials or owner tokens.

Storage lives under ignored `artifacts/live/recordings/`, separate from evidence
and ledgers. Directories require 0700 and files 0600. Atomic manifests, fsync,
manifest/event hashes, a final completion seal, and recording-ID binding reject
partial writes, unsupported versions, altered files and transplanted archives.
The configurable maximum 32 MiB includes reservation, events, manifest, seal and
temporary files at publication peaks. Listing is bounded to 128 records and
verifies complete records before advertising completion. Corrupt records remain
visible as errors; partial/aborted recordings cannot be replayed as complete.

Recording writes occur outside the session lock. A watchdog enforces Stop/lease
and reaps capture/model resources during a stalled write. Interrupted recordings
remain incomplete; an unresolved filesystem operation can retain a private writer
thread until the OS operation returns, but cannot retain the model or source.
Input/response freshness is rechecked after persistence. Final recording publication
is separate from resource cleanup: a terminal session can briefly show `partial`
until fsync and verification succeed. A pending interrupted model input prevents
completion. Write/cap failures never silently drop required events.

Ordinary replay reads/seek validate hashes, versions, metadata, raw sample/control
agreement, and exact full flight-state reproduction. They import no model runner,
open no source handles and invoke no neural computation. Replaying the HTTP-created
synthetic recording preserved artifact bytes and ledgers under explicit traps for
model, capture and ledger activity. No neural recomputation endpoint was added.

## Actual validation

Evidence root: ignored `artifacts/milestones/OBS04/`. Final exact argv, cwd, exits,
elapsed time and source hashes are in `final-success/commands.json` and the two
source manifests. XML and browser reports carry actual collection/pass/fail/skip
counts; `final-success/counts.json` summarizes XML. Counts overlap and must not be
summed as unique tests. All final suites below have zero failures/errors/skips.

| Command/check | Actual result |
|---|---|
| `make verify test-upstream EVIDENCE=artifacts/milestones/OBS04/final-success/foundation` | **Exit 0**: 2,965 Python, 150 upstream, 89 web contracts, 9 UI, 2 browser passes; doctor/schema/lint/build/dependency gates PASS |
| `make verify-live LIVE_EVIDENCE=artifacts/milestones/OBS04/final-success/live` | **Exit 0**: 583 live Python, 193 live UI/contracts, 124 lab Python, 15 lab UI, 8 browser passes |
| Actual TCP HTTP integration, included above | **13 PASS**: lifespan, blocked-model health, ownership/origin/body bounds, concurrent Start/retries, stale epochs, spectator lease expiry, reconnect/client cap, unread-socket backpressure, source/worker cleanup and HTTP recording/replay isolation |
| Temporary filesystem storage, included above | **47 PASS**: private permissions, caps, atomic write/fsync/rename failures, partial/error states, corruption/version/metadata/traversal/ID mismatch and exact replay |
| Recording lifecycle faults, included above | **7 PASS**: stalled input/sample writes with Stop/lease, write errors, delayed-response neutrality |
| Browser transport lifecycle, included above | **15 PASS**: explicit acquisition, consent, lease timers, hidden/closed tab release, failed renewal, passive reconnect and ordering |
| Protected identities | **60/60 unchanged**, exit 0, compared with prior repair evidence |

The maintained desktop/mobile browser suite was run because API capability schemas
and the page privacy text changed. Standalone successful WebGL context probes and
the installed-browser diagnostic suite were not repeated. The parent opened final
desktop/mobile synthetic-stage screenshots: original body/head/eyes, paired veined
wings, legs and repeated landmarks remain visible. This is regression inspection,
not new operator approval of real neural-driven flight. Existing dependency
deprecation warnings and the renderer chunk-size advisory remain in logs.

Development failures are preserved. The first HTTP run had eight passes and two
failures: a temporary test stub and an SSE iterator lifetime error in the test.
The next recording check exposed the worker's obsolete OBS02 recording rejection;
removing that guard enabled supervisor-owned recording, with model dynamics intact.
An old idle-only test expected Preview to be absent and was updated for the protected
endpoint. The first broad attempt (`final/`) had **2,964 passes, one failure**:
the new stalled-write test acquired ownership before the coordinator signaled final
accounting/lock cleanup. It now waits for that explicit signal within the deadline;
the focused coverage run passed 7/7 and the final aggregate passed. Early client
Response-reuse/type errors and storage test expectation fixes remain in their
respective evidence summaries. No failed run was overwritten or relabeled PASS.

## Preserved model and accounting

CPU baseline, graph/checkpoint identities, `windowed_reset`, all-one gains, disabled
learning, 100 × 0.2 ms integration, reset/seed progression, sensory encoder and
fixed flight decoder/physics remain intact. The worker's only functional change
removes its obsolete recording prohibition; persistence belongs to the coordinator.
No GPU integration, learning change, new database, upstream merge or renderer
redesign was introduced. LICENSE, NOTICE, attribution and both kits are preserved.

Actual ledgers before/after: **OBS 9 / 1,024, 1,015 remaining; P00 144 attempts**.
OBS04 made **zero additional full-model calls**. Tiny synthetic model calls use
temporary fixture ledgers and do not satisfy a real-model or real-OBS gate.

## Handoff and stop

`make serve-live` starts the actual local API idle at **http://127.0.0.1:8767/live**.
The service was started after validation; `/live`, health, config, empty status
and replay listing returned 200. Status had no session and no recording root was
created. See `local-service.json` and `local-service.log`. Runtime and exact identity
records are retained there and in the final source manifests.

| Gate | Status |
|---|---|
| OBS03 repaired-build operator playback and appearance/motion | **APPROVED**, explicit operator confirmation at `d07841c` |
| OBS04 implementation and local required checks | **PASS / COMPLETE** |
| Hosted run for `d07841c` | **FAILURE**, sandbox launch prerequisite identified |
| Hosted repair | **Local validation PASS; hosted rerun NOT_RUN**, requires future authorized push |
| OBS04 real neural-driven browser flight / real OBS / desktop recording | **NOT_RUN**, no expanded consent or real-flight claim |
| OBS05 / OBS06 / public release | **NOT_AUTHORIZED** by this instruction |

**Stop before OBS05.** A future authorized invocation may select
`flyjam-obs-kit/prompts/05-browser.md` to connect the tested transport, actual API,
source controls and replay to the existing stage. Preserve recording opt-in,
resource/lease deadlines, protected identities and current accounting. Real-source
execution still needs applicable capture consent; public release and remote writes
remain separate decisions. No push, deployment, paid service, token transaction or
social post was performed.


## OBS05 prerequisite revalidation — 2026-09-15

The OBS05 invocation explicitly supersedes the previous stop. Read-only inspection
of [hosted workflow 34995107755](https://github.com/beetee2/flycoinrh/actions/runs/34995107755)
confirmed **completed / success** for exact revision
`2bc0c675c62b5aeaaa5393697f02406d53a7b195`. The scoped browser sandbox prerequisite,
`make verify test-upstream`, and `make verify-live` all succeeded. Evidence is
`artifacts/milestones/OBS05/hosted-workflow.json`. This resolves the prior hosted
revalidation pending handoff; the original failed run and local repair records
above remain historical evidence. OBS03 operator appearance/motion approval remains
approval of the repaired synthetic preview; it does not approve real neural flight.
