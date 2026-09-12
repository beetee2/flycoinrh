# Milestone 05 — final bounded sensor-to-movement result

**Engineering PASS; interaction FAIL / STOP NAVIGATION; human_review: CHANGES_REQUESTED. Milestone 06 remains BLOCKED.**

The final experiment still produces predominantly lower/left boundary drift.
Four full-length visual confirmation episodes reached the 256-tick scored
timeout, with **zero destination contacts**. They spent **841/1,024 ticks
(82.1%)** within eight pixels of a wall, despite only **9 stationary ticks**.
The fixed calibration reduces downward requests, but this does not establish a
usable navigation interaction. Recommend stopping this navigation approach,
preserving the simulation and evidence for a possible separately authorized
stimulus-response interaction. No pivot or further tuning is started.

The human accepted the earlier bounded diagnostics and their negative conclusion;
navigation was not approved. This report adds the final authorized experiment.
Original and revision evidence/configurations/tests and the successful CI runtime
correction are preserved. Historical review markers remain historical; the
current overall milestone review is **CHANGES_REQUESTED**.

## Inspection and frozen design

The [preregistered plan](FEASIBILITY-05-FINAL-PLAN.md) records actual upstream,
adapter, retinal and motor inspection before behavior changes. The adapter has
no sign/unit mismatch: DNa02 right-minus-left drives x; averaged DNa01 minus MDN,
attenuated by DNp09, drives upward motion. Recorded MDN dominance and stronger
left steering explain backward/downward and leftward requests. The browser
pilot scrolls 300 pixels and recenters the cursor at vertical margins; its
apparent progress does not validate bounded-arena navigation.

The only observation candidate, `tracking16_v3`, uses a 96-pixel field with
camera center `48 + (position-48)/4`. Movement changes the pixels in quantized
four-world-pixel camera steps. Only those pixels cross the controller boundary.
The only motor calibration, `dark_balance_v3`, multiplies left steering rates by
**782/815** and MDN rates by **730/1341**, before the existing normalization,
clipping and stop attenuation. These positive readout weights balance means from
192 existing unique black-input development windows. They preserve zero motion
under neural silence and original axis signs. They are engineered calibration,
not learning; black pixels actively stimulate L2 and are not neural silence.
Original click telemetry is retained even when calibrated movement changes.

The [frozen configuration](../../experiments/feasibility-final-v3.json) has SHA256
`94e74d6a0756b245e6682be6703217aacbae235c1dabb6a9e06423d59b59eeb7`. Declaration preceded all new neural calls. Screening used
51001; confirmation reserved fresh development seeds 51003 and 51004. The motor
weights were already fixed before screening and were recorded again after its
448 calls, before confirmation. Individual trial UTC starts were not recorded;
the frozen runner order, attempt ledger and confirmation-freeze artifact establish
that ordering. No seed replacement, parameter adjustment, neural-dynamics change,
learning, held-out task outcome or additional candidate was used.

## All scheduled trials

All **14** scheduled trials executed successfully: eight 56-tick screening
**incomplete diagnostic cutoffs**, followed by six complete 256-tick confirmation
**scored timeouts**. All had zero contacts. The latter include four visual trials
and two black controls. No infrastructure termination or model failure occurred.

Positive y is down. Requested motion below is the applied mapping before physics,
in pixels/tick. Executed motion is net displacement over the episode. The wall
band includes before states within eight pixels of a wall; exact walls use contact.
Visited bins are distinct 8×8-pixel spatial bins, not destination visits.

