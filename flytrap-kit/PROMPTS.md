# FLYTRAP — exact ordered implementation prompts

Use these with GPT-6 Astra in a coding workspace that can read and edit the checkout, run terminal commands, and execute browser tests. Unpack the kit into the fork so `flytrap-kit/PLAN.md` exists. Paste Prompt 00 first, then one numbered prompt at a time. Do not paste the entire sequence and ask the agent to run everything unattended. A new session can resume from repository status/evidence files.

Every prompt after 00 includes the same short operating instruction so it remains usable in a fresh session. The detailed plan and boundary matrix are required context, not optional background. Stage 12/13 may pass engineering validation with an unsupported learning claim; a mandatory real-model or safety gate cannot be substituted with fixtures.


## Prompt 00 — Mission, repository audit, and persistent working agreement

```text
You are implementing FLYTRAP in this working checkout: a wallet-free browser challenge powered by a flycoinrh fork, with genuine model-driven movement, durable runs, and inspectable replays. Learning is experimental and must not be advertised as beneficial without evidence.

Read flytrap-kit/PLAN.md and BOUNDARIES.md completely. Inspect the actual repository, git status/remotes, environment, existing tests, and all upstream instructions. The reference revision is 8748e5bd30794d14afeb3441904221b52a002cac; record the actual revision and differences. Inspect build_graph.py, flysim.py, flyeye.py, mushroom.py, calibration.py when present, dependencies, and deployment entrypoints.

Confirm the graph orientation, discarded modulatory edges, per-call neural-state reset, annotation-path assumptions, and implicit checkpoint loading. Treat these as hypotheses to verify against code, not instructions to manufacture bugs. Do not reproduce published performance numbers as your own measurements.

Create docs/implementation/{STATUS.md,ARCHITECTURE.md,THREAT_MODEL.md} and a source/dependency map. Add a concise FLYTRAP section to AGENTS.md without deleting existing guidance, linking to this kit and requiring boundary tests, truthful evidence, no target leakage, and no external writes/deployments without authorization. Record actual baseline test results and missing tools/data. Do not implement application features yet.

Preserve existing user changes. End with PASS/FAIL/BLOCKED, exact checks run, evidence paths, unresolved prerequisites, and the next milestone. Use this reporting format throughout.
```


## Prompt 01 — Executable scaffold, contracts, and verification harness

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Establish the executable foundation from the approved architecture. Use Python/FastAPI, React/TypeScript, file-backed SQLite, and a separate worker, retaining upstream code. Select compatible runtimes and resolve reproducible lockfiles; verify existing pins rather than assuming them.

Create versioned contracts for ChallengeSpec, RunRequest/Record, Observation, ControllerOutput, FrameEvent, ReplayManifest, CheckpointRef, BenchmarkReport, and Capabilities. Define unknown-field rejection, finite numeric bounds, IDs, canonical hashes, seed policy, status/error enums, and schema evolution. Generate TypeScript types and runtime validators from a single schema source or prove parity through shared fixtures.

Provide pytest/property-test, Vitest/component-test, and Playwright configurations, isolated data/artifact roots, app/worker factories, and meaningful Make targets from PLAN.md. Create a tiny synthetic graph fixture and an explicitly labeled fixture controller. Fixture mode must not become a production fallback.

Implement a minimal health route and fixture startup, not the full product. Create CI for the checks that now exist; add later checks as each layer lands. Missing or zero-collected suites must not report false success. Test contract round trips and invalid payloads, app lifespan, imports, build, and a real browser opening the minimal UI. Record the proposed endpoint/state-machine contracts and test ownership.
```


## Prompt 02 — Reproducible graph data and anatomical metadata

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement controlled data preparation and regression tests. Use explicit configurable paths, upstream public data sources/attribution, checksums, source versions, and a manifest. Avoid importing wallet or launch code. Refactor only enough of build_graph.py to test pure graph construction on tiny data.

Preserve W[post,pre] for fast signaling. Separately retain unsigned anatomical counts or compact PAM/PPL1→MBON input metadata before fast-weight sign filtering, aligned to stable body IDs and a documented threshold policy. Do not turn dopamine into an artificial fast excitatory connection. Handle duplicate edges, missing types, sparse/large IDs, zeros, ties, and unmapped bodies deliberately.

Write hand-computed regression fixtures that fail for the reversed lookup and demonstrate why transposing the fast matrix does not restore dropped edges. Verify body ordering, mappings, metadata hashes, count aggregation, and round-trip loading. Incorrect data must fail clearly rather than produce an empty plausible model.

Provide doctor/data-build commands. Use actual available full data for a smoke test and record observed graph statistics; do not hard-code prior counts as truth. If large data is missing or acquisition is unavailable, finish synthetic tests and explicitly mark the real-data gate blocked. Leave production learning disabled; behavioral validation happens later.
```


