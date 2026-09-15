#!/usr/bin/env python3
"""Run the frozen post-confirmatory validation and write machine-readable results."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path

from scn_sorting.analysis.powerlaw import fit_power_law_tail
from scn_sorting.analysis.tail_validation import (
    bootstrap_power_law_gof,
    fit_alternative_tails,
)

WEIGHTS = [0, 0.1, 0.25, 0.5, 1, 2, 4]
PIVOTS = {"introsort", "quick", "quick-dual-pivot", "quick-median-three", "quick-random"}


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index + 1
        while end < len(order) and values[order[end]] == values[order[index]]:
            end += 1
        rank = (index + end - 1) / 2 + 1
        for position in order[index:end]:
            result[position] = rank
        index = end
    return result


def pearson(left: list[float], right: list[float]) -> float:
    lm, rm = statistics.fmean(left), statistics.fmean(right)
    numerator = sum((x - lm) * (y - rm) for x, y in zip(left, right))
    denominator = math.sqrt(sum((x - lm) ** 2 for x in left) * sum((y - rm) ** 2 for y in right))
    return numerator / denominator if denominator else math.nan


def spearman(left: list[float], right: list[float]) -> float:
    return pearson(ranks(left), ranks(right))


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    fraction = position - lower
    return ordered[lower] if lower + 1 == len(ordered) else ordered[lower] * (1 - fraction) + ordered[lower + 1] * fraction


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/results/batch-paper-final-19-algorithms-summary.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/results/paper-final-statistical-validation.json"))
    parser.add_argument("--bootstrap-replicates", type=int, default=250)
    args = parser.parse_args()
    rows = list(csv.DictReader(args.input.open(encoding="utf-8")))
    primary = [row for row in rows if int(row["n"]) == 4096]
    if len(primary) != 19 or any(int(row["trials"]) != 1000 for row in primary):
        raise ValueError("expected all 19 algorithms with 1,000 trials at n=4096")

    tails = []
    for number, row in enumerate(primary, 1):
        algorithm = row["algorithm"]
        histogram = {int(key): int(value) for key, value in json.loads(row["aggregate_degree_histogram"]).items()}
        power = fit_power_law_tail(histogram)
        alternatives = fit_alternative_tails(histogram, power.xmin, power.alpha)
        p_boot, successful, effective_size = bootstrap_power_law_gof(
            histogram,
            replicates=args.bootstrap_replicates,
            seed_text=f"scn-tail-bootstrap-v1:{algorithm}:4096",
        )
        print(f"[{number:02d}/19] {algorithm}: p_boot={p_boot:.3f}", flush=True)
        tails.append({
            "algorithm": algorithm,
            "xmin": power.xmin,
            "alpha": power.alpha,
            "tail_count": power.tail_count,
            "tail_fraction": power.tail_fraction,
            "ks": power.ks_distance,
            "power_vs_exponential_llr_per_observation": power.power_vs_exponential_llr_per_observation,
            **alternatives.as_dict(),
            "power_law_bootstrap_p": p_boot,
            "bootstrap_successful_replicates": successful,
            "bootstrap_effective_sample_size": effective_size,
        })

    llr = [fit_power_law_tail({int(k): int(v) for k, v in json.loads(row["aggregate_degree_histogram"]).items()}).power_vs_exponential_llr_per_observation for row in primary]
    efficiency = [float(row["combined_efficiency_equal_weights_mean"]) for row in primary]
    observed_rho = spearman(efficiency, llr)
    rng = random.Random("scn-algorithm-bootstrap-v1")
    boot = []
    while len(boot) < 10_000:
        indices = [rng.randrange(len(primary)) for _ in primary]
        rho = spearman([efficiency[i] for i in indices], [llr[i] for i in indices])
        if math.isfinite(rho):
            boot.append(rho)

    surfaces = {}
    for label, selected in (("full", list(range(19))), ("pivot_excluded", [i for i, row in enumerate(primary) if row["algorithm"] not in PIVOTS])):
        cells = []
        for a in WEIGHTS:
            for b in WEIGHTS:
                eta = []
                outcome = []
                for i in selected:
                    row = primary[i]
                    c = float(row["normalized_excess_comparisons_mean"])
                    w = float(row["movements_per_node_mean"])
                    s = float(row["peak_auxiliary_storage_fraction_mean"])
                    eta.append(1 / (1 + c + a * math.log1p(w) + b * math.log1p(s)))
                    outcome.append(llr[i])
                cells.append({"movement_weight": a, "storage_weight": b, "spearman": spearman(eta, outcome)})
        values = [cell["spearman"] for cell in cells]
        surfaces[label] = {"cells": cells, "minimum": min(values), "median": statistics.median(values), "maximum": max(values), "fraction_at_least_0_6": sum(value >= 0.6 for value in values) / len(values)}

    trends = []
    for n in sorted({int(row["n"]) for row in rows}):
        selected = [row for row in rows if int(row["n"]) == n]
        x = [float(row["combined_efficiency_equal_weights_mean"]) for row in selected]
        y = [fit_power_law_tail({int(k): int(v) for k, v in json.loads(row["aggregate_degree_histogram"]).items()}).power_vs_exponential_llr_per_observation for row in selected]
        trends.append({"n": n, "spearman": spearman(x, y)})

    document = {
        "schema_version": 1,
        "protocol": "docs/statistical-validation-protocol.md",
        "input": str(args.input),
        "primary": {"n": 4096, "algorithm_count": 19, "spearman": observed_rho, "descriptive_bootstrap_replicates": 10000, "descriptive_bootstrap_95_percentile_interval": [percentile(boot, 0.025), percentile(boot, 0.975)]},
        "correlation_by_n": trends,
        "tail_validation": tails,
        "resource_weight_sensitivity": surfaces,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
