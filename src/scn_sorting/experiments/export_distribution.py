"""Convert a batch summary CSV into browser-ready distribution data."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from scn_sorting.analysis.powerlaw import fit_power_law_tail


def optional_mean(row: dict[str, str], field: str) -> float | None:
    value = row.get(f"{field}_mean")
    return float(value) if value not in (None, "") else None


def build_document(input_path: Path) -> dict[str, object]:
    rows = list(csv.DictReader(input_path.open(encoding="utf-8")))
    if not rows:
        raise ValueError("batch summary contains no rows")
    datasets = []
    for row in rows:
        trials = int(row["trials"])
        n = int(row["n"])
        histogram = {int(key): int(value) for key, value in json.loads(row["aggregate_degree_histogram"]).items()}
        if sum(histogram.values()) != trials * n:
            raise ValueError(f"degree histogram size mismatch for {row['algorithm']}, n={n}")
        tail = fit_power_law_tail(histogram)
        datasets.append(
            {
                "algorithm": row["algorithm"],
                "n": n,
                "trials": trials,
                "comparison_mean": float(row["comparison_count_mean"]),
                "efficiency_ratio": float(row["comparison_efficiency_ratio_mean"]),
                "normalized_excess_comparisons": optional_mean(row, "normalized_excess_comparisons"),
                "record_movement_count": optional_mean(row, "record_movement_count"),
                "movements_per_node": optional_mean(row, "movements_per_node"),
                "peak_auxiliary_storage": optional_mean(row, "peak_auxiliary_storage"),
                "peak_auxiliary_storage_fraction": optional_mean(row, "peak_auxiliary_storage_fraction"),
                "mean_auxiliary_storage_fraction": optional_mean(row, "mean_auxiliary_storage_fraction"),
                "combined_cost_equal_weights": optional_mean(row, "combined_cost_equal_weights"),
                "combined_efficiency_equal_weights": optional_mean(row, "combined_efficiency_equal_weights"),
                "maximum_degree_mean": float(row["maximum_degree_mean"]),
                "degree_cv_mean": float(row["degree_cv_mean"]),
                "degree_gini_mean": float(row["degree_gini_mean"]),
                "degree_p80_fraction": optional_mean(row, "degree_p80_fraction"),
                "mean_rank_distance": optional_mean(row, "mean_rank_distance"),
                "mean_normalized_rank_distance": optional_mean(
                    row, "mean_normalized_rank_distance"
                ),
                "critical_comparison_fraction": optional_mean(
                    row, "critical_comparison_fraction"
                ),
                "long_range_comparison_fraction": optional_mean(
                    row, "long_range_comparison_fraction"
                ),
                "mean_information_gain": optional_mean(row, "mean_information_gain"),
                "maximum_information_gain": optional_mean(row, "maximum_information_gain"),
                "multi_relation_gain_fraction": optional_mean(
                    row, "multi_relation_gain_fraction"
                ),
                "maximum_active_edge_count": optional_mean(row, "maximum_active_edge_count"),
                "maximum_active_edge_fraction": optional_mean(
                    row, "maximum_active_edge_fraction"
                ),
                "mean_active_edge_count": optional_mean(row, "mean_active_edge_count"),
                "retired_active_edge_count": optional_mean(row, "retired_active_edge_count"),
                "maximum_retired_per_comparison": optional_mean(
                    row, "maximum_retired_per_comparison"
                ),
                "retirement_comparison_fraction": optional_mean(
                    row, "retirement_comparison_fraction"
                ),
                "endpoint_participation_gini": optional_mean(
                    row, "endpoint_participation_gini"
                ),
                "busiest_node_comparison_fraction": optional_mean(
                    row, "busiest_node_comparison_fraction"
                ),
                "top_10_percent_endpoint_share": optional_mean(
                    row, "top_10_percent_endpoint_share"
                ),
                "tail_alpha": tail.alpha,
                "tail_xmin": tail.xmin,
                "tail_count": tail.tail_count,
                "tail_fraction": tail.tail_fraction,
                "tail_span_decades": tail.tail_span_decades,
                "tail_ks_distance": tail.ks_distance,
                "tail_ccdf_r_squared": tail.loglog_ccdf_r_squared,
                "power_vs_exponential_llr": tail.power_vs_exponential_llr_per_observation,
                "histogram": [[degree, count] for degree, count in sorted(histogram.items())],
                "rank_distance_histogram": [
                    [int(distance), int(count)]
                    for distance, count in sorted(
                        json.loads(row.get("aggregate_rank_distance_histogram", "{}")).items(),
                        key=lambda item: int(item[0]),
                    )
                ],
                "information_gain_histogram": [
                    [int(gain), int(count)]
                    for gain, count in sorted(
                        json.loads(row.get("aggregate_information_gain_histogram", "{}")).items(),
                        key=lambda item: int(item[0]),
                    )
                ],
            }
        )
    return {"schema_version": 1, "datasets": datasets}


def convert_summary(input_path: Path, output_path: Path) -> dict[str, object]:
    document = build_document(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(document, separators=(",", ":")) + "\n", encoding="utf-8")
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    document = convert_summary(arguments.input, arguments.output)
    print(f"wrote {arguments.output} ({len(document['datasets'])} algorithm distributions)")


if __name__ == "__main__":
    main()
