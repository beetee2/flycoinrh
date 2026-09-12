# FLYTRAP status

Milestones **00–04 complete**. **05 bounded review revision complete;
human_review: PENDING. Do not start 06.**

Human review requested changes to the original milestone-05 result. The revision
preserves v1 and adds an explicit tangential-physics candidate, passive motor
telemetry, and one separately versioned observation experiment. Current
recommendation: **NO-GO for a playable core**. Passing mechanics and pipeline
checks do not establish an engaging two-choice interaction.

Latest validation: 2026-09-12 UTC (2026-09-11 US/Central).
Revision began at `a1ecbdc44d9397c97a4af41f3f4abf84c1d050e0`; changes remain local
and uncommitted. Learning remains disabled, with evidence **NOT_RUN**.

| Boundary | Status | Actual result |
|---|---|---|
| Historical trace diagnosis | PASS | All eight bundles read; 2,048 original actions/states/inputs reconstructed before new neural runs. |
| V1 preservation | PASS | Original implementation/configurations/checkpoint/traces/evidence intact; original artifact verifier still passes. |
| Candidate physics / sensory boundary | PASS | All-wall/corner/obstacle/swept/replay tests; exact v1 pad-row cutoff and optional full-scene samples verified. |
| Bounded development execution | PASS | 24 scheduled 96-tick diagnostics, 2,304 real calls, 896.1 measured phase seconds; no execution failures. |
| Interaction / task outcomes | NO-GO recommendation | Zero pad contacts; all diagnostics end as incomplete cutoffs. Tangential motion improves, bottom-wall residence persists. |
| Passive telemetry / determinism | PASS | DNa02/DNa01/MDN/DNp09 captured unchanged; 768 v1 prefix steps exactly match history; matched pixels/seeds/windows reproduce rates/actions. |
| Artifact reconstruction | PASS | All 2,304 new steps, exact inputs and trajectory images replayed under their recorded versions. |
| Required checks | PASS | 1,559 Python, 89 web contracts, 9 components, 2 fixture-browser checks; lint/types/build/locks/dependency checks pass. |
| Full real-model browser release | BLOCKED | Worker/API/replay integration remains pending; `make verify-real` exits 2. |
| Task competence / learning | UNSUPPORTED / NOT_RUN | No held-out evaluation or training; no condition promoted. |

Read the [short comparison](FEASIBILITY-05-REVISION.md),
[complete historical diagnosis](FEASIBILITY-05-DIAGNOSIS.md), and
[milestone record](milestones/05.md). Review
[actual visual trajectories and input pixels](../../artifacts/milestones/05/revision/analysis/canonical-trajectories-inputs.png)
and [all black controls](../../artifacts/milestones/05/revision/analysis/dark-trajectories-inputs.png).
The [tracked summary](../../experiments/feasibility-revision-v2-results.json)
retains all scheduled trial IDs; full local evidence is under ignored
[`artifacts/milestones/05/revision/`](../../artifacts/milestones/05/revision/).

The historical [core-v1 condition](../../experiments/core-v1.json) remains intact
and unapproved. The earlier proposed GO in the historical report is superseded
by this revision. Preserve the ignored graph, raw data and all historical and
revision evidence when moving the checkout. The graph remains SHA256
`4279e2222475b986a096634ea5f6ac9518d0f8feff3f3c2ed52ad1139d3cd2ed`.

Next: **human review of milestone 05 only**. No milestone 06, deployment, remote
push or publication is authorized by this revision.
