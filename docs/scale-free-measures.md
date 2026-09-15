# Measures of scale-free tail evidence

CV and Gini quantify degree heterogeneity. They do not establish that the upper tail follows a power law. The first-stage analysis therefore reports a collection of complementary tail measures rather than a single "scale-free score."

- **Tail exponent (alpha):** the fitted slope parameter in `P(D=k) proportional to k^-alpha`. It describes the tail's rate of decay, but is not a goodness-of-fit measure.
- **Lower cutoff (x-min):** the smallest degree included in the fitted tail. It is selected by minimizing the Kolmogorov–Smirnov distance among eligible cutoffs.
- **Tail count and fraction:** the number and proportion of observations at or above x-min. A good fit covering only a tiny fraction is weak evidence for a generally scale-free network.
- **Tail span:** `log10(max_degree / x-min)`. This reports how many orders of magnitude the fitted tail covers. A visually straight but very short range is weak evidence.
- **Tail KS distance:** the maximum distance between the empirical and fitted tail CCDFs. Smaller values indicate closer agreement.
- **Log-log CCDF R-squared:** descriptive straightness of the empirical fitted-tail CCDF. Larger is straighter, but R-squared alone is not a valid power-law test.
- **Power-law versus exponential log-likelihood advantage:** the mean per-tail-observation log-likelihood difference. Positive values favor the fitted power law; negative values favor the fitted discrete exponential.

The measures must be interpreted jointly. Stronger descriptive evidence consists of a small KS distance, positive likelihood advantage, substantial tail coverage, a reasonably long span, and a high CCDF R-squared. Alpha supplies the shape only.

These aggregate-distribution measures are exploratory. The confirmatory analysis will add a parametric-bootstrap goodness-of-fit p-value, uncertainty intervals, comparisons with lognormal and stretched-exponential alternatives, and execution-level robustness checks.

## Pareto degree concentration

Let `d_(1) >= ... >= d_(n)` be the node degrees and let
`m = sum_i d_(i)` be total degree. Define

`k_80 = min { k : sum_(i=1)^k d_(i) >= 0.8 m }`

and `P80 = k_80 / n`. This is the smallest fraction of highest-degree nodes
needed to account for at least 80% of total degree. Smaller values indicate
stronger concentration: `P80 = 0.2` is an 80/20 pattern, below `0.2` is more
concentrated, and a uniform positive degree sequence gives approximately `0.8`.

`P80` measures concentration rather than proving a power law, so it should be
reported alongside tail fit, tail extent, and distribution-comparison evidence.