## Prompt 03 — Real fly adapter and information isolation

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement the real FlyController adapter behind the Observation/ControllerOutput contracts. Inject graph, annotations, model parameters, calibration, and checkpoint paths explicitly. It must run independently of the current working directory and must not import roaming, wallet, or token-launch services.

Provide reset(run_seed, checkpoint) and step(observation). Only bounded grayscale observation pixels may cross the task-input boundary. No goal coordinates, challenge object, target label, reward, DOM, or distance-to-goal is available during evaluation. Define the task-independent per-step seed stream and bounded motor mapping. Label the preserved upstream behavior windowed_reset; do not silently add continuous membrane state.

Do not implicitly load prior mushroom-body state or upstream trained gains. Use an explicit untrained baseline. Validate required neural populations and finite output; errors must not trigger random or scripted fallback. Optimize repeated annotation loading only while preserving behavior.

Test path independence, reset isolation, repeatability with fixture graphs, malformed inputs, numeric bounds, no checkpoint contamination, and the serialized observation envelope. Check centered-crop sampling parity with FlyEye. Add architectural/import tests against privileged environment dependencies. Run a real-data adapter smoke when available and distinguish it from fixture results. Record actual performance without a real-time claim.
```


## Prompt 04 — Deterministic arena, rendering, and outcome rules

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement the constrained two-choice arena as a pure fixed-step state machine. Use two reachable patterned destination pads, a lower start, and zero to three allowed distractions. Define legal presets, margins, overlap/reachability checks, trial tick limits, terminal tie-breaking, and explicit success/wrong-pad/timeout outcomes. Keep cue-to-reward mapping consistent within the task/cohort.

Build one authoritative grayscale renderer. The same raster feeds the retina and is displayed by the browser later. Human labels, paths, avatar decoration, scores, and debug information belong in a separate overlay and never enter the observation. Freeze crop, pixel normalization, boundary sampling, and texture versions.

Apply bounded model actions without attraction to goals, hidden steering, rescue teleports, or scripted success. Use swept collision/goal intersection so large steps cannot skip obstacles or terminal pads. Keep wall time distinct from environment ticks and neural milliseconds.

Use pytest, property-based tests, and golden pixels for identical-seed replay, clipping, legal generation, terminal behavior, texture/crop consistency, and nonfinite input rejection. Add an information-flow test: identical observation/checkpoint/seed with changed hidden scoring metadata produces identical controller output. Test physics with known scripted controllers only as labeled test fixtures. Produce inspectable sample frames and trajectories, not claims of model competence.
```


## Prompt 05 — Real-model feasibility and task calibration gate

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Run the actual model and arena together before building the product shell. Use the full graph and actual fly adapter, not the synthetic controller. Measure cold load time, peak memory, step-latency distribution, actual trajectory/outcomes, finite motor activity, and observation hashes across fixed seeds.

Use development-only trials to examine bright/dark/patterned inputs, blank-input controls, left/right layout swaps, freezing/stuck behavior, and the effect of motor scaling. Measure whether distinct pixels influence outputs; do not equate movement or changing weights with learning. Do not require the fly to succeed at an arbitrary task to consider the pipeline functional.

Write a small reproducible JSON/Markdown report with hardware/software/data hashes, complete development trial IDs, failures, and the selected preset/action mapping. Freeze that configuration before held-out evaluation. Set proposed admission/latency/episode budgets from measured cost, not guesses.

