# FLYTRAP — boundary test matrix

Every row is a release obligation unless explicitly designated as learning-only. Fixtures validate mechanics; real-data gates validate actual integration. Tests must check real outputs and state, not just mock invocation counts.

| Boundary | Test level and tools | Required checks | Evidence/gate |
|---|---|---|---|
| Upstream source → fork | Audit; pytest regression fixtures | Pinned revision; preserve user changes/notices; distinguish inspected code from README claims | Source map, known issues, baseline test results |
| Raw connectome → graph/metadata | pytest unit + Hypothesis/property + real-data smoke | W[post,pre]; zero-fast-weight dopamine still retained in anatomy; tie/zero classification; body mapping/threshold/dedup; corrupt/missing data | Tiny hand-computed graph; data checksums; actual graph stats |
| Graph → simulation adapter | pytest unit + real model | Explicit data paths; numeric bounds; required populations; repeatability in locked environment; disclosed window resets; no inherited checkpoint | Structured doctor output; deterministic trace probe |
| Environment → controller | Contract + information-flow + architectural imports | Pixels only; wrong shape/NaN rejected; same pixels/seed/model → same output regardless of hidden scoring metadata; no goal/controller imports | Contract tests plus inspected IPC envelope |
| Controller → physics | pytest + Hypothesis | Fixed bounded movement, no target assistance, swept collision/goal checks, deterministic terminal tie rules, no extra steps after terminal | Property tests and known trajectories |
| Renderer → retina/browser | Golden pixel tests + Playwright | Canonical raster; correct crop/normalization; UI overlays excluded; displayed image and observation hashes agree with run data | Hash assertions plus visually inspected screenshots |
| Database schema → repositories | Actual temporary file-backed SQLite | Patched linked SQLite version; empty/install and upgrade migrations; FKs/checks/uniqueness; rollback; idempotency; independent connections; busy retry limits | Migration logs and database assertions |
| HTTP admission → durable queue | HTTPX with real DB + concurrent integration | Validation; atomic quotas/run creation; same-key retry; same-key/different-body conflict; queue full; no mock database | Response + persisted row counts under concurrent requests |
| Queue → worker | Multiprocess integration + fault injection | One host slot; transactional claim; leases/heartbeat/fencing; bounded retries; kill/restart; subprocess timeout; second worker cannot run concurrently | Attempt/state logs and no-duplicate-publication assertions |
| Worker → replay publication | Filesystem + DB integration/fault injection | Failure before/after write/fsync/rename/commit; stale attempt forbidden; orphan recovery; checksum failure; no completed row with absent bundle | Crash-matrix results and artifact verification |
| API → browser types | OpenAPI/JSON Schema + TS runtime schema tests | Shared version/enums; unknown fields; malformed numbers; maximum lengths; runtime response rejection, not TS compile alone | Contract generation diff check and fixtures |
| API lifecycle/stream → subscribers | HTTPX + actual uvicorn/network tests | Lifespan; SSE IDs/cursor; reconnect/dedupe; terminal recovery; disconnect cleanup; slow client; stream caps; admission responsiveness under compute | Real socket logs and bounded resource assertions |
| Replay trace → result | Unit/property + round-trip integration | Recompute physics/result from actions; validate chunk order/digests; tampering and truncation detection; schema mismatch; seed/provenance completeness | Verifier JSON output and tamper tests |
| UI state/components | Vitest + React Testing Library + axe | Editor validation; keyboard flow; queue/running/replay/errors; retry idempotency; fixture/experimental labels; reduced motion; malformed API data | Component reports and inspected desktop/mobile captures |
| Browser → full fixture stack | Playwright against actual UI/API/DB/worker | Create/run/reconnect/complete; retrieve in second context; share/download; worker outage; backend validation; no API interception on the golden path | Trace/video; DB row and manifest inspection |
| Browser → real model stack | Playwright + real graph, no controller/DB/API mocks | Actual request drives actual model; authentic telemetry/hashes; independent replay retrieval; true offline error; valid final result | Mandatory release gate; missing graph is BLOCKED/failed command, not skipped success |
| Experience → learning update | pytest unit + real-model learning smoke | Eligible KC→MBON only; no protected mutation; positive/negative event behavior; gain bounds; corrupt/mismatch loads; baseline reset; checkpoint immutability | Before/after tensors/hashes; graph-sensitive tests |
| Training → scientific claim | Offline controlled experiments + analysis-unit tests | Family-level holdout; matched seeds; learning-off/shuffled/random/blank controls; no weight changes during eval; preregistered metrics; clustered uncertainty; all episodes accounted for | Hashed config, full report, claims gate status |
| Report/checkpoint → comparison UI | API/integration + Playwright | Same challenge/seed/config; immutable approved model IDs; stale/absent/inconclusive report disables improvement claim; paired jobs admitted atomically | Flag-on/off tests; manifest links; no marketing-copy loophole |
| Public input → resource/security boundary | Integration + fuzz/property + load tests | Origin/cookie/proxy handling; payload bounds; rate/queue/stream/disk limits; path traversal; no arbitrary URLs/uploads; no secrets in bundles | Threat-model cases; dependency/secret scans; tested error codes |
| Container → persistent operation | Docker Compose integration and operational tests | Nonroot; read-only model; single host local volume; no wallet; process signals; readiness versus admission; restart/retrieve; restore backup | Container inspect, smoke report, backup/restore evidence |
| Release → public submission | Fresh-context review + deployed Playwright/manual check | Exact tested revision; clean build; no fake fixtures; public metadata; real representative replay; preserved attribution; verified contest terms | Release evidence bundle and human-reviewed submission drafts |

## No false-green rules

- `make verify-real` and `make test-e2e-real` must fail when full data or a real worker is unavailable. Ordinary PR suites can exclude them explicitly; release cannot.
- An API test with a fake repository is a unit test, not database integration. An in-memory database does not validate file-backed locking/durability.
- A browser test that intercepts every API request is a UI test, not system E2E. Keep such tests clearly labeled and separately run the real-service journey.
- The model can legitimately fail a challenge. Assert the process, telemetry, provenance, and scored outcome—not an invented success guarantee.
- Screenshot files are not a visual review. Open representative captures and record concrete findings. Do not bulk-accept baselines without inspection.
- Code-correct learning can still have no behavioral benefit. Keep engineering status separate from evidence status.
- Save actual commands, exit codes, collection counts, source/environment identity, and evidence paths. Include skipped counts and their reasons.
- Use fixed seeds and fake clocks where appropriate. Do not hide races with arbitrary sleeps, broad retries, or huge timeouts.
- Do not mutate production data or deploy publicly to make a test pass. Use isolated test databases, artifact roots, ports, sessions, and model checkpoints.
- Fault probes must themselves be bounded and confined to disposable local/test environments.
