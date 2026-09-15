# Pair-selection mechanism measures

These measures describe how a sorting algorithm chooses comparison pairs. They
are computed online by the common comparison tracker and do not depend on an
algorithm-specific implementation.

## Rank distance

For a comparison edge `e={u,v}`, rank distance is
`l(e)=|rank(u)-rank(v)|` in the final sorted order. The normalized value divides
by `n-1`. A distance-one comparison is a critical adjacent-rank comparison. A
long-range comparison has normalized distance at least one half. The tracker
reports their histogram, mean, critical fraction, and long-range fraction.

## Information gain

Information gain is the number of previously unknown ordered pairs added by a
comparison after transitive closure. A repeated or already-implied comparison
has gain zero. For a completed distinct-key sort, the gains sum to `n(n-1)/2`.
The tracker reports the histogram, mean, maximum, and fraction of comparisons
with gain greater than one.

## Active links

Active links are the cover relations in the current partial order, equivalently
the edges of its transitive reduction. If a new comparison retires `r_t`
existing cover edges, then `H_t=H_(t-1)+1-r_t` for a non-implied comparison.
The tracker reports final, maximum, and mean active-link counts, total retired
links, the maximum retired by one comparison, and the fraction of comparison
steps that retire links. `H_max / floor(n^2/4)` normalizes the maximum against
the sharp general Hasse-diagram bound.

## Endpoint reuse

Comparison participation counts every time a record is used as either endpoint,
including repeated comparisons. The summaries report participation Gini, the
fraction of comparisons involving the busiest record, and the share of all
comparison endpoints assigned to the busiest ten percent of records.

These mechanism measures should be analyzed alongside comparison efficiency and
degree-tail evidence. Rank distance describes comparison scale, while endpoint
concentration distinguishes distributed hierarchy from persistent representative
reuse.

## Operational and organizational resource costs

The experiment also records costs outside comparison count. A record movement is
one write of a record into an array position; consequently, exchanging two
records counts as two movements. Peak auxiliary storage is the greatest number
of record-equivalent temporary slots held simultaneously. It includes explicit
buffers and algorithm-managed stacks, but excludes fixed-size scalar variables
and the input array itself. Mean auxiliary storage is sampled at comparison
boundaries.

For input size `n`, the normalized components are comparison excess
`c=C/log2(n!)-1`, movements per node `w=W/n`, and peak storage fraction `m=M/n`.
The exploratory equal-weight score is `Q=c+w+m`, with efficiency
`E=1/(1+Q)`. This score is not claimed as a universal physical law: all three
components remain available so alternative weights and normalizations can be
tested rather than hidden inside one arbitrary index.
