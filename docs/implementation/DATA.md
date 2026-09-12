# Connectome preparation

Milestone 02 uses the public FlyEM MaleCNS v1.0 flat connectome with synapse
confidence cutoff 0.5. The [official download page](https://male-cns.janelia.org/download/)
lists the source assets. Attribution and CC-BY 4.0 remain in the repository's
[NOTICE](../../NOTICE) and in every graph manifest. The current URLs include
`connectome-data/flat-connectome/`; the older README prefix omits that segment.

[sources.json](../../flytrap/data/sources.json) pins all three objects by URL,
GCS generation, exact byte size, provider MD5, and locally measured SHA256. These
hashes identify the downloaded version; they do not establish biological fidelity.
Downloads use public HTTPS without credentials. Source acquisition is an explicit
operator action; no inference or API process downloads data automatically.

## Commands

From this checkout, after the locked `make bootstrap`:

```console
make data-fetch
make data-build
make data-doctor
make test-data-real EVIDENCE=artifacts/milestones/02
```

The default raw root is `data/`; the default graph root is `build/flytrap-v1/`.
Both are ignored. Override them with `RAW_ROOT=/absolute/raw/path` and
`GRAPH_ROOT=/absolute/new/bundle`. Each command also has an equivalent CLI:

```console
.venv/bin/python -m flytrap.cli data-fetch --raw-root data
.venv/bin/python -m flytrap.cli data-build --raw-root data --graph-root build/flytrap-v1
.venv/bin/python -m flytrap.cli data-doctor --raw-root data --graph-root build/flytrap-v1
```

`build_graph.py` delegates to `data-build` and accepts its path and threshold
arguments. Its output is now the bundle directory above. An upstream `FlyBrain`
can load the bundle's `graph.npz` through its explicit `graph_path` argument.
No unmanifested `build/graph.npz` alias is created.

`data-fetch` reuses an existing root only if all pinned files verify. It refuses
partial or corrupt roots. Downloads stage in a sibling temporary directory and
must pass size/MD5/SHA256 checks before publication. `data-build` verifies raw
bytes before reading tables, and refuses to overwrite an existing output. Choose
a new graph root for a new build or policy; preserve previous bundles for review.
The raw files occupy 1,109,008,094 bytes. Preparation streams Arrow IPC batches,
retains mapped endpoints, and then constructs the sparse graph in memory; a full
build still needs several GB of free memory and disk for its graph and staging.

`data-doctor` verifies the pinned raw files, manifest schema/source/policy,
archive checksum, canonical sparse structures, ordered body/metadata hashes,
anatomical input hashes, graph statistics, and the fast/anatomical weight relation.
Missing, corrupt, or fixture data fails with a nonzero exit. `make verify-real`
continues to fail until the real controller and later integration gates exist.
A data gate pass does not imply model behavior or a release pass.

## Graph policy

Both sparse matrices use `[post, pre]`. Body IDs are nonnegative int64 values in
ascending order, with allocation based on neuron count. Eligible bodies have
`status == Traced` and, when `statusLabel` is supplied, are not labeled `Glia`.
Only edges with two eligible endpoints survive. Isolated eligible bodies retain
their index. Metadata conflicts for a body fail; equal duplicate records collapse.

Directed duplicate edge counts are summed **before** applying `min_syn` (default
3). Zeros and aggregate counts below that threshold disappear from both matrices.
Malformed, negative, nonfinite, fractional, boolean, out-of-range, or ambiguous
numeric values fail. The builder rejects an empty anatomical graph and count
overflow. Streaming never drops individual subthreshold rows before aggregation.

The anatomical matrix retains unsigned integer counts. Fast weights equal
`float32(count) * float32(0.275) * presynaptic_sign`. Acetylcholine is positive;
GABA, glutamate and histamine are negative. Dopamine, octopamine, serotonin,
unclear and unknown are zero fast weight. Unrecognized transmitter names are
retained with zero sign and counted in statistics. Missing transmitter metadata
becomes `unknown`.

Type selection uses nonempty `type`, then `flywireType`, then `instance`, then
empty. Other missing descriptive fields remain empty. Types, neurotransmitters,
signs, superclass, subclass, receptor and fru metadata align with sorted body IDs.
No fixed-width truncation silently changes source names.

PAM/PPL1 input summaries select type prefixes and sum
`anatomy[MBON][:, PAM]` and `anatomy[MBON][:, PPL1]`. Results are `PAM`, `PPL1`,
`tie`, or `zero`. These are input-dominance heuristics; they do not validate
biological compartment labels or a learning rule. The signed fast matrix cannot
recover discarded dopamine edges by transposition.

## Bundle and validation scope

`graph.npz` preserves upstream fast CSR/body/metadata fields and adds
`anatomy_data`, `anatomy_indices`, and `anatomy_indptr`. `manifest.json` records
source attribution/checksums, build code identity, runtime/dependency versions,
threshold policy, observed statistics, and hashes for every ordered array and
derived PAM/PPL1 input summary. Logical array hashes encode kind/shape followed
by canonical little-endian numerical bytes or UTF-8 JSON strings.

The loader rejects pickle arrays, extra/missing arrays, invalid CSR structure,
misaligned body/metadata arrays, noncanonical ordering, altered signs/weights,
unsupported policy/schema, and corrupt archives. Bundle files are flushed and
renamed from a temporary directory. This operator graph publication is separate
from the later worker/replay crash-consistency milestone.

`make verify` explicitly excludes `tests/real_data/`. Its synthetic fixtures are
labeled and cover direction, duplicates across batches, large IDs, missing and
conflicting metadata, zeros/ties, corruption and acquisition failures. The
separate real-data suite requires all full files, checks raw directed counts,
and loads the resulting matrix through upstream `FlyBrain`. It executes no
neural trajectories. Real controller behavior is milestone 03 and feasibility
is milestone 05. Learning remains disabled.
