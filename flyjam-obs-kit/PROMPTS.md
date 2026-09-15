# Flyjam OBS — all ordered prompts

Read SPEC.md and TEST_MATRIX.md with every milestone. See README.md for installation and kickoff.


---

# OBS00 — scope, executable contracts, and environment

Read `flyjam-obs-kit/SPEC.md`, `flyjam-obs-kit/TEST_MATRIX.md`, applicable
`AGENTS.md`, actual git status, `docs/implementation/OBS-STATUS.md` if present,
and the latest relevant milestone report. Read the relevant implementation before
editing. Perform the actual work, run appropriate tests, and update the handoff.
Preserve user changes and existing evidence. Execute only this milestone.

Implement the foundation of the authorized OBS-to-flight workstream.

1. Confirm HEAD and local modifications. Read STATUS, PIVOT, P00 report, the
   controller, lab runner/sensory/API/budget, web entry point, Makefile and workflow.
   Adapt to newer local code without reverting it to the kit's reviewed revision.
   Update routing for OBS00–OBS06; do not resurrect the old navigation plan or
   falsely record P00 product approval. Explain any real instruction conflict
   using its exact file/section rather than inventing a permission gate.

2. Inspect Linux/distribution/kernel, Python and Node versions, relevant installed
   packages, disk, full model data/checkpoint, FFmpeg/V4L2 tooling and OBS presence.
   List capture device metadata without starting streams. Choose one supported
   capture backend. Do not install kernel modules, change permissions, use sudo,
   or open unselected sources. Missing host prerequisites produce an actionable
   setup note while independent code continues.

3. Create the live package and executable versioned contracts: source capability,
   frame identity/timing, encoder configuration, neural sample, flight controls,
   flight snapshot, session config/status, stream envelope and replay manifest.
   Strict sizes/types/finite numbers, epochs and explicit real/fixture labels.
   Generate TS types/runtime schemas with a drift check. Freeze the interfaces
   before delegating independent source/UI work.

4. Create a minimal live entry point, idle health/config endpoint and actual
   `make live-devices`, `make live-doctor` and `make serve-live` targets. It must
   not pretend capture/inference is implemented yet. Pin any new dependencies
   narrowly. Preserve existing app/lockfiles unless additions are necessary.
   Store operator configuration under an ignored local path or environment;
   source URLs and shell arguments are not accepted from clients.

5. Document session bounds, validation allowance, freshness/clock semantics,
   ownership, capture consent, evidence privacy, chosen backend, and planned
   artifact locations. Define acceptance states separately. Record the distinction
   between a persistent worker and unchanged windowed_reset dynamics.

Validation: strict schema positive/negative cases, TS/Python schema compatibility,
health/no-capture-on-start behavior, metadata discovery failure states, generated
checks, lint/types/build and relevant existing regressions. No real neural calls
are needed in OBS00.

Handoff: actual tests, selected backend, exact remaining setup needs and next
prompt. Stop. Do not demand a broad product reapproval to implement OBS01.


---

# OBS01 — OBS frame source, preview and exact Observation

Read `flyjam-obs-kit/SPEC.md`, `flyjam-obs-kit/TEST_MATRIX.md`, applicable
`AGENTS.md`, actual git status, `docs/implementation/OBS-STATUS.md` if present,
and the latest relevant milestone report. Read the relevant implementation before
editing. Perform the actual work, run appropriate tests, and update the handoff.
Preserve user changes and existing evidence. Execute only this milestone.

Implement the real source adapter plus a safe deterministic test source.

1. Implement source discovery/selection and bounded opening for an explicitly
   approved V4L2 OBS virtual device. Validate resolved device, driver/capabilities,
   pixel format, dimensions, rate and permissions. Do not probe by capturing every
   camera, default to /dev/video0, or substitute webcams/files on error.

2. Build continuous capture with a capacity-one latest-frame slot. Separate it
   from inference, include source epochs/sequences/receipt timestamps, and handle
   blocked reads, partial frames, format changes, EOF, stop, and cleanup. If using
   FFmpeg, use argument arrays; drain stdout/stderr and keep diagnostics bounded.
   Verify actual upstream buffering with a source carrying visible frame indices.
   No image equality-based automatic stop: a static scene is legitimate.

