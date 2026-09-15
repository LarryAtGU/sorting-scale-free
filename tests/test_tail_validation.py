from scn_sorting.analysis.powerlaw import fit_power_law_tail
from scn_sorting.analysis.tail_validation import bootstrap_power_law_gof, fit_alternative_tails


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
