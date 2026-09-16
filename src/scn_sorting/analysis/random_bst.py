"""Exact structural identities for unbalanced BST sorting comparison networks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BSTProfile:
    depth: tuple[int, ...]
    subtree_size: tuple[int, ...]
    degree: tuple[int, ...]
    edges: frozenset[tuple[int, int]]


@dataclass
class _Node:
    identity: int
    key: int
    left: _Node | None = None
    right: _Node | None = None


def bst_comparison_profile(permutation: tuple[int, ...]) -> BSTProfile:
    """Build the insertion BST and return exact SCN quantities by record identity."""
    n = len(permutation)
    root: _Node | None = None
    depths = [0] * n
    edges: set[tuple[int, int]] = set()
    for identity, key in enumerate(permutation):
        if root is None:
            root = _Node(identity, key)
            continue
        node = root
        depth = 0
        while True:
            depth += 1
            edge = (node.identity, identity) if node.key < key else (identity, node.identity)
            edges.add(edge)
            if key < node.key:
                if node.left is None:
                    node.left = _Node(identity, key)
                    break
                node = node.left
            else:
                if node.right is None:
                    node.right = _Node(identity, key)
                    break
                node = node.right
        depths[identity] = depth

    subtree_sizes = [0] * n

    def visit(node: _Node | None) -> int:
        if node is None:
            return 0
        size = 1 + visit(node.left) + visit(node.right)
        subtree_sizes[node.identity] = size
        return size

    visit(root)
    degrees = tuple(depths[i] + subtree_sizes[i] - 1 for i in range(n))
    return BSTProfile(tuple(depths), tuple(subtree_sizes), degrees, frozenset(edges))


def expected_subtree_count(n: int, size: int) -> float:
    """Expected random-BST nodes whose fringe subtree has exactly ``size`` nodes."""
    if not 1 <= size <= n:
        return 0.0
    if size == n:
        return 1.0
    return 2 * (n + 1) / ((size + 1) * (size + 2))


def canonical_first_pivot_quick_edges(permutation: tuple[int, ...]) -> frozenset[tuple[int, int]]:
    """SCN edges for stable first-pivot partitioning with one comparison per item."""
    records = list(enumerate(permutation))
    edges: set[tuple[int, int]] = set()

    def visit(values: list[tuple[int, int]]) -> None:
        if len(values) < 2:
            return
        pivot_identity, pivot_key = values[0]
        lower: list[tuple[int, int]] = []
        upper: list[tuple[int, int]] = []
        for identity, key in values[1:]:
            edge = (identity, pivot_identity) if key < pivot_key else (pivot_identity, identity)
            edges.add(edge)
            (lower if key < pivot_key else upper).append((identity, key))
        visit(lower)
        visit(upper)

    visit(records)
    return frozenset(edges)
