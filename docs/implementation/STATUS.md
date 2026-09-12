# FLYTRAP status

CI correction (2026-09-12): **local PASS**, hosted run pending branch push.
Foundation now uses uv 0.12.13 managed Python 3.14.7 with linked SQLite 3.53.1;
`make bootstrap` and `make verify test-upstream` exited 0. See the
[milestone 01 correction](milestones/01.md) for counts and evidence.

Milestones **00–04 complete**. **05 automated work complete; human review PENDING.**
Latest validation: 2026-09-12 UTC (2026-09-11 US/Central).
HEAD is `e999df631277d94277747271bc0a8b1359682b29`; milestone 05 changes are local
and uncommitted. All prior source hashes matched at entry.

**05 automated_status: PASS · human_review: PENDING.**
Learning evidence: **NOT_RUN**; learning and improvement claims remain disabled.
**Do not start 06 before explicit human approval of 05.** An identical resume
instruction is not approval.

| Boundary | Status | Actual result |
|---|---|---|
| Prior work / data / locked runtime | PASS | All 04 source hashes matched; fresh raw/graph doctor passed; locks unchanged. |
| Real model → arena feasibility | PASS | 8 complete development episodes, 2,048 steps; zero execution failures. |
| Controlled visual input / repeatability | PASS | 14 matched input/seed pairs × 2 repeats; changed pixels affect motors; repeats match. |
| Task outcomes | No competence demonstrated | 8/8 scored timeouts; all paths retained, substantial lower-wall trapping. |
| Measured cost | Recorded | 0.399 s median step; 101–103 s episodes; 739.1 MiB peak process RSS. |
| Artifact reconstruction | PASS | All 2,048 actions, states and observation hashes independently replayed. |
| Python checks | PASS | 1,405 full-suite passes; final verifier edit and added case: 41 focused passes; no failures/skips. |
| Web / build / dependencies | PASS | 89 contracts, 9 components, 2 browser startup checks; lint/types/build/locks/audit pass. |
| Interaction / condition decision | PENDING human review | Proposed GO for queued experimental core; frozen baseline mapping, zero distractions. |
| Full real-model browser release | BLOCKED | Later durable worker/API/replay/browser integration pending; make verify-real exits 2. |
| Learning benefit / held-out evaluation | NOT_RUN | No checkpoint training, comparison promotion or positive claim. |

Read [milestone 05](milestones/05.md), [FEASIBILITY](FEASIBILITY.md), and the
[frozen condition](../../experiments/core-v1.json). Review
[all eight trajectories](../../artifacts/milestones/05/trajectories.png),
[exact input pixels](../../artifacts/milestones/05/probe-inputs.png), the roughly
102-second episode cost and proposed queued/replay mode. This human gate must
judge whether the observed unsuccessful behavior is a worthwhile interaction.

Evidence is under ignored
[`artifacts/milestones/05/`](../../artifacts/milestones/05/); complete model output,
source/environment/data identity and per-trial traces are in
[trials/report.json](../../artifacts/milestones/05/trials/report.json).
Retain the ignored graph, raw files and evidence when moving the checkout.

The graph is `build/flytrap-v1/graph.npz`, SHA256
`4279e2222475b986a096634ea5f6ac9518d0f8feff3f3c2ed52ad1139d3cd2ed`.
`make data-doctor` checks the data; `make verify-feasibility EVIDENCE=artifacts/milestones/05`
checks these development artifacts. Neither passes the full release gate.
Use a new evidence root to rerun `make feasibility`; see [experiment methods](../../experiments/README.md).

Prior reports: [04](milestones/04.md), [03](milestones/03.md), [02](milestones/02.md),
[01](milestones/01.md), [00](milestones/00.md). [ARENA](ARENA.md),
[CONTROLLER](CONTROLLER.md), [DATA](DATA.md), [architecture](ARCHITECTURE.md),
[contracts](contracts/README.md) and [threat model](THREAT_MODEL.md) retain earlier boundaries.

Next: **05 human review**, then **06 — database/artifact repositories** after
approval. No later milestone, hosted CI, deployment or external publication occurred.
