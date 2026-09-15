# Frozen confirmatory analysis protocol

**Protocol version:** 1  
**Frozen:** 2026-09-14, before inspecting any 1,000-seed, 19-algorithm result  
**Production label:** `paper-final-19-algorithms`

## Status and purpose

The earlier 100-seed experiments are exploratory. They were used to develop the
measurements, select the algorithm panel, and formulate the hypotheses. The run
defined here is confirmatory. Its definitions, primary analysis, sensitivity
analyses, stopping rule, and reporting requirements are fixed before execution.

No measurement, weight, tail-fitting rule, algorithm implementation, family
classification, or exclusion rule may be changed after the production run starts
without creating a new protocol version. Any post-protocol analysis must be
identified as exploratory in the paper.

## Frozen experimental design

- Inputs are the existing deterministic SplitMix64/Fisher-Yates uniform
  permutations identified by `(n, seed)`.
- Sizes are `128, 256, 512, 1024, 2048, 4096`.
- Seeds are exactly `1..1000` at every algorithm-size cell.
- The 19 algorithms are exactly those listed in
  `configs/paper-final-19-algorithms.json`.
- Every algorithm receives the same permutation for a given `(n, seed)`.
- Tracking uses `--distribution-only`.
- Expected executions are `19 * 6 * 1000 = 114000`.
- The run stops only after all 114,000 executions finish. It must not stop early
  because a desired or undesired correlation has appeared.

The frozen command is:

```bash
.venv/bin/scn-run-batch \
  --distribution-only \
  --algorithms binary-insertion bitonic-network bubble heap insertion \
    introsort merge-bottom-up merge-insertion merge-top-down \
    odd-even-merge-network quick quick-dual-pivot quick-median-three \
    quick-random selection shell tournament tree-avl tree-unbalanced \
  --sizes 128 256 512 1024 2048 4096 \
  --first-seed 1 --last-seed 1000 \
  --label paper-final-19-algorithms
```

Interruptions do not change the protocol. The identical command resumes from
the trial-level checkpoint. The final checkpoint must contain exactly 114,000
unique `(algorithm, n, seed)` records, with 1,000 records in every cell.

## Frozen graph and resource definitions

For one execution, the SCN is the directed simple graph containing one permanent
record identity per node and one edge for each distinct compared pair, directed
from the smaller key to the larger key. Repeated comparison events count toward
comparison cost but do not add parallel edges. Tail analysis uses total degree,
`in_degree + out_degree`, so the degree sum is twice the distinct edge count.

- `C` is the number of comparison calls.
- One write of a record to an array position is one movement; a swap of two
  distinct records is two movements. `W` is the movement count.
- `M` is peak auxiliary storage in record-equivalent slots. It includes explicit
  buffers and algorithm-managed stacks and excludes the input array and
  fixed-size scalar variables.
- The information lower bound is `L(n) = log2(n!)`, calculated with log-gamma.

The frozen normalized components and equal-weight score are

```text
c = C / L(n) - 1
w = W / n
s = M / n
Q = c + w + s
eta = 1 / (1 + Q)
```

Higher `eta` means greater combined efficiency. Alternative weights,
transformations, or Pareto-front analyses are allowed only as explicitly labeled
exploratory analyses and cannot replace the confirmatory result.

## Frozen tail and concentration measures

Degree histograms are aggregated over the 1,000 executions within each
algorithm-size cell. The existing fitter:

1. considers positive integer cutoffs leaving at least five distinct degrees;
2. requires at least 50 observations in the fitted tail;
3. estimates the exponent with the discrete continuity correction;
4. chooses `xmin` by minimum KS distance, breaking ties toward smaller `xmin`;
5. reports mean per-tail-observation log-likelihood advantage of the fitted
   power law over a fitted discrete exponential.

Positive PL-Exp LLR favors the power law; negative LLR favors the exponential.
KS, tail fraction, tail span, exponent, and CCDF R-squared are supporting
descriptive measures. `P80` is the smallest fraction of highest-total-degree
nodes accounting for at least 80% of total degree; smaller values mean stronger
concentration. Neither positive LLR nor low `P80` alone is called proof that a
network is scale-free.

## Primary confirmatory analysis

The primary observational units are the 19 algorithms, not the 1,000 input
permutations. The primary endpoint is the Spearman rank correlation, at
`n = 4096`, between:

- predictor: combined efficiency `eta`; and
- outcome: aggregate degree-tail PL-Exp LLR.

The pre-specified direction is positive. Report the coefficient regardless of
its size or sign. For descriptive language, absolute Spearman correlation below
0.4 is weak, 0.4--0.59 is moderate, 0.6--0.79 is strong, and at least 0.8 is very
strong. These labels do not replace uncertainty analysis.

## Pre-specified secondary and sensitivity analyses

Report, without substituting them for the primary endpoint:

1. the same efficiency--LLR Spearman coefficient at all six sizes;
2. whether its direction persists with size; monotonic increase is not required;
3. efficiency versus `-P80`;
4. `-P80` versus PL-Exp LLR;
5. efficiency versus negative tail KS;
6. the primary analysis after excluding the frozen pivot family: Introsort,
   ordinary Quicksort, dual-pivot Quicksort, median-of-three Quicksort, and
   deterministic random-pivot Quicksort;
7. leave-one-family-out coefficients using the family labels below;
8. algorithm-level tables containing `eta`, all three resource components,
   `P80`, LLR, KS, tail fraction, and tail span.

Frozen families for sensitivity analysis are:

- pivot: the five algorithms listed above;
- merge: bottom-up Merge, top-down Merge, and Merge Insertion;
- tree: AVL and unbalanced tree sorts;
- network: Bitonic Network and Odd-Even Merge Network;
- insertion: Insertion and Binary Insertion;
- singleton controls: Bubble, Heap, Selection, Shell, and Tournament.

Family sensitivity is descriptive because the number of families is small.

## Failures, exclusions, and missing data

- No algorithm may be excluded because its result weakens the hypothesis.
- A trial producing an incorrectly sorted output is an implementation failure,
  not missing data. Freeze the affected result, diagnose it, and issue a new
  protocol version before rerunning changed code.
- System interruption is not a scientific exclusion; resume unchanged from the
  checkpoint.
- The primary analysis is not declared complete until every cell has exactly
  1,000 successful trials.
- Duplicate checkpoint keys, mixed tracking profiles, invalid permutations, or
  implementation-hash mismatches invalidate the production run pending audit.

## Required reporting

The paper must report the primary coefficient even if it is smaller than in the
100-seed exploratory experiment. It must also report the pivot-exclusion result,
the full size series, the algorithm count, the 1,000 trials per cell, all
departures from this protocol, and the fact that algorithm families are not
fully independent observations. Causal or universal claims are not permitted
from this experiment alone.

## Implementation identity

The implementation is identified by
`configs/paper-final-code-sha256.txt`. The Git HEAD recorded there is contextual
only because the working tree contained uncommitted files at freeze time. Before
starting or resuming production, verify the hashes from the project root:

```bash
shasum -a 256 -c configs/paper-final-code-sha256.txt
```

Lines beginning with `#` are comments and are ignored by the checksum command.
