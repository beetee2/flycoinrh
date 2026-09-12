# Prompt 17 — Authorized deployment and production smoke validation

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Prepare deployment from the verified release revision and the single-host runbook. Inspect existing deployment configuration and permissions. Deploy only to a target explicitly authorized for this project with approved credentials/budget; do not infer permission to create paid infrastructure or overwrite another service.

When a target is authorized, deploy the pinned images and verified model assets, apply migrations safely, configure the public origin/TLS/proxy and local persistent volumes, enforce the one-worker topology, and leave unsupported learning disabled. Verify health/admission, resource limits, secret isolation, and backup/rollback readiness.

Run a production-safe browser smoke: create one bounded real challenge, observe the actual simulation, open its replay in a second session, download/verify provenance, check metadata in initial HTML, and confirm service restart preserves the replay when a restart is authorized. Exercise only safe public error cases; keep destructive fault injection in staging/local environments. Compare production configuration and hashes with release evidence.

If no authorized target or credentials exist, produce the exact deployable package, environment template, operator commands, smoke script, and rollback steps; mark deployed verification BLOCKED, not completed. Do not invent a public URL or ask for secrets in chat. Record precisely what was deployed/tested versus merely prepared. No social post or upstream PR yet.
