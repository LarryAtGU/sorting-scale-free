#!/usr/bin/env python3
"""Produce the frozen concentration and exact-BST validation outputs."""

from __future__ import annotations

import csv
import gzip
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data/results"


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    output = [0.0] * len(values)
    first = 0
    while first < len(values):
        last = first + 1
        while last < len(values) and values[order[last]] == values[order[first]]:
            last += 1
        rank = (first + last + 1) / 2
        for index in range(first, last):
            output[order[index]] = rank
        first = last
    return output


def pearson(left: list[float], right: list[float]) -> float:
    mean_left = sum(left) / len(left)
    mean_right = sum(right) / len(right)
    numerator = sum((x - mean_left) * (y - mean_right) for x, y in zip(left, right))
    denominator = math.sqrt(
        sum((x - mean_left) ** 2 for x in left) * sum((y - mean_right) ** 2 for y in right)
    )
    return numerator / denominator


def spearman(left: list[float], right: list[float]) -> float:
    return pearson(ranks(left), ranks(right))


def family_mean_correlation(
    rows: list[dict[str, str]], family_map: dict[str, str], left_field: str, right_field: str
) -> float:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(family_map[row["algorithm"]], []).append(row)
    left = [sum(float(row[left_field]) for row in group) / len(group) for group in grouped.values()]
    right = [sum(float(row[right_field]) for row in group) / len(group) for group in grouped.values()]
    return spearman(left, right)


def expected_bst_degree_counts(n: int) -> list[float]:
    """Exact expected degree counts from F_n(k)=1[k=n-1]+2/n sum F_s(k-1)."""
    cumulative = [0.0] * n
    current = [0.0] * n
    for size in range(1, n + 1):
        current = [0.0] * n
        current[size - 1] = 1.0
        for degree in range(1, size):
            current[degree] += 2 * cumulative[degree - 1] / size
        for degree in range(size):
            cumulative[degree] += current[degree]
    return current


def ccdf(probabilities: list[float]) -> list[float]:
    remaining = 0.0
    output = [0.0] * len(probabilities)
    for degree in range(len(probabilities) - 1, -1, -1):
        remaining += probabilities[degree]
        output[degree] = remaining
    return output


def fitted_tail(probabilities: list[float], effective_sample_size: int) -> dict[str, float | int]:
    """Apply the manuscript's continuity-corrected KS scan to an exact distribution."""
    degrees = [degree for degree, probability in enumerate(probabilities) if degree > 0 and probability]
    best: tuple[float, int, float] | None = None
    for index, xmin in enumerate(degrees):
        tail_degrees = degrees[index:]
        tail_probability = sum(probabilities[degree] for degree in tail_degrees)
        if effective_sample_size * tail_probability < 50 or len(tail_degrees) < 5:
            continue
        denominator = sum(
            probabilities[degree] * math.log(degree / (xmin - 0.5)) for degree in tail_degrees
        )
        alpha = 1 + tail_probability / denominator
        empirical_remaining = tail_probability
        ks = 0.0
        for degree in tail_degrees:
            empirical_ccdf = empirical_remaining / tail_probability
            model_ccdf = ((degree - 0.5) / (xmin - 0.5)) ** (1 - alpha)
            ks = max(ks, abs(empirical_ccdf - model_ccdf))
            empirical_remaining -= probabilities[degree]
        candidate = (ks, xmin, alpha)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    if best is None:
        raise ValueError("exact distribution has no eligible tail")
    ks, xmin, alpha = best
    return {"xmin": xmin, "alpha": alpha, "ks": ks}


def ks_distance(left: list[float], right: list[float]) -> float:
    left_cdf = right_cdf = 0.0
    distance = 0.0
    for left_value, right_value in zip(left, right):
        left_cdf += left_value
        right_cdf += right_value
        distance = max(distance, abs(left_cdf - right_cdf))
    return distance