Choose an honest interaction mode: live progress when usable, otherwise queued computation and explicitly labeled replay. A minimal preset can replace an overambitious arena based on development evidence; never alter a trajectory secretly. If real data cannot run, mark the real-model gate BLOCKED. Do not fabricate a successful example or proceed as if fixture evidence validated the model. End with a concrete go/no-go for the playable core.
```


## Prompt 06 — Database schema, transactions, and artifact repositories

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement file-backed SQLite repositories and numbered, transactional migrations for challenges, anonymous sessions, runs, attempts, events, checkpoints, and comparison references. Use foreign keys, checks, uniqueness, indices, WAL, and bounded busy handling. Check the SQLite library actually linked by Python for the documented WAL-reset fix (3.51.3+ or a verified vendor backport), with a tested failure path for unpatched runtimes. Keep model computation outside transactions.

Implement immutable challenge specifications; legal run transitions; session-scoped idempotency with request digest; atomic quota/admission plus run creation; and compare-and-set updates for attempt ownership. A repeated key/payload returns the same run; a changed payload returns a conflict. Use real separate connections to test concurrency.

Create a safe artifact repository under one configured root: bounded trace chunks/manifests, stable identifiers instead of user paths, checksums, immutable publication, and temp-write/fsync/rename before committing the completed reference. Define reconciliation for orphan files and interrupted attempts. Never mark a run completed before its verified bundle exists.

Test fresh and upgrade migrations, constraints, rollback, same-key races, conflicting keys, busy timeouts, concurrent admissions, traversal attempts, truncation/corruption, and crashes on each side of rename/database commit. Use actual temporary database files and filesystem operations, not only mocks or an in-memory database. Produce database/artifact evidence and document backup/restore consistency expectations.
```


## Prompt 07 — Single-worker execution and fault recovery

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement the durable worker coordinator and isolated simulator subprocess. One exclusive host slot must prevent two active simulations even when two workers start and different jobs are queued. Queue claims also need transactions, attempt IDs, lease tokens, heartbeats, and bounded retries.

The coordinator must remain able to heartbeat and enforce deadlines while a model step is slow. Use bounded IPC and terminate/restart a hung child on a real wall-time or memory limit. The child receives only model setup and the approved observation envelope. Reset model/checkpoint state between jobs. Do not give the child wallet keys, the database, or arbitrary network/browser access.

Write bounded durable progress events and finalize immutable replay bundles using the artifact repository. Fence stale attempts from publishing. Preserve interrupted attempt history; retries restart transparently with declared semantics rather than pretending execution was exactly once. Handle SIGTERM and unavailable/corrupt models honestly.

Use multiprocess integration and fault injection: concurrent worker startup, duplicate claim, worker kill, expired lease, stale finalization, slow/hung model, disk failure, restart, and graceful shutdown. Assert no duplicate accepted completion or completed run with missing artifacts. Test that the API's future database reads are not blocked by model computation. Record throughput/resource measurements and pending failure cases.
```


## Prompt 08 — HTTP API, admission controls, and resumable events

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement the contracted FastAPI endpoints for config, health, challenge creation/read, run creation/read, approved checkpoints, committed SSE events, and replay lookup/download. Add an app factory with explicit lifespan and dependency injection. The API never performs simulation in its request loop.

Use actual repositories and worker status. Validate schema/body limits, JSON content type, Origin, signed/server-stored anonymous sessions, trusted proxy configuration, idempotency, per-session/source quotas, and the global queue cap. Distinguish liveness, service readiness, and capacity to admit new real runs. Return documented status/error bodies; no synthetic fallback when the worker is unavailable.

Implement bounded SSE with increasing event sequence, attempt IDs, Last-Event-ID/after cursor, duplicate-tolerant client semantics, keepalive, cleanup, stream limits, and terminal recovery. Slow spectators must not stall the worker or create unbounded memory queues. Public artifact requests resolve IDs within the configured root, never arbitrary paths.

Test contracts and HTTP behavior with HTTPX, application lifespan, and real file-backed repositories. Test streaming/reconnection/disconnects and responsiveness during actual worker computation against a real server/socket. Cover same-key retries, changed-payload conflicts, invalid challenge, quota exhaustion, worker down, missing/unfinished/corrupt replay, and forged proxy headers. Save OpenAPI and cross-language contract evidence.
```


## Prompt 09 — Replay verification and backend vertical slice

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement finalized replay manifests, trace serialization, download, and a CLI verifier. Include source/environment/data/checkpoint/config identity, state mode, seeds, renderer/reward versions, initial state, ordered actions, observation hashes, timing, attempts, outcome, and artifact digests. Keep every scored step; do not rely on a downsampled spectator stream as the only replay record.

