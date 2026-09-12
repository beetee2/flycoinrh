# Milestone 05 — bounded development revision

**Diagnostic execution PASS; interaction recommendation NO-GO for a playable core; human_review: PENDING.**
The candidate reduces collision-induced immobility, but the observed paths still concentrate near the lower walls. Keeping pad cues visible does not establish a useful two-choice interaction. No condition is promoted. Milestone 06 remains stopped.

The [complete eight-episode historical diagnosis](FEASIBILITY-05-DIAGNOSIS.md) reconstructs all 2,048 original actions and inputs, including wall/corner dwell, requested versus actual motion, canceled tangents, signed drift and cue loss. Original v1 source, configurations, baseline, traces and evidence are preserved. The earlier proposed GO is superseded by this review revision.

The [preregistration](../../experiments/feasibility-revision-v2.json) schedules 16 primary episodes, then at most eight sensory episodes, using development seeds 51001 and 51002, both layouts, and black controls. Each stops at 96 diagnostic ticks: these are **incomplete cutoffs**, not the unchanged arena's 256-tick scored timeouts. The budgets were 1,536 calls/900 seconds primary and 768 calls/450 seconds optional. The candidate lost pad samples on 334/384 visual ticks (87.0%), meeting the declared 50% trigger. All 24 scheduled episodes and 2,304 new real-model calls completed; no episode made a pad contact and no execution failed. No seeds were replaced, held-out data used, or learning enabled.

`no_sliding_v1` remains the default in `arena.core.step`. Opt-in `tangent_v2` removes blocked normal motion and retains the remaining tangential component, using exact swept contacts without renormalization. Simultaneous corner normals both stop; a removed axis stays removed for that tick. The separately tested `overview16_v2` samples the full canonical raster at x,y = 3,9,...,93. It keeps both pad textures visible, but its static image provides no feedback about avatar position. The controller still receives only 256 pixels, model state and the original seed stream; positive y still means down.

Each row below aggregates four matched 96-tick episodes. Wall and corner counts use before-state contact; a corner also counts toward its wall. Seconds sum recorded controller latency while stationary, not simulated environment duration. Black inputs have zero visible cues even where the canonical sampling coordinates intersect pads.

| Physics / crop / input | Stationary ticks | Stationary s | Bottom-wall ticks | Bottom-left corner ticks | Pad-visible inputs | Pad contacts |
|---|---:|---:|---:|---:|---:|---:|
| no_sliding_v1 / crop16_v1 / canonical | 197/384 (51.3%) | 73.5 | 234 | 32 | 48 | 0 |
| no_sliding_v1 / crop16_v1 / dark | 164/384 (42.7%) | 60.8 | 226 | 0 | 0 | 0 |
| tangent_v2 / crop16_v1 / canonical | 63/384 (16.4%) | 23.7 | 245 | 74 | 50 | 0 |
| tangent_v2 / crop16_v1 / dark | 40/384 (10.4%) | 14.9 | 226 | 0 | 0 | 0 |
| tangent_v2 / overview16_v2 / canonical | 55/384 (14.3%) | 21.8 | 286 | 67 | 384 | 0 |
| tangent_v2 / overview16_v2 / dark | 40/384 (10.4%) | 16.3 | 226 | 0 | 0 | 0 |

Passive telemetry records the rates already returned by the pilot. Mean visual-condition rates are in Hz; requested y is pixels per tick before collisions.

| Physics / crop | DNa02 L / R | DNa01 L / R | MDN | DNp09 | Requested y |
|---|---:|---:|---:|---:|---:|---:|
| no_sliding_v1 / crop16_v1 | 242.8 / 187.0 | 138.2 / 40.1 | 200.2 | 118.4 | +1.432 |
| tangent_v2 / crop16_v1 | 252.0 / 186.5 | 138.8 / 41.3 | 200.7 | 119.9 | +1.409 |
| tangent_v2 / overview16_v2 | 222.9 / 177.9 | 131.5 / 31.6 | 200.7 | 111.7 | +1.548 |

