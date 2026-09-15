"""Export one instrumented sorting trace for interactive replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scn_sorting.algorithms.initial import ALGORITHMS
from scn_sorting.experiments.permutations import generate_permutation
from scn_sorting.experiments.runner import run_sort


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algorithm", choices=sorted(ALGORITHMS), required=True)
    parser.add_argument("--n", type=int, default=32)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.n < 1:
        parser.error("--n must be positive")
    permutation = generate_permutation(arguments.n, arguments.seed)
    run = run_sort(arguments.algorithm, permutation, retain_trace=True)
    document = run.tracker.trace_document(
        algorithm=arguments.algorithm, input_values=permutation
    )
    document["seed"] = arguments.seed
    document["output"] = run.output_values
    output = arguments.output or Path(
        f"data/results/trace-{arguments.algorithm}-n{arguments.n}-seed{arguments.seed}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output} ({run.summary.comparison_count} comparison events)")


if __name__ == "__main__":
    main()

