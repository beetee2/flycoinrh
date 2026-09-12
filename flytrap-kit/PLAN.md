# FLYTRAP — implementation plan

Prepared for Brad • 2026-09-11

This is an implementation specification and ordered agent-prompt kit, not a completed application or a record of executed application tests. The source inspection used upstream commit `8748e5bd30794d14afeb3441904221b52a002cac`; the implementation agent must inspect the actual checkout and record any differences before changing code.

## 1. Product and completion criteria

Build a public, wallet-free browser challenge called FLYTRAP: a visitor arranges a constrained visual challenge, submits it, watches a connectome-based simulation produce movement, and shares an inspectable replay. The software scores the task; the controller receives only the rendered visual observation, its own model state, and a task-independent random seed stream. There is no language model, goal-coordinate injection, path planner, or hidden corrective steering in its control loop.

The minimum competition entry is a real-model challenge with provenance, honest telemetry, persistent runs, a working queue, and shareable replays. Learning is a gated experiment, not a condition that must be made to look successful. Implement and test the research machinery, but leave learning-improvement claims and the trained comparison disabled unless measurements support them.

A complete core release must pass a real-data run through browser → HTTP API → durable queue → isolated simulator → artifact publication → replay in a second browser session. Fixture-only tests are necessary but cannot satisfy that gate. Performance or learning superiority is not required to validate honest model-driven behavior.

Do not add wallets, token launches, transactions, public training endpoints, arbitrary website browsing, arbitrary uploads, user-written executable code, language-model narration, Kubernetes, Redis, or billing. Do not build a complicated maze before proving that the controller supports the basic two-choice arena.

## 2. Source facts that affect the implementation

At the inspected revision:

- `FlyBrain.run()` initializes membrane state, refractory counters, and its random generator on each call. Preserve this as a named `windowed_reset` mode for the core. A continuous mode would be a separately versioned model change with additional tests, not a silent refactor. [S1]
- `FlyPilot.step()` accepts a grayscale image and cursor coordinates, samples a local visual field through `FlyEye`, and returns movement/click signals derived from recorded neural activity. The adapter can provide an already-cropped observation centered at fixed coordinates, but sampling parity must be tested. Annotations are partly loaded through a working-directory-relative path, so data paths need injection. [S2]
- The fast matrix is stored as `W[post, pre]`. Dopamine gets zero fast weight and is removed from that matrix. `mushroom.py` nevertheless compares `W[pam][:, mbon]` and `W[ppl1][:, mbon]` as incoming connectivity. Preserve separate anatomical count metadata; a transpose of the fast matrix alone cannot recover removed edges. [S3, S4]
- The latest inspected commit adds calibration machinery, including reported olfactory experiments. Inspect it, but do not treat reported odor results or a preset named `CHOSEN` as evidence of visual task learning. Record any selected gains as an explicit experimental condition. [S5]
- Runtime learning persistence currently has implicit load behavior and broadly catches failures. FLYTRAP must not inherit undisclosed checkpoints or silently ignore corruption. [S4]

These are code-level observations. Correcting orientation or retaining anatomy does not, by itself, validate biological compartment labels, the learning rule, or task-level improvement. In product copy say “connectome-based simulation,” not an uploaded living brain or proof of intelligence.

## 3. Architecture

Use a small modular Python backend, a React/TypeScript interface, a real SQLite database on local persistent disk, and one simulation worker on the same host. Use FastAPI for HTTP and server-sent events (SSE). Prefer standard-library SQL access plus explicit numbered migrations over introducing an ORM just for this project; adapt only if the checkout already has a justified equivalent.

```text
Browser: editor / live viewer / replay / sharing
                    |
           HTTP JSON + SSE (same origin)
                    |
       FastAPI: validation / quotas / queries
                    |
       SQLite: challenges / runs / attempts / events
                    |
       Single worker coordinator + exclusive host slot
                    |
       Bounded IPC → simulator subprocess
                    |
    FlyController → FlyEye → FlyBrain → motor action
                    |
       Deterministic arena advances and scores
                    |
       Durable events + finalized replay artifacts
```

SSE is one-way observation. Visitors cannot steer through its channel. The API must remain responsive while simulation is running. Simulation runs in a separate process, not in request handlers or event-loop-blocking background tasks. Keep database write transactions short and do not run simulation while holding one.

