from __future__ import annotations

import csv
import json
from pathlib import Path

from scn_sorting.experiments.export_distribution import convert_summary


def test_summary_conversion(tmp_path: Path) -> None:
    source = tmp_path / "summary.csv"
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "algorithm", "n", "trials", "comparison_count_mean",
                "comparison_efficiency_ratio_mean", "maximum_degree_mean",
                "degree_cv_mean", "degree_gini_mean", "aggregate_degree_histogram",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "algorithm": "quick", "n": 8, "trials": 10, "comparison_count_mean": 5,
            "comparison_efficiency_ratio_mean": 1.1, "maximum_degree_mean": 3,
            "degree_cv_mean": 0.5, "degree_gini_mean": 0.2,
            "aggregate_degree_histogram": json.dumps(
                {"1": 30, "2": 20, "3": 12, "4": 8, "5": 5, "6": 3, "7": 2}
            ),
        })
    output = tmp_path / "dashboard.json"
    document = convert_summary(source, output)
    dataset = document["datasets"][0]
    assert dataset["histogram"] == [[1, 30], [2, 20], [3, 12], [4, 8], [5, 5], [6, 3], [7, 2]]
    assert 0 < dataset["tail_fraction"] <= 1
    assert dataset["tail_alpha"] > 1
    assert dataset["tail_xmin"] >= 1
    assert dataset["mean_rank_distance"] is None
    assert dataset["endpoint_participation_gini"] is None
    assert dataset["degree_p80_fraction"] is None
    assert dataset["record_movement_count"] is None
    assert dataset["movements_per_node"] is None
    assert dataset["peak_auxiliary_storage_fraction"] is None
    assert dataset["combined_efficiency_equal_weights"] is None
    assert json.loads(output.read_text()) == document


def test_dashboard_has_three_distribution_views() -> None:
    source = (Path(__file__).parents[1] / "visualization" / "distributions.html").read_text()
    assert 'id="linear"' in source
    assert 'id="logpmf"' in source
    assert 'id="ccdf"' in source
    assert "These are descriptive measures" in source
    assert "({x,c:+c,y:c/total})" in source
    assert "({x,+c" not in source


def test_every_metrics_column_is_sortable() -> None:
    source = (Path(__file__).parents[1] / "visualization" / "distributions.html").read_text()
    for key in (
        "algorithm",
        "comparison_mean",
        "efficiency_ratio",
        "normalized_excess_comparisons",
        "record_movement_count",
        "movements_per_node",
        "peak_auxiliary_storage",
        "peak_auxiliary_storage_fraction",
        "mean_auxiliary_storage_fraction",
        "combined_cost_equal_weights",
        "combined_efficiency_equal_weights",
        "maximum_degree_mean",
        "degree_cv_mean",
        "degree_gini_mean",
        "degree_p80_fraction",
        "tail_alpha",
        "tail_xmin",
        "tail_fraction",
        "tail_span_decades",
        "tail_ks_distance",
        "tail_ccdf_r_squared",
        "power_vs_exponential_llr",
        "mean_rank_distance",
        "mean_normalized_rank_distance",
        "critical_comparison_fraction",
        "long_range_comparison_fraction",
        "mean_information_gain",
        "maximum_information_gain",
        "multi_relation_gain_fraction",
        "maximum_active_edge_count",
        "maximum_active_edge_fraction",
        "mean_active_edge_count",
        "retired_active_edge_count",
        "maximum_retired_per_comparison",
        "retirement_comparison_fraction",
        "endpoint_participation_gini",
        "busiest_node_comparison_fraction",
        "top_10_percent_endpoint_share",
    ):
        assert f"key:'{key}'" in source
    assert "function sortedMetrics()" in source
    assert "sortDirection*=-1" in source
    assert "aria-sort" in source


def test_dashboard_columns_can_be_hidden_and_reordered() -> None:
    source = (Path(__file__).parents[1] / "visualization" / "distributions.html").read_text()
    assert 'id="columns-button"' in source
    assert 'id="column-panel"' in source
    assert "function drawColumnControls()" in source
    assert "data-column=" in source
    assert "data-move=" in source
    assert "localStorage.setItem('scn-distribution-columns-v1'" in source
    assert "defaultColumnState" in source


def test_dashboard_has_project_result_and_experiment_controls() -> None:
    source = (Path(__file__).parents[1] / "visualization" / "distributions.html").read_text()
    for identifier in (
        "project-root",
        "use-root",
        "result-set",
        "refresh-results",
        "load-result",
        "algorithm-choices",
        "size-choices",
        "run-experiment",
        "run-log",
    ):
        assert f'id="{identifier}"' in source
    assert "api('/api/project'" in source
    assert "api('/api/results'" in source
    assert "api('/api/run'" in source


def test_algorithm_visibility_controls_follow_project_console() -> None:
    source = (Path(__file__).parents[1] / "visualization" / "distributions.html").read_text()
    assert source.index('class="console"') < source.index('id="series"')
    assert source.index('id="series"') < source.index('id="linear"')
