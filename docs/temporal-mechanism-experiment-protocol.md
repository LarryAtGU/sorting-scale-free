# Temporal representative-exposure experiment protocol

**Version:** 1  
**Status:** targeted mechanism and intervention experiment

## Questions

1. Does comparison participation become concentrated during an execution?
2. Is future endpoint selection associated with current event strength?
3. Do persistent algorithmic representatives account for final degree concentration?
4. Does distributing partition work across more pivots reduce representative
   exposure and network concentration?

The experiment does not redefine the completed 19-algorithm endpoint.

## Inputs

- deterministic uniform permutations from generator version 1;
- sizes `128, 256, 512, 1024`;
- seeds `1..200`;
- identical permutation for every algorithm at a given `(n, seed)`.

## Algorithm panel

Observational controls:

- `tree-unbalanced`, `tree-avl`;
- `quick` (historical Hoare implementation), `quick-dual-pivot`;
- `merge-top-down`, `binary-insertion`, `heap`, `bitonic-network`.

Intervention family:

- `quick-multipivot-1`, `quick-multipivot-2`, `quick-multipivot-4`.

The intervention algorithms use stable recursive partitioning. They sort their
chosen pivots, classify every non-pivot record by binary search over the pivots,
and recursively sort the resulting buckets. They intentionally change both
representative exposure and some costs; all resource components remain reported.

Expected executions: `11 * 4 * 200 = 8,800`.

## Online temporal measurements

At comparison counts `1,2,4,8,...` and at completion, record for both distinct
degree and event strength:

- Gini coefficient;
- P80 node fraction;
- normalized entropy;
- maximum-node share.

For every node, accumulate the number of event steps spent at each current event
strength. Combine this opportunity count with the number of endpoint selections
made at that strength to estimate an empirical attachment kernel. This is a
descriptive conditional selection rate, not proof of causal preferential attachment.

## Representative measurements

Algorithms explicitly mark comparisons in which one endpoint acts as a pivot,
tree-search node, or binary-search midpoint. Record per execution:

- representative-comparison fraction;
- number and fraction of nodes used as representatives;
- Gini and P80 of representative exposure;
- maximum representative exposure share;
- mean and maximum represented span;
- mean representative lifetime, normalized by total comparisons;
- correlation of per-node representative exposure with final distinct degree
  and final event strength.

Algorithms with no privileged record representative report zero exposure rather
than having their ordinary symmetric comparisons relabelled.

## Outputs and exclusions

The resumable runner writes one JSON record per execution, a compressed final
run file, and algorithm-size CSV summaries. Incorrect sorting, inconsistent
profiles, duplicate keys, or non-finite metrics are implementation failures.
No algorithm or seed may be removed because its result weakens the mechanism.

## Staged execution

1. Smoke test: all algorithms, `n=128`, seeds `1..3`.
2. Verification run: all sizes, seeds `1..20`.
3. Production run: all sizes, seeds `1..200`, resuming the same label only if
   implementation hashes and the protocol remain unchanged.

Production must not begin until unit tests, cross-profile comparison parity, and
the smoke test pass.
