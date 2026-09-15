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