SQLite WAL permits useful reader/writer concurrency but retains a single-writer constraint and requires processes sharing WAL state to be on the same host. This design therefore deliberately excludes network filesystem database mounts and multiple application hosts. Moving beyond one host requires a new storage/queue decision, not scaling the existing deployment blindly. [S6]

Suggested modules, preserving upstream code and notices:

```text
flytrap/
  contracts.py
  arena/          # validation, fixed-step physics, scoring, canonical raster
  controllers/    # protocols, real fly adapter, test-only and baseline controllers
  learning/       # optional anatomical classification, training, evaluation
  persistence/    # repositories and numbered SQL migrations
  artifacts/      # manifests, trace files, verification, safe publication
  worker/         # exclusive slot, leases, supervision, bounded IPC
  api/            # app factory, routes, SSE, sessions, admission limits
  cli.py
web/              # React + TypeScript; same production origin as the API
tests/
  unit/
  property/
  contracts/
  integration/
  real_model/
web/tests/        # component tests and Playwright projects
docs/implementation/
  STATUS.md
  ARCHITECTURE.md
  THREAT_MODEL.md
  contracts/
  milestones/
experiments/      # preregistered configurations and small result summaries
artifacts/        # ignored local test evidence and generated outputs
```

Record the SQLite library actually linked by Python, not just the operating-system command-line version. Require SQLite 3.51.3 or later, or a specifically verified vendor backport of the WAL-reset fix; current SQLite documentation identifies that fix as necessary for the rare multi-connection WAL race. Add a startup/doctor check and test the rejection path. [S6]

Use one validated, locked Python runtime and one locked Node runtime compatible with the chosen dependencies. Do not guess that every upstream version pin remains installable. Use lockfiles and record the resolved versions. Keep a fixture test profile and a real-connectome profile, with different labels and gates.

## 4. Authoritative arena and controller boundary

Start with two reachable destination pads near the top of a compact arena and a fixed lower starting position. Use high-contrast grayscale patterns, no text recognition task. Permit only bounded choices such as destination side, approved textures, and zero to three approved distractions. Both destination regions must remain reachable and nonoverlapping. Use presets rather than arbitrary geometry for version one.

The cue-to-reward mapping must be consistent within a training cohort and its evaluation. Counterbalance destination position across challenges. When comparing different cue mappings, train separate cohorts. Do not randomize the correct destination invisibly on each evaluation episode and then claim a vision-only agent ought to learn it.

One canonical server-side renderer produces the sensory raster. The browser displays that raster, not an independently reimplemented scene. A separate overlay may show labels, the avatar, a path, or scores to humans; these must not enter the observation. Keep integer/quantized geometry, explicit clipping, texture versions, pixel normalization, and a defined nearest-neighbor crop so replay does not depend on fonts or browser antialiasing.

Proposed controller contract:

```python
class Controller(Protocol):
    def reset(self, *, run_seed: int, checkpoint: CheckpointRef) -> None: ...
    def step(self, observation: Observation) -> ControllerOutput: ...
```

`Observation` contains a bounded, normalized grayscale crop and its schema version. Tick/seed handling is internal and task-independent. `ControllerOutput` contains bounded movement plus genuine neural telemetry. A training-only interface can receive a bounded reward event after an observed action and outcome; evaluation never receives rewards or privileged world state.

The controller must not accept `ChallengeSpec`, goal coordinates, target labels, distance-to-goal, DOM nodes, a precomputed path, scores, or the environment object. Use an import boundary and an explicit serialized IPC envelope. An information-flow test changes hidden scoring metadata while keeping observation pixels, checkpoint, and seed identical; the controller's output must remain identical in the locked runtime. This is evidence of the interface boundary, not a proof against deliberately malicious code with unrestricted host access.

Freeze movement scaling, clamping, collisions, trial limits, and goal rules before evaluating. No runtime recentering, target attraction, scripted turn, or success animation may change a real trajectory. Score swept segment intersections so a large step cannot tunnel through pads or walls. Define tie-breaking when one step intersects more than one terminal region. A click is telemetry, not initially a success requirement.

Distinguish neural simulated milliseconds, environment ticks, and elapsed wall time. An experiment hitting the tick limit is a scored timeout; a worker hitting a resource deadline is an infrastructure termination and must be recorded separately.

## 5. Data contracts and provenance

