# FLYTRAP architecture agreement

This is the target architecture from [PLAN](../../flytrap-kit/PLAN.md), recorded by
audit 00 and updated through arena 04. Upstream source is mapped in
[SOURCE_MAP](SOURCE_MAP.md); current validation is in [milestone 04](milestones/04.md).

Milestone 01 implements strict Pydantic contracts, generated JSON Schema/TypeScript
with AJV runtime validation, health/config API, file-backed SQLite connection
policy, a separate explicitly synthetic worker process, and a minimal React page.
The fixture API lifespan starts/stops that worker; this is a startup harness, not
the durable queue/coordinator of milestone 07. It admits no runs. The real profile
serves liveness/config but readiness returns 503. Production rejects fixture mode.
Default runtime imports neither wallet services nor an upstream checkpoint.

Milestone 03 adds the explicit untrained FlyController described in
[CONTROLLER](CONTROLLER.md). Its annotation injection and exact spike-count
extensions preserve upstream neural-window and motor behavior. It loads the real
prepared graph and runs through a bounded pixels-only envelope; API admission and
the existing fixture worker remain the foundation harness until their milestones.

Milestone 04 adds pure quantized arena physics, swept collision/scoring and one
canonical grayscale raster with a clipped 16×16 observation. [ARENA](ARENA.md)
freezes geometry, cue mapping, movement, tick limits, crop and digest encodings.
Only labeled fixture trajectories have been exercised in the arena so far;
full-model task feasibility belongs to milestone 05.

Python 3.14.7 and Node 26.8.2 are pinned with uv.lock and web/package-lock.json.
Python links SQLite 3.53.4; startup rejects versions below 3.51.3. Schema v1 reserves
a 16×16 normalized crop; later sampling parity work must preserve the contract or
explicitly version a shape change.

```text
Browser (React/TypeScript)
  → same-origin FastAPI JSON / bounded observation-only SSE
  → file-backed SQLite durable admission, queue, attempts, events
  → one worker coordinator with exclusive host slot
  → supervised simulator subprocess / bounded serialized IPC
  → FlyController → FlyEye → FlyBrain → bounded neural action
  → deterministic arena physics and scoring
  → immutable replay bundle + verified database reference
```

One host holds API, worker, and persistent local SQLite/artifact storage. WAL and
short transactions support separate connections; simulation runs outside request
handlers and database transactions. Pin the Python-linked SQLite to the kit's
minimum or verified backport and test startup rejection later. Host version 3.53.4
is an audit observation, not a lock for future containers.

The server owns the grayscale raster, bounded two-pad arena, geometry, crop,
physics, and scoring. The controller receives a versioned normalized pixel crop,
explicit model/checkpoint state, and task-independent random stream. Goals, task
objects, reward labels, coordinates, scores, and DOM data cannot cross the evaluation
controller boundary. A training-only reward interface is separate. Human overlays
never enter the raster. Prove this with observation-equivalence and import/IPC tests.

Preserve `FlyBrain.run()` behavior as explicit `windowed_reset`: membrane,
refractory state, and RNG restart per call. Inject both annotation read paths;
test crop parity against integer truncation/clipping in FlyEye. Freeze the action
mapping and terminal rules before measurement; use swept intersection scoring and
explicit ties. Keep neural milliseconds, environment ticks, and wall time distinct.

Build anatomical counts before transmitter weighting so dopamine edges survive as
metadata. Store ordered body/synapse mapping hashes. Loading checkpoints and gains
must be explicit, immutable, validated, and provenance-bearing. Do not import the
MushroomBody constructor's automatic load behavior into the core baseline.

Admission and quota consumption are atomic with session-scoped idempotency. A
single host lock complements transactional queue claiming. Attempts carry lease
tokens; heartbeats remain responsive during model work; stale workers cannot
publish. Execution may repeat after a crash, with one accepted final publication.
Write, flush/fsync, verify, and rename a complete artifact bundle before committing
the completed database reference. Reconcile orphans and surface corruption.

Replays include source revision and tree digest, runtime/dependency versions, data
and mapping hashes, calibration/checkpoint identity, seeds, reset mode, renderer and
physics versions, complete actions, observation hashes, timing, results, and file
digests. The verifier recomputes outcomes from traces. Browser replay retrieval must
work in another session and after restart.

Keep upstream files and assets intact. Add modules under `flytrap/` and an isolated
test hierarchy in later milestones. Existing `web/live.html` and `web/roam.html`
must survive any React scaffold under `web/`. Existing Docker and site entrypoints
serve other upstream workflows and are unsuitable FLYTRAP launch commands.

Fixture mechanics and real-model gates remain separate. No silent fixture fallback
or unsupported learning comparison. A complete real-data browser → API → durable
queue → simulator → artifact → second-session replay is a mandatory release gate.
Learning is an offline experiment and improvement claims stay disabled until a
qualifying controlled report supports them.
