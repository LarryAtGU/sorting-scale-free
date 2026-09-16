from itertools import permutations

import pytest

from scn_sorting.analysis.random_bst import (
    bst_comparison_profile,
    canonical_first_pivot_quick_edges,
    expected_subtree_count,
)
from scn_sorting.experiments.runner import run_sort


@pytest.mark.parametrize("values", [(2, 0, 3, 1), (0, 1, 2, 3), (3, 1, 0, 2)])
def test_bst_degree_is_depth_plus_descendants(values: tuple[int, ...]) -> None:
    profile = bst_comparison_profile(values)
    run = run_sort("tree-unbalanced", values)
    assert profile.degree == run.summary.total_degree
    assert profile.edges == run.tracker.edges


@pytest.mark.parametrize("values", [(2, 0, 3, 1), (0, 1, 2, 3), (3, 1, 0, 2)])
def test_canonical_first_pivot_quicksort_has_same_comparison_graph_as_insertion_bst(
    values: tuple[int, ...],
) -> None:
    profile = bst_comparison_profile(values)
    assert canonical_first_pivot_quick_edges(values) == profile.edges


def test_historical_hoare_implementation_is_not_inputwise_bst_equivalent() -> None:
    values = (3, 1, 0, 2)
    assert run_sort("quick", values).tracker.edges != bst_comparison_profile(values).edges


@pytest.mark.parametrize("n", range(2, 8))
def test_exact_random_bst_expected_subtree_counts(n: int) -> None:
    totals = [0] * (n + 1)
    samples = 0
    for values in permutations(range(n)):
        profile = bst_comparison_profile(values)
        for size in profile.subtree_size:
            totals[size] += 1
        samples += 1
    for size in range(1, n + 1):
        assert totals[size] / samples == pytest.approx(expected_subtree_count(n, size))
