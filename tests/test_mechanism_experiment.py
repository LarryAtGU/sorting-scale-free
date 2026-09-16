from __future__ import annotations

import pytest

from scn_sorting.analysis.random_bst import canonical_first_pivot_quick_edges
from scn_sorting.experiments.batch import run_record
from scn_sorting.experiments.mechanism_batch import (
    attachment_rows,
    snapshot_rows,
    summarize_mechanisms,
)
from scn_sorting.experiments.permutations import generate_permutation
from scn_sorting.experiments.runner import run_sort


@pytest.mark.parametrize(
    "algorithm", ["quick-multipivot-1", "quick-multipivot-2", "quick-multipivot-4"]
)
def test_multipivot_algorithms_sort_and_release_storage(algorithm: str) -> None:
    run = run_sort(algorithm, generate_permutation(128, 7), mechanism_tracking=True)
    assert run.output_values == tuple(range(128))
    assert run.summary.current_auxiliary_storage == 0
    assert run.tracker.mechanism_summary()["representative_comparison_count"] > 0


def test_single_pivot_intervention_has_canonical_edges() -> None:
    permutation = generate_permutation(128, 19)
    run = run_sort("quick-multipivot-1", permutation)
    assert run.tracker.edges == canonical_first_pivot_quick_edges(permutation)


@pytest.mark.parametrize("algorithm", ["quick", "tree-unbalanced", "merge-top-down"])
def test_mechanism_tracking_does_not_change_sort_measurements(algorithm: str) -> None:
    permutation = generate_permutation(64, 3)
    baseline = run_sort(algorithm, permutation, distribution_only=True)
    measured = run_sort(algorithm, permutation, distribution_only=True, mechanism_tracking=True)
    assert measured.summary == baseline.summary


def test_attachment_opportunities_and_selections_are_conserved() -> None:
    run = run_sort(
        "quick-multipivot-2",
        generate_permutation(64, 11),
        distribution_only=True,
        mechanism_tracking=True,
    )
    mechanism = run.tracker.mechanism_summary()
    kernel = mechanism["attachment_kernel"]
    assert sum(cell["endpoint_selections"] for cell in kernel) == 2 * run.summary.comparison_count
    assert (
        sum(cell["node_event_opportunities"] for cell in kernel)
        == 64 * run.summary.comparison_count
    )
    assert mechanism["snapshots"][-1]["comparison_count"] == run.summary.comparison_count


def test_algorithms_without_record_representatives_report_zero() -> None:
    run = run_sort(
        "merge-top-down",
        generate_permutation(32, 2),
        distribution_only=True,
        mechanism_tracking=True,
    )
    mechanism = run.tracker.mechanism_summary()
    assert mechanism["representative_comparison_count"] == 0
    assert mechanism["representative_node_count"] == 0


def test_mechanism_batch_tables() -> None:
    records = [
        run_record(
            "quick-multipivot-1",
            16,
            seed,
            generate_permutation(16, seed),
            distribution_only=True,
            mechanism_tracking=True,
        )
        for seed in (1, 2)
    ]
    summary = summarize_mechanisms(records)
    assert summary[0]["trials"] == 2
    assert "representative_exposure_gini_mean" in summary[0]
    assert attachment_rows(records)
    snapshots = snapshot_rows(records)
    assert snapshots
    assert all(0 < float(row["progress_fraction"]) <= 1 for row in snapshots)
