# Prompt 15 — Security, resource control, operations, and containers

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Harden the completed system and package a single-host production profile. Use nonroot containers, pinned compatible runtimes, read-only model data, local persistent database/artifact volumes, one exclusive worker slot, explicit resource limits, and same-origin routing. Never mount wallet keys, home directories, Docker sockets, or SSH credentials. No inference-time arbitrary browsing or general outbound access is needed.

Implement and test bounded JSON/input sizes, approved layouts/checkpoints, Origin/session/proxy handling, admission quotas, queue/stream caps, subprocess deadlines, replay decompression limits, disk/log retention, and artifact path safety. Missing real data must produce clear unavailability, not a fixture fallback. Keep liveness/readiness/admission status distinct.

Add structured request/run/attempt logs and minimal metrics: queue depth, active worker, step latency, failures, heartbeat age, streams, and disk use. Implement tested backup/restore, reconciliation, graceful shutdown, and recovery. Use SQLite's supported backup flow and consistent artifact snapshots, not a blind copy of a live DB file.

Run dependency/secret checks, adversarial input tests, bounded load tests with a real active simulation, worker kills, disk-full simulation, restart/replay retrieval, and backup restore in disposable local containers. Record measured capacity and chosen limits, not invented concurrent-user promises. Produce runbooks and rollback instructions. Do not spend money or deploy publicly in this milestone.
