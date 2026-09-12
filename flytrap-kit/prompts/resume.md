# Active scope override: P00 only

Read docs/implementation/PIVOT.md and docs/implementation/milestones/P00.md first.
Navigation is stopped. Original milestones 06–18 are blocked and cannot be
selected by ordinary resume. Milestone 05 diagnostics were accepted without
approving navigation. Only finish authorized P00 if unfinished; when its
engineering work is complete, stop for human product review. Repeating resume
is not product approval or authorization for any successor or public release.
The historical routing below applies only if a future explicit human decision
reinstates it; do not use numeric selection now.

---

# Resume FLYTRAP — one milestone per invocation

Resume implementation in this checkout. Perform the actual work;
do not merely propose a plan.

## Recover context

Read:
- Applicable repository instructions, including AGENTS.md.
- flytrap-kit/PLAN.md.
- flytrap-kit/BOUNDARIES.md.
- docs/implementation/STATUS.md.
- The latest milestone report and any prerequisite reports relevant
  to the milestone being resumed.

Inspect actual git status, relevant code, and recorded evidence.
Preserve existing user changes. Do not rely on previous chat
summaries instead of repository files.

## Select the work

Consider only the numbered implementation milestones, 00 through 18.
This resume.md file is not an implementation milestone.

Select the earliest unfinished milestone in numeric order.
Resume an in-progress or failed milestone before starting another.

Do not skip a blocked milestone merely because a later milestone
appears executable. Follow only the plan's explicitly permitted
optional or fallback paths, and record the reason.

Verify that the selected milestone's prerequisites are actually met.
A status entry alone is not proof. If relevant code changes or missing
evidence invalidate a prerequisite, repair that prerequisite before
advancing.

Briefly state which milestone you selected and why. Then read its
complete prompt from flytrap-kit/prompts/ and execute its instructions.

## Implement and validate

Work on only the selected milestone and necessary prerequisite repairs.
Do not automatically continue to the following milestone.

Run the required validation for every affected boundary: unit,
property, contract, database, API, worker, integration, UI, Playwright,
real-model, or operational tests as specified by the plan.

Inspect test outputs and required visual evidence, not merely exit codes.

Never:
- Report unexecuted tests as passing.
- Treat missing data or tools as successful validation.
- Replace required real-service or real-model tests with mocks.
- Weaken acceptance criteria or remove failing tests to obtain a pass.
- Claim learning improvement without the required experimental evidence.

Distinguish engineering correctness from experimental outcomes.
An honestly inconclusive learning result may permit the plan's core
release path; it does not authorize an improvement claim.

If blocked by an external dependency, missing authorization, or
unavailable resources, preserve progress and stop. Report the exact
blocker and minimum action needed. Do not repeatedly retry unchanged
conditions or silently advance.

## Record the handoff

Update STATUS.md and the milestone report with:
- What changed and which milestone was addressed.
- Actual validation commands and results.
- Passed, failed, skipped, and unexecuted checks.
- Evidence paths and the code/configuration they validate.
- Remaining work, blockers, and the next milestone.

Mark the milestone complete only when its required acceptance
criteria are satisfied. Otherwise leave it explicitly unfinished.

End with a concise completion or blocker report, then stop.

## Authorization and completion

Repeating this resume instruction does not authorize remote pushes,
public deployment, paid infrastructure, token transactions, pull
requests, or social posts. Those require separate explicit user
authorization for the specific action.

When all milestones meet the plan's completion rules, report the final
state and evidence. Distinguish implementation complete, deployment
verified, and submission prepared or actually submitted. Do not invent
additional milestones or claim external actions that did not occur.

## Human review gates

Before selecting another milestone, check for pending human reviews.

Require explicit human review after milestones:
- 05: Real-model behavior and interaction-mode decision.
- 10: Hands-on local interface review.
- 16: Release readiness.
- 17: Public deployment acceptance.
- 18: Submission-package approval before publication.

After milestone 13, also require human review before promoting a
trained checkpoint or enabling a positive learning-improvement claim.

Keep engineering validation and human review separate:
- automated_status: PASS / FAIL / BLOCKED
- human_review: NOT_REQUIRED / PENDING / APPROVED / CHANGES_REQUESTED

At each human gate:
1. Finish the milestone's automated validation.
2. Record human_review: PENDING in STATUS.md and the milestone report.
3. Provide the exact working startup command/URL or evidence paths.
4. Give a short checklist of what I should inspect.
5. Stop before starting the next milestone.

An identical resume instruction is not approval.
Never approve your own work on my behalf.

When I request changes, implement them, rerun affected tests, and
present the updated work for review. Record approval against the
reviewed code/configuration; substantive changes invalidate affected
approvals.

Human approval of quality does not authorize paid resources, public
deployment, remote pushes, PRs, or social posts. Those still require
specific authorization for the target and action.