| Trial: seed / layout / input | Observation / motor | Ticks | Mean requested x,y | Net executed x,y | Wall band / exact ticks | Stationary | Visited bins |
|---|---|---:|---|---|---:|---:|---:|
| S1: 51001 / left / canonical | v1 / original | 56 | -0.714, +1.070 | -39.99, +16.00 | 44 / 25 | 4 | 11 |
| S2: 51001 / right / canonical | v1 / original | 56 | -0.714, +1.265 | -39.99, +16.00 | 45 / 27 | 3 | 10 |
| S3: 51001 / left / canonical | tracking / original | 56 | -1.016, +0.817 | -39.56, +16.00 | 51 / 34 | 8 | 10 |
| S4: 51001 / right / canonical | tracking / original | 56 | -1.460, +1.143 | -42.23, +16.00 | 50 / 35 | 11 | 9 |
| S5: 51001 / left / canonical | tracking / balanced | 56 | -0.209, +0.490 | -11.72, +14.14 | 37 / 11 | 0 | 9 |
| S6: 51001 / right / canonical | tracking / balanced | 56 | -1.294, +0.218 | -33.62, +9.11 | 37 / 10 | 0 | 13 |
| S7: 51001 / left / dark | tracking / original | 56 | +0.048, +0.912 | +2.67, +16.00 | 50 / 26 | 9 | 9 |
| S8: 51001 / left / dark | tracking / balanced | 56 | +0.181, -0.074 | +10.08, -4.15 | 0 / 0 | 0 | 8 |
| C1: 51003 / left / canonical | tracking / balanced | 256 | -0.432, +0.456 | -28.75, +15.61 | 220 / 122 | 1 | 20 |
| C2: 51003 / right / canonical | tracking / balanced | 256 | -0.513, +0.215 | -44.00, +13.53 | 185 / 64 | 2 | 16 |
| C3: 51003 / left / dark | tracking / balanced | 256 | -0.641, +0.112 | -41.94, +10.57 | 176 / 69 | 2 | 15 |
| C4: 51004 / left / canonical | tracking / balanced | 256 | -0.484, +0.234 | -28.49, +15.83 | 210 / 86 | 4 | 17 |
| C5: 51004 / right / canonical | tracking / balanced | 256 | -0.615, +0.283 | -28.93, +15.77 | 226 / 102 | 2 | 18 |
| C6: 51004 / left / dark | tracking / balanced | 256 | -0.170, +0.107 | -20.57, +11.21 | 223 / 26 | 0 | 19 |

S1–S8 are short diagnostics, not complete games. C1–C6 are full confirmations.
Every full trial's requested-versus-executed totals are below. Left/bottom/corner
counts use BEFORE states; the corner also counts toward each wall. Every other
wall and corner count is zero. Distance is the sum of tick-endpoint displacement
lengths; plots join recorded tick positions and omit within-tick collision bends.

| Confirmation | Raw request x,y px | Calibrated request x,y px | Quantized request x,y px | Executed net x,y px | Left / bottom / corner ticks | Tick displacement length px |
|---|---|---|---|---|---:|---:|
| 51003 / left / canonical | -148.44, +420.33 | -110.51, +116.68 | -110.57, +116.55 | -28.75, +15.61 | 23 / 100 / 1 | 697.34 |
| 51003 / right / canonical | -171.56, +341.75 | -131.21, +55.02 | -131.27, +54.88 | -44.00, +13.53 | 26 / 44 / 6 | 767.21 |
| 51003 / left / dark | -207.11, +320.22 | -164.21, +28.61 | -164.21, +28.52 | -41.94, +10.57 | 49 / 27 / 7 | 617.75 |
| 51004 / left / canonical | -164.44, +346.41 | -123.92, +59.96 | -123.96, +59.83 | -28.49, +15.83 | 28 / 65 / 7 | 744.35 |
| 51004 / right / canonical | -197.33, +366.49 | -157.53, +72.57 | -157.57, +72.44 | -28.93, +15.77 | 50 / 64 / 12 | 671.98 |
| 51004 / left / dark | -83.56, +327.62 | -43.50, +27.42 | -43.58, +27.38 | -20.57, +11.21 | 8 / 20 / 2 | 813.70 |

Across full visual confirmation, mean applied requests remain **−0.511 x,
+0.297 y pixels/tick**. There are 647 downward and 356 upward requests; larger
left requests yield net leftward bias despite 541 right versus 483 left requests.
Exact wall residence is 374/1,024 ticks; lower-left corner residence is 26 ticks.
Only 16–20 spatial bins are visited per visual episode, concentrated near the
lower/left walls. Nine stationary ticks alone would conceal this failure.

