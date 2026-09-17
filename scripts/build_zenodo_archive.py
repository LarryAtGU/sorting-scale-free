#!/usr/bin/env python3
"""Build a data-complete Zenodo ZIP from the checked-out repository files."""

from __future__ import annotations

import argparse
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_FILES = (
    Path("data/results/batch-paper-final-19-algorithms-runs.jsonl.gz"),
    Path("data/results/temporal-mechanism-v1/runs.jsonl.gz"),
)


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    )
    return [Path(item.decode()) for item in output.split(b"\0") if item]


def verify_raw_payloads() -> None:
    for relative in RAW_FILES:
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"missing required raw dataset: {relative}")
        head = path.read_bytes()[:200]
        if head.startswith(b"version https://git-lfs.github.com/spec/"):
            raise SystemExit(f"Git LFS pointer found instead of data: {relative}")
        if path.stat().st_size < 1_000_000 or not head.startswith(b"\x1f\x8b"):
            raise SystemExit(f"invalid or unexpectedly small raw dataset: {relative}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="1.3.0")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    verify_raw_payloads()
    subprocess.run(["python3", "scripts/audit_archive.py"], cwd=ROOT, check=True)

    output = args.output or ROOT / "dist" / f"sorting-scale-free-{args.version}-complete.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    prefix = Path(f"sorting-scale-free-{args.version}")

    with zipfile.ZipFile(output, "w", allowZip64=True) as archive:
        for relative in tracked_files():
            path = ROOT / relative
            if not path.is_file():
                continue
            compression = zipfile.ZIP_STORED if path.suffix == ".gz" else zipfile.ZIP_DEFLATED
            archive.write(path, prefix / relative, compress_type=compression)

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        for relative in RAW_FILES:
            member = str(prefix / relative)
            if member not in names or archive.getinfo(member).file_size != (ROOT / relative).stat().st_size:
                raise SystemExit(f"archive verification failed for {relative}")

    print(f"wrote {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
