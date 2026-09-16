"""Run the frozen temporal representative-exposure experiment."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import fmean, stdev
from typing import Any

from scn_sorting.algorithms.initial import ALGORITHMS
from scn_sorting.experiments.batch import (
    append_checkpoint,
    read_checkpoint,
    run_record,
    summarize,
    write_raw,
    write_summary,
)
from scn_sorting.experiments.permutations import read_dataset

MECHANISM_FIELDS = (
    "representative_comparison_count",
    "representative_comparison_fraction",
    "representative_node_count",
    "representative_node_fraction",
    "representative_exposure_gini",
    "representative_exposure_p80_fraction",
    "maximum_representative_exposure_share",
    "mean_represented_span",
    "maximum_represented_span",
    "mean_representative_lifetime_fraction",
    "representative_exposure_degree_correlation",
    "representative_exposure_strength_correlation",
    "mean_span_degree_correlation",
)


def experiment_manifest(
    config: Path,
    algorithms: list[str],
    sizes: list[int],
    first_seed: int,
    last_seed: int,
) -> dict[str, object]:
    """Fingerprint the protocol and implementation that produced a checkpoint."""
    project_root = Path(__file__).resolve().parents[3]
    source_paths = [
        project_root / "src/scn_sorting/algorithms/initial.py",
        project_root / "src/scn_sorting/algorithms/expanded.py",
        project_root / "src/scn_sorting/instrumentation/core.py",
        project_root / "src/scn_sorting/experiments/batch.py",
        Path(__file__).resolve(),
    ]
    return {
        "schema_version": 1,
        "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "implementation_sha256": {
            str(path.relative_to(project_root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_paths
        },
        "algorithms": algorithms,
        "sizes": sizes,
        "first_seed": first_seed,
        "last_seed": last_seed,
        "tracking_profile": "temporal-mechanism-distribution",
    }


def validate_or_write_manifest(path: Path, manifest: dict[str, object]) -> None:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != manifest:
            raise ValueError(
                f"experiment manifest differs from the existing run: {path}; "
                "use a new output directory"
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_protocol(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        protocol = json.load(stream)
    required = {"label", "algorithms", "sizes", "first_seed", "last_seed"}
    missing = required - protocol.keys()
    if missing:
        raise ValueError(f"protocol is missing fields: {sorted(missing)}")
    unknown = set(protocol["algorithms"]) - ALGORITHMS.keys()
    if unknown:
        raise ValueError(f"protocol contains unknown algorithms: {sorted(unknown)}")
    return protocol


def summarize_mechanisms(records: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = {(str(row["algorithm"]), int(row["n"])): row for row in summarize(records)}
    groups: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        groups[(str(record["algorithm"]), int(record["n"]))].append(record)
    for key, group in groups.items():
        row = rows[key]
        for field in MECHANISM_FIELDS:
            values = [float(record["mechanism"][field]) for record in group]  # type: ignore[index]
            row[f"{field}_mean"] = fmean(values)
            row[f"{field}_sd"] = stdev(values) if len(values) > 1 else 0.0
    return [rows[key] for key in sorted(rows)]


def attachment_rows(records: list[dict[str, object]]) -> list[dict[str, object]]:
    totals: dict[tuple[str, int, int], list[int]] = defaultdict(lambda: [0, 0, 0])
    for record in records:
        mechanism = record["mechanism"]  # type: ignore[assignment]
        for cell in mechanism["attachment_kernel"]:  # type: ignore[index]
            key = (str(record["algorithm"]), int(record["n"]), int(cell["current_strength"]))
            totals[key][0] += int(cell["endpoint_selections"])
            totals[key][1] += int(cell["node_event_opportunities"])
            totals[key][2] += 1
    return [
        {
            "algorithm": algorithm,
            "n": n,
            "current_strength": strength,
            "endpoint_selections": selected,
            "node_event_opportunities": opportunities,
            "selection_rate": selected / opportunities if opportunities else 0.0,
            "contributing_runs": runs,
        }
        for (algorithm, n, strength), (selected, opportunities, runs) in sorted(totals.items())
    ]


def snapshot_rows(records: list[dict[str, object]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for record in records:
        comparison_count = int(record["comparison_count"])
        mechanism = record["mechanism"]  # type: ignore[assignment]
        for snapshot in mechanism["snapshots"]:  # type: ignore[index]
            row = {
                "algorithm": record["algorithm"],
                "n": record["n"],
                "seed": record["seed"],
                **snapshot,
            }
            row["progress_fraction"] = (
                int(snapshot["comparison_count"]) / comparison_count if comparison_count else 0.0
            )
            output.append(row)
    return output


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/temporal-mechanism-v1.json"))
    parser.add_argument("--input", type=Path, default=Path("data/generated"))
    parser.add_argument("--output", type=Path, default=Path("data/results/temporal-mechanism-v1"))
    parser.add_argument("--first-seed", type=int, help="override protocol for staged execution")
    parser.add_argument("--last-seed", type=int, help="override protocol for staged execution")
    parser.add_argument("--sizes", nargs="+", type=int, help="override protocol for smoke tests")
    arguments = parser.parse_args()

    protocol = load_protocol(arguments.config)
    first_seed = arguments.first_seed or int(protocol["first_seed"])
    last_seed = arguments.last_seed or int(protocol["last_seed"])
    sizes = arguments.sizes or [int(value) for value in protocol["sizes"]]
    algorithms = [str(value) for value in protocol["algorithms"]]
    if not 1 <= first_seed <= last_seed <= 1000:
        parser.error("seed range must satisfy 1 <= first <= last <= 1000")

    output = arguments.output
    validate_or_write_manifest(
        output / "manifest.json",
        experiment_manifest(arguments.config, algorithms, sizes, first_seed, last_seed),
    )
    checkpoint_path = output / "checkpoint.jsonl"
    raw_path = output / "runs.jsonl.gz"
    summary_path = output / "summary.csv"
    attachment_path = output / "attachment-kernel.csv"
    snapshots_path = output / "snapshots.csv"
    records = read_checkpoint(checkpoint_path)
    expected = {
        (algorithm, n, seed)
        for algorithm in algorithms
        for n in sizes
        for seed in range(first_seed, last_seed + 1)
    }
    records = [
        record
        for record in records
        if (str(record["algorithm"]), int(record["n"]), int(record["seed"])) in expected
    ]
    if any("mechanism" not in record for record in records):
        parser.error("checkpoint contains records from a different tracking profile")
    completed = {
        (str(record["algorithm"]), int(record["n"]), int(record["seed"])) for record in records
    }
    if completed:
        print(f"resuming from {len(completed)} completed executions", flush=True)

    for n in sizes:
        dataset = read_dataset(arguments.input / f"permutations-n{n}.jsonl.gz")
        selected = {
            seed: permutation for _, seed, permutation in dataset if first_seed <= seed <= last_seed
        }
        missing_seeds = set(range(first_seed, last_seed + 1)) - selected.keys()
        if missing_seeds:
            raise ValueError(f"dataset n={n} is missing seeds: {sorted(missing_seeds)[:10]}")
        for algorithm in algorithms:
            pending = [seed for seed in sorted(selected) if (algorithm, n, seed) not in completed]
            print(f"running {algorithm}, n={n}, pending={len(pending)}", flush=True)
            for seed in pending:
                record = run_record(
                    algorithm,
                    n,
                    seed,
                    selected[seed],
                    distribution_only=True,
                    mechanism_tracking=True,
                )
                records.append(record)
                append_checkpoint(checkpoint_path, record)
                completed.add((algorithm, n, seed))
            if records:
                write_summary(summary_path, summarize_mechanisms(records))

    write_raw(raw_path, records)
    write_summary(summary_path, summarize_mechanisms(records))
    write_csv(attachment_path, attachment_rows(records))
    write_csv(snapshots_path, snapshot_rows(records))
    print(f"completed {len(records)} executions")
    for path in (raw_path, summary_path, attachment_path, snapshots_path):
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