Define versioned Pydantic models, checked JSON Schema/OpenAPI output, generated TypeScript types, and cross-language fixture validation. TypeScript compile-time types alone are not runtime response validation. Reject unknown fields, invalid enums, nonfinite numbers, out-of-range seeds, excessive arrays, oversized bodies, and client-supplied filesystem paths.

Required models:

| Contract | Important fields |
|---|---|
| ChallengeSpec | schema/preset/renderer versions, allowed texture choices, bounded layout parameters, canonical content hash |
| RunRequest | challenge ID, approved controller/checkpoint ID; seed policy is server-defined |
| RunRecord | run ID, source challenge, immutable seed/config, state, attempt, timestamps, approved model IDs |
| Observation | fixed shape/range pixels, schema version; no privileged task fields |
| ControllerOutput | finite bounded action, genuine sampled telemetry, model mode |
| FrameEvent | run/attempt/tick/event sequence, timestamps, action/state summary, canonical frame and observation hashes |
| ReplayManifest | complete provenance, trace digest, ordered chunk list, completion/incompleteness state |
| BenchmarkReport | preregistration hash, cohort/layout/seed lists, metrics, uncertainty, limitations, claim status |
| Capabilities | real model availability, admission state, fixture flag, approved comparison/report IDs |

A replay manifest must include source commit and source-tree digest, upstream revision, dependency/environment versions, graph/data checksums, ordered body/synapse mapping hashes, checkpoint hash, calibration/gain config, neural-state mode, random seeds, arena/render/reward versions, action mapping, initial state, complete ordered action log, observation hashes, final result, wall/simulated timing, and artifact digests. Derived metrics must be recomputable from the trace, not accepted from the client.

Checksums establish consistency and reproducibility within declared versions; they do not independently prove biological fidelity or prevent a dishonest author from fabricating an entire signed-looking dataset. Avoid “cryptographic proof the fly is real” claims.

## 6. Database, artifacts, and worker semantics

Use actual file-backed SQLite in integration tests, separate connections for API/worker behavior, `foreign_keys=ON`, WAL, and a bounded busy timeout. Suggested tables are `schema_migrations`, `challenges`, `sessions`, `runs`, `run_attempts`, `run_events`, `checkpoints`, and `comparison_pairs`. Add constraints, uniqueness, and indices with migrations. Store high-volume traces in bounded artifacts, not one database row per neuron per timestep.

Idempotency is scoped to a visitor session and key, with a normalized request digest. Same key and same payload returns the original run; same key and different payload returns 409. Admission, quota consumption, and job creation must be one transaction. A retry must not consume another queue slot.

Use an exclusive host-level worker lock or equivalently tested singleton mechanism. Queue claiming must also be transactional. A second worker must not start a second active simulation just because it selected a different job. Bind writes to the current attempt/lease token. Renew heartbeat independently of a slow model step; supervise a child process so an actual deadline can terminate hung computation. Release/restart cleanly after signals or crashes.

State transitions:

```text
queued → running → completed | failed | timed_out
            |
            └─ expired/interrupted attempt → queued (bounded retry)
```

The immutable attempt record explains every retry. Simulation execution may occur more than once after failures; do not claim exactly-once execution. Enforce one accepted final publication using state/lease checks. If a retry starts from tick zero, retain the first attempt as interrupted and make the retry visible.

Artifact publication order is: write temporary files under the configured root → flush/fsync → compute and verify digests → atomically rename a complete immutable bundle → commit its reference and completed run state. A crash between rename and database commit leaves an orphan for reconciliation, not a completed record referencing a missing file. Never overwrite an already published immutable replay. Corrupt/missing artifacts must surface as errors. Bound compressed and decompressed sizes and reject unsafe paths.

Provide backup/restore using SQLite's supported backup mechanism while quiescing or snapshotting immutable artifacts consistently. Test restoration. Do not copy just the active database file and assume the WAL contents are included. [S9]

## 7. HTTP and stream boundary

Default routes:

```text
GET  /health/live
GET  /health/ready
GET  /api/config
POST /api/challenges
GET  /api/challenges/{id}
POST /api/runs                     # Idempotency-Key required
GET  /api/runs/{id}
GET  /api/runs/{id}/events          # bounded SSE, resumable cursor
GET  /api/runs/{id}/replay          # immutable finalized manifest/reference
GET  /api/replays/{id}/download    # safe artifact lookup, not a user path
GET  /api/checkpoints              # public-approved only
POST /api/comparisons              # only after comparison feature gate
GET  /api/comparisons/{id}
GET  /r/{id}                       # share/replay page with server-rendered metadata
```

