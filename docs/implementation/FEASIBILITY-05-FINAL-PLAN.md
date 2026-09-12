# Final bounded sensor-to-movement experiment

Human review of milestone 05: **CHANGES_REQUESTED**. The human accepts the
previous diagnostic work and negative conclusion; navigation is unapproved and
milestone 06 is **BLOCKED**. This document defines the final experiment before
any new full-graph neural calls. No condition is promoted by its execution.

## Inspection and candidate definitions

`flyeye.py:131–149` averages per-neuron window rates in Hz. Steering is
right DNa02 minus left DNa02, divided by 450. Forward drive is averaged DNa01
minus MDN, divided by 450, clipped, then attenuated by DNp09. Negative speed
becomes positive (downward) y. The adapter divides upstream pixel output by 90;
the arena multiplies normalized actions by 8 pixels per axis per tick and
truncates to 1/256 pixel. Signs and units agree; no axis correction is justified.
The comment describing forward drive as a sum actually implements an average.

The existing 384 visual `tangent_v2/crop16_v1` windows have mean DNa02 L/R
251.953125/186.458333 Hz, DNa01 L/R 138.802083/41.276042 Hz, MDN 200.651042 Hz,
and DNp09 119.856771 Hz. Those rates request mean x = -1.164352 and y = +1.409144
pixels/tick. Collision then removes outward motion. This explains left/down
drift without treating the population-to-cursor mapping as validated biology.

`FlyEye` selects annotated L1/L2 cells, maps their hex coordinates to a unit
square, then truncates/clips image coordinates. Adapter coordinates are always
(8,8), field 16×16, float32 pixels in [0,1]. L1 input is luminance ×180 Hz;
L2 is (1-luminance) ×108 Hz. Black pixels are therefore active OFF stimulation,
not a silent neural control. Missing retinal coordinates are excluded. DNa02
and DNa01 sides use `somaSide`; MDN and DNp09 include their entire named
populations. Exact counts are saved from real provenance.

`FlyBrain.run` resets membrane voltage, refractory counters, and RNG each
100-step, 20 ms call. The adapter derives seeds from run seed and window index;
its reset restores all-one gains. We retain those dynamics, resets, populations,
input intensity, baseline checkpoint, and disabled learning.

`roam.py:535–555` clips the browser cursor, scrolls 300 pixels at the vertical
margins, and resets its y coordinate to 550 or 250. This changes both visible
page and cursor position. Its direction comment reverses the actual pilot signs.
That is a comment inconsistency; the implemented scrolling/recentering means
the browser demonstration is not evidence of bounded-arena navigation.

The **only observation candidate**, `tracking16_v3`, samples each axis at
`clip(floor(3 + 6*i + (position - 48)/4), 0, 95)`, i = 0…15. It is a 96-pixel
field whose camera center follows one quarter of displacement from arena center.
This task-independent camera calibration keeps both texture regions sampled
over the intended square [4,92]² while translating image content with movement.
It uses the original canonical raster with no avatar or scoring overlay. Exact
bytes, sampling coordinates, contrast, and layout differences are checked over
every quantization bin and displayed at representative positions. It sacrifices
the stronger motion parallax of v1; small movements can quantize to identical
inputs. `overview16_v2` is static and is not a navigation candidate.

The **only motor candidate**, `dark_balance_v3`, applies two positive fixed
readout weights: `a = mean(steer_R)/mean(steer_L)` and
`b = mean((fwd_L+fwd_R)/2)/mean(back)`, measured from the two existing unique
96-window black-input traces, seeds 51001 and 51002, tangent physics, crop v1,
left layout. Duplicate black layouts are excluded. Source hashes and exact
constants are frozen in the preregistration. The formula is:

```
dx = clip((steer_R - a*steer_L)/450, -1, 1)
dy = -clip(((fwd_L+fwd_R)/2 - b*back)/450, -1, 1)
     * (1 - clip(stop/450, 0, 1))
```

