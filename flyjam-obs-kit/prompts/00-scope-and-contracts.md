# OBS00 — scope, executable contracts, and environment

Read `flyjam-obs-kit/SPEC.md`, `flyjam-obs-kit/TEST_MATRIX.md`, applicable
`AGENTS.md`, actual git status, `docs/implementation/OBS-STATUS.md` if present,
and the latest relevant milestone report. Read the relevant implementation before
editing. Perform the actual work, run appropriate tests, and update the handoff.
Preserve user changes and existing evidence. Execute only this milestone.

Implement the foundation of the authorized OBS-to-flight workstream.

1. Confirm HEAD and local modifications. Read STATUS, PIVOT, P00 report, the
   controller, lab runner/sensory/API/budget, web entry point, Makefile and workflow.
   Adapt to newer local code without reverting it to the kit's reviewed revision.
   Update routing for OBS00–OBS06; do not resurrect the old navigation plan or
   falsely record P00 product approval. Explain any real instruction conflict
   using its exact file/section rather than inventing a permission gate.

2. Inspect Linux/distribution/kernel, Python and Node versions, relevant installed
   packages, disk, full model data/checkpoint, FFmpeg/V4L2 tooling and OBS presence.
   List capture device metadata without starting streams. Choose one supported
   capture backend. Do not install kernel modules, change permissions, use sudo,
   or open unselected sources. Missing host prerequisites produce an actionable
   setup note while independent code continues.

3. Create the live package and executable versioned contracts: source capability,
   frame identity/timing, encoder configuration, neural sample, flight controls,
   flight snapshot, session config/status, stream envelope and replay manifest.
   Strict sizes/types/finite numbers, epochs and explicit real/fixture labels.
   Generate TS types/runtime schemas with a drift check. Freeze the interfaces
   before delegating independent source/UI work.

4. Create a minimal live entry point, idle health/config endpoint and actual
   `make live-devices`, `make live-doctor` and `make serve-live` targets. It must
   not pretend capture/inference is implemented yet. Pin any new dependencies
   narrowly. Preserve existing app/lockfiles unless additions are necessary.
   Store operator configuration under an ignored local path or environment;
   source URLs and shell arguments are not accepted from clients.

5. Document session bounds, validation allowance, freshness/clock semantics,
   ownership, capture consent, evidence privacy, chosen backend, and planned
   artifact locations. Define acceptance states separately. Record the distinction
   between a persistent worker and unchanged windowed_reset dynamics.

Validation: strict schema positive/negative cases, TS/Python schema compatibility,
health/no-capture-on-start behavior, metadata discovery failure states, generated
checks, lint/types/build and relevant existing regressions. No real neural calls
are needed in OBS00.

Handoff: actual tests, selected backend, exact remaining setup needs and next
prompt. Stop. Do not demand a broad product reapproval to implement OBS01.
