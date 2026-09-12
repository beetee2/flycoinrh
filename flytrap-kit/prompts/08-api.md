# Prompt 08 — HTTP API, admission controls, and resumable events

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement the contracted FastAPI endpoints for config, health, challenge creation/read, run creation/read, approved checkpoints, committed SSE events, and replay lookup/download. Add an app factory with explicit lifespan and dependency injection. The API never performs simulation in its request loop.

Use actual repositories and worker status. Validate schema/body limits, JSON content type, Origin, signed/server-stored anonymous sessions, trusted proxy configuration, idempotency, per-session/source quotas, and the global queue cap. Distinguish liveness, service readiness, and capacity to admit new real runs. Return documented status/error bodies; no synthetic fallback when the worker is unavailable.

Implement bounded SSE with increasing event sequence, attempt IDs, Last-Event-ID/after cursor, duplicate-tolerant client semantics, keepalive, cleanup, stream limits, and terminal recovery. Slow spectators must not stall the worker or create unbounded memory queues. Public artifact requests resolve IDs within the configured root, never arbitrary paths.

Test contracts and HTTP behavior with HTTPX, application lifespan, and real file-backed repositories. Test streaming/reconnection/disconnects and responsiveness during actual worker computation against a real server/socket. Cover same-key retries, changed-payload conflicts, invalid challenge, quota exhaustion, worker down, missing/unfinished/corrupt replay, and forged proxy headers. Save OpenAPI and cross-language contract evidence.
