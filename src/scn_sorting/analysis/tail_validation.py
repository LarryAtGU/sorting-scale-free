"""Post-confirmatory tail-model validation for aggregate degree histograms."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass

import numpy as np

from scn_sorting.analysis.powerlaw import (
    PowerLawTailMeasures,
    _hurwitz_zeta,
    _likelihood_ratio,
    _linear_r_squared,
    fit_power_law_tail,
)


@dataclass(frozen=True)
class AlternativeTailMeasures:
    power_vs_lognormal_llr_per_observation: float
    power_vs_stretched_exponential_llr_per_observation: float
    lognormal_mu: float
    lognormal_sigma: float
    stretched_exponential_scale: float
    stretched_exponential_shape: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class FinitePowerLawMeasures:
    alpha: float
    finite_vs_unbounded_power_llr_per_observation: float
    finite_power_vs_exponential_llr_per_observation: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


def _logdiffexp(larger: float, smaller: float) -> float:
    if smaller >= larger:
        return -math.inf
    return larger + math.log1p(-math.exp(smaller - larger))


def _normal_cdf(value: float) -> float:
    return 0.5 * math.erfc(-value / math.sqrt(2))


def _normal_survival(value: float) -> float:
    return 0.5 * math.erfc(value / math.sqrt(2))


def _nelder_mead(
    objective: Callable[[tuple[float, float]], float],
    start: tuple[float, float],
    *,
    step: float = 0.25,
    iterations: int = 300,
) -> tuple[float, float]:
    cache: dict[tuple[float, float], float] = {}

    def evaluate(point: tuple[float, float]) -> float:
        if point not in cache:
            cache[point] = objective(point)
        return cache[point]

    simplex = [start, (start[0] + step, start[1]), (start[0], start[1] + step)]
    for _ in range(iterations):
        simplex.sort(key=evaluate)
        best, middle, worst = simplex
        centroid = ((best[0] + middle[0]) / 2, (best[1] + middle[1]) / 2)
        reflected = (2 * centroid[0] - worst[0], 2 * centroid[1] - worst[1])
        if evaluate(reflected) < evaluate(best):
            expanded = (
                centroid[0] + 2 * (reflected[0] - centroid[0]),
                centroid[1] + 2 * (reflected[1] - centroid[1]),
            )
            simplex[-1] = expanded if evaluate(expanded) < evaluate(reflected) else reflected
        elif evaluate(reflected) < evaluate(middle):
            simplex[-1] = reflected
        else:
            contracted = (
                centroid[0] + 0.5 * (worst[0] - centroid[0]),
                centroid[1] + 0.5 * (worst[1] - centroid[1]),
            )
            if evaluate(contracted) < evaluate(worst):
                simplex[-1] = contracted
            else:
                simplex = [best] + [
                    (
                        best[0] + 0.5 * (point[0] - best[0]),
                        best[1] + 0.5 * (point[1] - best[1]),
                    )
                    for point in simplex[1:]
                ]
        spread = max(math.dist(simplex[0], point) for point in simplex[1:])
        if spread < 1e-8:
            break
    return min(simplex, key=evaluate)


def fit_finite_power_law(
    histogram: dict[int, int], xmin: int, maximum: int
) -> FinitePowerLawMeasures:
    """Fit a power law normalized on the known finite support [xmin, maximum]."""
    tail = sorted((int(k), int(v)) for k, v in histogram.items() if xmin <= k <= maximum and v)
    count = sum(frequency for _, frequency in tail)
    log_sum = sum(frequency * math.log(degree) for degree, frequency in tail)
    support_logs = np.log(np.arange(xmin, maximum + 1, dtype=float))

    def negative_likelihood(alpha: float) -> float:
        terms = -alpha * support_logs
        largest = float(np.max(terms))
        log_normalization = largest + math.log(float(np.exp(terms - largest).sum()))
        return alpha * log_sum + count * log_normalization

    left, right = 1.000001, 200.0
    ratio = (math.sqrt(5) - 1) / 2
    x1, x2 = right - ratio * (right - left), left + ratio * (right - left)
    f1, f2 = negative_likelihood(x1), negative_likelihood(x2)
    for _ in range(120):
        if f1 < f2:
            right, x2, f2 = x2, x1, f1
            x1 = right - ratio * (right - left); f1 = negative_likelihood(x1)
        else:
            left, x1, f1 = x1, x2, f2
            x2 = left + ratio * (right - left); f2 = negative_likelihood(x2)
    alpha = (left + right) / 2
    finite_ll = -negative_likelihood(alpha)
    unbounded_alpha = 1 + count / sum(
        frequency * math.log(degree / (xmin - 0.5)) for degree, frequency in tail
    )
    unbounded_ll = -unbounded_alpha * log_sum - count * math.log(
        _hurwitz_zeta(unbounded_alpha, xmin)
    )
    mean_offset = sum((degree - xmin) * frequency for degree, frequency in tail) / count
    if mean_offset:
        q = mean_offset / (mean_offset + 1)
        exponential_ll = sum(
            frequency * (math.log1p(-q) + (degree - xmin) * math.log(q))
            for degree, frequency in tail
        )
    else:
        exponential_ll = math.inf
    return FinitePowerLawMeasures(
        alpha=alpha,
        finite_vs_unbounded_power_llr_per_observation=(finite_ll - unbounded_ll) / count,
        finite_power_vs_exponential_llr_per_observation=(finite_ll - exponential_ll) / count,
    )


def _weighted_log_likelihood(
    tail: list[tuple[int, int]], probability: Callable[[int], float]
) -> float:
    total = 0.0
    for degree, frequency in tail:
        mass = probability(degree)
        if not math.isfinite(mass) or mass <= 0:
            return -math.inf
        total += frequency * math.log(mass)
    return total


def fit_alternative_tails(
    histogram: dict[int, int], xmin: int, alpha: float
) -> AlternativeTailMeasures:
    """Fit conditional discrete lognormal and stretched-exponential alternatives."""
    tail = sorted((int(k), int(v)) for k, v in histogram.items() if k >= xmin and v > 0)
    count = sum(frequency for _, frequency in tail)
    if count == 0:
        raise ValueError("tail is empty")
    logs = [(math.log(degree), frequency) for degree, frequency in tail]
    mean_log = sum(value * frequency for value, frequency in logs) / count
    variance_log = sum(frequency * (value - mean_log) ** 2 for value, frequency in logs) / count
    boundary = xmin - 0.5

    def lognormal_objective(params: tuple[float, float]) -> float:
        mu, log_sigma = params
        sigma = math.exp(log_sigma)
        if not 1e-4 <= sigma <= 100:
            return math.inf
        survival = _normal_survival((math.log(boundary) - mu) / sigma)
        if survival <= 0:
            return math.inf

        def probability(degree: int) -> float:
            low = _normal_cdf((math.log(degree - 0.5) - mu) / sigma)
            high = _normal_cdf((math.log(degree + 0.5) - mu) / sigma)
            return (high - low) / survival

        likelihood = _weighted_log_likelihood(tail, probability)
        return -likelihood if math.isfinite(likelihood) else math.inf

    lognormal_params = _nelder_mead(
        lognormal_objective,
        (mean_log, math.log(max(math.sqrt(variance_log), 0.1))),
    )
    lognormal_likelihood = -lognormal_objective(lognormal_params)

    mean_degree = sum(degree * frequency for degree, frequency in tail) / count

    def stretched_objective(params: tuple[float, float]) -> float:
        log_scale, log_shape = params
        scale, shape = math.exp(log_scale), math.exp(log_shape)
        if not 1e-4 <= scale <= 1e9 or not 0.02 <= shape <= 20:
            return math.inf
        boundary_power = (boundary / scale) ** shape

        def probability(degree: int) -> float:
            low = -((degree - 0.5) / scale) ** shape + boundary_power
            high = -((degree + 0.5) / scale) ** shape + boundary_power
            log_mass = _logdiffexp(low, high)
            return math.exp(log_mass) if log_mass > -745 else 0.0

        likelihood = _weighted_log_likelihood(tail, probability)
        return -likelihood if math.isfinite(likelihood) else math.inf

    stretched_params = _nelder_mead(
        stretched_objective,
        (math.log(max(mean_degree, 1)), math.log(1.0)),
    )
    stretched_likelihood = -stretched_objective(stretched_params)

    power_log_zeta = math.log(_hurwitz_zeta(alpha, xmin))
    power_likelihood = sum(
        frequency * (-alpha * math.log(degree) - power_log_zeta)
        for degree, frequency in tail
    )
    return AlternativeTailMeasures(
        power_vs_lognormal_llr_per_observation=(power_likelihood - lognormal_likelihood) / count,
        power_vs_stretched_exponential_llr_per_observation=(
            power_likelihood - stretched_likelihood
        )
        / count,
        lognormal_mu=lognormal_params[0],
        lognormal_sigma=math.exp(lognormal_params[1]),
        stretched_exponential_scale=math.exp(stretched_params[0]),
        stretched_exponential_shape=math.exp(stretched_params[1]),
    )


def _downsample_histogram(histogram: dict[int, int], maximum: int) -> dict[int, int]:
    total = sum(histogram.values())
    if total <= maximum:
        return dict(histogram)
    expected = {degree: count * maximum / total for degree, count in histogram.items()}
    sampled = {degree: int(value) for degree, value in expected.items()}
    remaining = maximum - sum(sampled.values())
    order = sorted(expected, key=lambda degree: (expected[degree] - sampled[degree], -degree), reverse=True)
    for degree in order[:remaining]:
        sampled[degree] += 1
    return {degree: count for degree, count in sampled.items() if count}


def _fast_refit_ks(histogram: dict[int, int]) -> float:
    """Refit the frozen continuity-corrected model using vectorized KS scans."""
    degrees = np.array(sorted(degree for degree, count in histogram.items() if degree > 0 and count), dtype=float)
    counts = np.array([histogram[int(degree)] for degree in degrees], dtype=float)
    suffix_counts = np.cumsum(counts[::-1])[::-1]
    suffix_log_sums = np.cumsum((counts * np.log(degrees))[::-1])[::-1]
    best = math.inf
    for index in range(max(0, len(degrees) - 4)):
        tail_count = suffix_counts[index]
        if tail_count < 50:
            continue
        xmin = degrees[index]
        denominator = suffix_log_sums[index] - tail_count * math.log(xmin - 0.5)
        if denominator <= 0:
            continue
        alpha = 1 + tail_count / denominator
        empirical = suffix_counts[index:] / tail_count
        model = ((degrees[index:] - 0.5) / (xmin - 0.5)) ** (1 - alpha)
        best = min(best, float(np.max(np.abs(empirical - model))))
    if not math.isfinite(best):
        raise ValueError("insufficient distinct positive degrees for a power-law tail fit")
    return best


def fit_power_law_tail_vectorized(histogram: dict[int, int]) -> PowerLawTailMeasures:
    """Numerically equivalent fitted-tail calculation with vectorized cutoff scans."""
    values = {int(k): int(v) for k, v in histogram.items() if int(v) > 0}
    total = sum(values.values())
    degrees = np.array(sorted(degree for degree in values if degree > 0), dtype=float)
    counts = np.array([values[int(degree)] for degree in degrees], dtype=float)
    suffix_counts = np.cumsum(counts[::-1])[::-1]
    suffix_log_sums = np.cumsum((counts * np.log(degrees))[::-1])[::-1]
    best: tuple[float, int, float] | None = None
    for index in range(max(0, len(degrees) - 4)):
        tail_count = suffix_counts[index]
        if tail_count < 50:
            continue
        xmin = degrees[index]
        denominator = suffix_log_sums[index] - tail_count * math.log(xmin - 0.5)
        if denominator <= 0:
            continue
        alpha = 1 + tail_count / denominator
        empirical = suffix_counts[index:] / tail_count
        model = ((degrees[index:] - 0.5) / (xmin - 0.5)) ** (1 - alpha)
        candidate = (float(np.max(np.abs(empirical - model))), int(xmin), float(alpha))
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    if best is None:
        raise ValueError("insufficient distinct positive degrees for a power-law tail fit")
    ks, xmin, alpha = best
    tail = [(degree, values[degree]) for degree in sorted(values) if degree >= xmin]
    tail_count = sum(frequency for _, frequency in tail)
    remaining = tail_count
    points = []
    for degree, frequency in tail:
        points.append((math.log(degree), math.log(remaining / tail_count)))
        remaining -= frequency
    return PowerLawTailMeasures(
        alpha=alpha,
        xmin=xmin,
        tail_count=tail_count,
        tail_fraction=tail_count / total,
        tail_span_decades=math.log10(tail[-1][0] / xmin),
        ks_distance=ks,
        loglog_ccdf_r_squared=_linear_r_squared(points),
        power_vs_exponential_llr_per_observation=_likelihood_ratio(tail, xmin, alpha),
    )


def bootstrap_power_law_gof(
    histogram: dict[int, int],
    *,
    replicates: int = 250,
    maximum_sample_size: int = 50_000,
    seed_text: str,
) -> tuple[float, int, int]:
    """Return semiparametric bootstrap p, successful replicates, and effective size."""
    effective = _downsample_histogram(histogram, maximum_sample_size)
    observed = fit_power_law_tail(effective)
    degrees = np.array(sorted(effective), dtype=np.int64)
    counts = np.array([effective[int(degree)] for degree in degrees], dtype=np.int64)
    body_mask = degrees < observed.xmin
    body_degrees, body_counts = degrees[body_mask], counts[body_mask]
    total = int(counts.sum())
    tail_probability = observed.tail_count / total
    body_probabilities = body_counts / body_counts.sum() if body_counts.size else None
    seed = int.from_bytes(hashlib.sha256(seed_text.encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    at_least_observed = 0
    successful = 0
    scale = observed.xmin - 0.5
    for _ in range(replicates):
        tail_count = int(rng.binomial(total, tail_probability))
        synthetic: dict[int, int] = {}
        if tail_count < total and body_degrees.size:
            generated = rng.multinomial(total - tail_count, body_probabilities)
            synthetic.update(
                (int(degree), int(count))
                for degree, count in zip(body_degrees, generated)
                if count
            )
        if tail_count:
            uniforms = np.maximum(1 - rng.random(tail_count), np.finfo(float).tiny)
            tail_values = np.floor(
                np.minimum(
                    scale * uniforms ** (-1 / (observed.alpha - 1)) + 0.5,
                    np.iinfo(np.int64).max / 2,
                )
            ).astype(np.int64)
            unique, frequencies = np.unique(tail_values, return_counts=True)
            for degree, frequency in zip(unique, frequencies):
                key = int(max(degree, observed.xmin))
                synthetic[key] = synthetic.get(key, 0) + int(frequency)
        try:
            simulated_ks = _fast_refit_ks(synthetic)
        except ValueError:
            continue
        successful += 1
        at_least_observed += int(simulated_ks >= observed.ks_distance)
    return (1 + at_least_observed) / (1 + successful), successful, total
