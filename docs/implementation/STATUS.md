# Active routing — SG01 Screen Gremlin candidate review

**SG01 implementation and final affected regressions PASS.**
Screen Gremlin is the default, with local Legacy comparison,
original procedural Jam, an owned ephemeral JPEG backdrop, and clean landscape/
portrait compositions. Read the [SG01 report](milestones/SG01.md) and
[active handoff](OBS-LIVE-HANDOFF.md) for final validation and review media.

**Ground contact works: operator confirmation recorded. Product approval remains
PENDING.** SG01 real-OBS validation is NOT_RUN; the operator will approve and
perform that smoke test after reviewing this candidate. No new full-connectome
calls, desktop capture, decoder/model/physics changes or remote action.

**Launch-profile repair PASS.** `./scripts/dev_sg01.sh` is **Art review — capture-only demo
and saved replays.** Its server-authoritative capabilities disable neural Start
with visible guidance. `./scripts/dev_sg01_live.sh` starts the normal live API in
human mode and matching frontend proxy. Both start idle at
**http://127.0.0.1:5173/live**, require explicit source selection/actions, and refuse
occupied ports. See the [operator handoff](OBS-LIVE-HANDOFF.md) and
[repair evidence](milestones/SG01.md#launch-profile-and-unavailable-control-repair).
Zero new full-model calls or desktop capture; actual OBS smoke is the operator's
next step. SG01
supersedes earlier presentation stops for this task only. Historical reports
and evidence remain below.

---

# Active routing — focused OBS06 ground repair; stop for review

**Ground repair implementation PASS; human product re-review PENDING.** The
CHANGES_REQUESTED decision for below-ground travel is preserved. Read
[OBS-STATUS](OBS-STATUS.md), [handoff](OBS-LIVE-HANDOFF.md) and the
[ground-repair report](milestones/OBS06-ground.md).

Versioned v2 physics constrains new sessions to the original ground plane with
validated fly clearance; historical v1 replay and OBS06 causal results are
preserved. Full local repository/live checks pass. Reviewed hosted revision
3ee5b72 finished with two mobile browser failures; no new remote run or push.
Zero new full-connectome calls or desktop capture. Accounting remains
219/1,024 and P00 144. Capture/inference are stopped. Local zero-call preview:
**http://127.0.0.1:8769/live**. Stop for human review; no new milestone.

---

# Historical routing — OBS06 technical validation complete

**OBS06 technical validation PASS; final human product and causal-response review PENDING.**
Read [OBS-LIVE-HANDOFF](OBS-LIVE-HANDOFF.md), [OBS-STATUS](OBS-STATUS.md), and
[OBS06](milestones/OBS06.md). Operator Start/Stop and updating inferred input are
confirmed; ordinary OBS visual influence remains inconclusive. Fixed safe-stimulus
causal comparison passed without model or mapping changes.

Accounting: **OBS 219/1,024 (805 remaining), P00 144 unchanged**. Capture and
inference are off; manual service remains at http://127.0.0.1:8767/live with human
execution purpose. Local OBS06 changes are uncommitted/unpushed. Reviewed hosted
workflow 35000589668 passed exact revision a9688b39caaebb71a0c1058a6bf923ef86aab314.

Stop for final local human review. Historical navigation remains STOPPED and its
original milestone 06 remains BLOCKED. Previous entries below remain historical.

---

# Active routing — OBS05 browser experience

**OBS05 implementation and required local checks PASS / COMPLETE. Stop for human review.**
Read [OBS-STATUS](OBS-STATUS.md) and [OBS05](milestones/OBS05.md).

The operator's OBS03 synthetic appearance/motion approval is preserved separately
from pending real-flight product review. Reviewed hosted workflow 34995107755
passed the exact `2bc0c675c62b5aeaaa5393697f02406d53a7b195` prerequisite revision.
OBS05 connects actual capture/model sessions and recorded playback to the renderer;
its safe-model and explicitly approved `/dev/video0` checks have executed.
Recording stayed disabled for OBS; only two approved processed inputs were saved.

Accounting: **OBS 61/1,024 (963 remaining), P00 144 unchanged**. Startup:
`make serve-live`, http://127.0.0.1:8767/live. Capture/inference stop at handoff.
**Do not start OBS06.** No remote push or public deployment was authorized.

Agent validation added 18 calls. A later independently started browser session
added 34 calls under the default automated policy and ended at its bound. The final
service resource check confirmed capture and inference stopped. No product approval
was inferred from that session.

Previous entries remain historical evidence.

---

# Active routing — OBS04 complete

**OBS04 implementation and local validation PASS / COMPLETE. Stop before OBS05.**
Read [OBS-STATUS](OBS-STATUS.md) and the [OBS04 report](milestones/OBS04.md).

OBS03 repaired-build playback and current appearance/motion are **APPROVED by
explicit operator confirmation** at `d07841cfe426c36e01c5c805a790d6448f420c64`.
The original browser failure and repair evidence are preserved in [OBS03](milestones/OBS03.md).

The local API, owner lease, bounded streaming and opt-in private replay are
implemented and verified. Hosted run 34991210953 finished **FAILURE** at browser
sandbox startup; its scoped workflow repair passes local validation, with no
hosted rerun claimed. No push or dispatch was authorized.

Actual ledgers: **OBS 9/1,024; P00 144 attempts**. Zero new full-model calls or
desktop capture/recording. Real neural-driven browser flight, public release and
later milestones remain unapproved. The idle local handoff is `make serve-live`,
http://127.0.0.1:8767/live. No OBS05 work was started.

The earlier routing and navigation records below remain historical evidence.

---

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