3. Add producer-state monitoring required by SPEC. Test actual virtual-camera
   stop behavior. If the driver repeats frames and lacks trustworthy producer
   status, implement the read-only authenticated local OBS monitor. Unsupported
   status cannot silently become a verified Live label. Do not modify OBS itself.

4. Implement obs-rgb-letterbox16-v1 as a pure encoder. Pin its precise color,
   aspect-ratio, resize, rounding and padding rules. Keep normalized Observation
   and exact uint8 bytes/hash together. No brightness adaptation/content targeting.
   Provide a latest-source preview and exact encoded preview with matching IDs.
   Preview starts only on an explicit operator action and expires without neural
   work. It must not persist raw desktop images.

5. Add a source-neutral deterministic test/replay implementation for fixture CI.
   It must be explicitly selected and labeled. Generate an original harmless
   test page/clip with moving shapes and frame counters for the operator's OBS
   scene; do not use their private desktop for automated validation.

Validation: unit/property/golden pixel tests, channel order/orientation/letterbox,
large/malformed frames, stale epochs, same pixels with new timing, slow-consumer
recent-frame assertions, reader-stop/hang failures, producer-status simulation,
and real-backend preview with the selected approved source when available.
No neural model calls are needed in this milestone.

Handoff: report the actual device/config and whether real capture and OBS-stop
signaling were verified. Ask only for missing specific host setup/source consent.
When hardware is unavailable, finish safe implementation/fixture checks and mark
real_obs_status PENDING or BLOCKED. OBS02–OBS05 may proceed with the declared test
source; final verified completion still requires actual OBS. Stop.


---

# OBS02 — persistent neural session, telemetry and bounded lifecycle

Read `flyjam-obs-kit/SPEC.md`, `flyjam-obs-kit/TEST_MATRIX.md`, applicable
`AGENTS.md`, actual git status, `docs/implementation/OBS-STATUS.md` if present,
and the latest relevant milestone report. Read the relevant implementation before
editing. Perform the actual work, run appropriate tests, and update the handoff.
Preserve user changes and existing evidence. Execute only this milestone.

Connect admitted source observations to the existing real model.

1. Implement a supervised session that owns one reader and one isolated neural
   worker. Load FlyController once per session. Reset once with the explicit
   baseline/seed; retain its internal per-step seed sequence and windowed dynamics.
   One new admitted frame triggers at most one ordinary inference. When overloaded,
   take the newest complete frame; never chase a capture backlog or shorten neural
   numerical integration. Keep frame IDs separate from model-step indices.

2. Collect raw motor rates, original action and existing statistics passively.
   Compile the independently checked retinal mapping once during model loading;
   reuse its small arrays in live steps. Do not call the P00 helper that rereads
   and hashes the annotation file every frame. Compare compiled results to that
   independent reference, including actual model data. Keep historical model
   files and checkpoint bytes unchanged. A new helper outside those files is
   preferred to modifying the source-bound baseline.

3. Implement the state machine, single-process-and-cross-process ownership,
   shared P00 model exclusion, source loss, stale input/result rejection, bounded
   start/step deadlines, Stop and shutdown. Reject late generation results. Reap
   owned children and release the source/lock. Parent death and hung child tests
   must not leave unattended inference. Waiting for a slow sample is a visible
   state; neither old samples nor noise stand in for fresh input.

4. Implement separate append-before-call live ledgers for the workstream's
   automated validation and human-started sessions. Preserve P00's ledger.
   Enforce the 1,024 automated-attempt ceiling across milestones/restarts; count
   failures. Interactive sessions require explicit Start and enforce SPEC bounds.
   No automatic retries, resumed runs or replacement seeds. A corrupt ledger
   cannot create a fresh unlimited allowance.

