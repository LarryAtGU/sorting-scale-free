"""Descriptive evidence measures for discrete power-law degree tails."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PowerLawTailMeasures:
    alpha: float
    xmin: int
    tail_count: int
    tail_fraction: float
    tail_span_decades: float
    ks_distance: float
    loglog_ccdf_r_squared: float
    power_vs_exponential_llr_per_observation: float

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _weighted_histogram(histogram: dict[int, int] | Iterable[tuple[int, int]]) -> dict[int, int]:
    source = histogram.items() if isinstance(histogram, dict) else histogram
    result = {int(degree): int(count) for degree, count in source if int(count) > 0}
    if not result or any(degree < 0 for degree in result):
        raise ValueError("histogram must contain positive counts at nonnegative degrees")
    return result


def _continuous_alpha(tail: list[tuple[int, int]], xmin: int) -> float:
    count = sum(value for _, value in tail)
    denominator = sum(value * math.log(degree / (xmin - 0.5)) for degree, value in tail)
    return 1.0 + count / denominator if denominator > 0 else math.inf


def _power_law_ks(tail: list[tuple[int, int]], xmin: int, alpha: float) -> float:
    count = sum(value for _, value in tail)
    remaining = count
    maximum = 0.0
    scale = xmin - 0.5
    for degree, frequency in tail:
        empirical = remaining / count
        model = ((degree - 0.5) / scale) ** (1.0 - alpha)
        maximum = max(maximum, abs(empirical - model))
        remaining -= frequency
    return maximum


def _linear_r_squared(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    mean_x = sum(x for x, _ in points) / len(points)
    mean_y = sum(y for _, y in points) / len(points)
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in points)
    variance_x = sum((x - mean_x) ** 2 for x, _ in points)
    variance_y = sum((y - mean_y) ** 2 for _, y in points)
    if variance_x == 0 or variance_y == 0:
        return 0.0
    return covariance**2 / (variance_x * variance_y)


def _hurwitz_zeta(alpha: float, xmin: int) -> float:
    """Accurate-enough Hurwitz zeta using summation and Euler-Maclaurin tail."""
    terms = 4096
    total = sum((xmin + offset) ** -alpha for offset in range(terms))
    boundary = xmin + terms
    tail = boundary ** (1 - alpha) / (alpha - 1)
    tail += 0.5 * boundary**-alpha
    tail += alpha / 12 * boundary ** (-alpha - 1)
    tail -= alpha * (alpha + 1) * (alpha + 2) / 720 * boundary ** (-alpha - 3)
    return total + tail


def _likelihood_ratio(tail: list[tuple[int, int]], xmin: int, alpha: float) -> float:
    count = sum(frequency for _, frequency in tail)
    log_zeta = math.log(_hurwitz_zeta(alpha, xmin))
    power_log_likelihood = sum(
        frequency * (-alpha * math.log(degree) - log_zeta) for degree, frequency in tail
    )
    mean_offset = sum((degree - xmin) * frequency for degree, frequency in tail) / count
    if mean_offset == 0:
        return -math.inf
    geometric_q = mean_offset / (mean_offset + 1)
    exponential_log_likelihood = sum(
        frequency
        * (math.log1p(-geometric_q) + (degree - xmin) * math.log(geometric_q))
        for degree, frequency in tail
    )
    return (power_log_likelihood - exponential_log_likelihood) / count


def fit_power_law_tail(
    histogram: dict[int, int] | Iterable[tuple[int, int]],
    *,
    minimum_tail_count: int = 50,
    minimum_distinct_degrees: int = 5,
) -> PowerLawTailMeasures:
    """Choose xmin by minimum KS distance and return tail evidence measures.

    The exponent estimator uses the standard discrete continuity correction.
    These measures are descriptive; a later bootstrap stage will attach formal
    goodness-of-fit probabilities and comparisons with additional alternatives.
    """
    values = _weighted_histogram(histogram)
    total_count = sum(values.values())
    positive_degrees = sorted(degree for degree in values if degree > 0)
    candidates = positive_degrees[: -(minimum_distinct_degrees - 1)]
    fits: list[tuple[float, int, float, list[tuple[int, int]]]] = []
    for xmin in candidates:
        tail = [(degree, values[degree]) for degree in positive_degrees if degree >= xmin]
        tail_count = sum(frequency for _, frequency in tail)
        if tail_count < minimum_tail_count:
            continue
        alpha = _continuous_alpha(tail, xmin)
        if math.isfinite(alpha) and alpha > 1:
            fits.append((_power_law_ks(tail, xmin, alpha), xmin, alpha, tail))
    if not fits:
        raise ValueError("insufficient distinct positive degrees for a power-law tail fit")

    ks_distance, xmin, alpha, tail = min(fits, key=lambda fit: (fit[0], fit[1]))
    tail_count = sum(frequency for _, frequency in tail)
    maximum_degree = tail[-1][0]
    remaining = tail_count
    ccdf_points = []
    for degree, frequency in tail:
        ccdf_points.append((math.log(degree), math.log(remaining / tail_count)))
        remaining -= frequency
    return PowerLawTailMeasures(
        alpha=alpha,
        xmin=xmin,
        tail_count=tail_count,
        tail_fraction=tail_count / total_count,
        tail_span_decades=math.log10(maximum_degree / xmin),
        ks_distance=ks_distance,
        loglog_ccdf_r_squared=_linear_r_squared(ccdf_points),
        power_vs_exponential_llr_per_observation=_likelihood_ratio(tail, xmin, alpha),
    )
