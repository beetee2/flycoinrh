# P00 — FLYTRAP LAB scope decision

Recorded before implementation, 2026-09-11 US/Central.

- Diagnostic work on milestone 05: ACCEPTED, including its negative result.
- Navigation: STOPPED. No navigation interaction or candidate is approved.
- Original milestone 06: BLOCKED; the old numbered plan cannot resume.
- P00: AUTHORIZED, local-only stimulus-response prototype.
- Public release: NOT AUTHORIZED. Engineering PASS does not approve the product.

Build one React/FastAPI screen with bounded 16×16 grayscale A/B inputs, exact
submitted pixels, actual L1/L2 coverage and input drive, raw motor rates, existing
neural statistics, matched-seed comparisons and downloadable provenance JSON.
Use the explicit untrained baseline and declared windowed_reset mode. Preserve
all historical code, configurations, tests, reports, data and ignored evidence,
and the working CI configuration.

Validate browser → API → Observation → actual FlyEye → drive → real model → UI
with an independent sampling oracle and real data. Distinguish pixels, input
drive and output firing. Show discarded information. Three fixed matched seeds
(17, 29, 43); each explicit comparison performs A, A repeat and B per seed
(9 attempted calls). Same-image controls and equal-brightness patterns are
required. No claims of perception, recognition, preference, learning, biological
vision or intelligence. Matching motor outputs do not identify whole-brain state.

One active isolated model job, explicit Run, finite payload/work/time limits,
visible busy/unavailable/error states, isolated artifacts under
artifacts/milestones/P00/. Hard budget: at most 256 attempted new full-model
calls across validation and demonstration; persistent accounting before calls,
stop at cap. No optimization sweeps or automatic repeated comparisons.

No moving avatar, goals, physics, training, calibration search, leaderboard,
wallet, arbitrary uploads, posting, production queue, new database schema or
public hosting. No paid infrastructure, remote push, PR, transactions or social
posts. Provide startup command, verified loopback URL, inspected desktop/mobile
captures, review JSON and an outline only for possible later milestones. Stop
for human use and product review after P00.

## Suggested later outline — not authorized or implemented

- P01: Human-approved interaction refinement, accessibility and clearer sensory
  explanations based on hands-on P00 feedback. Preserve encoding unless a new,
  separately measured model version is explicitly approved.
- P02: Reproducibility and local packaging; decide whether durable result storage
  and further operational work are warranted, with a new bounded compute budget.
- P03: Contest-fit review and an authentic demonstration/claims package; decide
  whether the measured interaction supports an entry before public work.
- P04: Separately authorized release engineering and deployment, followed by
  human release/submission approval. Public writes require explicit authorization.

An ordinary resume cannot start this outline. P00 stops for human use.
