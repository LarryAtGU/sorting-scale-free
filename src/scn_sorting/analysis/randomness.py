"""Statistical diagnostics for ensembles of random permutations."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from itertools import pairwise
from statistics import NormalDist


def normal_two_sided_p(z: float) -> float:
    return 2.0 * NormalDist().cdf(-abs(z))


def _regularized_gamma_q(shape: float, value: float) -> float:
    """Regularized upper incomplete gamma Q(shape, value)."""
    if shape <= 0 or value < 0:
        raise ValueError("shape must be positive and value nonnegative")
    if value == 0:
        return 1.0
    epsilon = 1e-14
    tiny = 1e-300
    maximum_iterations = 10_000
    log_scale = shape * math.log(value) - value - math.lgamma(shape)

    if value < shape + 1:
        term = 1.0 / shape
        total = term
        argument = shape
        for _ in range(maximum_iterations):
            argument += 1.0
            term *= value / argument
            total += term
            if abs(term) <= abs(total) * epsilon:
                return min(1.0, max(0.0, 1.0 - total * math.exp(log_scale)))
        raise ArithmeticError("gamma series did not converge")

    b = value + 1.0 - shape
    c = 1.0 / tiny
    d = 1.0 / b
    fraction = d
    for iteration in range(1, maximum_iterations + 1):
        coefficient = -iteration * (iteration - shape)
        b += 2.0
        d = coefficient * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + coefficient / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        fraction *= delta
        if abs(delta - 1.0) <= epsilon:
            return min(1.0, max(0.0, math.exp(log_scale) * fraction))
    raise ArithmeticError("gamma continued fraction did not converge")


def chi_square_p(statistic: float, degrees_of_freedom: int) -> float:
    if degrees_of_freedom <= 0:
        raise ValueError("degrees_of_freedom must be positive")
    if statistic < 0:
        raise ValueError("statistic must be nonnegative")
    return _regularized_gamma_q(degrees_of_freedom / 2.0, statistic / 2.0)


def chi_square(observed: Sequence[float], expected: Sequence[float]) -> tuple[float, float]:
    if len(observed) != len(expected) or len(observed) < 2:
        raise ValueError("observed and expected must have equal length of at least two")
    if any(value <= 0 for value in expected):
        raise ValueError("expected counts must be positive")
    statistic = sum((actual - target) ** 2 / target for actual, target in zip(observed, expected))
    return statistic, chi_square_p(statistic, len(observed) - 1)


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    """Return Holm-Bonferroni adjusted p-values in original order."""
    count = len(p_values)
    adjusted = [1.0] * count
    running_maximum = 0.0
    for rank, index in enumerate(sorted(range(count), key=p_values.__getitem__)):
        candidate = min(1.0, (count - rank) * p_values[index])
        running_maximum = max(running_maximum, candidate)
        adjusted[index] = running_maximum
    return adjusted


def inversion_count(permutation: Sequence[int]) -> int:
    tree = [0] * (len(permutation) + 1)

    def prefix_sum(index: int) -> int:
        total = 0
        while index:
            total += tree[index]
            index -= index & -index
        return total

    inversions = 0
    for seen, value in enumerate(permutation):
        tree_index = value + 1
        inversions += seen - prefix_sum(tree_index)
        while tree_index < len(tree):
            tree[tree_index] += 1
            tree_index += tree_index & -tree_index
    return inversions


def descent_count(permutation: Sequence[int]) -> int:
    return sum(left > right for left, right in pairwise(permutation))


def fixed_point_count(permutation: Sequence[int]) -> int:
    return sum(index == value for index, value in enumerate(permutation))


def pearson_correlation(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("correlation inputs must have equal length of at least two")
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_scale = sum((x - left_mean) ** 2 for x in left)
    right_scale = sum((y - right_mean) ** 2 for y in right)
    if left_scale == 0 or right_scale == 0:
        return 0.0
    return numerator / math.sqrt(left_scale * right_scale)


@dataclass(frozen=True)
class Diagnostic:
    name: str
    statistic: float
    p_value: float
    adjusted_p_value: float = 1.0
    details: dict[str, float | int | str] | None = None


def _mean_test(
    name: str,
    values: Sequence[float],
    expected_mean: float,
    population_variance: float,
) -> Diagnostic:
    observed_mean = sum(values) / len(values)
    standard_error = math.sqrt(population_variance / len(values))
    z_score = (observed_mean - expected_mean) / standard_error
    return Diagnostic(
        name=name,
        statistic=z_score,
        p_value=normal_two_sided_p(z_score),
        details={"observed_mean": observed_mean, "expected_mean": expected_mean},
    )


def _selected_values(n: int, count: int = 32) -> list[int]:
    return sorted({round(index * (n - 1) / (min(count, n) - 1)) for index in range(min(count, n))})


def diagnose_permutation_ensemble(
    permutations: Sequence[Sequence[int]],
    *,
    alpha: float = 0.01,
    position_bins: int = 16,
) -> dict[str, object]:
    """Diagnose an ensemble expected to contain uniform independent permutations."""
    if not permutations:
        raise ValueError("at least one permutation is required")
    n = len(permutations[0])
    trial_count = len(permutations)
    if any(len(permutation) != n for permutation in permutations):
        raise ValueError("all permutations must have the same length")
    if position_bins < 2 or trial_count / position_bins < 5:
        raise ValueError("position bins must give at least five expected observations per bin")

    inversions = [inversion_count(permutation) for permutation in permutations]
    descents = [descent_count(permutation) for permutation in permutations]
    fixed_points = [fixed_point_count(permutation) for permutation in permutations]

    diagnostics = [
        _mean_test(
            "inversion_mean",
            inversions,
            n * (n - 1) / 4,
            n * (n - 1) * (2 * n + 5) / 72,
        ),
        _mean_test("descent_mean", descents, (n - 1) / 2, (n + 1) / 12),
        _mean_test("fixed_point_mean", fixed_points, 1.0, 1.0),
    ]

    # Test marginal position uniformity for deterministically selected record IDs.
    for value in _selected_values(n):
        observed = [0] * position_bins
        for permutation in permutations:
            position = permutation.index(value)
            observed[min(position * position_bins // n, position_bins - 1)] += 1
        expected = [trial_count / position_bins] * position_bins
        statistic, p_value = chi_square(observed, expected)
        diagnostics.append(
            Diagnostic(
                name=f"position_uniformity_value_{value}",
                statistic=statistic,
                p_value=p_value,
                details={"bins": position_bins},
            )
        )

    # The fixed-point distribution converges rapidly to Poisson(1).
    observed_fixed = [0] * 5
    for count in fixed_points:
        observed_fixed[min(count, 4)] += 1
    probabilities = [math.exp(-1) / math.factorial(k) for k in range(4)]
    probabilities.append(1.0 - sum(probabilities))
    statistic, p_value = chi_square(
        observed_fixed, [trial_count * probability for probability in probabilities]
    )
    diagnostics.append(
        Diagnostic("fixed_point_distribution", statistic, p_value, details={"tail_bin": "4+"})
    )

    # Adjacent seeds should not generate correlated permutations. Comparing rank
    # vectors is a Spearman correlation because values and positions are ranks.
    pair_count = min(50, trial_count // 2)
    for pair_index in range(pair_count):
        left = permutations[2 * pair_index]
        right = permutations[2 * pair_index + 1]
        correlation = pearson_correlation(left, right)
        z_score = correlation * math.sqrt(max(1, n - 1))
        diagnostics.append(
            Diagnostic(
                name=f"cross_trial_rank_correlation_{2 * pair_index + 1}_{2 * pair_index + 2}",
                statistic=correlation,
                p_value=normal_two_sided_p(z_score),
            )
        )

    adjusted = holm_adjust([diagnostic.p_value for diagnostic in diagnostics])
    completed = [
        Diagnostic(
            name=diagnostic.name,
            statistic=diagnostic.statistic,
            p_value=diagnostic.p_value,
            adjusted_p_value=adjusted[index],
            details=diagnostic.details,
        )
        for index, diagnostic in enumerate(diagnostics)
    ]
    warnings = [item.name for item in completed if item.adjusted_p_value < alpha]
    return {
        "n": n,
        "trial_count": trial_count,
        "alpha": alpha,
        "multiple_testing_correction": "Holm-Bonferroni",
        "status": "warning" if warnings else "pass",
        "warnings": warnings,
        "diagnostics": [asdict(item) for item in completed],
        "summaries": {
            "inversion_sample_variance": _sample_variance(inversions),
            "inversion_expected_variance": n * (n - 1) * (2 * n + 5) / 72,
            "descent_sample_variance": _sample_variance(descents),
            "descent_expected_variance": (n + 1) / 12,
            "fixed_point_sample_variance": _sample_variance(fixed_points),
            "fixed_point_expected_variance": 1.0,
        },
    }


def _sample_variance(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / (len(values) - 1)
