# Historical milestone 05 trace diagnosis

All eight complete local episode bundles were read. Every one of the 2,048 actions, states, canonical rasters and controller observation hashes was reconstructed from the recorded version 1 inputs. No neural calls were made. Positive y points down.

| Episode | First wall tick | Left / bottom / corner dwell ticks | Zero / quantized / collision stationary ticks | Legal tangent canceled | First pad loss state tick | Visible inputs / unique inputs |
|---|---:|---|---|---:|---:|---|
| dev-51001-blank_left | 12 | 25 / 161 / 6 | 1 / 0 / 130 | 106 | 8 | 0 / 1 |
| dev-51001-half_left | 24 | 0 / 155 / 0 | 3 / 0 / 108 | 93 | 21 | 21 / 8 |
| dev-51001-left | 18 | 62 / 160 / 44 | 6 / 0 / 129 | 90 | 15 | 15 / 10 |
| dev-51001-right | 15 | 60 / 166 / 44 | 5 / 0 / 133 | 92 | 13 | 13 / 9 |
| dev-51002-blank_left | 21 | 31 / 148 / 9 | 1 / 0 / 117 | 97 | 20 | 0 / 1 |
| dev-51002-half_left | 32 | 25 / 164 / 5 | 7 / 0 / 127 | 106 | 21 | 23 / 10 |
| dev-51002-left | 16 | 87 / 162 / 46 | 2 / 0 / 146 | 105 | 9 | 10 / 11 |
| dev-51002-right | 16 | 55 / 174 / 24 | 2 / 0 / 146 | 114 | 11 | 12 / 11 |

Dwell counts BEFORE-state contact. Corner ticks also count toward the constituent walls; all right-wall, top-wall, and other corner dwell is zero. Environment ticks have no seconds conversion. The next table gives recorded controller compute seconds spent while each before-state was at contact, not environment or biological duration.

| Episode | Seconds through first wall | Left seconds | Bottom seconds | Left-bottom corner seconds |
|---|---:|---:|---:|---:|
| dev-51001-blank_left | 4.643 | 9.979 | 65.544 | 2.425 |
| dev-51001-half_left | 9.528 | 0.000 | 61.245 | 0.000 |
| dev-51001-left | 6.997 | 25.253 | 64.452 | 17.827 |
| dev-51001-right | 5.971 | 24.530 | 66.721 | 18.047 |
| dev-51002-blank_left | 8.581 | 12.076 | 59.201 | 3.588 |
| dev-51002-half_left | 12.334 | 9.879 | 64.997 | 1.867 |
| dev-51002-left | 6.198 | 34.962 | 64.366 | 18.475 |
| dev-51002-right | 6.232 | 22.056 | 68.952 | 9.607 |

| Episode | Raw requested x, y pixels | Scaled requested x, y pixels | Quantized requested x, y pixels | Actual net x, y pixels | Actual path length pixels |
|---|---|---|---|---|---:|
| dev-51001-blank_left | -136.889 / +304.864 | -136.889 / +304.864 | -136.816 / +304.586 | -38.668 / +14.703 | 370.923 |
| dev-51001-half_left | -139.556 / +276.988 | -69.778 / +138.494 | -69.727 / +138.262 | -34.301 / +15.605 | 219.938 |
| dev-51001-left | -111.111 / +286.531 | -111.111 / +286.531 | -111.082 / +286.285 | -41.125 / +16.000 | 311.785 |
| dev-51001-right | -112.889 / +305.111 | -112.889 / +305.111 | -112.848 / +304.852 | -41.125 / +16.000 | 302.061 |
| dev-51002-blank_left | -132.444 / +274.753 | -132.444 / +274.753 | -132.402 / +274.484 | -44.000 / +16.000 | 336.903 |
| dev-51002-half_left | -220.444 / +303.481 | -110.222 / +151.741 | -110.172 / +151.465 | -44.000 / +16.000 | 166.139 |
| dev-51002-left | -324.444 / +320.877 | -324.444 / +320.877 | -324.328 / +320.598 | -44.000 / +16.000 | 265.390 |
| dev-51002-right | -282.667 / +326.975 | -282.667 / +326.975 | -282.590 / +326.676 | -44.000 / +16.000 | 264.332 |

| Episode | Mean requested y before / after first wall | Mean actual y before / after first wall |
|---|---|---|
| dev-51001-blank_left | +1.342 / +1.183 | +1.340 / -0.005 |
| dev-51001-half_left | +0.582 / +0.527 | +0.581 / -0.002 |
| dev-51001-left | +0.867 / +1.127 | +0.866 / +0.000 |
| dev-51001-right | +0.996 / +1.185 | +0.996 / +0.000 |
| dev-51002-blank_left | +0.761 / +1.099 | +0.761 / +0.000 |
| dev-51002-half_left | +0.468 / +0.604 | +0.468 / +0.000 |
| dev-51002-left | +0.937 / +1.268 | +0.936 / +0.000 |
| dev-51002-right | +1.053 / +1.286 | +1.052 / +0.000 |

