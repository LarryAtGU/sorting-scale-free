# Statistical validation extension

**Extension version:** 1  
**Version:** final archived protocol
**Status:** diagnostic validation of the observational
`paper-final-19-algorithms` dataset

## Scope

This extension does not alter or replace the primary confirmatory result in
`frozen-analysis-protocol.md`. It adds diagnostics requested for publication.
All results defined here must be reported regardless of whether they strengthen
or weaken the paper's hypothesis. Any later change is exploratory and requires a
new extension version.

## Input data

Use only `batch-paper-final-19-algorithms-summary.csv` and, where execution-level
uncertainty is required, its associated frozen run file. Do not rerun sorting,
remove algorithms, change degree definitions, or refit the combined-efficiency
score for this extension.

## Power-law goodness-of-fit

For every algorithm at `n = 4096`, use the already frozen cutoff-selection and
continuity-corrected discrete power-law fitter. Estimate a semiparametric
bootstrap goodness-of-fit probability with 250 replicates and a deterministic
seed derived from the string `scn-tail-bootstrap-v1`, the algorithm name, and
the input size.

Each replicate has the observed aggregate sample size. Values below the
observed fitted cutoff are drawn from their empirical distribution; values in
the tail are drawn from the fitted continuity-corrected power law. To bound
runtime, the bootstrap representation may be proportionally downsampled to at
most 50,000 observations before generation. The observed and simulated
histograms must use the same effective size, and the cutoff and exponent must be
re-estimated for every replicate. Report

`p_boot = (1 + count(KS_sim >= KS_observed)) / 251`.

Interpret `p_boot < 0.1` as evidence against the fitted power law. A value at or
above 0.1 means the power law is not rejected; it does not prove that the model
is true.

## Alternative tail models

At each observed power-law cutoff, fit discrete conditional lognormal and
discrete conditional stretched-exponential distributions by maximum likelihood.
Use integer-bin probability masses with lower boundary `xmin - 0.5`. Compare
the fitted power law separately against:

- the existing discrete exponential;
- the discrete lognormal; and
- the discrete stretched exponential.

Report mean log-likelihood difference per tail observation, positive when the
power law is favored. These comparisons are descriptive model comparisons; do
not treat their signs as formal hypothesis-test p-values.

## Resource-score sensitivity

The frozen equal-weight score remains the primary predictor. As a robustness
analysis, calculate

`Q(a,b) = c + a * log(1 + w) + b * log(1 + s)`

and `eta(a,b) = 1 / (1 + Q(a,b))` on the final `n = 4096` algorithm means for
every pair

`a,b in {0, 0.1, 0.25, 0.5, 1, 2, 4}`.

Report the complete 7-by-7 Spearman-correlation surface against PL-Exp LLR, its
minimum, median, and maximum, and the fraction of grid points at or above 0.6.
Do not select the maximum as a replacement score. Recalculate the surface after
excluding the frozen pivot family.

## Uncertainty and plots

Use algorithms as the observational units. Report the primary 19-algorithm
Spearman coefficient with a deterministic, algorithm-level nonparametric
bootstrap interval using 10,000 resamples. Because related algorithms violate
independence, label this interval descriptive and accompany it with the frozen
leave-one-family-out analysis.

Produce these publication figures from the frozen data:

1. efficiency--LLR Spearman correlation versus input size;
2. combined efficiency versus PL-Exp LLR at `n = 4096`, labeled by algorithm
   and visually grouped by frozen family;
3. the full resource-weight sensitivity heat map;
4. representative log--log CCDFs for ordinary Quicksort, AVL Tree sort,
   bottom-up Merge sort, Shell sort, and Bitonic Network.

Figures must state that degree histograms aggregate 1,000 executions per cell.

## Required reporting

The manuscript must distinguish the original confirmatory endpoint from this
post-confirmatory validation extension. It must report failed goodness-of-fit
tests, alternative models that outperform the power law, the entire weight-grid
range, and limitations caused by aggregation and algorithm-family dependence.
