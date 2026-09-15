"""First-stage comparison sorting algorithms."""

from __future__ import annotations

from collections.abc import Callable

from scn_sorting.algorithms.expanded import (
    introsort,
    odd_even_merge_network,
    quick_sort_deterministic_random,
    shell_sort,
    tournament_sort,
    tree_sort_avl,
    tree_sort_unbalanced,
)
from scn_sorting.instrumentation.core import ComparisonTracker, Record

SortFunction = Callable[[list[Record], ComparisonTracker], None]


def _swap(items: list[Record], first: int, second: int, tracker: ComparisonTracker) -> None:
    if first != second:
        items[first], items[second] = items[second], items[first]
        tracker.record_movements(2)


def _write(items: list[Record], index: int, value: Record, tracker: ComparisonTracker) -> None:
    items[index] = value
    tracker.record_movements(1)


def bubble_sort(items: list[Record], tracker: ComparisonTracker) -> None:
    end = len(items) - 1
    swapped = True
    while swapped and end > 0:
        swapped = False
        for index in range(end):
            if tracker.compare(items[index], items[index + 1]) > 0:
                _swap(items, index, index + 1, tracker)
                swapped = True
        end -= 1


def quick_sort(items: list[Record], tracker: ComparisonTracker) -> None:
    """First-element-pivot Quicksort corresponding to the historical program."""
    stack = [(0, len(items) - 1)]
    tracker.allocate_auxiliary_storage(2)
    while stack:
        start, end = stack.pop()
        tracker.release_auxiliary_storage(2)
        if start >= end:
            continue
        pivot = items[start]
        lower = start + 1
        upper = end
        while True:
            while lower <= upper and tracker.compare(pivot, items[lower]) > 0:
                lower += 1
            while lower <= upper and tracker.compare(pivot, items[upper]) < 0:
                upper -= 1
            if lower > upper:
                break
            _swap(items, lower, upper, tracker)
            lower += 1
            upper -= 1
        _swap(items, start, upper, tracker)
        stack.append((start, upper - 1))
        stack.append((upper + 1, end))
        tracker.allocate_auxiliary_storage(4)


