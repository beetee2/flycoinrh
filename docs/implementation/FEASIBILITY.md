# Real-model feasibility — development report

**Automated PASS · human review PENDING · learning NOT_RUN.**

Decision: **GO for a queued experimental core with explicitly labeled replay**,
subject to human review. The actual model produces finite, pixel-sensitive output,
but this pilot provides no evidence of useful task-solving. Every scheduled episode
is retained below, including timeouts. The next milestone must wait for review.

The frozen selection is [core-v1.json](../../experiments/core-v1.json). It retains
the existing two-choice geometry, zero distractions, stripes reward cohort,
8-pixel action mapping, 256-tick limit, all-one gains and windowed resets.
Both destination sides remain supported. The half-speed development variant is
not selected: it did not provide evidence warranting a mapping change. No held-out
evaluation has run. Any future tuning requires a new version before evaluation.

## Measured cost

Workstation: Intel(R) Core(TM) i9-10900KF CPU @ 3.70GHz; 31.1 GiB physical RAM; Python 3.14.7,
Node v26.8.2, linked SQLite 3.53.4.
Exact software versions, source identity and data hashes are in the
[JSON summary](../../experiments/feasibility-v1-results.json) and full
[execution report](../../artifacts/milestones/05/trials/report.json).

| Measurement | Actual value |
|---|---:|
| Baseline preparation / controller construction | 1.926 / 3.200 s |
| Combined startup | 5.125 s |
| Step latency min / median / p95 / max | 0.289 / 0.399 / 0.447 / 0.558 s |
| Peak process RSS | 739.1 MiB |
| Episode ticks / simulated neural time | 256 / 5,120 ms each |
| Actual model calls | 2076 (2048 episode + 28 probe) |

First construction used a fresh process, with OS file caches retained and baseline
preparation reading the graph first. This is not a cold-storage measurement.
Wall cost is separate from neural simulated time. The host was not isolated;
brief lightweight analysis tests ran concurrently. The p95 is descriptive.

Proposed worker limits are one active simulation, one queued job, a **240-second**
episode resource deadline, **1536 MiB** simulator memory allowance, and
progress snapshots about every **1 second**. The deadline is twice
the sum of startup and 256 times measured p95, rounded upward to ten seconds. Memory is
twice measured peak RSS, rounded upward to 256 MiB. One queued job bounds nominal
waiting to one deadline; it is not a throughput guarantee. These are proposed
budgets for later worker/container validation, not implemented admission controls.
A future resource deadline must remain an infrastructure termination, distinct
from a scored 256-tick timeout.

## Complete development episodes

| Trial ID | Outcome | Wall s | Stationary % | Longest stationary ticks | Path pixels |
|---|---|---:|---:|---:|---:|
| dev-51001-left | trial_timeout | 103.24 | 52.7 | 41 | 311.8 |
| dev-51001-right | trial_timeout | 103.12 | 53.9 | 41 | 302.1 |
| dev-51001-blank_left | trial_timeout | 103.47 | 51.2 | 12 | 370.9 |
| dev-51001-half_left | trial_timeout | 101.76 | 43.4 | 16 | 219.9 |
| dev-51002-left | trial_timeout | 101.68 | 57.8 | 19 | 265.4 |
| dev-51002-right | trial_timeout | 101.54 | 57.8 | 19 | 264.3 |
| dev-51002-blank_left | trial_timeout | 102.39 | 46.1 | 11 | 336.9 |
| dev-51002-half_left | trial_timeout | 101.04 | 52.3 | 12 | 166.1 |

View the [eight recorded trajectories](../../artifacts/milestones/05/trajectories.png).
Blue is the start; red is the recorded path/end. Each full-resolution overlay
and complete trace is under its trial ID in
[trials](../../artifacts/milestones/05/trials/). The blank control sees only black
pixels; its displayed scene is the scored world, not the sensory input.
Half-speed changes only the declared multiplier and retains raw motor output.
Stationary fractions count positions after collisions, not absence of neural
activity. Neural activity and nonzero motor output continued during wall trapping.

## Controlled visual sensitivity

Every input was presented at step index zero after resetting the same checkpoint
to the same seed. Each of 14 seed/input pairs repeated twice with exactly equal
serialized model outputs. All six non-dark conditions changed motor output and
spike telemetry against dark input for both matched seeds. Swapping the two
canonical pad layouts also changed motor output for both seeds. These are local
sensitivity measurements; they do not establish recognition, preference, or learning.
The [input contact sheet](../../artifacts/milestones/05/probe-inputs.png) shows
the exact grayscale inputs. Probe hashes and outputs remain in the JSON report.

## Verification and review

The independent verifier reconstructed every applied action, state, observation
hash and scored result; checked all schedules/repetitions; decoded canonical PNGs;
and bound the real baseline, graph, configuration and execution-source hashes.
It did not independently re-run the neural computation. The execution snapshot
precedes the verifier and report files; final source identity is recorded separately
in [milestone 05](milestones/05.md).

Review the trajectories and their wall cost, the queued/replay interaction choice,
the zero-distraction preset, and the explicit absence of task-solving or learning
claims. Human review remains PENDING. This completes the automated feasibility
work; it does not pass the later full browser/worker release gate.
