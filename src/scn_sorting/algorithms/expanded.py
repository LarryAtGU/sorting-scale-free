"""Additional algorithm families used to test SCN mechanism hypotheses."""

from __future__ import annotations

from dataclasses import dataclass

from scn_sorting.instrumentation.core import ComparisonTracker, Record


def _swap(items: list[Record], i: int, j: int, tracker: ComparisonTracker) -> None:
    if i != j:
        items[i], items[j] = items[j], items[i]
        tracker.record_movements(2)


def _write(items: list[Record], i: int, value: Record, tracker: ComparisonTracker) -> None:
    items[i] = value
    tracker.record_movements(1)


def shell_sort(items: list[Record], tracker: ComparisonTracker) -> None:
    """Shell sort with the Ciura gap sequence, extended geometrically."""
    gaps = [1, 4, 10, 23, 57, 132, 301, 701]
    while gaps[-1] < len(items) // 2:
        gaps.append(int(gaps[-1] * 2.25))
    for gap in reversed([gap for gap in gaps if gap < len(items)]):
        for index in range(gap, len(items)):
            value = items[index]
            position = index
            while position >= gap and tracker.compare(items[position - gap], value) > 0:
                _write(items, position, items[position - gap], tracker)
                position -= gap
            if position != index:
                _write(items, position, value, tracker)


def _sift_range(
    items: list[Record],
    start: int,
    count: int,
    root: int,
    tracker: ComparisonTracker,
) -> None:
    while 2 * root + 1 < count:
        child = 2 * root + 1
        if (
            child + 1 < count
            and tracker.compare(
                items[start + child],
                items[start + child + 1],
            )
            < 0
        ):
            child += 1
        if tracker.compare(items[start + root], items[start + child]) >= 0:
            return
        _swap(items, start + root, start + child, tracker)
        root = child


