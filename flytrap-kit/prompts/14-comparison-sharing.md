# Prompt 14 — Gated comparisons and contest-ready sharing

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement share/replay pages with crawler-readable metadata in initial HTML, a real-result share card, clipboard links, methodology/limitations, and links to provenance. Use actual run data and a server-configured public origin, not arbitrary request Host values. Share without X credentials, token purchases, or automatic posts.

Implement paired comparison only when an approved evidence report and matching immutable checkpoints permit it. Admit both jobs atomically under quotas; use the same challenge/seed/physics/renderer/action mapping, record any sequential execution, and keep learning off during both trials. Comparison playback must align recorded ticks without implying the jobs ran simultaneously in real time.

Show uncertainty and the report behind any improvement claim. Missing, stale, inconclusive, unsupported, or mismatched evidence must disable that claim and avoid orphaned “trained smarter” copy. The core replay/share experience must still work with comparison disabled. An experimental report may be shown honestly without positive marketing.

Test flag on/off, report/checkpoint mismatch, paired seed/config parity, atomic quota failures, metadata HTML without JavaScript, safe text escaping, replay URLs in a second browser session, mobile sharing, and accessibility. Inspect generated cards for legible accurate content and no fixture-as-real labeling. Save Playwright/API/DB evidence and a truthful draft submission copy; do not publish it.