def main() -> None:
    summary = [
        row
        for row in csv.DictReader(
            (RESULTS / "batch-paper-final-19-algorithms-summary.csv").open(encoding="utf-8")
        )
        if int(row["n"]) == 4096
    ]
    validation = json.loads((RESULTS / "paper-final-statistical-validation.json").read_text())
    llr_by_algorithm = {
        row["algorithm"]: row["power_vs_exponential_llr_per_observation"]
        for row in validation["tail_validation"]
    }
    for row in summary:
        row["power_vs_exponential_llr_per_observation"] = str(llr_by_algorithm[row["algorithm"]])
    comparison_efficiency = [-float(row["normalized_excess_comparisons_mean"]) for row in summary]
    combined_efficiency = [float(row["combined_efficiency_equal_weights_mean"]) for row in summary]
    degree_gini = [float(row["degree_gini_mean"]) for row in summary]
    negative_p80 = [-float(row["degree_p80_fraction_mean"]) for row in summary]

    mechanism_families = {
        "quick": "pivot",
        "quick-dual-pivot": "pivot",
        "quick-median-three": "pivot",
        "quick-random": "pivot",
        "introsort": "pivot",
        "tree-unbalanced": "tree",
        "tree-avl": "tree",
        "merge-bottom-up": "merge-tournament",
        "merge-top-down": "merge-tournament",
        "tournament": "merge-tournament",
        "bitonic-network": "network",
        "odd-even-merge-network": "network",
        "bubble": "adjacent-exchange",
        "insertion": "adjacent-exchange",
        "binary-insertion": "chain-insertion",
        "merge-insertion": "chain-insertion",
        "heap": "heap",
        "shell": "shell",
        "selection": "selection",
    }

    identity_pairs = [
        ("bubble", "insertion"),
        ("merge-bottom-up", "merge-top-down"),
        ("merge-bottom-up", "tournament"),
    ]
    cache: dict[tuple[str, int, int], dict[str, int]] = {}
    with gzip.open(RESULTS / "batch-paper-final-19-algorithms-runs.jsonl.gz", "rt") as stream:
        for line in stream:
            record = json.loads(line)
            if any(record["algorithm"] in pair for pair in identity_pairs):
                cache[record["algorithm"], record["n"], record["seed"]] = record["degree_histogram"]
    equivalence = []
    for first, second in identity_pairs:
        keys = {(n, seed) for algorithm, n, seed in cache if algorithm == first} & {
            (n, seed) for algorithm, n, seed in cache if algorithm == second
        }
        matches = sum(cache[first, n, seed] == cache[second, n, seed] for n, seed in keys)
        equivalence.append(
            {"first": first, "second": second, "matches": matches, "cells": len(keys)}
        )

    row = next(item for item in summary if item["algorithm"] == "tree-unbalanced")
    histogram = {int(k): int(v) for k, v in json.loads(row["aggregate_degree_histogram"]).items()}
    total = sum(histogram.values())
    empirical = [histogram.get(degree, 0) / total for degree in range(4096)]
    expected_counts = expected_bst_degree_counts(4096)
    expected = [count / 4096 for count in expected_counts]
    empirical_cdf = []
    expected_cdf = []
    left = right = 0.0
    for x, y in zip(empirical, expected):
        left += x
        right += y
        empirical_cdf.append(left)
        expected_cdf.append(right)
    ks = max(abs(x - y) for x, y in zip(empirical_cdf, expected_cdf))
    exact_tail_fits = []
    for size in (128, 256, 512, 1024, 2048, 4096):
        probabilities = [count / size for count in expected_bst_degree_counts(size)]
        exact_tail_fits.append({"n": size, **fitted_tail(probabilities, 1000 * size)})

    temporal_rows = list(
        csv.DictReader((RESULTS / "temporal-mechanism-v1/summary.csv").open(encoding="utf-8"))
    )
    temporal_1024 = [row for row in temporal_rows if int(row["n"]) == 1024]
    exact_1024 = [count / 1024 for count in expected_bst_degree_counts(1024)]
    algorithm_bst_ks = []
    for item in temporal_1024:
        histogram = json.loads(item["aggregate_degree_histogram"])
        denominator = sum(int(value) for value in histogram.values())
        probabilities = [int(histogram.get(str(degree), 0)) / denominator for degree in range(1024)]
        algorithm_bst_ks.append(
            {"algorithm": item["algorithm"], "ks_against_exact_bst": ks_distance(probabilities, exact_1024)}
        )

    bst_runs = []
    with gzip.open(RESULTS / "temporal-mechanism-v1/runs.jsonl.gz", "rt") as stream:
        for line in stream:
            record = json.loads(line)
            if record["algorithm"] == "tree-unbalanced" and record["n"] == 1024:
                histogram = record["degree_histogram"]
                bst_runs.append([int(histogram.get(str(degree), 0)) for degree in range(1024)])
    generator = random.Random(20260916)
    bootstrap_ks = []
    for _ in range(500):
        aggregate = [0] * 1024
        for _ in range(len(bst_runs)):
            selected = bst_runs[generator.randrange(len(bst_runs))]
            aggregate = [left + right for left, right in zip(aggregate, selected)]
        denominator = sum(aggregate)
        bootstrap_ks.append(
            ks_distance([value / denominator for value in aggregate], exact_1024)
        )
    bootstrap_ks.sort()

    lifetime_results = []
    for item in temporal_1024:
        if float(item["representative_node_fraction_mean"]) > 0:
            lifetime_results.append(
                {
                    "algorithm": item["algorithm"],
                    "mean_representative_lifetime_fraction": float(
                        item["mean_representative_lifetime_fraction_mean"]
                    ),
                    "mean_represented_span": float(item["mean_represented_span_mean"]),
                    "mean_span_degree_correlation": float(item["mean_span_degree_correlation_mean"]),
                }
            )

    output = {
        "schema_version": 1,
        "n": 4096,
        "concentration_correlations": {
            "comparison_efficiency_vs_degree_gini": spearman(comparison_efficiency, degree_gini),
            "comparison_efficiency_vs_negative_p80": spearman(comparison_efficiency, negative_p80),
            "combined_efficiency_vs_degree_gini": spearman(combined_efficiency, degree_gini),
            "combined_efficiency_vs_negative_p80": spearman(combined_efficiency, negative_p80),
        },
        "degree_histogram_equivalence": equivalence,
        "nine_family_sensitivity": {
            "family_count": len(set(mechanism_families.values())),
            "combined_efficiency_vs_pl_exp_llr": family_mean_correlation(
                summary,
                mechanism_families,
                "combined_efficiency_equal_weights_mean",
                "power_vs_exponential_llr_per_observation",
            ),
            "combined_efficiency_vs_degree_gini": family_mean_correlation(
                summary,
                mechanism_families,
                "combined_efficiency_equal_weights_mean",
                "degree_gini_mean",
            ),
            "combined_efficiency_vs_negative_p80": spearman(
                [
                    sum(float(row["combined_efficiency_equal_weights_mean"]) for row in group)
                    / len(group)
                    for group in {
                        family: [row for row in summary if mechanism_families[row["algorithm"]] == family]
                        for family in dict.fromkeys(mechanism_families.values())
                    }.values()
                ],
                [
                    -sum(float(row["degree_p80_fraction_mean"]) for row in group) / len(group)
                    for group in {
                        family: [row for row in summary if mechanism_families[row["algorithm"]] == family]
                        for family in dict.fromkeys(mechanism_families.values())
                    }.values()
                ],
            ),
        },
        "exact_bst_full_distribution_ks": ks,
        "exact_bst_expected_count_sum": sum(expected_counts),
        "exact_bst_tail_fits": exact_tail_fits,
        "temporal_n1024_ks_against_exact_bst": algorithm_bst_ks,
        "bst_aggregate_200_run_bootstrap_ks_95_interval": [
            bootstrap_ks[12],
            bootstrap_ks[487],
        ],
        "representative_lifetime_n1024": lifetime_results,
    }
    path = RESULTS / "paper-theory-validation.json"
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(path)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
