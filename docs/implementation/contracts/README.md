# Version 1 contracts

The source is `flytrap/contracts.py`. Generate the JSON Schema 2020-12 bundle with
`.venv/bin/python -m scripts.generate_contracts`; add `--check` to fail on missing
or stale output. The frontend generates its TypeScript definitions from
`web/src/generated/schemas.json` and compiles these schemas with strict AJV2020
runtime validation. Changes to generated artifacts must come from their generators.

All root and nested models require `schema_version: "1"`, forbid unknown keys,
and reject numeric strings, booleans in numeric fields, and nonfinite numbers.
JSON Schema defines integer by value: `1`, `1.0`, and `1e0` represent an integer.
Python normalizes finite integral floats before strict integer validation so this
agrees with JavaScript JSON parsing. Fractional numbers remain invalid integers.
Safe IDs contain lowercase ASCII letters, digits, underscores, or hyphens, start
with a letter, and have at most 64 characters. End anchoring rejects final newlines
in both runtimes. IDs are opaque identifiers; no caller field accepts a filesystem
path, executable, or URL.

SHA-256 fields contain exactly 64 lowercase hexadecimal characters. Source Git
revisions contain exactly 40. Timestamps are nonnegative Unix milliseconds bounded
by JavaScript's largest safe integer. Other counters, collection lengths, text,
positions, actions, durations, and configuration values have explicit bounds.
Seeds are unsigned 32-bit integers. A `RunRequest` cannot supply a seed: admission
will choose and persist it once, then retry attempts reuse it. Random stream
version `seed32_v1` reserves task-independent randomness for the later adapter.

| Contract | Role and version 1 boundary |
|---|---|
| ChallengeSpec | Two-choice preset, renderer version, approved textures, destination side, at most three preset distractions, content digest. Arena reachability and collision rules land in milestone 04. |
| RunRequest | Challenge ID, allowlisted controller kind, approved checkpoint ID. Registry approval is a server responsibility. |
| RunRecord | Immutable challenge/config digests and seed, checkpoint, state, bounded attempt number, timestamps, nullable error. |
| Observation | Exactly 256 normalized grayscale pixels, row-major 16 × 16 crop. No tick, position, seed, reward, score, labels, or challenge object. |
| ControllerOutput | Bounded `dx`/`dy` in [-1, 1], click, explicit `fixture` or `windowed_reset` mode, sampled-neuron/spike counts and neural milliseconds. |
| FrameEvent | Run/attempt/tick/event sequence, wall timestamp, action, position, canonical frame and observation digests. Environment state belongs outside controller input. |
| CheckpointRef | Opaque checkpoint ID, checkpoint/graph digests, explicit model mode. |
| ReplayManifest | Source commit/tree and upstream revision; locked environment versions; graph/data and ordered body/synapse digests; checkpoint/calibration/mode/seeds; arena/render/reward/action versions; initial state; ordered trace chunks/digests; result/timing/completion and claim status. |
| BenchmarkReport | Preregistration/source/model/checkpoint digests, bounded cohort/layout/seed lists, scheduled-episode metrics, uncertainty, limitations and claim status. |
| Capabilities | Fixture label, real-model availability, admission state, learning claim status, approved checkpoint/comparison IDs. |
| ErrorResponse | Versioned error code, bounded message and retryability. |

`canonical_sha256` hashes sorted-key compact UTF-8 JSON with nonfinite values
forbidden. This is the explicitly versioned Python encoding, not RFC 8785.
Challenge content uses only strings and a bounded string array, so it has no
cross-runtime float-format ambiguity. `create_challenge` validates content and
computes the hash with `content_sha256` omitted; it rejects a caller-supplied hash.
`verify_challenge_hash` checks integrity of an already validated challenge. JSON
Schema validates hash syntax; it cannot validate a digest against its content.
Both construction and tamper rejection have executed tests.

These schemas establish wire structure. They do not prove biological provenance,
registry approval, claim support, canonical frame correctness, timestamp ordering,
or an allowed state transition. Those require the layer that owns the data. A
complete replay's ordered chunks must contain the entire action log and observation
hash sequence; milestone 06/09 publication/verifier code must enforce continuity,
matching counts/digests and a complete final result. Merely parsing a manifest or a
`SUPPORTED` report never enables a claim. The foundation capabilities publish
`NOT_RUN` and empty approved comparison/checkpoint lists.

Additive fields are not silently tolerated because version 1 rejects unknown
fields. Changes to accepted fields, bounds, enum values, raster shape or model
semantics require a new schema version plus an explicit compatibility/migration
decision and cross-language cases. Existing replay versions must remain inspectable
or fail with an explicit unsupported-version error.

The proposed HTTP surface is:

| Endpoint | Milestone and behavior |
|---|---|
| GET `/health/live` | 01: process liveness. |
| GET `/health/ready` | 01: fixture worker readiness; real profile returns 503 unavailable. |
| GET `/api/config` | 01: validated capabilities; admission remains closed/unavailable. |
| POST `/api/challenges` | 08: validate/canonicalize approved preset and return its stored ID. |
| POST `/api/runs` | 08: session-scoped idempotency, atomic admission, server-selected seed, RunRecord. |
| GET `/api/runs/{run_id}` | 08: current RunRecord. |
| GET `/api/runs/{run_id}/events` | 08: one-way SSE, event ID/cursor recovery and terminal state. |
| GET `/api/runs/{id}/replay` | 09: immutable verified ReplayManifest/reference. |
| GET `/api/replays/{id}/download` | 09: safe artifact lookup by approved replay ID. |
| GET `/api/challenges/{id}` | 08: retrieve the stored challenge. |
| GET `/api/checkpoints` | 08/14: public-approved checkpoint list. |
| POST `/api/comparisons`, GET `/api/comparisons/{id}` | 14: gated, atomically admitted paired runs and retrieval. |
| GET `/r/{id}` | 09/14: replay/share page with initial-HTML metadata. |

The later persisted run state machine is `queued → running → completed | failed |
timed_out`. An expired/interrupted running attempt can requeue with a bounded
retry. Attempt history is immutable; lease fencing and one accepted final
publication belong to milestones 06–08. A scored trial timeout is a completed
simulation with `trial_timeout`; a resource deadline is an infrastructure outcome.
The foundation has no run admission or persisted run state machine.

Test ownership follows the boundary matrix:

- `tests/contracts/`: Pydantic/JSON Schema parity, shared wire cases, round trips,
  unknown and privileged fields, numeric validity, checked generation, content hash.
- `tests/property/`: pixel preservation, seed bounds, path rejection, bounded action,
  and canonical digest stability across object ordering.
- `tests/fixtures/contracts/cases.json`: labeled synthetic valid/invalid payloads
  consumed by Python and TypeScript; provenance values are fixture data.
- `web/tests/`: strict runtime schema validation, shared cases, nonfinite numbers,
  minimal UI rendering and explicit fixture/unavailability labels.
- Parent foundation tests own app lifespan, health/OpenAPI, settings, SQLite
  prerequisites and fixture worker process lifecycle; subsequent layer owners add
  the remaining BOUNDARIES obligations when those layers exist.
