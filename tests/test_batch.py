from __future__ import annotations

import json

import pytest

from scn_sorting.experiments.batch import (
    append_checkpoint,
    gini,
    pareto_node_fraction,
    read_checkpoint,
    run_record,
    summarize,
)


def test_gini_known_cases() -> None:
    assert gini((0, 0, 0)) == 0
    assert gini((1, 1, 1)) == pytest.approx(0)
    assert gini((0, 0, 3)) == pytest.approx(2 / 3)


def test_pareto_node_fraction_known_cases() -> None:
    assert pareto_node_fraction(()) == 0
    assert pareto_node_fraction((0, 0, 0)) == 0
    assert pareto_node_fraction((1, 1, 1, 1, 1)) == pytest.approx(0.8)
    assert pareto_node_fraction((8, 1, 1, 0, 0)) == pytest.approx(0.2)
    with pytest.raises(ValueError):
        pareto_node_fraction((1, 2), 0)


def test_run_record_and_summary() -> None:
    first = run_record("quick", 4, 1, (2, 0, 3, 1))
    second = run_record("quick", 4, 2, (1, 3, 0, 2))
    assert first["algorithm"] == "quick"
    assert first["n"] == 4
    assert first["comparison_count"] >= 3
    histogram = first["degree_histogram"]
    assert sum(histogram.values()) == 4
    assert first["mean_rank_distance"] >= 1
    assert first["critical_comparison_fraction"] > 0
    assert first["maximum_active_edge_count"] >= 3
    assert 0 <= first["endpoint_participation_gini"] <= 1
    assert 0 < first["degree_p80_fraction"] <= 1
    assert sum(first["rank_distance_histogram"].values()) == first["comparison_count"]
    assert sum(first["information_gain_histogram"].values()) == first["comparison_count"]
    assert first["record_movement_count"] >= 0
    assert first["movements_per_node"] >= 0
    assert first["peak_auxiliary_storage_fraction"] >= 0
    assert 0 < first["combined_efficiency_equal_weights"] <= 1

    rows = summarize([first, second])
    assert len(rows) == 1
    assert rows[0]["trials"] == 2
    assert sum(json.loads(rows[0]["aggregate_degree_histogram"]).values()) == 8
    assert "maximum_active_edge_count_mean" in rows[0]
    assert "degree_p80_fraction_mean" in rows[0]
    assert sum(json.loads(rows[0]["aggregate_rank_distance_histogram"]).values()) == (
        first["comparison_count"] + second["comparison_count"]
    )


def test_distribution_only_record_matches_exact_distribution() -> None:
    permutation = (2, 0, 3, 1)
    exact = run_record("quick", 4, 1, permutation)
    fast = run_record("quick", 4, 1, permutation, distribution_only=True)
    for field in (
        "comparison_count",
        "unique_edge_count",
        "record_movement_count",
        "degree_histogram",
        "degree_p80_fraction",
    ):
        assert fast[field] == exact[field]
    assert fast["tracking_profile"] == "distribution"
    assert fast["maximum_active_edge_count"] == 0


def test_checkpoint_is_append_only_and_readable(tmp_path) -> None:
    path = tmp_path / "checkpoint.jsonl"
    append_checkpoint(path, {"algorithm": "quick", "n": 4, "seed": 1})
    append_checkpoint(path, {"algorithm": "heap", "n": 4, "seed": 1})
    assert read_checkpoint(path) == [
        {"algorithm": "quick", "n": 4, "seed": 1},
        {"algorithm": "heap", "n": 4, "seed": 1},
    ]
