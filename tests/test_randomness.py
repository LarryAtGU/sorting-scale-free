from __future__ import annotations

import pytest

from scn_sorting.analysis.randomness import (
    chi_square,
    chi_square_p,
    descent_count,
    diagnose_permutation_ensemble,
    fixed_point_count,
    holm_adjust,
    inversion_count,
    pearson_correlation,
)
from scn_sorting.experiments.permutations import generate_permutation


def test_combinatorial_statistics_known_answers() -> None:
    assert inversion_count((0, 1, 2, 3)) == 0
    assert inversion_count((3, 2, 1, 0)) == 6
    assert inversion_count((2, 0, 3, 1)) == 3
    assert descent_count((2, 0, 3, 1)) == 2
    assert fixed_point_count((0, 2, 1, 3)) == 2


def test_chi_square_known_values() -> None:
    statistic, p_value = chi_square([10, 10], [10, 10])
    assert statistic == 0
    assert p_value == 1
    assert chi_square_p(3.841458820694124, 1) == pytest.approx(0.05, rel=1e-9)


def test_holm_adjustment_known_values() -> None:
    assert holm_adjust([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_correlation_known_values() -> None:
    assert pearson_correlation([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
    assert pearson_correlation([1, 2, 3], [6, 4, 2]) == pytest.approx(-1.0)


def test_generated_ensemble_produces_complete_report() -> None:
    permutations = [generate_permutation(128, seed) for seed in range(1, 201)]
    report = diagnose_permutation_ensemble(permutations, position_bins=10)
    assert report["n"] == 128
    assert report["trial_count"] == 200
    assert report["status"] in {"pass", "warning"}
    assert len(report["diagnostics"]) >= 35


def test_obviously_biased_ensemble_is_flagged() -> None:
    # Cyclic shifts are valid and distinct but have exactly zero descents in one
    # case and one descent otherwise, far from a uniform-permutation ensemble.
    n = 128
    permutations = [tuple(range(shift, n)) + tuple(range(shift)) for shift in range(100)]
    report = diagnose_permutation_ensemble(permutations, position_bins=10)
    assert report["status"] == "warning"
    assert "descent_mean" in report["warnings"]


def test_invalid_ensemble_parameters_are_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        diagnose_permutation_ensemble([])
    with pytest.raises(ValueError, match="same length"):
        diagnose_permutation_ensemble([(0, 1), (0, 1, 2)])
    with pytest.raises(ValueError, match="five expected"):
        diagnose_permutation_ensemble([(0, 1)] * 10, position_bins=16)

