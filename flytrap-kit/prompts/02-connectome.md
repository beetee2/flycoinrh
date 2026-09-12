# Prompt 02 — Reproducible graph data and anatomical metadata

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement controlled data preparation and regression tests. Use explicit configurable paths, upstream public data sources/attribution, checksums, source versions, and a manifest. Avoid importing wallet or launch code. Refactor only enough of build_graph.py to test pure graph construction on tiny data.

Preserve W[post,pre] for fast signaling. Separately retain unsigned anatomical counts or compact PAM/PPL1→MBON input metadata before fast-weight sign filtering, aligned to stable body IDs and a documented threshold policy. Do not turn dopamine into an artificial fast excitatory connection. Handle duplicate edges, missing types, sparse/large IDs, zeros, ties, and unmapped bodies deliberately.

Write hand-computed regression fixtures that fail for the reversed lookup and demonstrate why transposing the fast matrix does not restore dropped edges. Verify body ordering, mappings, metadata hashes, count aggregation, and round-trip loading. Incorrect data must fail clearly rather than produce an empty plausible model.

Provide doctor/data-build commands. Use actual available full data for a smoke test and record observed graph statistics; do not hard-code prior counts as truth. If large data is missing or acquisition is unavailable, finish synthetic tests and explicitly mark the real-data gate blocked. Leave production learning disabled; behavioral validation happens later.
