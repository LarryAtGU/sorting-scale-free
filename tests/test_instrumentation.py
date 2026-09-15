from __future__ import annotations

import pytest

from scn_sorting.instrumentation.core import (
    ComparisonTracker,
    Record,
    records_from_permutation,
)


def test_direction_repetition_implication_and_reduction() -> None:
    records = records_from_permutation((0, 1, 2))
    tracker = ComparisonTracker(records, retain_trace=True)
    assert tracker.compare(records[0], records[1]) == -1
    assert tracker.compare(records[1], records[2]) == -1
    assert tracker.is_implied(0, 2)
    assert tracker.compare(records[0], records[2]) == -1
    assert tracker.compare(records[1], records[0]) == 1

    summary = tracker.summary()
    assert tracker.edges == {(0, 1), (1, 2), (0, 2)}
    assert tracker.transitive_reduction_edges() == {(0, 1), (1, 2)}
    assert summary.comparison_count == 4
    assert summary.unique_edge_count == 3
    assert summary.repeated_comparison_count == 1
    assert summary.implied_comparison_count == 2
    assert summary.in_degree == (0, 1, 2)
    assert summary.out_degree == (2, 1, 0)
    assert sum(summary.total_degree) == 2 * summary.unique_edge_count
    assert summary.rank_distance_histogram == ((1, 3), (2, 1))
    assert summary.critical_comparison_fraction == pytest.approx(3 / 4)
    assert summary.mean_information_gain == pytest.approx(3 / 4)
    assert summary.maximum_information_gain == 2
    assert summary.active_edge_count == 2
    assert summary.maximum_active_edge_count == 2
    assert summary.mean_active_edge_count == pytest.approx(7 / 4)
    assert summary.retired_active_edge_count == 0
    assert [event.information_gain for event in tracker.events] == [1, 2, 0, 0]
    assert [event.active_edge_count for event in tracker.events] == [1, 2, 2, 2]


def test_trace_can_be_disabled_for_batch_mode() -> None:
    records = records_from_permutation((1, 0))
    tracker = ComparisonTracker(records)
    tracker.compare(records[0], records[1])
    assert tracker.events == ()
    with pytest.raises(ValueError, match="disabled"):
        tracker.trace_document(algorithm="test", input_values=(1, 0))


def test_distribution_only_matches_exact_degree_and_counts() -> None:
    records = records_from_permutation((2, 0, 3, 1))
    exact = ComparisonTracker(records)
    fast = ComparisonTracker(records, distribution_only=True)
    comparisons = ((0, 1), (0, 2), (2, 3), (0, 1))
    for left, right in comparisons:
        assert exact.compare(records[left], records[right]) == fast.compare(
            records[left], records[right]
        )
    exact_summary = exact.summary()
    fast_summary = fast.summary()
    assert fast_summary.comparison_count == exact_summary.comparison_count
    assert fast_summary.unique_edge_count == exact_summary.unique_edge_count
    assert fast_summary.repeated_comparison_count == exact_summary.repeated_comparison_count
    assert fast_summary.total_degree == exact_summary.total_degree
    assert fast_summary.comparison_participation == exact_summary.comparison_participation
    assert fast_summary.rank_distance_histogram == exact_summary.rank_distance_histogram
    assert fast_summary.maximum_active_edge_count == 0
    with pytest.raises(ValueError, match="disabled"):
        fast.is_implied(0, 1)
    with pytest.raises(ValueError, match="disabled"):
        fast.transitive_reduction_edges()
    with pytest.raises(ValueError, match="cannot retain"):
        ComparisonTracker(records, retain_trace=True, distribution_only=True)


def test_resource_accounting_validates_storage_lifecycle() -> None:
    records = records_from_permutation((1, 0))
    tracker = ComparisonTracker(records)
    tracker.allocate_auxiliary_storage(3)
    tracker.compare(records[0], records[1])
    tracker.record_movements(2)
    tracker.release_auxiliary_storage(3)
    summary = tracker.summary()
    assert summary.record_movement_count == 2
    assert summary.peak_auxiliary_storage == 3
    assert summary.mean_auxiliary_storage == 3
    assert summary.current_auxiliary_storage == 0
    with pytest.raises(ValueError, match="movement"):
        tracker.record_movements(-1)
    with pytest.raises(ValueError, match="storage release"):
        tracker.release_auxiliary_storage(1)


def test_records_require_distinct_keys_and_contiguous_identities() -> None:
    with pytest.raises(ValueError, match="distinct"):
        ComparisonTracker([Record(0, 1), Record(1, 1)])
    with pytest.raises(ValueError, match="0..n-1"):
        ComparisonTracker([Record(1, 0)])


def test_six_node_extremal_active_scn_reaches_n_squared_over_four() -> None:
    records = records_from_permutation(tuple(range(6)))
    tracker = ComparisonTracker(records, retain_trace=True)
    for lower in range(3):
        for upper in range(3, 6):
            tracker.compare(records[lower], records[upper])
    assert tracker.summary().active_edge_count == 9
    assert tracker.transitive_reduction_edges() == {
        (lower, upper) for lower in range(3) for upper in range(3, 6)
    }

    for left, right in ((0, 1), (1, 2), (3, 4), (4, 5)):
        tracker.compare(records[left], records[right])
    summary = tracker.summary()
    assert summary.maximum_active_edge_count == 9
    assert summary.active_edge_count == 5
    assert summary.retired_active_edge_count == 8
    assert summary.retired_active_edge_count == summary.comparison_count - 5
    assert sum(event.information_gain for event in tracker.events) == 15
    assert tracker.transitive_reduction_edges() == {(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)}