## Visual feedback, retinal coverage, and controls

Exact raw bytes and sampling coordinates were checked over every one of the
529 distinct camera-bin pairs spanning [4,92]². Each 16×16 input retains at least
eight samples per pad, including black and white contrast. Representative positions
produce changed inputs. See [left input comparison](../../artifacts/milestones/05/final-sensorimotor/inputs/left-input-comparison.png)
and [right input comparison](../../artifacts/milestones/05/final-sensorimotor/inputs/right-input-comparison.png).
The old v1 crop loses all destination samples at the bottom wall.
`overview16_v2` remains a preserved static diagnostic and is not promoted.

**Whole-region retinal preservation of both patterns failed.** A separate
zero-neural-call inspection of the actual L1/L2 coordinates passed an independent
sampling oracle but found both pads' black/white contrast in only **48/529 camera
bins** in each population. These are bin counts, not time or area percentages.
At all recorded tracking visual positions, both complete pad contrasts reached
the retina on **zero ticks**. All 529 bins still distinguish swapped layouts in
at least 48 L1 and 47 L2 drive entries, potentially through one pad alone.
Consequently, full-input visibility does not establish complete retinal pattern
visibility, recognition, or task competence. The failed coverage assertion and
its source are retained; the candidate was not altered in response.

The full visual traces have changing next inputs after **453/1,011 moving steps
with an available next observation**. Both 16×16 pad contrasts are present on
1,024/1,024 visual confirmation inputs, with the retinal limitation above.
Black controls have no scene cues and no movement-dependent pixel changes.

Observation-only screening changes all 56 actions and positions in each layout,
but wall-band residence rises from 89/112 to 101/112 ticks. Motor-only screening
reduces that to 74/112 and stationary ticks from 19 to zero. These short comparisons
separate the two engineering changes; they do not estimate complete-game results.
Full visual confirmation covers the calibrated candidate only, so there is no
full-length uncalibrated visual performance estimate on the fresh seeds.

Mirrored visual confirmations differ on **254/256** motor actions for seed 51003
and **255/256** for 51004. End separations are 15.394 and 0.438 pixels. Each visual
versus matched black confirmation differs on all 256 actions, yet all outcomes
are timeouts. Equal or nearby endpoints therefore do not imply equal trajectories.
Across new trials, 101 matching seed/window/pixel groups reproduce raw neural
outputs and rates exactly. Three applicable 56-step prefixes also exactly reproduce
prior evidence, with matching runtime, model, input, seed and physics configurations.

Black-input motor/layout comparisons can reuse the recorded sequence exactly:
the model sees the same black pixels and task-independent window seeds regardless
of position or layout. Eight explicitly derived traces replay 1,648 source windows
with **zero new calls**; they are not independent neural trials. Both mirrored
black layouts follow identical paths for a given seed/motor. Full black controls:

| Seed | Motor | Execution | Wall band | Stationary | Visited bins |
|---|---|---|---:|---:|---:|
| 51003 | dark_balance_v3 | new model trial | 176/256 | 2/256 | 15 |
| 51004 | dark_balance_v3 | new model trial | 223/256 | 0/256 | 19 |
| 51003 | upstream_pilot_v1 | exact reuse | 250/256 | 49/256 | 12 |
| 51004 | upstream_pilot_v1 | exact reuse | 247/256 | 18/256 | 13 |

The [confirmation trajectories and inputs](../../artifacts/milestones/05/final-sensorimotor/analysis/confirm-trajectories-inputs.png),
[screening comparisons](../../artifacts/milestones/05/final-sensorimotor/analysis/screen-trajectories-inputs.png),
and [derived black controls](../../artifacts/milestones/05/final-sensorimotor/analysis/derived-black-trajectories-inputs.png)
show the actual recorded positions. Root visually inspected all three sheets,
both input sheets, and the fixture desktop/mobile captures. All confirmation
paths stay low in the arena; the visible destination pads remain unreached.
The fixture browser still labels its synthetic profile and closed admission.

## Runtime, checks, and preservation

