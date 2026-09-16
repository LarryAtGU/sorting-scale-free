"""Instrumented records, comparison events, and directed SCNs."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from itertools import pairwise
from typing import Any


@dataclass(frozen=True, slots=True)
class Record:
    """A sortable key with an identity that survives moves and swaps."""

    identity: int
    key: int


@dataclass(frozen=True, slots=True)
class ComparisonEvent:
    index: int
    left_identity: int
    right_identity: int
    smaller_identity: int
    larger_identity: int
    result: int
    repeated: bool
    implied_before: bool
    new_edge: bool
    rank_distance: int
    information_gain: int
    active_edge_count: int
    retired_active_edges: int


@dataclass(frozen=True)
class SCNSummary:
    node_count: int
    comparison_count: int
    unique_edge_count: int
    repeated_comparison_count: int
    implied_comparison_count: int
    in_degree: tuple[int, ...]
    out_degree: tuple[int, ...]
    total_degree: tuple[int, ...]
    maximum_degree: int
    mean_degree: float
    comparison_participation: tuple[int, ...]
    rank_distance_histogram: tuple[tuple[int, int], ...]
    mean_rank_distance: float
    mean_normalized_rank_distance: float
    critical_comparison_count: int
    critical_comparison_fraction: float
    long_range_comparison_fraction: float
    information_gain_histogram: tuple[tuple[int, int], ...]
    mean_information_gain: float
    maximum_information_gain: int
    multi_relation_gain_fraction: float
    active_edge_count: int
    maximum_active_edge_count: int
    mean_active_edge_count: float
    retired_active_edge_count: int
    maximum_retired_per_comparison: int
    retirement_comparison_fraction: float
    record_movement_count: int
    peak_auxiliary_storage: int
    mean_auxiliary_storage: float
    current_auxiliary_storage: int


class ComparisonTracker:
    """The only permitted gateway for comparisons in instrumented sorts.

    Reachability is maintained as Python integer bitsets. The canonical SCN is
    the directed simple graph of distinct compared pairs. Repeated and implied
    calls remain part of the comparison count and optional chronological trace.
    """

    def __init__(
        self,
        records: list[Record],
        *,
        retain_trace: bool = False,
        distribution_only: bool = False,
        mechanism_tracking: bool = False,
    ) -> None:
        identities = sorted(record.identity for record in records)
        if identities != list(range(len(records))):
            raise ValueError("record identities must be exactly 0..n-1")
        if len({record.key for record in records}) != len(records):
            raise ValueError("record keys must be distinct")
        if retain_trace and distribution_only:
            raise ValueError("distribution-only tracking cannot retain a trace")
        self._n = len(records)
        self._keys = tuple(record.key for record in sorted(records, key=lambda item: item.identity))
        sorted_identities = sorted(records, key=lambda item: item.key)
        self._ranks = [0] * self._n
        for rank, record in enumerate(sorted_identities):
            self._ranks[record.identity] = rank
        self._descendants = [0] * self._n
        self._ancestors = [0] * self._n
        self._active_out = [0] * self._n
        self._active_in = [0] * self._n
        self._edges: set[tuple[int, int]] = set()
        self._distribution_only = distribution_only
        self._mechanism_tracking = mechanism_tracking
        self._edge_bits = [0] * self._n
        self._fast_in_degree = [0] * self._n
        self._fast_out_degree = [0] * self._n
        self._fast_unique_edge_count = 0
        self._seen_pairs: set[tuple[int, int]] = set()
        self._comparison_count = 0
        self._repeated_count = 0
        self._implied_count = 0
        self._retain_trace = retain_trace
        self._events: list[ComparisonEvent] = []
        self._participation = [0] * self._n
        self._rank_distance_counts: dict[int, int] = {}
        self._rank_distance_sum = 0
        self._critical_comparisons = 0
        self._long_range_comparisons = 0
        self._information_gain_counts: dict[int, int] = {}
        self._information_gain_sum = 0
        self._maximum_information_gain = 0
        self._multi_relation_gain_comparisons = 0
        self._active_edge_count = 0
        self._maximum_active_edge_count = 0
        self._active_edge_count_sum = 0
        self._retired_active_edges = 0
        self._maximum_retired_per_comparison = 0
        self._retirement_comparisons = 0
        self._record_movements = 0
        self._current_auxiliary_storage = 0
        self._peak_auxiliary_storage = 0
        self._auxiliary_storage_comparison_sum = 0
        self._mechanism_degrees = [0] * self._n
        self._mechanism_last_strength_change = [0] * self._n
        self._mechanism_selection_counts: dict[int, int] = {}
        self._mechanism_opportunities: dict[int, int] = {}
        self._mechanism_snapshots: list[dict[str, float | int]] = []
        self._mechanism_next_checkpoint = 1
        self._representative_counts = [0] * self._n
        self._representative_span_sum = [0] * self._n
        self._representative_max_span = [0] * self._n
        self._representative_first_event = [-1] * self._n
        self._representative_last_event = [-1] * self._n
        self._representative_kinds: dict[str, int] = {}
        self._mechanism_finalized = False

    @property
    def comparison_count(self) -> int:
        return self._comparison_count

    @property
    def edges(self) -> frozenset[tuple[int, int]]:
        if self._distribution_only:
            return frozenset(
                (source, target)
                for source, targets in enumerate(self._edge_bits)
                for target in range(self._n)
                if targets & (1 << target)
            )
        return frozenset(self._edges)

    @property
    def events(self) -> tuple[ComparisonEvent, ...]:
        return tuple(self._events)

    def record_movements(self, count: int) -> None:
        if count < 0:
            raise ValueError("movement count cannot be negative")
        self._record_movements += count

    def allocate_auxiliary_storage(self, slots: int) -> None:
        if slots < 0:
            raise ValueError("storage allocation cannot be negative")
        self._current_auxiliary_storage += slots
        self._peak_auxiliary_storage = max(
            self._peak_auxiliary_storage, self._current_auxiliary_storage
        )

    def release_auxiliary_storage(self, slots: int) -> None:
        if slots < 0 or slots > self._current_auxiliary_storage:
            raise ValueError("invalid storage release")
        self._current_auxiliary_storage -= slots

    def compare(self, left: Record, right: Record) -> int:
        """Compare two records, record the event, and return -1 or 1."""
        self._auxiliary_storage_comparison_sum += self._current_auxiliary_storage
        if self._mechanism_tracking:
            time = self._comparison_count
            for identity in (left.identity, right.identity):
                strength = self._participation[identity]
                elapsed = time + 1 - self._mechanism_last_strength_change[identity]
                self._mechanism_opportunities[strength] = (
                    self._mechanism_opportunities.get(strength, 0) + elapsed
                )
                self._mechanism_selection_counts[strength] = (
                    self._mechanism_selection_counts.get(strength, 0) + 1
                )
                self._mechanism_last_strength_change[identity] = time + 1
        if left.identity == right.identity:
            raise ValueError("a record cannot be compared with itself")
        if left.key < right.key:
            smaller, larger, result = left.identity, right.identity, -1
        else:
            smaller, larger, result = right.identity, left.identity, 1

        pair = tuple(sorted((left.identity, right.identity)))
        if self._distribution_only:
            edge_bit = 1 << larger
            repeated = bool(self._edge_bits[smaller] & edge_bit)
        else:
            repeated = pair in self._seen_pairs
            self._seen_pairs.add(pair)

        implied = (
            False if self._distribution_only else bool(self._descendants[smaller] & (1 << larger))
        )
        edge = (smaller, larger)
        if self._distribution_only:
            new_edge = not repeated
            if new_edge:
                self._edge_bits[smaller] |= edge_bit
                self._fast_out_degree[smaller] += 1
                self._fast_in_degree[larger] += 1
                self._fast_unique_edge_count += 1
        else:
            new_edge = edge not in self._edges
            if new_edge:
                self._edges.add(edge)
        information_gain, retired = (0, 0)
        if not implied and not self._distribution_only:
            information_gain, retired = self._add_to_transitive_closure(smaller, larger)

        rank_distance = abs(self._ranks[left.identity] - self._ranks[right.identity])
        self._participation[left.identity] += 1
        self._participation[right.identity] += 1
        self._rank_distance_counts[rank_distance] = (
            self._rank_distance_counts.get(rank_distance, 0) + 1
        )
        self._rank_distance_sum += rank_distance
        self._critical_comparisons += int(rank_distance == 1)
        self._long_range_comparisons += int(2 * rank_distance >= max(1, self._n - 1))
        self._information_gain_counts[information_gain] = (
            self._information_gain_counts.get(information_gain, 0) + 1
        )
        self._information_gain_sum += information_gain
        self._maximum_information_gain = max(self._maximum_information_gain, information_gain)
        self._multi_relation_gain_comparisons += int(information_gain > 1)
        self._active_edge_count_sum += self._active_edge_count
        self._retired_active_edges += retired
        self._maximum_retired_per_comparison = max(self._maximum_retired_per_comparison, retired)
        self._retirement_comparisons += int(retired > 0)

        self._comparison_count += 1
        self._repeated_count += int(repeated)
        self._implied_count += int(implied)
        if self._retain_trace:
            self._events.append(
                ComparisonEvent(
                    index=self._comparison_count,
                    left_identity=left.identity,
                    right_identity=right.identity,
                    smaller_identity=smaller,
                    larger_identity=larger,
                    result=result,
                    repeated=repeated,
                    implied_before=implied,
                    new_edge=new_edge,
                    rank_distance=rank_distance,
                    information_gain=information_gain,
                    active_edge_count=self._active_edge_count,
                    retired_active_edges=retired,
                )
            )
        if self._mechanism_tracking:
            if new_edge:
                self._mechanism_degrees[smaller] += 1
                self._mechanism_degrees[larger] += 1
            if self._comparison_count == self._mechanism_next_checkpoint:
                self._capture_mechanism_snapshot()
                self._mechanism_next_checkpoint *= 2
        return result

    def compare_representative(
        self,
        representative: Record,
        other: Record,
        *,
        span_size: int,
        kind: str,
    ) -> int:
        """Compare while marking one endpoint as an algorithmic representative."""
        result = self.compare(representative, other)
        if self._mechanism_tracking:
            identity = representative.identity
            event = self._comparison_count
            self._representative_counts[identity] += 1
            self._representative_span_sum[identity] += max(1, span_size)
            self._representative_max_span[identity] = max(
                self._representative_max_span[identity], max(1, span_size)
            )
            if self._representative_first_event[identity] < 0:
                self._representative_first_event[identity] = event
            self._representative_last_event[identity] = event
            self._representative_kinds[kind] = self._representative_kinds.get(kind, 0) + 1
        return result

    @staticmethod
    def _concentration(values: list[int]) -> tuple[float, float, float, float]:
        total = sum(values)
        if not values or total == 0:
            return 0.0, 0.0, 0.0, 0.0
        ordered = sorted(values)
        n = len(ordered)
        weighted = sum((index + 1) * value for index, value in enumerate(ordered))
        gini = (2 * weighted) / (n * total) - (n + 1) / n
        cumulative = 0
        p80 = 1.0
        for count, value in enumerate(reversed(ordered), 1):
            cumulative += value
            if cumulative >= 0.8 * total:
                p80 = count / n
                break
        entropy = -sum((value / total) * math.log(value / total) for value in values if value)
        normalized_entropy = entropy / math.log(n) if n > 1 else 0.0
        return gini, p80, normalized_entropy, max(values) / total

    def _capture_mechanism_snapshot(self) -> None:
        degree = self._concentration(self._mechanism_degrees)
        strength = self._concentration(self._participation)
        self._mechanism_snapshots.append(
            {
                "comparison_count": self._comparison_count,
                "degree_gini": degree[0],
                "degree_p80_fraction": degree[1],
                "degree_normalized_entropy": degree[2],
                "maximum_degree_share": degree[3],
                "strength_gini": strength[0],
                "strength_p80_fraction": strength[1],
                "strength_normalized_entropy": strength[2],
                "maximum_strength_share": strength[3],
            }
        )

    @staticmethod
    def _pearson(left: list[float], right: list[float]) -> float:
        if len(left) < 2:
            return 0.0
        mean_left = sum(left) / len(left)
        mean_right = sum(right) / len(right)
        numerator = sum((x - mean_left) * (y - mean_right) for x, y in zip(left, right))
        denominator = math.sqrt(
            sum((x - mean_left) ** 2 for x in left) * sum((y - mean_right) ** 2 for y in right)
        )
        return numerator / denominator if denominator else 0.0

    def mechanism_summary(self) -> dict[str, Any]:
        if not self._mechanism_tracking:
            raise ValueError("mechanism tracking was disabled")
        if not self._mechanism_finalized:
            total_time = self._comparison_count
            for identity, strength in enumerate(self._participation):
                elapsed = total_time - self._mechanism_last_strength_change[identity]
                self._mechanism_opportunities[strength] = (
                    self._mechanism_opportunities.get(strength, 0) + elapsed
                )
            if not self._mechanism_snapshots or (
                self._mechanism_snapshots[-1]["comparison_count"] != total_time
            ):
                self._capture_mechanism_snapshot()
            self._mechanism_finalized = True
        representative_total = sum(self._representative_counts)
        representatives = [i for i, count in enumerate(self._representative_counts) if count]
        exposure = self._concentration(self._representative_counts)
        lifetimes = [
            self._representative_last_event[i] - self._representative_first_event[i] + 1
            for i in representatives
        ]
        mean_spans = [
            self._representative_span_sum[i] / self._representative_counts[i]
            for i in representatives
        ]
        return {
            "schema_version": 1,
            "snapshots": self._mechanism_snapshots,
            "attachment_kernel": [
                {
                    "current_strength": strength,
                    "endpoint_selections": self._mechanism_selection_counts.get(strength, 0),
                    "node_event_opportunities": opportunities,
                    "selection_rate": (
                        self._mechanism_selection_counts.get(strength, 0) / opportunities
                        if opportunities
                        else 0.0
                    ),
                }
                for strength, opportunities in sorted(self._mechanism_opportunities.items())
            ],
            "representative_comparison_count": representative_total,
            "representative_comparison_fraction": (
                representative_total / self._comparison_count if self._comparison_count else 0.0
            ),
            "representative_node_count": len(representatives),
            "representative_node_fraction": len(representatives) / self._n if self._n else 0.0,
            "representative_exposure_gini": exposure[0],
            "representative_exposure_p80_fraction": exposure[1],
            "maximum_representative_exposure_share": exposure[3],
            "mean_represented_span": (
                sum(self._representative_span_sum) / representative_total
                if representative_total
                else 0.0
            ),
            "maximum_represented_span": max(self._representative_max_span, default=0),
            "mean_representative_lifetime_fraction": (
                sum(lifetimes) / (len(lifetimes) * self._comparison_count)
                if lifetimes and self._comparison_count
                else 0.0
            ),
            "representative_exposure_degree_correlation": self._pearson(
                [float(self._representative_counts[i]) for i in representatives],
                [float(self._mechanism_degrees[i]) for i in representatives],
            ),
            "representative_exposure_strength_correlation": self._pearson(
                [float(self._representative_counts[i]) for i in representatives],
                [float(self._participation[i]) for i in representatives],
            ),
            "mean_span_degree_correlation": self._pearson(
                mean_spans,
                [float(self._mechanism_degrees[i]) for i in representatives],
            ),
            "representative_kind_counts": dict(sorted(self._representative_kinds.items())),
        }

    def _add_to_transitive_closure(self, smaller: int, larger: int) -> tuple[int, int]:
        predecessors = self._ancestors[smaller] | (1 << smaller)
        successors = self._descendants[larger] | (1 << larger)
        information_gain = 0
        remaining = predecessors
        while remaining:
            bit = remaining & -remaining
            predecessor = bit.bit_length() - 1
            information_gain += (successors & ~self._descendants[predecessor]).bit_count()
            remaining ^= bit

        retired = 0
        remaining = predecessors
        while remaining:
            bit = remaining & -remaining
            predecessor = bit.bit_length() - 1
            removed = self._active_out[predecessor] & successors
            retired += removed.bit_count()
            self._active_out[predecessor] &= ~removed
            while removed:
                target_bit = removed & -removed
                target = target_bit.bit_length() - 1
                self._active_in[target] &= ~bit
                removed ^= target_bit
            remaining ^= bit
        self._active_out[smaller] |= 1 << larger
        self._active_in[larger] |= 1 << smaller
        self._active_edge_count += 1 - retired
        self._maximum_active_edge_count = max(
            self._maximum_active_edge_count, self._active_edge_count
        )

        remaining = predecessors
        while remaining:
            bit = remaining & -remaining
            predecessor = bit.bit_length() - 1
            self._descendants[predecessor] |= successors
            remaining ^= bit
        remaining = successors
        while remaining:
            bit = remaining & -remaining
            successor = bit.bit_length() - 1
            self._ancestors[successor] |= predecessors
            remaining ^= bit
        return information_gain, retired

    def is_implied(self, first_identity: int, second_identity: int) -> bool:
        if self._distribution_only:
            raise ValueError("implication tracking is disabled in distribution-only mode")
        return bool(
            self._descendants[first_identity] & (1 << second_identity)
            or self._descendants[second_identity] & (1 << first_identity)
        )

    def transitive_reduction_edges(self) -> frozenset[tuple[int, int]]:
        if self._distribution_only:
            raise ValueError("transitive reduction is disabled in distribution-only mode")
        return frozenset(
            (source, target)
            for source, targets in enumerate(self._active_out)
            for target in range(self._n)
            if targets & (1 << target)
        )

    def summary(self) -> SCNSummary:
        if self._distribution_only:
            in_degree = self._fast_in_degree
            out_degree = self._fast_out_degree
            unique_edge_count = self._fast_unique_edge_count
        else:
            in_degree = [0] * self._n
            out_degree = [0] * self._n
            for smaller, larger in self._edges:
                out_degree[smaller] += 1
                in_degree[larger] += 1
            unique_edge_count = len(self._edges)
        total_degree = tuple(left + right for left, right in zip(in_degree, out_degree))
        comparisons = self._comparison_count
        return SCNSummary(
            node_count=self._n,
            comparison_count=self._comparison_count,
            unique_edge_count=unique_edge_count,
            repeated_comparison_count=self._repeated_count,
            implied_comparison_count=self._implied_count,
            in_degree=tuple(in_degree),
            out_degree=tuple(out_degree),
            total_degree=total_degree,
            maximum_degree=max(total_degree, default=0),
            mean_degree=(2 * unique_edge_count / self._n) if self._n else 0.0,
            comparison_participation=tuple(self._participation),
            rank_distance_histogram=tuple(sorted(self._rank_distance_counts.items())),
            mean_rank_distance=self._rank_distance_sum / comparisons if comparisons else 0.0,
            mean_normalized_rank_distance=(
                self._rank_distance_sum / (comparisons * (self._n - 1))
                if comparisons and self._n > 1
                else 0.0
            ),
            critical_comparison_count=self._critical_comparisons,
            critical_comparison_fraction=(
                self._critical_comparisons / comparisons if comparisons else 0.0
            ),
            long_range_comparison_fraction=(
                self._long_range_comparisons / comparisons if comparisons else 0.0
            ),
            information_gain_histogram=tuple(sorted(self._information_gain_counts.items())),
            mean_information_gain=(
                self._information_gain_sum / comparisons if comparisons else 0.0
            ),
            maximum_information_gain=self._maximum_information_gain,
            multi_relation_gain_fraction=(
                self._multi_relation_gain_comparisons / comparisons if comparisons else 0.0
            ),
            active_edge_count=self._active_edge_count,
            maximum_active_edge_count=self._maximum_active_edge_count,
            mean_active_edge_count=(
                self._active_edge_count_sum / comparisons if comparisons else 0.0
            ),
            retired_active_edge_count=self._retired_active_edges,
            maximum_retired_per_comparison=self._maximum_retired_per_comparison,
            retirement_comparison_fraction=(
                self._retirement_comparisons / comparisons if comparisons else 0.0
            ),
            record_movement_count=self._record_movements,
            peak_auxiliary_storage=self._peak_auxiliary_storage,
            mean_auxiliary_storage=(
                self._auxiliary_storage_comparison_sum / comparisons if comparisons else 0.0
            ),
            current_auxiliary_storage=self._current_auxiliary_storage,
        )

    def trace_document(self, *, algorithm: str, input_values: tuple[int, ...]) -> dict[str, Any]:
        if not self._retain_trace:
            raise ValueError("trace retention was disabled")
        return {
            "schema_version": 2,
            "algorithm": algorithm,
            "input": input_values,
            "nodes": [
                {"identity": identity, "key": key} for identity, key in enumerate(self._keys)
            ],
            "events": [asdict(event) for event in self._events],
            "summary": asdict(self.summary()),
        }


def records_from_permutation(permutation: tuple[int, ...]) -> list[Record]:
    """Give every input position a permanent record identity."""
    return [Record(identity=index, key=value) for index, value in enumerate(permutation)]


def assert_sorted(records: list[Record]) -> None:
    if any(left.key > right.key for left, right in pairwise(records)):
        raise AssertionError("sorting algorithm produced an unsorted result")