5. Expose typed snapshots for downstream decoder/API without full graph/annotation
   payloads per frame. Hash source/model/config identity once per session. Include
   observed timing, capture drops, actual model Hz, cumulative simulated neural
   time and source/step identities. Explain any unavailable timing measurement.

Validation: synthetic process and clock tests, model-load-count test, step-seed
progression, shared P00 contention, kill/hang/restart/failure, no stale result
application, ledger corruption/exhaustion, and a small real-model run on the
safe deterministic source. Prove equal inputs/config/seed reproduce the original
adapter output and live interception does not change it. Missing real data is
BLOCKED, not fixture-success. Record I/O-call instrumentation showing no repeated
raw-file reads in the hot path. Update OBS02 and stop.


---

# OBS03 — neural flight decoder and an early third-person fly

Read `flyjam-obs-kit/SPEC.md`, `flyjam-obs-kit/TEST_MATRIX.md`, applicable
`AGENTS.md`, actual git status, `docs/implementation/OBS-STATUS.md` if present,
and the latest relevant milestone report. Read the relevant implementation before
editing. Perform the actual work, run appropriate tests, and update the handoff.
Preserve user changes and existing evidence. Execute only this milestone.

Deliver visible movement without changing the neural model.

1. Define one explicit decoder version mapping raw motor-rate channels to yaw,
   pitch and thrust/speed targets. Write the formula, scales, deadbands, smoothing,
   units and caps first. Use a simple fixed mapping justified from existing
   recorded ranges, not a new parameter search. Preserve raw upstream actions.
   No direct source/image/hash/text access. Zero rates must produce neutral motion.
   This mapping is a human-engineered interface, not learned flight physiology.

2. Implement pure fixed-time-step flight physics and authoritative FlightState:
   orientation, position, velocity and sequence/tick. Bound acceleration/rotation;
   handle stale controls, Stop and source loss as SPEC requires. Keep control
   application ticks in the record. No arena goal/wall logic or invisible rescue.
   Use an open/repeating visual space and document any display-only rebasing.

3. Add a minimal third-person browser stage now. Prefer original procedural fly
   geometry with recognizable head/body/eyes/legs/wings and a simple scene that
   makes translation and turns visible. Use locally bundled assets/dependencies.
   Consume typed server/replay snapshots; frontend frame rate is not authoritative
   physics time. A clearly labeled synthetic control sequence may drive this
   early development preview and must never be labeled actual neural behavior.

4. Keep decorative wing cycles, bank animation and camera follow distinct from
   substantive neural movement. Stop must not leave the fly autonomously traveling.
   Do not replace absent neural output with random motion or a successful scripted
   performance. Provide renderer cleanup, reset and unavailable-WebGL behavior.

Validation: known rate-vector signs/bounds, nonfinite/missing schema rejection,
zero/saturated/constant controls, dt/replay invariance, delayed controls and
terminal states, neutralization, display-rebasing invariance, render-loop cleanup
and an actual browser smoke test. Record and open a screenshot or short local
capture of the recognizable fly. Hardware/model absence does not prevent this
explicitly synthetic presentation check.

Handoff: show the preview and the fixed mapping. Flag appearance/motion questions
for the human without pretending the real source is integrated. Continue toward
OBS04 when instructed; do not start an additional model experiment. Stop.


---

# OBS04 — local session API, streaming and opt-in replay storage

Read `flyjam-obs-kit/SPEC.md`, `flyjam-obs-kit/TEST_MATRIX.md`, applicable
`AGENTS.md`, actual git status, `docs/implementation/OBS-STATUS.md` if present,
and the latest relevant milestone report. Read the relevant implementation before
editing. Perform the actual work, run appropriate tests, and update the handoff.
Preserve user changes and existing evidence. Execute only this milestone.

Wire existing modules through a real local service; no new database.

1. Implement strict endpoints for source metadata/preview, session Start/Stop,
   status, current snapshot and bounded live events. One active owner, idempotent
   requests, trusted loopback hosts, same-origin writes plus appropriate session
   protection, no arbitrary path or command inputs. Starting capture is explicit.
   Status/reconnect/replay/health cannot initiate work. Keep P00 available.