**1,984 trial calls + 4 real-adapter regression calls = 1,988**, below the 2,048
user cap. The 60 unused calls were not reallocated. Screening took 158.747 seconds
and confirmation 552.473 seconds of episode wall time. The runner total was
**714.820 seconds** within its 1,300-second limit; fresh-process controller load
was 3.206 seconds and peak RSS 740.020 MiB. Model latency min/median/p95/max was
0.225/0.357/0.403/0.486 seconds. The four-call regression command took 7.483 seconds.
The host was not isolated: lightweight inspections and the 43.824-second required
repository verification overlapped trial execution. No real-time or service
capacity claim follows from these local measurements.

The actual runtime was Python 3.14.7, linked SQLite 3.53.4, NumPy 2.4.2, SciPy
1.17.1, and Node v26.8.2. The successful CI correction's historical SQLite 3.53.1
record remains intact; this experiment reports the runtime actually used.
Source HEAD was `f077ceb6d048d59606a9127ba2679b90411c49e5`; the exact execution tree, dependency/data
hashes, parameters, populations, checkpoint and seeds are in `trials/report.json`.
The graph remains `4279e2222475b986a096634ea5f6ac9518d0f8feff3f3c2ed52ad1139d3cd2ed`.

| Check | Actual result |
|---|---|
| Preflight pixels, isolation, motor, parity and sliding properties | PASS: 644 collected/passed, zero failures/skips. |
| Existing real-adapter reset/provenance regression | PASS: 1 test, exactly 4 real calls; identical repeated outputs. |
| `make verify test-upstream` | Exit 0: 2,257 Python + 150 upstream + 89 web contracts + 9 components + 2 fixture-browser passes; lint/generated types/build/locks/dependencies pass. |
| Later derived-metadata regression | PASS: 32 affected tests, including 1 new case beyond the 2,257-test full-suite collection. No duplicate counts added to the full suite. |
| Independent final replay | PASS: all 14 trials / 1,984 steps, exact raw/calibrated motor formulas, inputs, states, PNGs, schedule, call ledger and freeze verified. |
| Derived controls and analysis | PASS: 8 traces / 1,648 reused steps; all 22 metrics records and 29 comparisons reconstructed. |
| Original and revision replay | PASS: original 8/2,048, primary 16/1,536, overview 8/768 trials/steps; no neural reruns. |
| Raw-data/graph doctor; preservation | PASS: source checksums valid; all 496 inventoried original/revision artifact hashes unchanged. |
| Retinal preservation of both full patterns | FAIL across the whole operating region; exact sampling still matches its oracle. |
| Full real-model browser/worker release | BLOCKED: `make verify-real` exits 2; later integration is unimplemented. |

The original tracking test generator initially triggered a Hypothesis health-check
failure; its bounded random tile generator was corrected and subsequent tests
passed. Its original native logs were not retained, which the agent validation
record discloses; root's preflight/full-suite logs are retained. Early local lint
found an unused analysis import and ambiguous loop variables, then passed after
cleanup. Review caught stale inherited metrics in derived `trial.json`; that was
fixed before analysis execution and covered by the later regression. The separate
analysis artifact checker first compared Python tuples with JSON lists; it now
normalizes JSON structure while comparing every value. Its initial code/error log
and corrected PASS remain retained. The retinal-contrast assertion failure is a
substantive negative finding, not an error suppressed to claim sensory success.

[All scheduled results and comparisons](../../experiments/feasibility-final-v3-results.json),
[command argv/exits](../../artifacts/milestones/05/final-sensorimotor/commands.jsonl),
[test counts](../../artifacts/milestones/05/final-sensorimotor/test-counts.json), and
[full local evidence](../../artifacts/milestones/05/final-sensorimotor/) are available for review.
Evidence is ignored locally and must be preserved with the checkout.

The final handoff is **human review of milestone 05 only**. Navigation remains
unapproved, no configuration is promoted, learning is disabled/NOT_RUN, and
milestone 06 stays blocked. Recommend ending this navigation experiment;
a later stimulus-response interaction would require a separate decision.
