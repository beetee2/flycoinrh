# FLYTRAP status

Milestones **00–04 complete**. Latest validation ran on 2026-09-12 UTC
(2026-09-11 US/Central). HEAD remains
`8748e5bd30794d14afeb3441904221b52a002cac`; implementation is local and uncommitted.

**04 automated_status: PASS · human_review: NOT_REQUIRED.**
No pending human reviews. Learning evidence: **NOT_RUN**; learning disabled.

| Boundary | Status | Actual result |
|---|---|---|
| Prior work / preservation | PASS | Entry hashes match 03; kit/user edits, LICENSE, NOTICE and attribution preserved. |
| Locked runtime | PASS | Python 3.14.7, Node 26.8.2, linked SQLite 3.53.4; locks unchanged. |
| Data / adapter prerequisite | PASS | Fresh raw/bundle doctor; unchanged source/data/runtime permit reuse of 03 real adapter evidence. |
| 04 legal arena / physics / scoring | PASS | Fixed reachable presets, explicit cohort mapping, swept contacts, quantized motion and terminal rules. |
| 04 raster / retina / isolation | PASS | Golden pixels, lossless PNG parity, clipped normalized crop; actual adapter on synthetic graph respects hidden-scoring isolation. |
| 04 fixture traces / inspection | PASS | Four labeled samples inspected; all 530 actions recompute states and observation hashes. |
| Python regressions | PASS | 1,329 passed including 137 arena cases; 0 failures/errors/skips. Later doctor-message edit: 12 foundation tests passed. |
| Web contracts / components / browser startup | PASS | 89 / 9 / 2 passed; desktop/mobile screenshots and trace responses inspected. |
| Build / package / dependencies | PASS | make verify; final wheel matches package files; lint/types/generated contracts/dependency checks pass. |
| Fault probes | PASS | Disposable collision, renderer-input and crop-rounding mutations produce intended failures. |
| Real task feasibility | NOT_RUN | Controlled visual sensitivity and interaction decision belong to 05. |
| Full real-model E2E / release | BLOCKED | Worker/API/replay/browser run integration pending; make verify-real exits 2. |
| Learning benefit | NOT_RUN | No trained checkpoint, approved comparison or improvement claim. |

Read [milestone 04](milestones/04.md) for commands, outputs and handoff;
[ARENA](ARENA.md) freezes geometry, scoring, raster, crop and movement.
[CONTROLLER](CONTROLLER.md) documents the adapter. Prior [03](milestones/03.md),
[02](milestones/02.md), [01](milestones/01.md), [00](milestones/00.md),
[DATA](DATA.md), [contracts](contracts/README.md), [architecture](ARCHITECTURE.md)
and [threat model](THREAT_MODEL.md) remain available.

The verified bundle is `build/flytrap-v1/graph.npz`, SHA256
`4279e2222475b986a096634ea5f6ac9518d0f8feff3f3c2ed52ad1139d3cd2ed`.
Run `make data-doctor` to recheck data and `make test-controller-real` for the
adapter smoke. Neither command is the full release gate.

Evidence is under ignored [`artifacts/milestones/04/`](../../artifacts/milestones/04/).
Run `make arena-samples EVIDENCE=artifacts/milestones/04` to reproduce the
**SCRIPTED FIXTURE — NOT REAL MODEL** images and trajectories. These demonstrate
mechanics, not model competence. Retain ignored raw/graph files and
prior evidence when moving the checkout. Hosted CI and deployment remain
unexecuted; no external publication occurred.

Next: **05 — real-model feasibility and task calibration**, on the next explicit
invocation. Preserve the declared configuration while measuring development
behavior; record any permitted calibration as an explicit versioned condition.
05 requires human review of behavior and the interaction-mode decision after
automated validation. No later milestone started.
