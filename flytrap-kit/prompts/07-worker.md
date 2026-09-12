# Prompt 07 — Single-worker execution and fault recovery

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement the durable worker coordinator and isolated simulator subprocess. One exclusive host slot must prevent two active simulations even when two workers start and different jobs are queued. Queue claims also need transactions, attempt IDs, lease tokens, heartbeats, and bounded retries.

The coordinator must remain able to heartbeat and enforce deadlines while a model step is slow. Use bounded IPC and terminate/restart a hung child on a real wall-time or memory limit. The child receives only model setup and the approved observation envelope. Reset model/checkpoint state between jobs. Do not give the child wallet keys, the database, or arbitrary network/browser access.

Write bounded durable progress events and finalize immutable replay bundles using the artifact repository. Fence stale attempts from publishing. Preserve interrupted attempt history; retries restart transparently with declared semantics rather than pretending execution was exactly once. Handle SIGTERM and unavailable/corrupt models honestly.

Use multiprocess integration and fault injection: concurrent worker startup, duplicate claim, worker kill, expired lease, stale finalization, slow/hung model, disk failure, restart, and graceful shutdown. Assert no duplicate accepted completion or completed run with missing artifacts. Test that the API's future database reads are not blocked by model computation. Record throughput/resource measurements and pending failure cases.