Define status codes and stable error bodies: 202 accepted run, 409 conflicting idempotency/state, 413 too large, 422 invalid challenge, 429 admission limit, 503 unavailable real worker. Distinguish an unknown replay from an unfinished replay and a corrupt finalized one. Check the contract rather than inventing a different response for each endpoint.

SSE publishes committed events with strictly increasing per-run sequence numbers and attempt IDs. Respect Last-Event-ID and an initial after cursor. Document at-least-once delivery and client deduplication. Close slow readers or shed/coalesce nonessential frames within explicit bounds. Never lose the ability to recover durable progress and the terminal result. Use keepalives, disconnect cleanup, stream limits, maximum duration, and reconnect jitter. Reconnect need not replay every old image; it must recover consistent run state and ordered event references.

Use an opaque, signed or server-stored anonymous session for quotas and idempotency. No personal profile is needed. Require same-origin JSON writes and Origin validation; use secure cookie settings and a configured proxy trust list. Do not trust a client-supplied forwarding header. Limit per-session and per-source admissions, global queue length, max trial compute, active viewers, payloads, and disk use. Anonymous limits deter abuse but do not prove one human per identity.

FastAPI in-process HTTP tests need proper application lifespan handling. Streaming/disconnect behavior must additionally be exercised against a real server, not inferred solely from an in-process transport. [S7]

## 8. Interface and replay experience

Screens are the editor, queue/live run, completed replay, methodology, and gated paired comparison. Mobile and keyboard use are required. Use plain-language states: QUEUED, LIVE SIMULATION, REPLAY, RECONNECTING, FAILED, and EXPERIMENTAL. A test profile must have a persistent FIXTURE — NOT REAL MODEL label. Never fall back silently to random movement or an old replay when the worker is unavailable.

The visual direction is a compact arcade/laboratory interface. Show the actual scene prominently, a bounded trail, a genuine observation thumbnail, and a few legible telemetry values. Idle decoration must not be labeled real neural activity. Respect reduced motion and avoid rapid flashes. Use accessible HTML controls around canvas content and a text equivalent of the result.

Replay comes from recorded authoritative state/actions. It must support pause, seek, speed control with an explicit rate label, and an independently shareable URL. Browser-side interpolation may smooth display but must be identified as rendering between recorded ticks; it cannot change outcome or neural telemetry. Sharing uses clipboard and ordinary links, not access to X credentials. The share page must include metadata in its initial HTML so crawlers need not execute the app.

## 9. Learning and evaluation: two separate gates

### Engineering gate

Retain anatomical pre/post counts or compact PAM/PPL1-to-MBON metadata aligned to the graph before applying fast-transmitter signs. Apply a documented synapse-count threshold consistently. Keep ties, zeros, unrecognized classes, and uncertain assignments explicit. Correct indexing without pretending those heuristics establish complete biological compartment truth.

Restrict plasticity to documented KC→MBON edges. Test trace eligibility, allowed gain range, bounded input validation, recovery, unsupported compartments, repeat loads, atomic save/load, graph/mapping mismatch rejection, and inability to mutate protected weights. Load baseline weights explicitly and avoid double-applying gains. Raise rather than swallow a checkpoint failure.

Train through an offline/operator-only command on training layouts only. Every community-derived challenge is untrusted training input: validate it, deduplicate it, stage it in a candidate dataset, and exclude holdout families. Never mutate a public evaluation checkpoint in response to a visitor, and never upload arbitrary user checkpoints. Candidate checkpoints are immutable and promoted by an operator only after evaluation.

### Evidence gate

Before opening the held-out set, fix task families, cue mappings, movement/physics, training budgets, primary metric, comparison groups, exclusions, seed sets, and stopping rules in a hashed configuration. Separate train, validation, and test at the layout-family level; changing only a random seed is not necessarily a new task.

Compare trained/frozen versus identical untrained/learning-disabled checkpoints; include a shuffled-reward control to distinguish associative benefit from exposure/global depression. Add a development-calibrated matched-speed random controller and blank-observation fly conditions. Calibrate the random controller only on development data. Freeze gains, recovery/forgetting, checkpoint selection, and action scaling during evaluation. Test before/after model checksums.

