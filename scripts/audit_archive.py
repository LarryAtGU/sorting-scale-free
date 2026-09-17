#!/usr/bin/env python3
"""Verify the completeness and integrity of the deposited research archive."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/archive-manifest.sha256"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_hashes() -> None:
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"SHA-256 mismatch for {relative}: {actual}")


def count_gzip_jsonl(relative: str) -> int:
    with gzip.open(ROOT / relative, "rt", encoding="utf-8") as stream:
        count = 0
        for count, line in enumerate(stream, 1):
            json.loads(line)
    return count


def read_csv(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    check_hashes()

    observational_runs = count_gzip_jsonl(
        "data/results/batch-paper-final-19-algorithms-runs.jsonl.gz"
    )
    if observational_runs != 114_000:
        raise ValueError(f"expected 114000 observational runs, found {observational_runs}")
    observational_summary = read_csv(
        "data/results/batch-paper-final-19-algorithms-summary.csv"
    )
    if len(observational_summary) != 114:
        raise ValueError(f"expected 114 observational cells, found {len(observational_summary)}")
    if any(int(row["trials"]) != 1000 for row in observational_summary):
        raise ValueError("an observational summary cell does not contain 1000 trials")

    temporal_runs = count_gzip_jsonl("data/results/temporal-mechanism-v1/runs.jsonl.gz")
    if temporal_runs != 8_800:
        raise ValueError(f"expected 8800 temporal runs, found {temporal_runs}")
    temporal_summary = read_csv("data/results/temporal-mechanism-v1/summary.csv")
    if len(temporal_summary) != 44:
        raise ValueError(f"expected 44 temporal cells, found {len(temporal_summary)}")
    if any(int(row["trials"]) != 200 for row in temporal_summary):
        raise ValueError("a temporal summary cell does not contain 200 trials")

    temporal_manifest = json.loads(
        (ROOT / "data/results/temporal-mechanism-v1/manifest.json").read_text()
    )
    if temporal_manifest["config_sha256"] != (
        "ab7369843a74b51584978fd666da810aace7acfaff18693f3b59eb400550f13f"
    ):
        raise ValueError("unexpected temporal configuration hash")

    print("archive audit passed")
    print(f"observational: {observational_runs} runs, {len(observational_summary)} cells")
    print(f"temporal: {temporal_runs} runs, {len(temporal_summary)} cells")
    print(f"verified files: {len(MANIFEST.read_text().splitlines())}")


if __name__ == "__main__":
    main()
