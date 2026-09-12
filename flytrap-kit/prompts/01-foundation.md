# Prompt 01 — Executable scaffold, contracts, and verification harness

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Establish the executable foundation from the approved architecture. Use Python/FastAPI, React/TypeScript, file-backed SQLite, and a separate worker, retaining upstream code. Select compatible runtimes and resolve reproducible lockfiles; verify existing pins rather than assuming them.

Create versioned contracts for ChallengeSpec, RunRequest/Record, Observation, ControllerOutput, FrameEvent, ReplayManifest, CheckpointRef, BenchmarkReport, and Capabilities. Define unknown-field rejection, finite numeric bounds, IDs, canonical hashes, seed policy, status/error enums, and schema evolution. Generate TypeScript types and runtime validators from a single schema source or prove parity through shared fixtures.

Provide pytest/property-test, Vitest/component-test, and Playwright configurations, isolated data/artifact roots, app/worker factories, and meaningful Make targets from PLAN.md. Create a tiny synthetic graph fixture and an explicitly labeled fixture controller. Fixture mode must not become a production fallback.

Implement a minimal health route and fixture startup, not the full product. Create CI for the checks that now exist; add later checks as each layer lands. Missing or zero-collected suites must not report false success. Test contract round trips and invalid payloads, app lifespan, imports, build, and a real browser opening the minimal UI. Record the proposed endpoint/state-machine contracts and test ownership.
