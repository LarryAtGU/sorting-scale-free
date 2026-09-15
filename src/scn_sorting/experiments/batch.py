"""Headless batch execution and SCN summary generation."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import math
from collections import Counter
from pathlib import Path
from statistics import fmean, stdev

from scn_sorting.algorithms.initial import ALGORITHMS
from scn_sorting.experiments.permutations import PRODUCTION_SIZES, read_dataset
from scn_sorting.experiments.runner import run_sort


def gini(values: tuple[int, ...]) -> float:
    if not values or sum(values) == 0:
        return 0.0
    ordered = sorted(values)
    count = len(ordered)
    weighted = sum((index + 1) * value for index, value in enumerate(ordered))
    return (2 * weighted) / (count * sum(ordered)) - (count + 1) / count


def pareto_node_fraction(values: tuple[int, ...], target: float = 0.8) -> float:
    """Return the smallest node fraction accounting for ``target`` of the total."""
    if not 0 < target <= 1:
        raise ValueError("target must be in (0, 1]")
    total = sum(values)
    if not values or total == 0:
        return 0.0
    threshold = target * total
    cumulative = 0
    for count, value in enumerate(sorted(values, reverse=True), start=1):
        cumulative += value
        if cumulative >= threshold:
            return count / len(values)
    return 1.0


def run_record(
    algorithm: str,
    n: int,
    seed: int,
    permutation: tuple[int, ...],
    *,
    distribution_only: bool = False,
) -> dict[str, object]:
    run = run_sort(algorithm, permutation, distribution_only=distribution_only)
    summary = run.summary
    degree_mean = summary.mean_degree
    degree_variance = (
        sum((degree - degree_mean) ** 2 for degree in summary.total_degree) / n if n else 0.0
    )
    lower_bound = math.lgamma(n + 1) / math.log(2)
    participation = summary.comparison_participation
    endpoint_total = sum(participation)
    top_count = max(1, math.ceil(n * 0.1)) if n else 0
    comparison_excess = summary.comparison_count / lower_bound - 1
    movements_per_node = summary.record_movement_count / n if n else 0.0
    peak_storage_fraction = summary.peak_auxiliary_storage / n if n else 0.0
    mean_storage_fraction = summary.mean_auxiliary_storage / n if n else 0.0
    combined_cost = comparison_excess + movements_per_node + peak_storage_fraction
    return {
        "algorithm": algorithm,
        "n": n,
        "seed": seed,
        "tracking_profile": "distribution" if distribution_only else "exact",
        "comparison_count": summary.comparison_count,
        "unique_edge_count": summary.unique_edge_count,
        "repeated_comparison_count": summary.repeated_comparison_count,
        "implied_comparison_count": summary.implied_comparison_count,
        "comparison_efficiency_ratio": summary.comparison_count / lower_bound,
        "normalized_excess_comparisons": comparison_excess,
        "record_movement_count": summary.record_movement_count,
        "movements_per_node": movements_per_node,
        "peak_auxiliary_storage": summary.peak_auxiliary_storage,
        "peak_auxiliary_storage_fraction": peak_storage_fraction,
        "mean_auxiliary_storage_fraction": mean_storage_fraction,
        "combined_cost_equal_weights": combined_cost,
        "combined_efficiency_equal_weights": 1 / (1 + combined_cost),
        "mean_degree": degree_mean,
        "maximum_degree": summary.maximum_degree,
        "degree_variance": degree_variance,
        "degree_cv": math.sqrt(degree_variance) / degree_mean if degree_mean else 0.0,
        "degree_gini": gini(summary.total_degree),
        "degree_p80_fraction": pareto_node_fraction(summary.total_degree),
        "mean_rank_distance": summary.mean_rank_distance,
        "mean_normalized_rank_distance": summary.mean_normalized_rank_distance,
        "critical_comparison_fraction": summary.critical_comparison_fraction,
        "long_range_comparison_fraction": summary.long_range_comparison_fraction,
        "mean_information_gain": summary.mean_information_gain,
        "maximum_information_gain": summary.maximum_information_gain,
        "multi_relation_gain_fraction": summary.multi_relation_gain_fraction,
        "maximum_active_edge_count": summary.maximum_active_edge_count,
        "maximum_active_edge_fraction": (
            summary.maximum_active_edge_count / (n * n // 4) if n > 1 else 0.0
        ),
        "mean_active_edge_count": summary.mean_active_edge_count,
        "retired_active_edge_count": summary.retired_active_edge_count,
        "maximum_retired_per_comparison": summary.maximum_retired_per_comparison,
        "retirement_comparison_fraction": summary.retirement_comparison_fraction,
        "endpoint_participation_gini": gini(participation),
        "busiest_node_comparison_fraction": (
            max(participation, default=0) / summary.comparison_count
            if summary.comparison_count
            else 0.0
        ),
        "top_10_percent_endpoint_share": (
            sum(sorted(participation, reverse=True)[:top_count]) / endpoint_total
            if endpoint_total
            else 0.0
        ),
        "rank_distance_histogram": dict(summary.rank_distance_histogram),
        "information_gain_histogram": dict(summary.information_gain_histogram),
        "degree_histogram": dict(sorted(Counter(summary.total_degree).items())),
    }


def summarize(records: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, int], list[dict[str, object]]] = {}
    for record in records:
        groups.setdefault((str(record["algorithm"]), int(record["n"])), []).append(record)
    fields = [
        "comparison_count",
        "unique_edge_count",
        "repeated_comparison_count",
        "implied_comparison_count",
        "comparison_efficiency_ratio",
        "normalized_excess_comparisons",
        "record_movement_count",
        "movements_per_node",
        "peak_auxiliary_storage",
        "peak_auxiliary_storage_fraction",
        "mean_auxiliary_storage_fraction",
        "combined_cost_equal_weights",
        "combined_efficiency_equal_weights",
        "mean_degree",
        "maximum_degree",
        "degree_variance",
        "degree_cv",
        "degree_gini",
        "degree_p80_fraction",
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
    ]
    output = []
    for (algorithm, n), group in sorted(groups.items()):
        row: dict[str, object] = {"algorithm": algorithm, "n": n, "trials": len(group)}
        for field in fields:
            values = [float(record[field]) for record in group]
            row[f"{field}_mean"] = fmean(values)
            row[f"{field}_sd"] = stdev(values) if len(values) > 1 else 0.0
        histogram: Counter[int] = Counter()
        distance_histogram: Counter[int] = Counter()
        information_gain_histogram: Counter[int] = Counter()
        for record in group:
            histogram.update({int(k): int(v) for k, v in record["degree_histogram"].items()})
            distance_histogram.update(
                {int(k): int(v) for k, v in record["rank_distance_histogram"].items()}
            )
            information_gain_histogram.update(
                {int(k): int(v) for k, v in record["information_gain_histogram"].items()}
            )
        row["aggregate_degree_histogram"] = json.dumps(dict(sorted(histogram.items())))
        row["aggregate_rank_distance_histogram"] = json.dumps(
            dict(sorted(distance_histogram.items()))
        )
        row["aggregate_information_gain_histogram"] = json.dumps(
            dict(sorted(information_gain_histogram.items()))
        )
        output.append(row)
    return output


def write_raw(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed,
        io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as stream,
    ):
        for record in records:
            stream.write(json.dumps(record, separators=(",", ":")) + "\n")


def write_summary(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("cannot write an empty summary")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_checkpoint(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid checkpoint line {line_number}: {path}") from error
    return records


def append_checkpoint(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, separators=(",", ":")) + "\n")
        stream.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/generated"))
    parser.add_argument("--output", type=Path, default=Path("data/results"))
    parser.add_argument("--algorithms", nargs="+", choices=sorted(ALGORITHMS), default=sorted(ALGORITHMS))
    parser.add_argument("--sizes", nargs="+", type=int, default=list(PRODUCTION_SIZES))
    parser.add_argument("--first-seed", type=int, default=1)
    parser.add_argument("--last-seed", type=int, default=1000)
    parser.add_argument("--label", default="production")
    parser.add_argument(
        "--distribution-only",
        action="store_true",
        help="skip transitive-closure mechanism metrics for scalable degree-distribution runs",
    )
    arguments = parser.parse_args()
    if arguments.first_seed < 1 or arguments.last_seed > 1000 or arguments.first_seed > arguments.last_seed:
        parser.error("seed range must satisfy 1 <= first <= last <= 1000")

    raw_path = arguments.output / f"batch-{arguments.label}-runs.jsonl.gz"
    summary_path = arguments.output / f"batch-{arguments.label}-summary.csv"
    checkpoint_path = arguments.output / f"batch-{arguments.label}-checkpoint.jsonl"
    requested_profile = "distribution" if arguments.distribution_only else "exact"
    records = read_checkpoint(checkpoint_path)
    requested_algorithms = set(arguments.algorithms)
    requested_sizes = set(arguments.sizes)
    records = [
        record
        for record in records
        if str(record["algorithm"]) in requested_algorithms
        and int(record["n"]) in requested_sizes
        and arguments.first_seed <= int(record["seed"]) <= arguments.last_seed
    ]
    wrong_profile = [
        record
        for record in records
        if record.get("tracking_profile", "exact") != requested_profile
    ]
    if wrong_profile:
        parser.error(f"checkpoint tracking profile does not match {requested_profile!r}")
    completed = {
        (str(record["algorithm"]), int(record["n"]), int(record["seed"]))
        for record in records
    }
    if completed:
        print(f"resuming from {len(completed)} completed trials in {checkpoint_path}", flush=True)
    for n in arguments.sizes:
        dataset = read_dataset(arguments.input / f"permutations-n{n}.jsonl.gz")
        selected = [row for row in dataset if arguments.first_seed <= row[1] <= arguments.last_seed]
        for algorithm in arguments.algorithms:
            pending = [row for row in selected if (algorithm, n, row[1]) not in completed]
            print(
                f"running {algorithm}, n={n}, pending={len(pending)}, "
                f"complete={len(selected) - len(pending)}",
                flush=True,
            )
            for _, seed, permutation in pending:
                record = run_record(
                    algorithm,
                    n,
                    seed,
                    permutation,
                    distribution_only=arguments.distribution_only,
                )
                records.append(record)
                append_checkpoint(checkpoint_path, record)
                completed.add((algorithm, n, seed))
            if records:
                write_summary(summary_path, summarize(records))

    write_raw(raw_path, records)
    write_summary(summary_path, summarize(records))
    print(f"wrote {raw_path}")
    print(f"wrote {summary_path}")


if __name__ == "__main__":
    main()