def _heap_sort_range(
    items: list[Record],
    start: int,
    end: int,
    tracker: ComparisonTracker,
) -> None:
    count = end - start + 1
    for root in range(count // 2 - 1, -1, -1):
        _sift_range(items, start, count, root, tracker)
    for remaining in range(count - 1, 0, -1):
        _swap(items, start, start + remaining, tracker)
        _sift_range(items, start, remaining, 0, tracker)


def introsort(items: list[Record], tracker: ComparisonTracker) -> None:
    """Quicksort with a logarithmic depth limit and heap-sort fallback."""
    if len(items) < 2:
        return
    depth_limit = 2 * (len(items).bit_length() - 1)
    stack = [(0, len(items) - 1, depth_limit)]
    tracker.allocate_auxiliary_storage(3)
    while stack:
        start, end, depth = stack.pop()
        tracker.release_auxiliary_storage(3)
        if start >= end:
            continue
        if depth == 0:
            _heap_sort_range(items, start, end, tracker)
            continue
        pivot_index = (start + end) // 2
        _swap(items, pivot_index, end, tracker)
        pivot = items[end]
        store = start
        for index in range(start, end):
            if tracker.compare(items[index], pivot) < 0:
                _swap(items, store, index, tracker)
                store += 1
        _swap(items, store, end, tracker)
        if start < store - 1:
            stack.append((start, store - 1, depth - 1))
            tracker.allocate_auxiliary_storage(3)
        if store + 1 < end:
            stack.append((store + 1, end, depth - 1))
            tracker.allocate_auxiliary_storage(3)


def quick_sort_deterministic_random(items: list[Record], tracker: ComparisonTracker) -> None:
    """Quicksort with a reproducible pseudo-random pivot for each subproblem.

    The pivot index is derived from the identities at the range boundaries and
    range length, so no hidden global random state or additional seed is used.
    """
    stack = [(0, len(items) - 1)]
    tracker.allocate_auxiliary_storage(2)
    while stack:
        start, end = stack.pop()
        tracker.release_auxiliary_storage(2)
        if start >= end:
            continue
        span = end - start + 1
        mixed = (
            items[start].identity * 1_103_515_245
            + items[end].identity * 12_345
            + span * 2_654_435_761
        ) & 0xFFFFFFFF
        pivot_index = start + mixed % span
        _swap(items, pivot_index, end, tracker)
        pivot = items[end]
        store = start
        for index in range(start, end):
            if tracker.compare(items[index], pivot) < 0:
                _swap(items, store, index, tracker)
                store += 1
        _swap(items, store, end, tracker)
        if start < store - 1:
            stack.append((start, store - 1))
            tracker.allocate_auxiliary_storage(2)
        if store + 1 < end:
            stack.append((store + 1, end))
            tracker.allocate_auxiliary_storage(2)


def _stable_multipivot_sort(
    items: list[Record], tracker: ComparisonTracker, *, pivot_count: int
) -> None:
    """Stable recursive partitioning with a controlled number of representatives."""
    if pivot_count < 1:
        raise ValueError("pivot_count must be positive")

    def sort_values(values: list[Record]) -> list[Record]:
        if len(values) < 2:
            return values[:]
        count = min(pivot_count, len(values) - 1)
        pivots = values[:count]
        tracker.allocate_auxiliary_storage(len(values))
        tracker.record_movements(len(values))
        for index in range(1, len(pivots)):
            pivot = pivots[index]
            position = index
            while (
                position > 0
                and tracker.compare_representative(
                    pivots[position - 1],
                    pivot,
                    span_size=len(values),
                    kind=f"multipivot-{pivot_count}-order",
                )
                > 0
            ):
                pivots[position] = pivots[position - 1]
                tracker.record_movements(1)
                position -= 1
            pivots[position] = pivot
            tracker.record_movements(1)
        pivot_identities = {pivot.identity for pivot in pivots}
        buckets: list[list[Record]] = [[] for _ in range(count + 1)]
        for value in values:
            if value.identity in pivot_identities:
                continue
            lower, upper = 0, count
            while lower < upper:
                middle = (lower + upper) // 2
                comparison = tracker.compare_representative(
                    pivots[middle],
                    value,
                    span_size=len(values),
                    kind=f"multipivot-{pivot_count}",
                )
                if comparison < 0:
                    lower = middle + 1
                else:
                    upper = middle
            buckets[lower].append(value)
            tracker.record_movements(1)
        result: list[Record] = []
        for index, bucket in enumerate(buckets):
            result.extend(sort_values(bucket))
            if index < count:
                result.append(pivots[index])
        tracker.record_movements(len(result))
        tracker.release_auxiliary_storage(len(values))
        return result

    items[:] = sort_values(items)
    tracker.record_movements(len(items))


def quick_sort_multipivot_1(items: list[Record], tracker: ComparisonTracker) -> None:
    _stable_multipivot_sort(items, tracker, pivot_count=1)


def quick_sort_multipivot_2(items: list[Record], tracker: ComparisonTracker) -> None:
    _stable_multipivot_sort(items, tracker, pivot_count=2)


def quick_sort_multipivot_4(items: list[Record], tracker: ComparisonTracker) -> None:
    _stable_multipivot_sort(items, tracker, pivot_count=4)


def tournament_sort(items: list[Record], tracker: ComparisonTracker) -> None:
    """Repeated-min tournament using an explicit complete winner tree."""
    n = len(items)
    if n < 2:
        return
    leaf_count = 1 << (n - 1).bit_length()
    tree: list[Record | None] = [None] * (2 * leaf_count)
    tracker.allocate_auxiliary_storage(2 * leaf_count)
    for index, value in enumerate(items):
        tree[leaf_count + index] = value
        tracker.record_movements(1)

    def winner(left: Record | None, right: Record | None) -> Record | None:
        if left is None:
            return right
        if right is None:
            return left
        return left if tracker.compare(left, right) <= 0 else right

    for node in range(leaf_count - 1, 0, -1):
        tree[node] = winner(tree[2 * node], tree[2 * node + 1])
        if tree[node] is not None:
            tracker.record_movements(1)
    leaf_by_identity = {value.identity: leaf_count + index for index, value in enumerate(items)}
    for output in range(n):
        minimum = tree[1]
        assert minimum is not None
        _write(items, output, minimum, tracker)
        node = leaf_by_identity[minimum.identity]
        tree[node] = None
        node //= 2
        while node:
            tree[node] = winner(tree[2 * node], tree[2 * node + 1])
            if tree[node] is not None:
                tracker.record_movements(1)
            node //= 2
    tracker.release_auxiliary_storage(2 * leaf_count)


@dataclass
class _TreeNode:
    value: Record
    left: _TreeNode | None = None
    right: _TreeNode | None = None
    height: int = 1
    size: int = 1


def _tree_sort(items: list[Record], tracker: ComparisonTracker, *, balanced: bool) -> None:
    root: _TreeNode | None = None

    def height(node: _TreeNode | None) -> int:
        return node.height if node else 0

    def rotate_left(node: _TreeNode) -> _TreeNode:
        child = node.right
        assert child is not None
        node.right, child.left = child.left, node
        node.height = 1 + max(height(node.left), height(node.right))
        node.size = (
            1 + (node.left.size if node.left else 0) + (node.right.size if node.right else 0)
        )
        child.height = 1 + max(height(child.left), height(child.right))
        child.size = (
            1 + (child.left.size if child.left else 0) + (child.right.size if child.right else 0)
        )
        return child

    def rotate_right(node: _TreeNode) -> _TreeNode:
        child = node.left
        assert child is not None
        node.left, child.right = child.right, node
        node.height = 1 + max(height(node.left), height(node.right))
        node.size = (
            1 + (node.left.size if node.left else 0) + (node.right.size if node.right else 0)
        )
        child.height = 1 + max(height(child.left), height(child.right))
        child.size = (
            1 + (child.left.size if child.left else 0) + (child.right.size if child.right else 0)
        )
        return child

    def insert(node: _TreeNode | None, value: Record) -> _TreeNode:
        if node is None:
            tracker.allocate_auxiliary_storage(1)
            tracker.record_movements(1)
            return _TreeNode(value)
        comparison = -tracker.compare_representative(
            node.value, value, span_size=node.size, kind="tree-search"
        )
        if comparison < 0:
            node.left = insert(node.left, value)
        else:
            node.right = insert(node.right, value)
        node.height = 1 + max(height(node.left), height(node.right))
        node.size = (
            1 + (node.left.size if node.left else 0) + (node.right.size if node.right else 0)
        )
        if not balanced:
            return node
        balance = height(node.left) - height(node.right)
        if balance > 1:
            assert node.left is not None
            if tracker.compare(value, node.left.value) > 0:
                node.left = rotate_left(node.left)
            return rotate_right(node)
        if balance < -1:
            assert node.right is not None
            if tracker.compare(value, node.right.value) < 0:
                node.right = rotate_right(node.right)
            return rotate_left(node)
        return node

    for value in items:
        root = insert(root, value)
    output = 0
    stack: list[_TreeNode] = []
    node = root
    while node is not None or stack:
        while node is not None:
            stack.append(node)
            node = node.left
        node = stack.pop()
        _write(items, output, node.value, tracker)
        output += 1
        node = node.right
    tracker.release_auxiliary_storage(len(items))


def tree_sort_unbalanced(items: list[Record], tracker: ComparisonTracker) -> None:
    _tree_sort(items, tracker, balanced=False)


def tree_sort_avl(items: list[Record], tracker: ComparisonTracker) -> None:
    _tree_sort(items, tracker, balanced=True)


def odd_even_merge_network(items: list[Record], tracker: ComparisonTracker) -> None:
    """Batcher's odd-even mergesort network for power-of-two sizes."""
    n = len(items)
    if n == 0 or n & (n - 1):
        raise ValueError("odd-even merge network requires a power-of-two input size")

    def merge(start: int, length: int, stride: int) -> None:
        step = stride * 2
        if step < length:
            merge(start, length, step)
            merge(start + stride, length, step)
            for index in range(start + stride, start + length - stride, step):
                compare_exchange(index, index + stride)
        else:
            compare_exchange(start, start + stride)

    def sort(start: int, length: int) -> None:
        if length > 1:
            half = length // 2
            sort(start, half)
            sort(start + half, half)
            merge(start, length, 1)

    def compare_exchange(first: int, second: int) -> None:
        if tracker.compare(items[first], items[second]) > 0:
            _swap(items, first, second, tracker)

    sort(0, n)