Replay by reapplying recorded actions to deterministic physics and recomputing observations/outcome. Distinguish this from rerunning neural inference, whose reproducibility is scoped to declared runtimes/tolerances. Checksum validity proves internal consistency, not independent authenticity of a brain claim.

Reject reordered/missing chunks, digest mismatches, invalid schema, unsafe decompression, inconsistent terminal results, and mismatched model references. Reconstruct display frames from canonical versions or include sufficient immutable assets. Preserve incomplete attempts as incomplete.

Run a headless vertical integration: real HTTP request → file database → worker → actual model → published bundle → verifier → second independent HTTP client. Also run a small fixture version in CI. Inspect database state and artifact contents; a 200 response alone is insufficient. Missing full data blocks the real integration gate. Save a genuine representative replay as the seed for later browser and submission tests, clearly recording successes and failures.
```


## Prompt 10 — Editor, live viewer, replay, and accessibility

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement the React/TypeScript interface using the generated contracts plus runtime response validation. Build the bounded challenge editor, queue state, live viewer, completed replay, error/reconnect states, methodology panel, and shareable replay route. Use the authoritative server raster; never make an independent browser simulation look authoritative.

Make the scene the focal point, with a legible trail, actual observation thumbnail, and a few genuine telemetry values. Use restrained arcade/laboratory styling, accessible HTML controls around canvas, keyboard operation, mobile layout, and reduced-motion support. Labels must distinguish LIVE SIMULATION, REPLAY, FIXTURE — NOT REAL MODEL, and EXPERIMENTAL. No fake neural activity while idle.

Deduplicate SSE events, display retries/attempts, reconnect safely, prevent double admission on double-click, and preserve the idempotency key through request retry. Replay supports pause, seek, and labeled playback speed. A disabled learning gate must leave no implied trained-performance claim. Do not auto-post to X or connect wallets.

Use Vitest/React Testing Library for state and form behavior, malformed API data, accessibility, and retries. Use Playwright to inspect desktop/mobile captures and renderer/hash parity against the real service. Open and visually review screenshots rather than just generating them. Fix layout/contrast/overflow defects and save evidence. Reserve full system journeys for the next milestone.
```


## Prompt 11 — Browser-to-database-to-real-model system validation

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement and run Playwright system tests against actual UI, HTTP server, file-backed database, worker process, and artifact root. Keep UI/API/controller mocks out of the system golden path. Use separate ports/directories and deterministic setup/teardown, with traces on failure.

Fixture suite: create a valid challenge; reject invalid input; submit once despite double-click/retry; observe queued/running/terminal states; disconnect/reconnect; open the replay in another browser context; seek/pause; copy its URL; download and verify its bundle; test worker-down, full-queue, corrupt-replay, and mobile/keyboard paths. Verify database rows and provenance, not just browser text.

Real suite: execute the same essential path with the full connectome and real FlyController. Assert genuine configuration and telemetry, canonical image/observation agreement, complete trace, an honestly scored result, and independent replay retrieval. Do not assert guaranteed task success. No fixture fallback, intercepted API, or fake database is permitted in this suite.

Ensure make test-e2e-real and make verify-real fail clearly when required data/service is missing rather than silently skipping. Inspect actual screenshots/traces for truthful labels and visible usability. Record boundary-by-boundary evidence. Fix defects before declaring the core complete; keep public deployment blocked until hardening and release review also pass.
```


## Prompt 12 — Optional, explicit learning implementation

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement learning behind a default-off feature flag and an offline/operator-only training command. Reuse the preserved anatomical metadata, not signed fast weights, for documented PAM/PPL1→MBON classification. Treat ties, zero input, and ambiguous assignments explicitly; the classification is a model heuristic, not proof of biological validity. Inspect current calibration.py but do not assume odor calibration validates visual learning.

Restrict updates to allowed KC→MBON synapses with tested eligibility, bounded reward events/gains, declared recovery, and explicit timing. Load a pristine baseline and apply a checkpoint exactly once. Provide immutable checkpoints whose manifests bind graph/body/synapse mappings, gains, learning parameters, source, training data, and calibration. Reject corruption or mismatch loudly; remove implicit autoload and swallowed-error behavior from this path.

Training receives outcomes only after observations/actions. Evaluation cannot update, forget, or save gains. Validate/deduplicate community-derived layouts into candidate training data; never allow public requests to mutate the active model or supply arbitrary checkpoint files.

Test selective versus protected weight changes, event signs/bounds, inactive traces, ties, repeated load, no double application, crash-safe saves, graph mismatch, and isolation across runs. Run a small real-data learning smoke measuring what changes and KC activation; do not call it task improvement. Mechanical PASS with learning still unproven is an acceptable milestone result.
```


