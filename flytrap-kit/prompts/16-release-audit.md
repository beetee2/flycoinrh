# Prompt 16 — Fresh-context adversarial release audit

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Review the implementation as a skeptical independent release engineer. Use a fresh context/worktree where practical, read the actual code and evidence, and do not accept previous PASS summaries without checking their artifacts. Confirm scope, source attribution, observation isolation, no fake steering, no implicit checkpoint loading, database integrity, worker fencing, real-service E2E, honest labels, and the scientific claim gate.

Use bounded local fault/mutation probes to demonstrate that tests catch reversed connectivity, target metadata leakage, duplicate finalization, corrupt artifacts, disabled-feature bypass, and fixture-as-real labeling. Keep probes out of release code and restore fixtures afterward. Inspect representative browser traces/screenshots manually; test collection and coverage totals alone are not enough.

Run the full ordinary verification suite and mandatory real-model release suite against the intended clean source revision. Check clean install/build, migrations, lockfiles, local container smoke, restart, and backup restore. Separate code defects, evidence gaps, unavailable external prerequisites, and inconclusive research.

Fix reproducible defects with regression tests and rerun affected plus release checks. Produce a release evidence index bound to exact code/data/model/config hashes, unresolved risks, and PASS/FAIL/BLOCKED per boundary. Do not waive a failing real-model gate or weaken assertions to obtain green. No remote pushes or public release actions are authorized here.