2. Give the browser an expiring owner lease and require renewal. Closing or
   hiding the control tab releases it; missing renewals terminate within the
   deadline. Extra spectator connections cannot keep an abandoned control session
   alive, claim ownership, or spawn another model. Bound client count/queues.
   Do not compare Python monotonic timestamps directly with browser performance.now.

3. Serve current authoritative snapshots with session generation, flight tick,
   observation/response identity, timing ages and lifecycle. Implement reconnect
   from a current snapshot, ordering/deduplication and terminal-state query. Slow
   clients cannot block inference or receive an unbounded historical backlog.
   Differentiate newest-source preview from last accepted neural observation.

4. Implement optional recording, off by default, with user-visible privacy consent.
   Save exact processed inputs, raw responses, controls with application ticks,
   verified flight state and versioned provenance under private local IDs. Never
   persist raw full-resolution desktop video or OBS secrets. Atomic manifests,
   private permissions, byte bounds, partial/error state and hash verification.
   Do not mark failed/partial recordings complete.

5. Implement replay read/verification and seeking from these bounded records.
   Replaying controls/state performs zero neural calls and opens zero devices.
   Reject unsupported versions, corrupted events/manifests, path traversal and
   metadata mismatches. Keep optional neural recomputation a separately invoked,
   explicitly budgeted test—not part of ordinary replay.

Validation: actual HTTP-server integration with lifecycle startup/shutdown, health
while model blocked, concurrent requests, session ownership/origin/body-size
rejection, stream disconnect/reconnect/backpressure, idempotence, stale epochs,
lease expiration and partial artifacts. Use actual temporary filesystem storage,
not fake repository objects alone. Fault-test disk/write failure and corrupted
records. Test replay neutrality to ledgers and source handles. Update OBS04 and stop.


---

# OBS05 — usable OBS-to-flight screen

Read `flyjam-obs-kit/SPEC.md`, `flyjam-obs-kit/TEST_MATRIX.md`, applicable
`AGENTS.md`, actual git status, `docs/implementation/OBS-STATUS.md` if present,
and the latest relevant milestone report. Read the relevant implementation before
editing. Perform the actual work, run appropriate tests, and update the handoff.
Preserve user changes and existing evidence. Execute only this milestone.

Complete the operator experience around the actual live services.

1. Deliver `/live` with the fly stage as the primary visual, a source selector,
   explicit Preview, Start/Stop, session bounds/seed, record-replay consent and
   current status. A small approved source preview and exact last-inferred input
   belong behind a clear inspection toggle; neural tables are not the main page.
   Keep `/lab` working as a separate diagnostic experience.

2. Use strict runtime validation of every response/event. Display capture rate,
   neural update rate and rendering rate separately, with relevant ages and
   source/model mode. Properly label waiting, disconnected, stale, failed,
   replay and synthetic modes. Never smooth a failure into fake Live behavior.
   Make late/foreign-session packets harmless and show accepted input IDs.

3. Connect the actual server-authoritative flight state to the renderer. Smooth
   between legitimate snapshots without unbounded prediction. Browsers/tabs at
   different frame rates must not produce different authoritative trajectories.
   On transport loss or expired state, stop visual translational advancement
   within the documented limit. One renderer loop per mounted stage, cleanup on
   unmount, visible-tab/lease policy, clear browser-back/reload behavior.

4. Complete replay list/load/pause/seek, labeled recording playback and evidence
   download. No inference on replay or UI edit. Include clear artifact/privacy
   handling. Rendered controls/poses and downloaded trace refer to the same run.

5. Refine appearance with actual screenshots: identifiable fly silhouette,
   attractive restrained scene, useful scale/depth, visible turns and motion,
   readable status, keyboard-operable controls and responsive layout. Previewing
   or recording must not accidentally capture the output window. No need for a
   fly-eye camera, audio, token UI, gallery accounts or public publishing.