## Prompt 13 — Controlled evaluation and evidence-based claim gate

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement the evaluation protocol in PLAN.md. Before held-out evaluation, commit/hash the task families, cue mappings, training budget, seed blocks, primary/secondary metrics, exclusions, candidate selection, stopping rule, and proposed meaningful-effect threshold. Separate train/validation/test by layout family. Tune only on development data and keep the held-out test untouched until the configuration is frozen.

Compare trained/frozen against identical untrained/learning-disabled and shuffled-reward controls. Add development-calibrated matched-speed random and blank-observation controls. Use paired challenge/seed blocks, fixed action mapping, and immutable evaluation checkpoints; verify weight/config hashes before and after. Account for every scheduled episode, timeout, failure, and exclusion.

Implement analysis with hand-calculated fixtures and null-effect synthetic checks. Estimate paired uncertainty at the independent layout/cohort level, not from correlated timesteps. Report success fraction, carefully defined steps-to-outcome, wrong-pad/timeout rates, and wall cost. A small pilot is explicitly exploratory; do not manufacture sample size or statistical confidence.

Run the declared experiment within measured resource budgets. Produce machine-readable and readable reports, full trace references, and SUPPORTED/UNSUPPORTED/INCONCLUSIVE/NOT_RUN claim status. Only a qualifying report bound to the exact checkpoint/config enables trained-improvement claims. Negative or inconclusive evidence must keep the feature disabled while allowing the validated core to ship. Do not reroll seeds until a favorable result appears.
```


## Prompt 14 — Gated comparisons and contest-ready sharing

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement share/replay pages with crawler-readable metadata in initial HTML, a real-result share card, clipboard links, methodology/limitations, and links to provenance. Use actual run data and a server-configured public origin, not arbitrary request Host values. Share without X credentials, token purchases, or automatic posts.

Implement paired comparison only when an approved evidence report and matching immutable checkpoints permit it. Admit both jobs atomically under quotas; use the same challenge/seed/physics/renderer/action mapping, record any sequential execution, and keep learning off during both trials. Comparison playback must align recorded ticks without implying the jobs ran simultaneously in real time.

Show uncertainty and the report behind any improvement claim. Missing, stale, inconclusive, unsupported, or mismatched evidence must disable that claim and avoid orphaned “trained smarter” copy. The core replay/share experience must still work with comparison disabled. An experimental report may be shown honestly without positive marketing.

Test flag on/off, report/checkpoint mismatch, paired seed/config parity, atomic quota failures, metadata HTML without JavaScript, safe text escaping, replay URLs in a second browser session, mobile sharing, and accessibility. Inspect generated cards for legible accurate content and no fixture-as-real labeling. Save Playwright/API/DB evidence and a truthful draft submission copy; do not publish it.
```


## Prompt 15 — Security, resource control, operations, and containers

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Harden the completed system and package a single-host production profile. Use nonroot containers, pinned compatible runtimes, read-only model data, local persistent database/artifact volumes, one exclusive worker slot, explicit resource limits, and same-origin routing. Never mount wallet keys, home directories, Docker sockets, or SSH credentials. No inference-time arbitrary browsing or general outbound access is needed.

Implement and test bounded JSON/input sizes, approved layouts/checkpoints, Origin/session/proxy handling, admission quotas, queue/stream caps, subprocess deadlines, replay decompression limits, disk/log retention, and artifact path safety. Missing real data must produce clear unavailability, not a fixture fallback. Keep liveness/readiness/admission status distinct.

