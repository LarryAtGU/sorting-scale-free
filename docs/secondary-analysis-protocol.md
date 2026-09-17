# Secondary analysis protocol

**Input:** the completed `paper-final-19-algorithms` experiment only

## Purpose

This protocol defines secondary analyses of the 19-algorithm endpoint.
It does not redefine or replace that endpoint or the separately specified
tail-validation extension. The analyses below assess resource decomposition,
family dependence, cutoff sensitivity, execution-block dependence, and
finite-size behavior, and must be reported regardless of direction or magnitude.

No additional sorting algorithm is included in this analysis. The temporal
experiment introduces controlled implementation variants separately.

## Mechanism families

- pivot: `introsort`, `quick`, `quick-dual-pivot`, `quick-median-three`,
  `quick-random`;
- tree: `tree-avl`, `tree-unbalanced`;
- merge: `merge-bottom-up`, `merge-top-down`, `merge-insertion`;
- network: `bitonic-network`, `odd-even-merge-network`;
- insertion: `insertion`, `binary-insertion`;
- tournament: `tournament`;
- heap: `heap`;
- shell: `shell`;
- exchange: `bubble`;
- selection: `selection`.

Singleton families remain separate. `tournament` is not pooled with merge even
if its marginal degree distribution resembles merge in the frozen results.

## Resource decomposition

At every input size and primarily at `n=4096`, report Spearman correlations of
PL--Exp mean log-likelihood difference with efficiencies derived from:

1. comparison excess `c` alone;
2. movements per node `w` alone;
3. peak auxiliary-storage fraction `s` alone;
4. `c+w`, `c+s`, and `w+s`;
5. the historical `c+w+s` score.

For a resource cost `q`, use `eta=1/(1+q)`. Also report the minimum, median,
maximum, and interquartile range of `c`, `w`, and `s`, plus each component's
fraction of `c+w+s` where the denominator is positive.

Run two separate 7-by-7 grids for `a,b in {0,0.1,0.25,0.5,1,2,4}`:

- raw-weight grid: `c+a*w+b*s`;
- transformed grid: `c+a*log(1+w)+b*log(1+s)`.

Do not select the best cell as a new primary score.

## Family dependence

At `n=4096`, report the historical full correlation, pivot-excluded,
tree-excluded, and pivot-plus-tree-excluded correlations. Compute one observation
per frozen family by taking within-family means of the predictor and outcome,
then report its Spearman coefficient. Estimate a descriptive 95% interval from
10,000 deterministic family-cluster bootstrap replicates: resample families
with replacement and retain all algorithms from each selected family. Degenerate
replicates are omitted and their count reported.

## Tail-cutoff sensitivity

For every algorithm and size, retain the existing optimized-cutoff fit and
report `xmin`, exponent, tail count, tail fraction, tail span, maximum degree,
and maximum degree divided by `n`.

At `n=4096`, additionally compare power-law and geometric/exponential models on
fixed upper-degree fractions `5%, 10%, 20%, 30%`. Select the degree cutoff that
includes at least the requested fraction, including the entire boundary tie.
Report actual fraction, cutoff, total LLR, and LLR per observation. The fixed-tail
analysis is sensitivity analysis, not a new scale-free classifier.

## Execution and block dependence

Use the compressed frozen execution records. For each algorithm at `n=4096`,
divide seeds in their deterministic order into 20 non-overlapping blocks of 50.
Aggregate degree histograms only within each block and apply the existing fitted
cutoff procedure. Report the median and 2.5--97.5 percentile range across blocks
for exponent, cutoff, tail fraction, KS, and PL--Exp LLR. Also report Spearman
efficiency--LLR correlations separately for each of the 20 matched seed blocks.

These block summaries are the primary dependence-aware diagnostic. Individual
execution fits may be summarized when the minimum-tail requirements are met but
must not silently discard failed fits.

## Alternative tails and finite-size behavior

Add a finite-support (truncated) power-law comparison reflecting
`degree <= n-1`. Report alternative-model comparisons as effect sizes with
block-level uncertainty, not merely by their sign on the pooled histogram.

Across all six sizes, plot for every algorithm family: exponent, `xmin/n`, tail
fraction, tail span, and `dmax/n`. Report these as finite-size long-tail
diagnostics unless a separately justified scaling analysis supports stronger
terminology.

## Weighted-SCN and intervention gate

The frozen records do not contain per-node comparison-event strength, so weighted
degree cannot be reconstructed. Before any rerun, instrument and test event-degree
histograms and document resource accounting. Then freeze a separate protocol for
`n=4096`, first 100 verification seeds and, only if successful, 1,000 seeds.

Candidate controlled variants are linked-list merge, index-based representations,
Hoare/Lomuto partition variants, and explicit representative-persistence
interventions. They are not authorized by this protocol.

## Required reporting

- State that H2 supports persistence but not monotonic strengthening.
- Treat concentrated hierarchical reuse as a conjecture except where proved for
  the random-BST/Quicksort model.
- Report unfavorable, null, degenerate, and failed-fit results.
- Distinguish comparison-only, implementation-resource, family-cluster, and
  distributional conclusions.
- Do not extrapolate to natural evolution as an empirical result.