The contact action is isolated in JSON and excluded from the before/after drift means. Downward requested drift persists after contact, while net actual vertical displacement nearly vanishes. Most stationary ticks are collision effects, and many cancel a legal horizontal component. Quantization causes no stationary tick in these eight episodes.

Version 1 samples floor(position - 60 + 8*i), clipped to 0..95. At start (48, 76), sampled pad rows are 16 and 24. At y=88, the first sampled row is 28; destination raster rows are half-open 12..27, so no destination pixel is sampled for any y >= 88. Start sensitivity does not persist along the paths. Black controls can have geometric pad sample locations but contain no pad pixels; their visible-input count is zero.

See [crop comparison](../../artifacts/milestones/05/revision/diagnosis/crop-comparison.png), [exact coordinates and 256 raw bytes for each position/layout](../../artifacts/milestones/05/revision/diagnosis/crop-comparison.json), [full summary and historical file hashes](../../artifacts/milestones/05/revision/diagnosis/report.json), and each episode JSON for every requested/quantized/actual action, stationary cause, canceled tangent tick and visibility transition. The image includes actual positions from states 16, 64 and 128 of dev-51001-left. The canonical raster is shown alongside exact nearest-neighbor enlarged inputs; yellow crosses annotate sampled canonical pixel centers only.

Visual inspection: the top two destination texture rows appear in the starting input, become one row at path positions, and disappear entirely at the cutoff and all shown bottom-wall/actual later positions. Swapped scene textures remain visible to humans in the scene panels but the paired controller input panels are then identical.

Validation: targeted diagnostic/crop suite collected 33 and passed 33; failures 0, skips 0. These are synthetic behavioral tests and raster checks, not neural competence evidence.

Every outer wall and corner is enumerated below as `before-state ticks / recorded controller seconds`. A corner contributes to both of its wall columns.

| Episode | Left | Right | Top | Bottom | Left-top | Left-bottom | Right-top | Right-bottom |
|---|---|---|---|---|---|---|---|---|
| dev-51001-blank_left | 25 / 9.979 | 0 / 0.000 | 0 / 0.000 | 161 / 65.544 | 0 / 0.000 | 6 / 2.425 | 0 / 0.000 | 0 / 0.000 |
| dev-51001-half_left | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 155 / 61.245 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 |
| dev-51001-left | 62 / 25.253 | 0 / 0.000 | 0 / 0.000 | 160 / 64.452 | 0 / 0.000 | 44 / 17.827 | 0 / 0.000 | 0 / 0.000 |
| dev-51001-right | 60 / 24.530 | 0 / 0.000 | 0 / 0.000 | 166 / 66.721 | 0 / 0.000 | 44 / 18.047 | 0 / 0.000 | 0 / 0.000 |
| dev-51002-blank_left | 31 / 12.076 | 0 / 0.000 | 0 / 0.000 | 148 / 59.201 | 0 / 0.000 | 9 / 3.588 | 0 / 0.000 | 0 / 0.000 |
| dev-51002-half_left | 25 / 9.879 | 0 / 0.000 | 0 / 0.000 | 164 / 64.997 | 0 / 0.000 | 5 / 1.867 | 0 / 0.000 | 0 / 0.000 |
| dev-51002-left | 87 / 34.962 | 0 / 0.000 | 0 / 0.000 | 162 / 64.366 | 0 / 0.000 | 46 / 18.475 | 0 / 0.000 | 0 / 0.000 |
| dev-51002-right | 55 / 22.056 | 0 / 0.000 | 0 / 0.000 | 174 / 68.952 | 0 / 0.000 | 24 / 9.607 | 0 / 0.000 | 0 / 0.000 |

Cue transitions below refer to geometric pad sampling at the BEFORE state. `15 absent` means the action taking state 15 to state 16 receives no destination-pad sample. The first wall-contact tick is the AFTER state of the contacting action: tick 18 means action 18 advances state 17 to wall contact at state 18. The 256 observations therefore use state ticks 0 through 255. A `present` transition in a black control indicates only that the canonical crop would include pad coordinates; its actual supplied pixels remain black.

| Episode | All geometric cue visibility transitions (state tick) |
|---|---|
| dev-51001-blank_left | 0 present, 8 absent, 42 present, 44 absent, 100 present, 101 absent |
| dev-51001-half_left | 0 present, 21 absent |
| dev-51001-left | 0 present, 15 absent |
| dev-51001-right | 0 present, 13 absent |
| dev-51002-blank_left | 0 present, 20 absent, 206 present, 207 absent |
| dev-51002-half_left | 0 present, 21 absent, 24 present, 25 absent, 27 present, 28 absent |
| dev-51002-left | 0 present, 9 absent, 228 present, 229 absent |
| dev-51002-right | 0 present, 11 absent, 228 present, 229 absent |

This diagnosis supports a bounded physics and sensory experiment. It demonstrates neither an engaging two-choice interaction nor task competence or learning. Milestone 05 human review remains PENDING; milestone 06 is not authorized.