Add structured request/run/attempt logs and minimal metrics: queue depth, active worker, step latency, failures, heartbeat age, streams, and disk use. Implement tested backup/restore, reconciliation, graceful shutdown, and recovery. Use SQLite's supported backup flow and consistent artifact snapshots, not a blind copy of a live DB file.

Run dependency/secret checks, adversarial input tests, bounded load tests with a real active simulation, worker kills, disk-full simulation, restart/replay retrieval, and backup restore in disposable local containers. Record measured capacity and chosen limits, not invented concurrent-user promises. Produce runbooks and rollback instructions. Do not spend money or deploy publicly in this milestone.
```


## Prompt 16 — Fresh-context adversarial release audit

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Review the implementation as a skeptical independent release engineer. Use a fresh context/worktree where practical, read the actual code and evidence, and do not accept previous PASS summaries without checking their artifacts. Confirm scope, source attribution, observation isolation, no fake steering, no implicit checkpoint loading, database integrity, worker fencing, real-service E2E, honest labels, and the scientific claim gate.

Use bounded local fault/mutation probes to demonstrate that tests catch reversed connectivity, target metadata leakage, duplicate finalization, corrupt artifacts, disabled-feature bypass, and fixture-as-real labeling. Keep probes out of release code and restore fixtures afterward. Inspect representative browser traces/screenshots manually; test collection and coverage totals alone are not enough.

Run the full ordinary verification suite and mandatory real-model release suite against the intended clean source revision. Check clean install/build, migrations, lockfiles, local container smoke, restart, and backup restore. Separate code defects, evidence gaps, unavailable external prerequisites, and inconclusive research.

Fix reproducible defects with regression tests and rerun affected plus release checks. Produce a release evidence index bound to exact code/data/model/config hashes, unresolved risks, and PASS/FAIL/BLOCKED per boundary. Do not waive a failing real-model gate or weaken assertions to obtain green. No remote pushes or public release actions are authorized here.
```


## Prompt 17 — Authorized deployment and production smoke validation

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Prepare deployment from the verified release revision and the single-host runbook. Inspect existing deployment configuration and permissions. Deploy only to a target explicitly authorized for this project with approved credentials/budget; do not infer permission to create paid infrastructure or overwrite another service.

When a target is authorized, deploy the pinned images and verified model assets, apply migrations safely, configure the public origin/TLS/proxy and local persistent volumes, enforce the one-worker topology, and leave unsupported learning disabled. Verify health/admission, resource limits, secret isolation, and backup/rollback readiness.

Run a production-safe browser smoke: create one bounded real challenge, observe the actual simulation, open its replay in a second session, download/verify provenance, check metadata in initial HTML, and confirm service restart preserves the replay when a restart is authorized. Exercise only safe public error cases; keep destructive fault injection in staging/local environments. Compare production configuration and hashes with release evidence.

If no authorized target or credentials exist, produce the exact deployable package, environment template, operator commands, smoke script, and rollback steps; mark deployed verification BLOCKED, not completed. Do not invent a public URL or ask for secrets in chat. Record precisely what was deployed/tested versus merely prepared. No social post or upstream PR yet.
```


## Prompt 18 — Authentic demonstration and submission package

```text
Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Build the submission package exclusively from verified implementation and run evidence. Select a representative real replay and link aggregate results; do not imply one cherry-picked success is typical. Capture an actual browser demonstration with original source recording, then produce a concise 35–45-second edit when recording tools are available. Label replays and playback acceleration. Never fabricate neural activity, successful behavior, user engagement, or a learning improvement.

Prepare README quickstart, architecture/testing overview, methodology/limitations, provenance download instructions, attribution/notices, a claims-to-evidence ledger, continued-building plan, and draft X submission tagging the organizer and $FLYBRAIN. If beneficial, prepare a narrowly scoped upstream graph/learning fix patch plus tests and a constructive draft PR description. Do not post, push, or open a PR without separate authorization.

Verify the demo link when actually deployed, current release identity, replay reproducibility, metadata, and evidence supporting every number/claim. Use the quote only as provisional contest information; verify deadline/judging/payout terms when accessible, and label unknown terms rather than inventing them.

Finish with a deliverable inventory and links/paths, boundary test status, supported versus unsupported claims, remaining operational prerequisites, and the exact final submission text. If video/deployment/real-data validation was unavailable, report that explicitly and supply the completed artifacts without pretending the missing work happened.
```