Original click telemetry is retained. These are engineered motor readout weights,
not neural gains or learning. Silence still produces zero motion. Equal mean
opponent rates before stop attenuation do not guarantee zero mean final motion.
Black stimulation is an arbitrary calibration origin, not biological rest.
The uncalibrated output and all rates are retained on every step.

## Frozen schedule, controls, budget, and stopping rules

All trials are development-only, with no outcomes used to fit parameters.
All use `two_choice_v1`, no distractions, `tangent_v2`, the same start (48,76),
8 pixels per normalized action, and the unchanged 256-tick scored timeout.

Screening uses seed **51001**, eight episodes of at most **56 ticks** each:
v1 observation/uncalibrated motor on both visual layouts; tracking observation/
uncalibrated motor on both; tracking/calibrated on both; tracking/black on the
left layout with each motor mapping. Observation and motor effects thus have
separate matched comparisons. The 56-tick limits are incomplete diagnostic
cutoffs, never complete games or scored timeouts.

Confirmation uses fresh development seeds **51003 and 51004**, reserved from
calibration and screening. For each, run tracking/calibrated on left and right
visual layouts and one black-input episode: six episodes, each allowed to run
through first pad contact or the full **256-tick scored timeout**. No selection
based on screening outcomes and no parameter changes before or during confirmation.
The black rate sequence may also be replayed with the other layout and original
motor mapping: identical black pixels, checkpoint, seed and internal window make
that reuse exact. Derived controls are explicitly labeled and not independent
neural trials. Full visual confirmation is limited to the calibrated candidate;
the uncalibrated visual comparisons remain short screening diagnostics.

Maximum scheduled calls: **448 screening + 1,536 confirmation = 1,984**.
One existing real-adapter repeatability regression adds **4**, for **1,988**
new full-connectome model calls maximum. The remaining **60** of the user's
2,048 cap are unused, not available for further candidates or replacement seeds.
Synthetic fixture tests use tiny labeled graphs, separately from this real-model
compute budget. Every attempted trial call is durably counted before invocation.
Failure stops the run, retains partial traces, and marks remaining scheduled
trials NOT_RUN. No retries, extensions, or budget reallocation. No new real
model calls are authorized after these scheduled trials and the four-call check.

Wall budget: 1,300 seconds for the serial trial runner, plus at most 120 seconds
for the real-adapter regression (test timeout). Historical ~0.4 s/call suggests
~795 seconds neural time; the balance covers load and host variability.
Load time, call latency distribution, RSS, failures and elapsed phase/total
time are recorded. A wall deadline is infrastructure failure, not a scored timeout.

## Metrics and decision

Recompute raw requested, calibrated requested, quantized and executed motion;
signed drift, movement direction counts, actual path length; exact wall/corner
residence and residence within eight pixels of any wall; stationary causes;
visited 8×8-pixel bins and spatial extents; both-pad sampling/contrast, distinct
input hashes and changes following movement; destination contacts and termination;
matched layout, black, observation-only and motor-only trajectory differences.
Save all actual trajectories and representative exact controller inputs.

Engineering passes require finite real output, exact input and physics replay,
preserved model/checkpoint identities, honest accounting, and affected unit,
property, contract and regression checks. Interaction suitability is a separate
human decision. If full visual confirmation predominantly occupies the boundary
band (>50% of before states within eight pixels of a wall), with continued
directional drift and no convincing exploration/contact behavior, recommend
stopping this navigation approach. A stationary-tick reduction or isolated
destination contact cannot establish a playable interaction, recognition, or
learning. Preserve simulation/evidence for a possible later stimulus-response
interaction; do not implement that pivot or milestone 06.

Return all scheduled results and an engineering/interaction verdict for human
review. Existing evidence/configuration/tests and the CI runtime correction
remain preserved. No deployment, remote write, PR, paid resource or publication.
