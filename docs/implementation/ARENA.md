# Deterministic arena and raster

Milestone 04 implements [core.py](../../flytrap/arena/core.py) and
[render.py](../../flytrap/arena/render.py). These are pure local building blocks;
the durable worker, replay service and browser arena display come later.

## Versioned rules

`two_choice_v1` is 96×96 pixels. The controlled object is a point, with initial
position (48,76). Its center stays within the closed square [4,92]×[4,92].
The left pad is [12,36]×[12,28], the right [60,84]×[12,28]. A pad counts closed
boundary contact. Their raster fills use half-open rectangles, so an endpoint on
the lower/right scoring boundary can visually sit one pixel beyond the pattern.
The collision body has no rendered avatar or radius; human decoration does not
change it.

Distractions are solid white rectangles at x=[44,52] and y=[36,40], [48,52],
[60,64], named top/middle/bottom. Choose zero through three, without duplicates,
in that canonical order. These fixed presets leave a clear lower horizontal
corridor and vertical routes at x=24 and x=72 to both pads. Arbitrary rectangles,
overlapping pads and arrangements that block those routes are rejected. Pads
have an eight-pixel margin from the wall's inner boundary and a 24-pixel gap.

Each scene has one stripes pad and one checkerboard pad. `destination_v1`
scores entry into the selected destination as `success`, the other as
`wrong_pad`. `build_arena` requires the selected side's texture to match an
explicit cohort `target_texture`, default `stripes`. A checkerboard-reward cohort
must explicitly select that rule. Reversing the destination while keeping the
same cohort rule fails. Do not mix different reward mappings within a cohort.

`generate_challenge` produces deterministic bounded presets from an unsigned
32-bit development seed. This seed is separate from the controller's run seed.
It can generate either destination side; later evaluation must enumerate equal
side counts explicitly. Random generation alone is not exact counterbalancing.
The existing ChallengeSpec wire schema is unchanged; geometry, uniqueness,
ordering, digest and cohort checks occur at the arena admission boundary.

## Motion and termination

`bounded_xy_v1` uses **8 pixels per tick per axis**. Revalidate ControllerOutput,
multiply each bounded dx/dy by 8×256, and truncate toward zero. State coordinates
are integer multiples of 1/256 pixel. Diagonal movement therefore has a maximum
length of 8√2 pixels. Positive y points down. Tiny actions may quantize to zero.

The full proposed segment is intersected with walls, solid obstacles and pads
using rational arithmetic. The first contact stops both axes. Solids block entry
into their open interior; tangency and movement along or away from a contacted
edge are allowed. There is no sliding correction. Intersections are quantized
toward the preceding position, preventing movement through a contacted solid.

Order equal-time contacts by solid before pad, then left before right. Legal
preset geometry prevents simultaneous solid/pad or two-pad contacts; the ordering
is still explicit. Pad contact takes precedence over the tick-limit outcome.
A trial ends after **256 environment ticks** with `trial_timeout` if it has not
reached a pad. Further steps raise an error. Click and neural telemetry do not
affect scoring or movement. Physics has no clock or random input: neural
milliseconds, environment ticks and wall time are separate quantities. A future
worker resource deadline must be an infrastructure failure, not a trial timeout.

## Canonical pixels and crop

`grayscale_v1` produces immutable row-major uint8 bytes, exactly 96×96. Background
is 128; the four-pixel perimeter is 0; distraction rectangles are 255. Pad
patterns use local eight-pixel cells. Stripes alternate by x-cell; checkerboard
alternates by x+y parity. The first cell is white (255), the next black (0).
`render` accepts only the visible immutable Scene. Scoring, checkpoint metadata,
labels, path, avatar, tick and score are absent from that input.

`crop16_v1`, fixed as part of renderer v1, samples a **128×128 world-pixel field**
into the existing 16×16 Observation. For each axis, sample index i at
`floor(position - 64 + 4 + 8*i)`, then clip to [0,95]. This is nearest sampling
at each output cell center, with edge replication and no interpolation.
Normalize sampled bytes with Python division by 255. FlyController then converts
to float32 and uses its documented clipped 16×16 retinal sampling; see
[CONTROLLER](CONTROLLER.md). Texture/obstacle aliasing at this resolution is a
declared condition for milestone 05's visual-feasibility measurements.

Frame SHA256 hashes 9,216 raw raster bytes. Observation SHA256 hashes 256 sampled
raw bytes before normalization, **not JSON floats or PNG encoding**. Renderer and
crop versions give those digests meaning. `png_bytes` losslessly encodes the
same raster for later browser display; tests decode it and compare every pixel.
The earlier adapter smoke's JSON-envelope hashes are diagnostic evidence with a
different stated encoding, not arena observation digests.

## Local evidence and handoff

Run `make test-arena EVIDENCE=artifacts/milestones/04` for the arena boundary
tests. `make arena-samples EVIDENCE=artifacts/milestones/04` exports canonical
pixels/PNG, an observation PNG, four complete action traces and separate human
overlay PNGs under `artifacts/milestones/04/samples/`.

All sample paths are explicitly **SCRIPTED FIXTURE — NOT REAL MODEL**. They
demonstrate success, wrong-pad, obstacle timeout and wall timeout rules. Neural
time is zero. The renderer never reads the overlays. Golden fixtures have their
own [construction notes](../../tests/fixtures/arena/README.md).

The information-flow regression runs the actual adapter on a labeled synthetic
graph. Identical pixels/checkpoint/run seed produce byte-identical controller
output under two different explicit cohort scoring rules. This validates the
boundary, not model competence. Milestone 05 must measure actual full-graph arena
trajectories and controlled visual sensitivity before deciding an interaction
mode. Learning and improvement claims remain disabled.
