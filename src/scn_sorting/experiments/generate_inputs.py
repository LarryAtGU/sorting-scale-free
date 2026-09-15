"""Command-line entry point for deterministic permutation datasets."""

from __future__ import annotations

import argparse
from pathlib import Path

from scn_sorting.experiments.permutations import PRODUCTION_SEEDS, PRODUCTION_SIZES, write_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/generated"),
        help="output directory (default: data/generated)",
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=list(PRODUCTION_SIZES),
        help="input sizes",
    )
    parser.add_argument("--first-seed", type=int, default=PRODUCTION_SEEDS.start)
    parser.add_argument("--last-seed", type=int, default=PRODUCTION_SEEDS.stop - 1)
    arguments = parser.parse_args()

    if arguments.first_seed > arguments.last_seed:
        parser.error("--first-seed must not exceed --last-seed")

    seeds = range(arguments.first_seed, arguments.last_seed + 1)
    for n in arguments.sizes:
        manifest = write_dataset(arguments.output, n, seeds)
        print(
            f"generated n={n}: {manifest.sequence_count} permutations -> "
            f"{arguments.output / manifest.data_file}"
        )


if __name__ == "__main__":
    main()

