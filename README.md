# Sorting Comparison Network Experiments

Reproducible experiments relating comparison-sort efficiency to the structure
of sorting comparison networks (SCNs).

## Project layout

```text
configs/             Version-controlled experiment configurations
data/generated/      Reproducible generated permutations (not committed)
data/results/        Raw and summarized experiment results (not committed)
docs/                Mathematical definitions and research notes
figures/             Publication-ready generated figures (not committed)
scripts/             Command-line entry scripts
src/scn_sorting/     Python package
  algorithms/        Instrumented sorting algorithms
  analysis/          Statistical and network analysis
  experiments/       Experiment generation and execution
  instrumentation/   Records, comparison tracking, and SCN construction
tests/                Automated correctness and measurement tests
```

Git has intentionally not been initialized. The experimental implementation
will be added after the mathematical SCN and redundancy definitions are fixed.

