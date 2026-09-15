from __future__ import annotations

import itertools

import pytest

from scn_sorting.algorithms.initial import ALGORITHMS
from scn_sorting.experiments.permutations import generate_permutation
from scn_sorting.experiments.runner import run_sort


@pytest.mark.parametrize("algorithm", sorted(ALGORITHMS))
@pytest.mark.parametrize("n", [1, 2, 4, 8])
def test_algorithms_sort_all_small_permutations(algorithm: str, n: int) -> None:
    for permutation in itertools.permutations(range(n)):
        run = run_sort(algorithm, permutation)
        assert run.output_values == tuple(range(n))


@pytest.mark.parametrize("algorithm", sorted(ALGORITHMS))
def test_algorithms_sort_deterministic_random_inputs(algorithm: str) -> None:
    for seed in range(1, 11):
        permutation = generate_permutation(128, seed)
        run = run_sort(algorithm, permutation)
        assert run.output_values == tuple(range(128))
        assert sum(run.summary.total_degree) == 2 * run.summary.unique_edge_count
        assert run.summary.active_edge_count == 127
        assert run.summary.maximum_active_edge_count <= 128**2 // 4
        assert sum(
            gain * count for gain, count in run.summary.information_gain_histogram
        ) == 128 * 127 // 2
        assert run.summary.record_movement_count >= 0
        assert run.summary.peak_auxiliary_storage >= 0
        assert run.summary.current_auxiliary_storage == 0


def test_bubble_known_comparison_trace() -> None:
    run = run_sort("bubble", (2, 0, 1), retain_trace=True)
    assert run.summary.comparison_count == 3
    assert [(e.left_identity, e.right_identity) for e in run.tracker.events] == [
        (0, 1),
        (0, 2),
        (1, 2),
    ]
    assert run.summary.record_movement_count == 4


def test_merge_storage_and_movement_are_measured() -> None:
    top_down = run_sort("merge-top-down", (3, 2, 1, 0))
    bottom_up = run_sort("merge-bottom-up", (3, 2, 1, 0))
    assert top_down.summary.peak_auxiliary_storage > 4
    assert bottom_up.summary.peak_auxiliary_storage == 4
    assert top_down.summary.record_movement_count == 16
    assert bottom_up.summary.record_movement_count == 16


def test_unknown_algorithm_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown"):
        run_sort("not-an-algorithm", (1, 0))


def test_expanded_algorithm_registry() -> None:
    assert {
        "insertion",
        "selection",
        "merge-top-down",
        "merge-bottom-up",
        "quick-median-three",
        "quick-dual-pivot",
        "shell",
        "introsort",
        "tournament",
        "tree-unbalanced",
        "tree-avl",
        "quick-random",
        "odd-even-merge-network",
    } <= ALGORITHMS.keys()


@pytest.mark.parametrize(
    "algorithm",
    ["shell", "introsort", "tournament", "tree-unbalanced", "tree-avl", "quick-random"],
)
def test_added_families_measure_resources(algorithm: str) -> None:
    run = run_sort(algorithm, generate_permutation(32, 7))
    assert run.summary.comparison_count > 0
    assert run.summary.record_movement_count > 0
    assert run.summary.current_auxiliary_storage == 0


@pytest.mark.parametrize("algorithm", ["tournament", "tree-unbalanced", "tree-avl"])
def test_explicit_organization_algorithms_measure_storage(algorithm: str) -> None:
    run = run_sort(algorithm, generate_permutation(32, 7))
    assert run.summary.peak_auxiliary_storage >= 32


def test_added_network_rejects_non_power_of_two_size() -> None:
    with pytest.raises(ValueError, match="power-of-two"):
        run_sort("odd-even-merge-network", (2, 0, 1))


def test_random_pivot_quicksort_is_reproducible() -> None:
    permutation = generate_permutation(128, 17)
    first = run_sort("quick-random", permutation, retain_trace=True)
    second = run_sort("quick-random", permutation, retain_trace=True)
    assert first.summary == second.summary
    assert first.tracker.events == second.tracker.events


@pytest.mark.parametrize(
    "algorithm",
    [
        "insertion",
        "merge-top-down",
        "merge-bottom-up",
        "quick-median-three",
        "quick-dual-pivot",
    ],
)
def test_new_algorithms_do_not_repeat_comparisons(algorithm: str) -> None:
    for seed in range(1, 11):
        run = run_sort(algorithm, generate_permutation(128, seed))
        assert run.summary.repeated_comparison_count == 0
