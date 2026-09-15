# Implementation Plan and Progress

This file is the working implementation plan for the Sorting Comparison Network
(SCN) experiment software. Update the checkboxes and notes whenever a milestone
is completed or its scope changes.

## Current status

- Current phase: Phase 1 - Formalize the experimental contract
- Next milestone: approve the formal SCN, comparison, and redundancy definitions
- Production experiments have not started.

## Confirmed research decisions

- [x] Use distinct records arranged as uniformly random permutations.
- [x] Use 1,000 independently generated permutations for every input size.
- [x] Give every algorithm the same 1,000 permutations for a paired comparison.
- [x] Preserve a permanent identity for every record as it moves.
- [x] Construct a separate SCN for every algorithm execution.
- [x] Define the canonical SCN as a directed graph.
- [x] Direct each comparison edge from the smaller record to the larger record.
- [x] Use directed reachability for logical implication and redundancy analysis.
- [x] Derive an undirected projection when an analysis requires undirected degree,
      clustering, or conventional degree-distribution statistics.
- [x] Do not pool executions into one graph; average features across executions.
- [x] Use production sizes `{128, 256, 512, 1024, 2048, 4096}`.
- [x] Identify the 1,000 trials for each size by seeds `1..1000`.
- [x] Make each permutation a deterministic function of `(n, seed)`.
- [x] Require hard validation of permutation validity, reproducibility, and no
      duplicate sequences within each input size.
- [x] Require ensemble-level uniform-permutation randomness diagnostics.
- [x] Preserve step-by-step SCN visualization and gradual force-directed layout
      as a separate, optional feature.
- [x] Keep production statistical runs headless, with no visualization or layout
      overhead.
- [ ] Finalize the initial algorithm catalogue.
- [ ] Finalize the operational definition of hierarchical allocation.
- [ ] Finalize the statistical definition and classification of scale-freeness.

## Phase 1 - Formalize the experimental contract

- [x] Establish the repository structure.
- [x] Decide that the canonical SCN is directed.
- [ ] Complete the formal SCN definition.
- [ ] Define repeated comparisons precisely.
- [ ] Define transitively implied comparisons precisely.
- [ ] Decide whether repeated or implied comparisons remain in the event log while
      being excluded from the simple SCN.
- [ ] Define comparison-efficiency measures.
- [ ] Define persistent-representative hierarchical allocation (PRHA).
- [ ] Define raw, per-run, and summarized result schemas.

Exit criterion: the definitions are sufficiently precise that two independent
implementations would construct the same SCN from the same comparison trace.

## Phase 2 - Comparison instrumentation

- [x] Implement records with permanent identities and sortable keys.
- [x] Implement the single comparison gateway used by every algorithm.
- [x] Record comparison time, endpoints, result, repetition, and implication.
- [ ] Prevent uninstrumented key comparisons.
- [x] Add unit tests for comparison semantics and identity preservation.

## Phase 3 - SCN and partial-order construction

- [x] Build the directed SCN from comparison events.
- [x] Maintain directed reachability for the known partial order.
- [x] Detect repeated comparisons.
- [x] Detect comparisons already implied by a directed path.
- [x] Produce total degree for the undirected simple projection.
- [x] Validate edge direction and the degree handshake identities in tests.

## Phase 4 - Initial sorting algorithms

- [x] Bubble sort (inefficient control).
- [x] Quicksort (persistent partition representatives).
- [x] Heapsort (positional hierarchy).
- [x] Binary insertion sort (hierarchical search).
- [x] Merge-insertion family baseline.
- [ ] Reproduce and validate the historical Jacobsthal merge-insertion schedule.
- [x] Top-down and bottom-up merge sort (hierarchical blocks without persistent pivots).
- [ ] Binary-search-tree sort (persistent routing hierarchy).
- [x] Bitonic sorting network (practical distributed-comparison control,
      correctly labelled with its `O(log^2 n)` depth bound).
- [x] Record AKS `O(log n)` depth as a theoretical rather than runnable benchmark.
- [x] Add exhaustive small-input correctness tests for every initial algorithm.

## Phase 5 - Reproducible input generation

- [x] Specify production sizes `{128, 256, 512, 1024, 2048, 4096}`.
- [x] Specify trial seeds `1..1000` for every size.
- [x] Require deterministic generation from `(n, seed)`.
- [x] Require the same permutations across algorithms.
- [x] Specify hard duplicate and permutation-validity checks.
- [x] Specify ensemble-level randomness diagnostics.
- [x] Implement the version-stable PRNG and unbiased Fisher-Yates shuffle.
- [x] Store the size, trial seed, generator version, and checksum.
- [x] Implement exact duplicate detection with digest pre-screening.
- [x] Implement ensemble randomness diagnostics with multiple-testing correction.
- [ ] Review and calibrate diagnostic thresholds after the first production report.
- [x] Generate all six production datasets with 1,000 sequences each.
- [x] Validate production dataset counts, checksums, reproducibility, permutation
      validity, and absence of duplicates.
- [ ] Support exact enumeration for selected small input sizes.
- [x] Verify deterministic regeneration with automated tests.

## Phase 6 - Result storage

- [x] Define first-version compact per-execution records.
- [ ] Define optional detailed comparison-event traces.
- [x] Write compressed raw JSON Lines and summarized CSV outputs.
- [ ] Store configuration and implementation versions with results.
- [ ] Support resumable experiments without silently mixing configurations.

## Phase 7 - SCN metrics