The unchanged mapping uses DNa02 right-minus-left for horizontal steering and averaged DNa01 minus MDN for forward speed, attenuated by DNp09. MDN dominance requests downward motion unless stopping fully suppresses speed. In the primary visual runs, requested y remains positive after first wall contact (means +1.406 to +1.569 pixels/tick in v1 and +1.438 to +1.506 in the candidate). Collision removes movement despite continued motor drive. These are implementation-level motor-bias measurements, not validated biological behavior claims.

All 768 new v1 states/actions/input hashes exactly match corresponding historical prefixes. Across all conditions, 450 matched seed/window/pixel groups have identical captured rates and actions. Every black layout pair follows the same trajectory. Swapping visible layouts changes trajectories as follows; equal final positions do not imply equal paths.

| Condition and seed | Different motor actions | Different positions | Separation at common final tick, px |
|---|---:|---:|---:|
| no_sliding_v1-crop16_v1-51001 | 35/96 | 96/96 | 0.797 |
| no_sliding_v1-crop16_v1-51002 | 61/96 | 78/96 | 0.000 |
| tangent_v2-crop16_v1-51001 | 21/96 | 22/96 | 0.000 |
| tangent_v2-crop16_v1-51002 | 22/96 | 25/96 | 0.000 |
| tangent_v2-overview16_v2-51001 | 95/96 | 96/96 | 26.238 |
| tangent_v2-overview16_v2-51002 | 96/96 | 87/96 | 0.887 |

The full report also retains every visual-versus-black, physics-only and observation-only pair. Local visual influence is supported; task competence is unsupported and learning is NOT_RUN. The [counterfactual old-action replay](../../artifacts/milestones/05/revision/counterfactual/trajectories.png) reduces stationary ticks 1,063 to 291 and canceled tangents 803 to zero, with eight timeouts. It used zero neural calls and changed unconsumed observations, so it is separate from closed-loop evidence.

Measured phase cost: physics: 1536 calls, 580.6 s, 739.5 MiB peak RSS; overview: 768 calls, 315.6 s, 739.8 MiB peak RSS. Total 896.1 seconds, within the 1,350-second budget. Command logs include process startup overhead. The host was not isolated; lightweight checks and the 29.9-second repository verification ran during primary computation. No timing claim extends beyond this host and bounded experiment.

| Review boundary | Result |
|---|---|
| Pipeline correctness | PASS: actual graph, unchanged baseline, finite rates/actions; all scheduled evidence retained. |
| Physics and sensory boundary | PASS: original assertions retained; candidate collision/property tests and exact pixel replay pass. |
| Interaction suitability | NO-GO recommendation: movement improves, but observed behavior remains near lower walls; human review pending. |
| Task competence or learning | UNSUPPORTED / NOT_RUN: no pad contacts, no held-out evaluation or training. |
| Full browser/worker release | BLOCKED: later integration is unimplemented; `make verify-real` exits 2. |

Validation: `make verify` exits 0 with 1,559 Python, 89 web-contract, nine component and two fixture-browser passes; zero failures/skips. The focused affected suite has 330 passes. The historical verifier still passes. New artifact verifiers reconstruct every recorded state/input and check trajectory/input image pixels, schedules, preregistration, budgets, graph/baseline identity and execution-source hashes. Fixture checks do not establish real-model release readiness.

Review the [actual visual trajectories and inputs](../../artifacts/milestones/05/revision/analysis/canonical-trajectories-inputs.png), [all black controls](../../artifacts/milestones/05/revision/analysis/dark-trajectories-inputs.png), [exact v1 crop coordinates/pixels](../../artifacts/milestones/05/revision/diagnosis/crop-comparison.png), [all per-trial metrics and comparisons](../../artifacts/milestones/05/revision/analysis/report.json), and [tracked compact results](../../experiments/feasibility-revision-v2-results.json). Execution snapshots in `primary/report.json` and `overview/report.json` bind the exact tested files; [final source identity](../../artifacts/milestones/05/revision/final-source-identity.json) binds the completed revision. Next handoff: human review of milestone 05 only.