Primary metric: success fraction over all scheduled evaluation episodes. Secondary: steps-to-outcome with explicit treatment of failure/timeouts, wrong-pad fraction, and wall cost. Do not report steps among successes as if it describes all attempts. Include all scheduled seeds; infrastructure failures, exclusions, and retried episodes remain auditable. Pair compared conditions on challenge/seed blocks. Estimate uncertainty at the independent layout/cohort level rather than treating correlated timesteps as independent samples. Check the analysis code against small hand-calculated fixtures and simulated zero-effect data.

Start with a declared pilot sized according to measured runtime; a small pilot is exploratory, not definitive. A proposed product gate is a preregistered meaningful improvement (for example, at least ten percentage points) over untrained and shuffled-reward controls with a paired 95% uncertainty interval excluding zero. The ten-point threshold is a product decision, not a universal scientific standard. Predeclare multiple-comparison handling and checkpoint-selection rules. A wider or zero-crossing interval means inconclusive. A lack of evidence is a valid result, not permission to tune on the holdout until it passes.

A manifest with `claim_status: SUPPORTED` must reference the tested source/model/checkpoint hashes and qualifying report. Unsupported, missing, stale, or inconclusive reports leave the trained-improvement feature off. Replays still work. This gate controls marketing claims, not the ability to publish honest negative findings.

## 10. Verification and CI

See BOUNDARIES.md for required tests. Create real commands, not shell targets that print success without collecting tests:

```text
make bootstrap          # install from locks in an isolated environment
make doctor             # versions, paths, checksum validation, resource/config checks
make test-unit
make test-property
make test-contract
make test-db
make test-api
make test-worker
make test-ui
make test-e2e            # real local services + fixture controller, explicitly labeled
make test-e2e-real       # full model + actual services, no controller/API/DB mocks
make verify             # all ordinary required checks, types, builds, dependency checks
make verify-real        # real data and real end-to-end gate; missing data is failure
make verify-release     # verifies evidence against the current release revision
```

Playwright can manage local web servers and retain traces for diagnosing failures. Use pinned browser/runtime versions and isolated test data. A trace/screenshot must be inspected; collecting it alone is not a visual review. [S8]

PR CI runs tiny graph fixtures and real database/worker/API/UI processes on ephemeral runners. The full-connectome suite is an operator-run or protected dispatch release gate. Never run untrusted pull-request code on the user's personal self-hosted workstation with secrets or a funded wallet. It may be reasonable to skip heavy real-model tests in ordinary PR CI, but the explicitly requested real-model gate must fail rather than quietly skip when data is absent.

Use normal command exit codes, nonzero test collection checks, JUnit reports, relevant branch coverage, screenshots, traces, and database/artifact inspection. Test critical invariants directly; an aggregate coverage percentage cannot replace them. Use targeted fault injection/mutation probes to prove tests catch reversed connectivity, leaked target information, duplicate finalization, ignored feature flags, and dishonest fixture labels.

## 11. Milestone order and release gates

| Prompt | Scope | Gate/output |
|---|---|---|
| 00 | Audit and working agreement | Source map, local environment facts, source revision, safe agent rules |
| 01 | Scaffold, contracts, test harness | Runnable fixture profile, validated contracts, CI skeleton |
| 02 | Data preparation and anatomical metadata | Synthetic regression tests plus explicit data provenance |
| 03 | Real fly adapter and observation boundary | Determinism/isolation/path tests; disclosed reset mode |
| 04 | Arena, renderer, scoring | Property/golden/information-flow tests |
| 05 | Real-model feasibility | Measured operation and visual sensitivity; no fake fallback |
| 06 | Database and artifact repositories | Real-file migrations, constraints, concurrency and crash tests |
| 07 | Worker and supervision | Single active slot, bounded retries, fencing and resource control |
| 08 | API, sessions, admission, SSE | Contract, HTTP and actual streaming tests |
| 09 | Replay and headless vertical slice | Trace verification and real-model integration through all backend layers |
| 10 | User interface | Component/runtime-validation/accessibility and visual evidence |
| 11 | Browser end-to-end | Fixture and real-model browser journeys; mandatory core gate |
| 12 | Optional learning implementation | Mechanically correct, offline-only, default disabled |
| 13 | Controlled evaluation | Reproducible report; honest supported/unsupported/inconclusive status |
| 14 | Gated comparisons and sharing | Paired trials, metadata pages, claim controls |
| 15 | Hardening, operations, containers | Local production-profile tests, abuse limits, restore and resource evidence |
| 16 | Independent release audit | Fresh-context review, fault probes, clean-release evidence |
| 17 | Deployment and production smoke | Actual deployment only if target authorized; otherwise deployable package and explicit blocker |
| 18 | Submission package | Authentic replay/video evidence, claims ledger, PR/submission drafts |

