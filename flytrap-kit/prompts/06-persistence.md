# Prompt 06 — Database schema, transactions, and artifact repositories

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement file-backed SQLite repositories and numbered, transactional migrations for challenges, anonymous sessions, runs, attempts, events, checkpoints, and comparison references. Use foreign keys, checks, uniqueness, indices, WAL, and bounded busy handling. Check the SQLite library actually linked by Python for the documented WAL-reset fix (3.51.3+ or a verified vendor backport), with a tested failure path for unpatched runtimes. Keep model computation outside transactions.

Implement immutable challenge specifications; legal run transitions; session-scoped idempotency with request digest; atomic quota/admission plus run creation; and compare-and-set updates for attempt ownership. A repeated key/payload returns the same run; a changed payload returns a conflict. Use real separate connections to test concurrency.

Create a safe artifact repository under one configured root: bounded trace chunks/manifests, stable identifiers instead of user paths, checksums, immutable publication, and temp-write/fsync/rename before committing the completed reference. Define reconciliation for orphan files and interrupted attempts. Never mark a run completed before its verified bundle exists.

Test fresh and upgrade migrations, constraints, rollback, same-key races, conflicting keys, busy timeouts, concurrent admissions, traversal attempts, truncation/corruption, and crashes on each side of rename/database commit. Use actual temporary database files and filesystem operations, not only mocks or an in-memory database. Produce database/artifact evidence and document backup/restore consistency expectations.
