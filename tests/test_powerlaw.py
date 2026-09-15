from __future__ import annotations

import pytest

from scn_sorting.analysis.powerlaw import fit_power_law_tail


def test_power_law_shaped_histogram_has_strong_tail_evidence() -> None:
    histogram = {degree: max(1, round(200_000 * degree**-2.5)) for degree in range(1, 101)}
    measures = fit_power_law_tail(histogram)
    assert measures.alpha == pytest.approx(2.5, abs=0.2)
    assert measures.ks_distance < 0.08
    assert measures.loglog_ccdf_r_squared > 0.88
    assert measures.power_vs_exponential_llr_per_observation > 0


def test_exponential_histogram_does_not_prefer_power_law() -> None:
    histogram = {degree: max(1, round(50_000 * 0.72**degree)) for degree in range(1, 31)}
    measures = fit_power_law_tail(histogram)
    assert measures.power_vs_exponential_llr_per_observation < 0


def test_fit_rejects_insufficient_support() -> None:
    with pytest.raises(ValueError, match="insufficient"):
        fit_power_law_tail({0: 100, 1: 10, 2: 5})
