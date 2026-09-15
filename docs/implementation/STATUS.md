# Active routing — OBS03 browser repair

**Stop after the focused OBS03 repair. Do not start OBS04.**
Read [OBS-STATUS](OBS-STATUS.md), the [repair report](milestones/OBS03.md),
and [fixed flight mapping](OBS-FLIGHT.md).

The operator confirms normal Chrome playback after enabling graphics acceleration.
The new diagnostics distinguish loaded synthetic data from a working renderer;
bounded Retry graphics leaves playback paused. Independent browser evidence is
recorded separately from the operator's session and human appearance approval.
Automated rendering is PASS (8 desktop/mobile tests); installed Chrome
compatibility is PASS (4 headed tests). Repaired-build normal-browser confirmation
and human appearance approval remain BLOCKED pending operator review.
See OBS-STATUS for the separate gates.

Zero new neural calls, capture, recording or host changes. OBS accounting stays
9/1,024 (1,015 remaining), P00 stays 144 attempts, protected identities remain
preserved. Repair is local/uncommitted, with no push or deployment. Human review
of the repaired build remains pending; later milestones are unauthorized.
Historical navigation remains STOPPED and original 06 remains BLOCKED.

The P00 and navigation records below remain historical evidence.

---

# Active routing — P00 FLYTRAP LAB

Milestone 05 diagnostic work and its negative result are ACCEPTED. Navigation
is STOPPED, not approved. Original milestone 06 remains BLOCKED.
P00 local prototype engineering is PASS / COMPLETE; human product review PENDING.
Public release is NOT AUTHORIZED. Read [PIVOT](PIVOT.md) and
[P00](milestones/P00.md). P00 is complete: ordinary resume must stop
for human review. It cannot select any old navigation milestone or proposed successor.

Local handoff: `make serve-lab`, http://127.0.0.1:8766/lab (server left running).
72/256 attempted full-model calls; real API/model and Playwright checks PASS.
Actual retina: 137/256 pixels sampled, 119 discarded. Explicit untrained
windowed_reset baseline; no navigation candidates or learning enabled.
Review bundle: `artifacts/milestones/P00/review-bundle.zip`. Full commands,
counts, identities, inspected screenshots and limitations are in the P00 record.
Preservation check: 908 existing files unchanged; working CI configuration retained.

The previous status below is a historical execution snapshot; its pending
decision is superseded only by the decisions above. Experiment results stand.

---

# FLYTRAP status

CI correction (2026-09-12): **local and hosted PASS**. Foundation now uses uv
0.12.13 managed Python 3.14.7 with linked SQLite 3.53.1; `make bootstrap` and
`make verify test-upstream` exited 0 locally, and
[hosted run 34668843967](https://github.com/beetee2/flycoinrh/actions/runs/34668843967)
passed. See the [milestone 01 correction](milestones/01.md) for counts and
evidence.

Milestones **00–04 complete**. **05 human_review: CHANGES_REQUESTED.**
The human accepted the prior bounded diagnostic work and negative conclusion;
the navigation interaction remains unapproved. **Milestone 06 is BLOCKED.**

The final authorized sensor-to-movement experiment is complete. Engineering and
replay checks pass; the interaction verdict is **FAIL / STOP NAVIGATION**.
All four full visual confirmation episodes timed out with zero destination
contacts and 841/1,024 before-state ticks (82.1%) within eight pixels of a wall.
Only nine ticks were stationary, so movement alone does not establish suitability.

One position-dependent observation and one fixed, target-free motor readout
calibration were tested separately. The 16×16 inputs retain both patterns, but
the existing retinal map preserves both full contrasts in only 48/529 camera
bins and at none of the actual tracking visual positions. Layout changes still
influence retinal drive and movement. Whole-region retinal pattern preservation
and usable navigation were not achieved.

| Boundary | Status | Actual evidence |
|---|---|---|
| Overall milestone human review | CHANGES_REQUESTED | Prior diagnostics accepted; navigation not approved. Return for a new decision. |
| Final bounded experiment | PASS execution | 14/14 scheduled trials, 1,984 trial calls plus 4 regression calls = 1,988 of 2,048 cap; no replacements or tuning. |
| Complete versus partial episodes | PASS accounting | Eight 56-tick incomplete screening cutoffs; six 256-tick scored confirmation timeouts; zero contacts/failures. |
| Controller input / fixed readout / reset | PASS | Pixels-only isolation, exact samples/rates/mapping and unchanged windowed dynamics; positive fixed readout weights, learning disabled. |
| Navigation sensory fit | FAIL | Both patterns survive in pixels but not throughout the retinal operating region; no further candidate searched. |
| Interaction suitability | FAIL / STOP recommendation | Predominantly lower/left wall drift; no demonstrated usable interaction or task competence. |
| Artifact replay / preservation | PASS | 1,984 new steps and 1,648 exact reused black steps checked; all 496 prior artifact hashes unchanged; original/revision verifiers pass. |
| Required repository checks | PASS | `make verify test-upstream`: 2,257 Python, 150 upstream, 89 web contracts, 9 components, 2 fixture-browser passes; later 32-case affected regression includes one additional test. |
| Full real-model browser release | BLOCKED | `make verify-real` exits 2; later worker/API/end-to-end integration remains unimplemented. |
| Learning | NOT_RUN / disabled | Engineered readout calibration is not learning; no held-out outcomes used. |

Latest execution: 2026-09-12 UTC (2026-09-11 US/Central), from source HEAD
`f077ceb` with local final-experiment additions. Runner time 714.820 seconds,
within 1,300 seconds; actual runtime Python 3.14.7 / SQLite 3.53.4. The successful
CI correction above and its historical evidence remain preserved.

Read the [final report](FEASIBILITY-05-FINAL.md),
[frozen plan](FEASIBILITY-05-FINAL-PLAN.md),
[milestone record](milestones/05.md), and
[all scheduled results](../../experiments/feasibility-final-v3-results.json).
Review the [full confirmation trajectories and inputs](../../artifacts/milestones/05/final-sensorimotor/analysis/confirm-trajectories-inputs.png).
Complete local evidence is under ignored
[`artifacts/milestones/05/final-sensorimotor/`](../../artifacts/milestones/05/final-sensorimotor/).

Preserve the [original](FEASIBILITY.md), [historical diagnosis](FEASIBILITY-05-DIAGNOSIS.md),
[previous revision](FEASIBILITY-05-REVISION.md), their configurations/tests,
and all ignored raw/graph/evidence files. No condition is promoted.
The graph remains SHA256
`4279e2222475b986a096634ea5f6ac9518d0f8feff3f3c2ed52ad1139d3cd2ed`.

Next: **human review of milestone 05 only**. Recommend stopping navigation and
retaining the simulation/evidence for a possible separately authorized
stimulus-response interaction. No automatic pivot, milestone 06, deployment,
remote push, PR, paid resource or publication is authorized.