Run prompts in order, not as one giant instruction. Prompts 12–13 may finish with mechanically passing code and no supported learning claim; that allows the core to proceed with the feature disabled. A missing real-model execution blocks a real-model release. A failed database/UI/security gate also blocks release. Missing deployment credentials blocks production verification but not the honest preparation of a local package.

Do not add a fixed-hours promise to this expanded plan. This specification is larger than an untested demo. Protect scope by trimming optional learning, visual decoration, and comparisons—not by trimming real-model validation, persistence correctness, provenance, or basic deployment safety.

## 12. Agent execution and evidence protocol

Start each milestone in a working checkout with shell, filesystem, Python/Node, and browser-test access. Read root AGENTS.md, this plan, the boundary matrix, and STATUS.md. Read actual code before editing; source comments and README assertions are not automatically true.

Bootstrap should add concise root instructions linking to these files without erasing existing instructions. Record decisions and interfaces in repository files so a new agent session does not depend on old chat messages. Parallel work is not needed; if used after interfaces stabilize, assign disjoint files/worktrees and integrate through the same tests.

For each prompt: inspect prerequisites → state bounded plan → implement only that milestone → add or tighten tests → execute tests → inspect evidence → fix failures → update status → stop. Do not proceed automatically to the next milestone or change tests simply to accept incorrect behavior. Do not use broad ignores, blanket skips, giant timeouts, or mock substitutions to conceal failures.

Write `docs/implementation/milestones/NN.md` with source paths and actual decisions. Store machine-readable evidence under ignored `artifacts/milestones/NN/`: commands, exits, collected/pass/fail/skip counts, environment versions, source revision/digest, logs, screenshots, traces, and artifact references. Records should distinguish PASS / FAIL / BLOCKED, and research claims separately as SUPPORTED / UNSUPPORTED / INCONCLUSIVE / NOT_RUN.

End every milestone with a small boundary-level status table and a handoff. Do not say “tests pass” when they were not run. Do not fabricate results, timestamps, or screenshots. Keep preexisting user work intact; make only local changes unless external action is separately authorized. No paid resources, public deployments, remote pushes, pull requests, or social posts without specific authorization. A clean local release commit may be created with only the implementation's intended files; never sweep unrelated files or secrets into a commit.

## 13. Deployment and contest evidence

Production shape: one host, same-origin reverse proxy, API process, one coordinated simulator child, persistent local volumes for database/artifacts, read-only model data, and unprivileged containers. Pin image/runtime versions after verifying compatibility. Never mount a wallet, the host's home directory, a Docker socket, or SSH credentials. Do not run the upstream wallet/launch services. Asset acquisition is a separate controlled command; inference has no need for general outbound internet.

Configure explicit body, queue, process memory/CPU, wall-time, stream, log, and disk limits. Production never substitutes fixture mode on errors. Missing worker data means honest unavailability plus optional clearly labeled existing replays. Liveness, API readiness, and the ability to admit new simulations are separate states. Use current measured throughput to describe capacity; do not make invented real-time or concurrent-user promises.

Before submitting, verify the public URL in a second independent browser session, perform a real run, restart the service and retrieve the same replay, verify the download manifest, and validate crawler-readable sharing metadata. A representative demo should include failures or link to aggregate results, not suggest a cherry-picked success is universal. Any playback acceleration must be shown on screen.

Prepare a truthful README, methodology and limitations page, report, code attribution, optional narrowly scoped upstream fix patch, brief continued-building plan, 35–45-second authentic screen recording, and draft X submission. Do not post or open the PR automatically. The prior quotation does not establish a deadline, an equal split, or payout terms; verify those separately before claiming the submission meets all contest conditions.
