# Prompt 09 — Replay verification and backend vertical slice

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement finalized replay manifests, trace serialization, download, and a CLI verifier. Include source/environment/data/checkpoint/config identity, state mode, seeds, renderer/reward versions, initial state, ordered actions, observation hashes, timing, attempts, outcome, and artifact digests. Keep every scored step; do not rely on a downsampled spectator stream as the only replay record.

Replay by reapplying recorded actions to deterministic physics and recomputing observations/outcome. Distinguish this from rerunning neural inference, whose reproducibility is scoped to declared runtimes/tolerances. Checksum validity proves internal consistency, not independent authenticity of a brain claim.

Reject reordered/missing chunks, digest mismatches, invalid schema, unsafe decompression, inconsistent terminal results, and mismatched model references. Reconstruct display frames from canonical versions or include sufficient immutable assets. Preserve incomplete attempts as incomplete.

Run a headless vertical integration: real HTTP request → file database → worker → actual model → published bundle → verifier → second independent HTTP client. Also run a small fixture version in CI. Inspect database state and artifact contents; a 200 response alone is insufficient. Missing full data blocks the real integration gate. Save a genuine representative replay as the seed for later browser and submission tests, clearly recording successes and failures.