Validation: meaningful Vitest/Testing Library tests, keyboard/accessibility checks,
actual fixture-service Playwright journeys, small/desktop viewport, preview and
Start/Stop/error/replay paths, stale state and cleanup. Include a real-model
journey using the safe source under the workstream budget, and actual OBS when
approved/available. Test displayed neural values, accepted observation bytes and
server flight state—not only that a canvas exists. Open and inspect the screenshots.

Handoff: exact verified startup command/URL and a short hands-on checklist. Record
implementation status separately from real-OBS and human taste. The human should
now try their approved OBS scene and judge motion/framing/responsiveness. Stop;
OBS06 performs the final integration and maintenance checks when instructed.


---

# OBS06 — real OBS acceptance, causality, CI and final handoff

Read `flyjam-obs-kit/SPEC.md`, `flyjam-obs-kit/TEST_MATRIX.md`, applicable
`AGENTS.md`, actual git status, `docs/implementation/OBS-STATUS.md` if present,
and the latest relevant milestone report. Read the relevant implementation before
editing. Perform the actual work, run appropriate tests, and update the handoff.
Preserve user changes and existing evidence. Execute only this milestone.

Finish the assignment rather than proposing another pivot.

1. Review OBS00–OBS05 against SPEC/TEST_MATRIX and the actual code. Resolve concrete
   defects. Ensure every required make target performs real work and returns
   meaningful failures. Keep historical navigation release checks unchanged.
   Evidence must identify the tested checkout, configuration and environment.

2. Make ordinary CI include lab + live schema drift, component tests and separate
   fixture-browser journeys, as well as existing required checks. Dedicated real
   model/OBS targets must fail nonzero for missing requirements. Do not ask hosted
   PR CI to install a kernel module, open hardware, or download private recordings.
   Preserve the managed-runtime CI correction and use isolated evidence paths.

3. Execute the real-model gate, then the real-OBS gate using the operator-selected
   device and approved safe content. A real fixture-source test is not an OBS
   pass. Check Start, source changes, responsive health, explicit Stop, actual
   virtual-camera stop, source restart, no backlog, late-worker results, control
   tab closure/lease expiry, opt-in record and zero-call replay. Confirm no orphan
   subprocesses, leaked locks, raw desktop files or exposed secrets. Do not infer
   source health from identical/different pixels alone.

4. Run the bounded input-influence comparison from TEST_MATRIX on recorded safe
   observations: changing, frozen and actually disconnected drive, matched seeds,
   one exact repeat. Freeze the schedule first and use the remaining workstream
   allowance. The disconnected control must be an explicit diagnostic hook;
   black input is not neural silence. Do not mutate baseline files or pretend
   diagnostic ablations are ordinary live-mode outputs. Compare rates, decoded
   controls and flight state with fixed initial pose and playback timing.

5. Measure capture/receipt ages, encoding, model load/step latency, stale output
   rejection, capture overwrites, API responsiveness, rendering and session RSS
   separately. Include a small slow-consumer/failure soak within explicit bounds.
   Report measured values without equating wall time, neural simulated time or
   renderer FPS. Do not benchmark by changing the model fidelity.

6. Produce `docs/implementation/OBS-LIVE-HANDOFF.md`, current OBS-STATUS, final
   report and a private review bundle from safe approved content. Include actual
   commands/results, startup/setup instructions, exact source configuration,
   source/model/encoder/decoder identity, screenshots, a short real flight capture
   when feasible, optional replay, remaining limitations and cleanup/recovery.
   Desktop content or footage stays local; sanitize anything proposed for sharing.

7. Stop with a clear final result:
   - implementation_status
   - real_model_status
   - real_obs_status
   - causal_validation_status
   - human_review

If hardware or permission is missing, finish all independent code and tests and
return BLOCKED only for the affected gate, with the exact minimum operator action
and rerun command. Do not report complete verified OBS integration. If the neural
mapping yields weak visual variation, report the measurements and request a scoped
mapping change; do not invent an impressive result or abandon the integrated app.

No public deployment, token work, remote push, PR, privileged system changes or
social publication. Final human approval concerns this local experience only.
