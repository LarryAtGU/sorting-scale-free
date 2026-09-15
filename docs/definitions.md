# Formal Definitions

This document records the mathematical objects used by the experiment software.
Items marked **Draft** must be resolved before the corresponding implementation
is treated as stable.

## Records and input

An experiment input contains `n` distinct records. Every record has a permanent
identity that does not change when the sorting algorithm moves it. For each input
size, inputs are sampled independently and uniformly from the `n!` permutations.

## Directed sorting comparison network

For one execution, the canonical sorting comparison network is a directed graph

`G = (V, E)`.

- `V` contains one vertex for each permanent record identity.
- Whenever a comparison establishes that record `u` is smaller than record `v`,
  the directed comparison relation is `u -> v`.
- Because keys are distinct and every edge follows the true total order, `G` is
  a directed acyclic graph.

The direction is semantically important. A directed path

`u -> x1 -> ... -> xr -> v`

means that `u < v` is already implied by transitivity.

## Comparison events and graph edges

The event trace and the simple SCN are different objects. The trace retains the
chronological sequence of comparison calls. The simple SCN contains at most one
directed edge for a compared record pair.

**Draft decision:** repeated and transitively implied comparison calls should
remain visible in the event trace and in comparison-cost measurements, while the
simple SCN should contain only one edge for their ordered pair. This preserves
the behaviour of the original algorithm without turning the canonical SCN into
a multigraph.

## Repeated comparison

A comparison is repeated if the same unordered pair of permanent record
identities appeared in an earlier comparison event. Direction is not considered
when deciding whether the pair was previously compared.

## Transitively implied comparison

Immediately before comparing records `u` and `v`, the comparison is implied if
the current directed SCN already contains a directed path from `u` to `v` or from
`v` to `u`. Its result is therefore logically determined by earlier comparisons.

## Undirected projection

Some conventional network statistics are defined for undirected graphs. The
undirected projection replaces every directed SCN edge `u -> v` with the
undirected edge `{u, v}`. Direction is retained in the canonical data and is
discarded only for a specifically identified analysis.

## Degree

For a vertex `v`:

- in-degree counts directly compared smaller records;
- out-degree counts directly compared larger records;
- undirected degree counts distinct records directly compared with `v`.

For the simple directed SCN,

`sum(v) [in_degree(v) + out_degree(v)] = 2 |E|`.

## Comparison efficiency

For algorithm `A` and uniformly random input size `n`, let `M_A(n)` be its
comparison count. Its average comparison-efficiency ratio is

`rho_A(n) = E[M_A(n)] / log2(n!)`.

The normalized excess is

`epsilon_A(n) = rho_A(n) - 1`.

The expectation is estimated from the 1,000 shared random permutations at each
input size.

## Hierarchical allocation and scale-freeness

**Draft:** persistent-representative hierarchical allocation and the statistical
classification of scale-freeness will be specified after measurable,
algorithm-independent criteria are agreed.