- [x] Calculate directed in-degree and out-degree in each SCN summary.
- [x] Calculate undirected total degree for the simple projection.
- [x] Calculate mean, maximum, and variance in first batch output.
- [x] Calculate coefficient of variation and Gini coefficient.
- [ ] Add skewness, quantiles, and maximum-to-average degree ratio.
- [ ] Calculate CCDF and applicable clustering/connectivity measures.
- [ ] Calculate temporal comparison-concentration measurements.

## Phase 8 - Comparison-efficiency metrics

- [x] Calculate the lower bound using log-gamma:
      `log2(n!) = logGamma(n + 1) / log(2)`.
- [x] Calculate `rho = comparisons / log2(n!)`.
- [x] Calculate normalized excess comparisons `epsilon = rho - 1`.
- [x] Count record movements, treating a swap as two relocations.
- [x] Measure peak and comparison-time mean auxiliary storage.
- [x] Export normalized movement/storage costs and an equal-weight baseline score.
- [ ] Summarize means, confidence intervals, and empirical quantiles.

## Phase 9 - Hierarchical-allocation analysis

- [x] Add final-rank comparison distance and normalized distance profiles.
- [x] Add exact per-comparison information gain.
- [x] Add active transitive-reduction size, maximum, and retirement dynamics.
- [x] Add comparison-endpoint participation concentration and busiest-node reuse.
- [ ] Define algorithm-independent PRHA indicators.
- [ ] Measure persistence of high-exposure records.
- [ ] Measure early-degree versus final-degree association.
- [ ] Measure comparison participation conditional on current degree.
- [ ] Where available, relate partition/subtree size to SCN degree.
- [ ] Compare concentrated hierarchical reuse with distributed logarithmic work.

## Phase 10 - Distribution analysis

- [x] Estimate a descriptive discrete power-law exponent and lower cutoff.
- [x] Perform bootstrap goodness-of-fit testing.
- [x] Compare power law with lognormal, exponential, and stretched exponential.
- [x] Report fitted-tail sample size, fraction, and span.
- [ ] Analyze average distributions and individual executions separately.
- [x] Validate the descriptive measures using synthetic power-law and exponential distributions.
- [x] Report tail KS, log-log CCDF R², and normalized power-law-versus-exponential likelihood advantage.

## Phase 11 - Figures and summaries

- [ ] Plot mean comparisons and efficiency ratio against input size.
- [x] Plot degree histograms and CCDFs on appropriate axes.
- [ ] Plot hub strength and inequality against input size.
- [x] Plot efficiency versus scale-free evidence.
- [ ] Plot PRHA strength versus scale-free evidence.
- [x] Export publication-quality figures and machine-readable validation results.
- [x] Add an interactive cross-algorithm degree-distribution dashboard.
- [x] Show linear PMF, log-log PMF, and log-log CCDF simultaneously.
- [x] Add algorithm visibility controls and a comparative metrics table.

## Phase 11A - Interactive SCN replay and visualization

- [x] Define the first versioned comparison-trace format.
- [x] Implement play, pause, single-step, reset, speed, and timeline seeking.
- [x] Animate directed comparison edges as the SCN is formed.
- [x] Distinguish active and already-implied comparisons visually.
- [x] Display the observed SCN separately from its current transitive reduction.
- [x] Implement input-order, final-order, and force-directed layouts.
- [x] Preserve node positions between frames and gradually improve the layout.
- [x] Allow inspection of record identity, value, degree, and history.
- [ ] Verify replay reconstructs exactly the same SCN as the batch engine.
- [x] Verify batch mode retains no trace by default and imports no viewer code.

## Phase 12 - Expand the algorithm catalogue

- [x] Add standard insertion sort and selection sort controls.
- [x] Add median-of-three and dual-pivot Quicksort variants.
- [x] Run the first expanded-catalogue pilot at `n=128`, seeds `1..100`.
- [ ] Add further exchange, partition, heap, tree, network,
      adaptive, and advanced comparison-sort families.
- [x] Require the same correctness and instrumentation tests for every addition.

## Phase 13 - Production runner

- [x] Support algorithm, size, trial, and seed configuration.
- [ ] Support safe parallel execution.
- [x] Support trial-level checkpoints and resumption.
- [x] Run a smoke test before production work.
- [x] Preserve completed trials when an execution is interrupted.
- [x] Generate incremental summaries and progress reports.
- [x] Add a scalable distribution-only profile with exact degree/count parity.
- [x] Generate first-stage compressed run records and CSV summaries.
- [x] Complete and validate the first 6-algorithm, 1,000-seed batch at `n=128`.

## Phase 14 - Reproducibility audit

- [x] Freeze the 19-algorithm confirmatory analysis protocol before production.
- [x] Record SHA-256 identities for the frozen implementation files.
- [x] Freeze the post-confirmatory statistical-validation extension.
- [ ] Verify every output is correctly sorted.
- [ ] Verify all key comparisons pass through the instrumentation layer.
- [ ] Compare exact small-size results with Monte Carlo estimates.
- [ ] Reproduce results from the same configuration and seed.
- [x] Audit validation result schema, publication figures, tests, and manuscript compilation.

## Development sequence

The first working milestone will contain only the formal definitions, comparison
instrumentation, directed SCN construction, Bubble sort, Quicksort, tests, one
small reproducible experiment, and basic comparison/degree plots. The remaining
algorithms and statistical models will be added only after this foundation is
validated.
