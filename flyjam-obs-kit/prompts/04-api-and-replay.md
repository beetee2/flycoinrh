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