def heap_sort(items: list[Record], tracker: ComparisonTracker) -> None:
    def sift_down(root: int, end: int) -> None:
        while 2 * root + 1 <= end:
            child = 2 * root + 1
            if child + 1 <= end and tracker.compare(items[child], items[child + 1]) < 0:
                child += 1
            if tracker.compare(items[root], items[child]) >= 0:
                return
            _swap(items, root, child, tracker)
            root = child

    for root in range(len(items) // 2 - 1, -1, -1):
        sift_down(root, len(items) - 1)
    for end in range(len(items) - 1, 0, -1):
        _swap(items, 0, end, tracker)
        sift_down(0, end - 1)


def binary_insertion_sort(items: list[Record], tracker: ComparisonTracker) -> None:
    for index in range(1, len(items)):
        value = items[index]
        lower, upper = 0, index
        while lower < upper:
            middle = (lower + upper) // 2
            if tracker.compare(items[middle], value) > 0:
                upper = middle
            else:
                lower = middle + 1
        if lower < index:
            items[lower + 1 : index + 1] = items[lower:index]
            items[lower] = value
            tracker.record_movements(index - lower + 1)


def insertion_sort(items: list[Record], tracker: ComparisonTracker) -> None:
    """Stable linear-search insertion sort."""
    for index in range(1, len(items)):
        value = items[index]
        position = index
        while position > 0 and tracker.compare(items[position - 1], value) > 0:
            _write(items, position, items[position - 1], tracker)
            position -= 1
        if position != index:
            _write(items, position, value, tracker)


def selection_sort(items: list[Record], tracker: ComparisonTracker) -> None:
    for start in range(len(items) - 1):
        minimum = start
        for index in range(start + 1, len(items)):
            if tracker.compare(items[index], items[minimum]) < 0:
                minimum = index
        if minimum != start:
            _swap(items, start, minimum, tracker)


def _merge(
    items: list[Record], auxiliary: list[Record | None], start: int, middle: int, end: int,
    tracker: ComparisonTracker,
) -> None:
    auxiliary[start:end] = items[start:end]
    tracker.record_movements(end - start)
    left, right = start, middle
    for output in range(start, end):
        if left >= middle:
            _write(items, output, auxiliary[right], tracker)  # type: ignore[arg-type]
            right += 1
        elif right >= end:
            _write(items, output, auxiliary[left], tracker)  # type: ignore[arg-type]
            left += 1
        else:
            left_item, right_item = auxiliary[left], auxiliary[right]
            assert left_item is not None and right_item is not None
            if tracker.compare(left_item, right_item) <= 0:
                _write(items, output, left_item, tracker)
                left += 1
            else:
                _write(items, output, right_item, tracker)
                right += 1


def merge_sort_top_down(items: list[Record], tracker: ComparisonTracker) -> None:
    auxiliary: list[Record | None] = [None] * len(items)
    tracker.allocate_auxiliary_storage(len(items))

    def sort_range(start: int, end: int) -> None:
        tracker.allocate_auxiliary_storage(2)
        if end - start < 2:
            tracker.release_auxiliary_storage(2)
            return
        middle = (start + end) // 2
        sort_range(start, middle)
        sort_range(middle, end)
        _merge(items, auxiliary, start, middle, end, tracker)
        tracker.release_auxiliary_storage(2)

    sort_range(0, len(items))
    tracker.release_auxiliary_storage(len(items))


def merge_sort_bottom_up(items: list[Record], tracker: ComparisonTracker) -> None:
    auxiliary: list[Record | None] = [None] * len(items)
    tracker.allocate_auxiliary_storage(len(items))
    width = 1
    while width < len(items):
        for start in range(0, len(items), 2 * width):
            middle = min(start + width, len(items))
            end = min(start + 2 * width, len(items))
            if middle < end:
                _merge(items, auxiliary, start, middle, end, tracker)
        width *= 2
    tracker.release_auxiliary_storage(len(items))


def _median_of_three(
    first: Record, second: Record, third: Record, tracker: ComparisonTracker,
) -> tuple[Record, Record, Record]:
    """Return low, median, high using no repeated pair comparison."""
    if tracker.compare(first, second) < 0:
        if tracker.compare(second, third) < 0:
            return first, second, third
        if tracker.compare(first, third) < 0:
            return first, third, second
        return third, first, second
    if tracker.compare(first, third) < 0:
        return second, first, third
    if tracker.compare(second, third) < 0:
        return second, third, first
    return third, second, first


def quick_sort_median_three(items: list[Record], tracker: ComparisonTracker) -> None:
    def insertion_range(start: int, end: int) -> None:
        for index in range(start + 1, end + 1):
            value, position = items[index], index
            while position > start and tracker.compare(items[position - 1], value) > 0:
                _write(items, position, items[position - 1], tracker)
                position -= 1
            if position != index:
                _write(items, position, value, tracker)

    def place(record: Record, target: int, start: int, end: int) -> None:
        current = next(i for i in range(start, end + 1) if items[i].identity == record.identity)
        _swap(items, current, target, tracker)

    stack = [(0, len(items) - 1)]
    tracker.allocate_auxiliary_storage(2)
    while stack:
        start, end = stack.pop()
        tracker.release_auxiliary_storage(2)
        if end - start < 3:
            insertion_range(start, end)
            continue
        middle = (start + end) // 2
        low, pivot, high = _median_of_three(items[start], items[middle], items[end], tracker)
        place(low, start, start, end)
        place(high, end, start, end)
        place(pivot, end - 1, start, end)
        store = start + 1
        for index in range(start + 1, end - 1):
            if tracker.compare(items[index], pivot) < 0:
                _swap(items, store, index, tracker)
                store += 1
        _swap(items, store, end - 1, tracker)
        stack.append((start, store - 1))
        stack.append((store + 1, end))
        tracker.allocate_auxiliary_storage(4)


def quick_sort_dual_pivot(items: list[Record], tracker: ComparisonTracker) -> None:
    stack = [(0, len(items) - 1)]
    tracker.allocate_auxiliary_storage(2)
    while stack:
        start, end = stack.pop()
        tracker.release_auxiliary_storage(2)
        if start >= end:
            continue
        if tracker.compare(items[start], items[end]) > 0:
            _swap(items, start, end, tracker)
        lower_pivot, upper_pivot = items[start], items[end]
        lower, scan, upper = start + 1, start + 1, end - 1
        while scan <= upper:
            if tracker.compare(items[scan], lower_pivot) < 0:
                _swap(items, scan, lower, tracker)
                lower += 1
            elif tracker.compare(items[scan], upper_pivot) > 0:
                while scan < upper and tracker.compare(items[upper], upper_pivot) > 0:
                    upper -= 1
                _swap(items, scan, upper, tracker)
                upper -= 1
                if scan <= upper and tracker.compare(items[scan], lower_pivot) < 0:
                    _swap(items, scan, lower, tracker)
                    lower += 1
            scan += 1
        lower -= 1
        upper += 1
        _swap(items, start, lower, tracker)
        _swap(items, end, upper, tracker)
        stack.extend(((start, lower - 1), (lower + 1, upper - 1), (upper + 1, end)))
        tracker.allocate_auxiliary_storage(6)


def merge_insertion_sort(items: list[Record], tracker: ComparisonTracker) -> None:
    """Stable merge-insertion implementation using binary insertion into a main chain.

    This represents the merge-insertion family used in the paper. A later
    milestone will separately reproduce and validate the historical Jacobsthal
    insertion schedule at the level required for exact comparison-count matching.
    """
    if len(items) < 2:
        return
    pair_count = len(items) // 2
    storage_slots = 3 * pair_count
    tracker.allocate_auxiliary_storage(storage_slots)
    tracker.record_movements(storage_slots)
    pairs: list[tuple[Record, Record]] = []
    unpaired: Record | None = None
    index = 0
    while index + 1 < len(items):
        first, second = items[index], items[index + 1]
        if tracker.compare(first, second) > 0:
            first, second = second, first
        pairs.append((first, second))
        index += 2
    if index < len(items):
        unpaired = items[index]

    maxima = [larger for _, larger in pairs]
    merge_insertion_sort(maxima, tracker)
    tracker.allocate_auxiliary_storage(3 * pair_count)
    tracker.record_movements(3 * pair_count)
    storage_slots += 3 * pair_count
    partner = {larger.identity: smaller for smaller, larger in pairs}
    chain = maxima[:]
    pending = [partner[larger.identity] for larger in maxima]
    if pending:
        tracker.record_movements(len(chain) + 1)
        chain.insert(0, pending.pop(0))
    if unpaired is not None:
        pending.append(unpaired)
        tracker.allocate_auxiliary_storage(1)
        tracker.record_movements(1)
        storage_slots += 1

    # Binary insertion is correct and comparison-efficient. The pending order is
    # deterministic; exact Ford-Johnson scheduling is tracked as follow-up work.
    for value in pending:
        lower, upper = 0, len(chain)
        while lower < upper:
            middle = (lower + upper) // 2
            if tracker.compare(chain[middle], value) > 0:
                upper = middle
            else:
                lower = middle + 1
        tracker.record_movements(len(chain) - lower + 1)
        chain.insert(lower, value)
        tracker.allocate_auxiliary_storage(1)
        storage_slots += 1
    items[:] = chain
    tracker.record_movements(len(items))
    tracker.release_auxiliary_storage(storage_slots)


def bitonic_sorting_network(items: list[Record], tracker: ComparisonTracker) -> None:
    """Runnable data-oblivious control for power-of-two input sizes.

    Batcher's bitonic network has depth O(log^2 n), not the strict O(log n) AKS
    bound. It is included as a practical network control and labelled accordingly.
    """
    n = len(items)
    if n == 0 or n & (n - 1):
        raise ValueError("bitonic sorting network requires a power-of-two input size")
    width = 2
    while width <= n:
        stride = width // 2
        while stride:
            for index in range(n):
                partner = index ^ stride
                if partner <= index:
                    continue
                ascending = (index & width) == 0
                comparison = tracker.compare(items[index], items[partner])
                if (ascending and comparison > 0) or (not ascending and comparison < 0):
                    _swap(items, index, partner, tracker)
            stride //= 2
        width *= 2


ALGORITHMS: dict[str, SortFunction] = {
    "binary-insertion": binary_insertion_sort,
    "bitonic-network": bitonic_sorting_network,
    "bubble": bubble_sort,
    "heap": heap_sort,
    "insertion": insertion_sort,
    "introsort": introsort,
    "merge-bottom-up": merge_sort_bottom_up,
    "merge-insertion": merge_insertion_sort,
    "merge-top-down": merge_sort_top_down,
    "quick": quick_sort,
    "quick-dual-pivot": quick_sort_dual_pivot,
    "quick-median-three": quick_sort_median_three,
    "quick-random": quick_sort_deterministic_random,
    "selection": selection_sort,
    "shell": shell_sort,
    "tournament": tournament_sort,
    "tree-avl": tree_sort_avl,
    "tree-unbalanced": tree_sort_unbalanced,
    "odd-even-merge-network": odd_even_merge_network,
}
