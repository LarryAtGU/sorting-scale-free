"""Run one instrumented sorting execution."""

from __future__ import annotations

from dataclasses import dataclass

from scn_sorting.algorithms.initial import ALGORITHMS
from scn_sorting.instrumentation.core import (
    ComparisonTracker,
    SCNSummary,
    assert_sorted,
    records_from_permutation,
)


@dataclass(frozen=True)
class SortRun:
    algorithm: str
    input_values: tuple[int, ...]
    output_values: tuple[int, ...]
    summary: SCNSummary
    tracker: ComparisonTracker


def run_sort(
    algorithm: str,
    permutation: tuple[int, ...],
    *,
    retain_trace: bool = False,
    distribution_only: bool = False,
    mechanism_tracking: bool = False,
) -> SortRun:
    try:
        sort_function = ALGORITHMS[algorithm]
    except KeyError as error:
        raise ValueError(f"unknown algorithm: {algorithm}") from error
    records = records_from_permutation(permutation)
    tracker = ComparisonTracker(
        records,
        retain_trace=retain_trace,
        distribution_only=distribution_only,
        mechanism_tracking=mechanism_tracking,
    )
    sort_function(records, tracker)
    assert_sorted(records)
    return SortRun(
        algorithm=algorithm,
        input_values=permutation,
        output_values=tuple(record.key for record in records),
        summary=tracker.summary(),
        tracker=tracker,
    )
