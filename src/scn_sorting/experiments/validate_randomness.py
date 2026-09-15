"""Validate generated permutation datasets and write randomness diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scn_sorting.analysis.randomness import diagnose_permutation_ensemble
from scn_sorting.experiments.permutations import (
    GENERATOR_NAME,
    GENERATOR_VERSION,
    PRODUCTION_SIZES,
    find_duplicate_permutations,
    generate_permutation,
    read_dataset,
)


def validate_dataset(directory: Path, n: int, alpha: float) -> dict[str, object]:
    manifest_path = directory / f"permutations-n{n}.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data_path = directory / manifest["data_file"]
    checksum = hashlib.sha256(data_path.read_bytes()).hexdigest()
    if checksum != manifest["data_sha256"]:
        raise ValueError(f"n={n}: data checksum does not match manifest")
    if manifest["generator"] != GENERATOR_NAME or manifest["generator_version"] != GENERATOR_VERSION:
        raise ValueError(f"n={n}: unsupported generator identity or version")

    records = read_dataset(data_path)
    if len(records) != 1000:
        raise ValueError(f"n={n}: expected 1000 records, received {len(records)}")
    seeds = [seed for row_n, seed, _ in records if row_n == n]
    if seeds != list(range(1, 1001)) or len(seeds) != len(records):
        raise ValueError(f"n={n}: expected ordered seeds 1..1000")
    permutations = [permutation for _, _, permutation in records]
    duplicates = find_duplicate_permutations(permutations)
    if duplicates:
        raise ValueError(f"n={n}: duplicate permutations at row pairs {duplicates}")
    for _, seed, permutation in records:
        if permutation != generate_permutation(n, seed):
            raise ValueError(f"n={n}, seed={seed}: regeneration mismatch")

    report = diagnose_permutation_ensemble(permutations, alpha=alpha)
    report["hard_validation"] = {
        "status": "pass",
        "checksum": checksum,
        "permutations_valid": True,
        "seeds_complete": True,
        "reproducible": True,
        "duplicates": 0,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/generated"))
    parser.add_argument(
        "--output", type=Path, default=Path("data/results/randomness-report.json")
    )
    parser.add_argument("--sizes", type=int, nargs="+", default=list(PRODUCTION_SIZES))
    parser.add_argument("--alpha", type=float, default=0.01)
    arguments = parser.parse_args()
    if not 0 < arguments.alpha < 1:
        parser.error("--alpha must be between zero and one")

    reports = []
    for n in arguments.sizes:
        print(f"validating n={n}...", flush=True)
        report = validate_dataset(arguments.input, n, arguments.alpha)
        reports.append(report)
        print(f"n={n}: {report['status']}", flush=True)

    complete_report = {
        "schema_version": 1,
        "generator": GENERATOR_NAME,
        "generator_version": GENERATOR_VERSION,
        "overall_status": "warning" if any(r["status"] == "warning" for r in reports) else "pass",
        "reports": reports,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(complete_report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {arguments.output}")


if __name__ == "__main__":
    main()

