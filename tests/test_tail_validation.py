from scn_sorting.analysis.powerlaw import fit_power_law_tail
from scn_sorting.analysis.tail_validation import (
    bootstrap_power_law_gof,
    fit_alternative_tails,
    fit_finite_power_law,
    fit_power_law_tail_vectorized,
)


def test_alternative_tail_fit_is_finite() -> None:
    histogram = {degree: max(1, round(10000 * degree ** -2.5)) for degree in range(2, 80)}
    power = fit_power_law_tail(histogram)
    result = fit_alternative_tails(histogram, power.xmin, power.alpha)
    assert result.lognormal_sigma > 0
    assert result.stretched_exponential_scale > 0
    assert result.power_vs_stretched_exponential_llr_per_observation == result.power_vs_stretched_exponential_llr_per_observation


def test_bootstrap_is_deterministic_and_bounded() -> None:
    histogram = {degree: max(1, round(2000 * degree ** -2.3)) for degree in range(2, 50)}
    first = bootstrap_power_law_gof(histogram, replicates=5, maximum_sample_size=1000, seed_text="test")
    second = bootstrap_power_law_gof(histogram, replicates=5, maximum_sample_size=1000, seed_text="test")
    assert first == second
    assert 0 < first[0] <= 1
    assert first[1] == 5
    assert first[2] == min(sum(histogram.values()), 1000)


def test_vectorized_fit_matches_reference() -> None:
    histogram = {degree: max(1, round(5000 * degree ** -2.2)) for degree in range(2, 120)}
    reference = fit_power_law_tail(histogram)
    vectorized = fit_power_law_tail_vectorized(histogram)
    assert vectorized.xmin == reference.xmin
    assert abs(vectorized.alpha - reference.alpha) < 1e-12
    assert abs(vectorized.ks_distance - reference.ks_distance) < 1e-12
    assert abs(vectorized.power_vs_exponential_llr_per_observation - reference.power_vs_exponential_llr_per_observation) < 1e-12


def test_finite_power_law_fit_is_valid() -> None:
    histogram = {degree: max(1, round(10000 * degree ** -2.1)) for degree in range(2, 100)}
    result = fit_finite_power_law(histogram, 5, 99)
    assert 1 < result.alpha < 3
    assert result.finite_vs_unbounded_power_llr_per_observation > 0
