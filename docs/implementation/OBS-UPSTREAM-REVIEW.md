# OBS03 upstream review

2026-09-15. Reviewed fork `7c35af0299d918f6294e2ba64452ec89108372d8`
and upstream `f2fdedf49bbd2712834c5404c690670af26c2028`. GitHub's comparison
confirms divergence and common ancestor
`8748e5bd30794d14afeb3441904221b52a002cac`. Commit patches and the pinned GPU
source were inspected through read-only GitHub API calls. No upstream changes
were merged or applied during this review.

## Dispositions

1. **Preserve the OBS03 baseline.** Keep the CPU implementation, all-one gains,
   learning disabled, and `windowed_reset` with the existing 100 integration steps
   and seed sequence. Do not merge all of upstream, overwrite protected model
   files, or replace the source-bound checkpoint.

2. **GPU: separate optional-backend qualification.**
   [856693a](https://github.com/fruitflydev/flycoinrh/commit/856693ae77d191047b2787b41a531ab9948e1ce3)
   introduces a Torch sparse-matrix backend, batched seeds, equivalence tests and
   a benchmark. The pinned `flysim_gpu.py` returns `_total_hz`,
   `_spikes_per_sec`, `_fired`, `_mean_mv` and `_state`, but lacks the fork's
   `_total_spikes`. Future integration must expose the accumulated integer spike
   count directly, preserve the complete required result/typed neural-output
   contract, record a distinct backend identity, and qualify parity and timing
   on our actual **100-step, batch-size-one, all-one-gain baseline**. Upstream's
   reported 60/250-step and batched timings are not that qualification.
   [3c38477](https://github.com/fruitflydev/flycoinrh/commit/3c384771acdc534e2328f4a9a0e5f45a61d1efef)
   changes the lesion-pattern test to skip when the external `lesion.py` helper
   cannot be imported; it does not correct the missing result field or establish
   that boundary here. No GPU backend installation or activation belongs in OBS03.
   The flight decoder must consume existing typed neural outputs without a CPU
   implementation dependency.

3. **Learning: separate maintenance backport before enablement.**
   [53bcb7f](https://github.com/fruitflydev/flycoinrh/commit/53bcb7f6dc7ce617c074210d29554e4df6a24cb6)
   derives dopamine sides from raw incoming synapse counts and ships
   `build/mb_sides.json`; the simulator matrix omits zero-sign dopamine edges.
   [84d2201](https://github.com/fruitflydev/flycoinrh/commit/84d2201e7321494dd26910ec643495976a7a96b0)
   uses that table instead of the reversed MBON-output lookup, versions saved
   gains with side-table/calibration identity, and applies wall-clock forgetting
   to the actual weights. Backport and validate these together before enabling
   MushroomBody learning. They are not prerequisites for learning-disabled OBS03.

4. **Reset and sensory scope: defer.**
   [6d6a21b](https://github.com/fruitflydev/flycoinrh/commit/6d6a21bafdc94523b735972361327942a4cbc5ab)
   adds optional carried membrane/refractory/random state and a changed plume
   protocol. [6a075e1](https://github.com/fruitflydev/flycoinrh/commit/6a075e1eb8bcf338e2872ca12be2edce653dd30c)
   adds `extra_drive` and `extra_record` to `FlyPilot.step`. Neither reset
   semantics nor sensory scope changes during OBS03.

5. **Hosted prerequisite: verified PASS for the reviewed fork commit.**
   A fresh `gh run view` confirms
   [FLYTRAP foundation run 34982619140](https://github.com/beetee2/flycoinrh/actions/runs/34982619140)
   is `completed`, conclusion `success`, head
   `7c35af0299d918f6294e2ba64452ec89108372d8`, updated
   `2026-09-15T14:38:37Z`. This resolves the previous pending hosted note for
   that commit; it does not certify subsequent OBS03 changes.

## Evidence and attribution

Raw API results, exact command arguments/exits, comparison identity and the
pinned GPU source are retained under ignored
`artifacts/milestones/OBS03/upstream-review/`. All recorded API verification
commands exited 0; no upstream tests, benchmarks or model calls were executed.
GPU source SHA256:
`944cde29a89f791ed6352ea7179f9b84fd9d0cfb0a5c90e849e4e5d423e146b2`.
Initial local inspection found the upstream commit objects absent; the review
used the API without changing checkout refs. Subsequent working-tree edits
belong to the concurrent authorized OBS03 implementation and were preserved.

OBS03 uses original procedural fly geometry. No upstream `backrooms.html`
visuals, relay, conversation service, behavioral motion, world controller or full
page are copied. Repository LICENSE, NOTICE and data attribution remain applicable
and preserved; commit links above credit the inspected upstream work.
