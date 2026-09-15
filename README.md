# Sorting Comparison Network Experiments

Reproducible experiments relating comparison-sort efficiency to the structure
of sorting comparison networks (SCNs).

## Project layout

```text
configs/             Version-controlled experiment configurations
data/generated/      Reproducible generated permutations (not committed)
data/results/        Raw and summarized experiment results (not committed)
docs/                Mathematical definitions and research notes
figures/             Publication-ready generated figures (not committed)
scripts/             Command-line entry scripts
src/scn_sorting/     Python package
  algorithms/        Instrumented sorting algorithms
  analysis/          Statistical and network analysis
  experiments/       Experiment generation and execution
  instrumentation/   Records, comparison tracking, and SCN construction
tests/                Automated correctness and measurement tests
```

Git has intentionally not been initialized. The experimental implementation
will be added after the mathematical SCN and redundancy definitions are fixed.

## Exporting and viewing an SCN trace

With the virtual environment activated, export one step-by-step trace:

```bash
scn-export-trace --algorithm quick --n 32 --seed 1
```

Start the local viewer server from the project root:

```bash
./scripts/serve_viewer.sh
```

Then open [http://127.0.0.1:8765/viewer.html](http://127.0.0.1:8765/viewer.html)
and select the generated JSON file from `data/results/`. Serving the page avoids
browser restrictions on `file://` pages and ensures the permanent project copy
is used rather than a temporary staging file.

The viewer supports directed edges, step/play/pause, timeline seeking,
degree-based node sizing, transitive-reduction display, and input-order,
sorted-order, stable, or gradually improving force layouts.

Trace export is optional. Production statistical runs do not retain event traces
or execute visualization/layout code.

View the cross-algorithm degree distributions at
[http://127.0.0.1:8765/distributions.html](http://127.0.0.1:8765/distributions.html).
The dashboard shows the ordinary degree probability, log-log probability, and
log-log CCDF together with comparison-efficiency and degree-inequality metrics.

The distribution page also acts as a local experiment console. It identifies
the project root, searches `data/results/` recursively for batch summary files,
loads any discovered result directly, and launches validated batch experiments.
The page constructs an allowlisted `scn-run-batch` command from the selected
algorithms, generated input sizes, seed interval, and output label; it cannot
execute arbitrary shell commands. Experiment output and completion status are
shown in the page, and a completed result is discovered and loaded automatically.

If automatic project-root discovery is unavailable, enter the absolute project
folder in the **Project root** box and choose **Use folder**. The folder must
contain this project's `pyproject.toml`, `src/scn_sorting/`, and visualization.

Nodes can be selected and dragged directly on the canvas. In `Stable` layout,
dragged nodes remain fixed. In `Force` layout, a node is fixed during the drag
and released back into the simulation when the pointer is released.

## Running batch statistics

The registry spans elementary, insertion, merge, heap, quicksort, sorting-network,
Shell, tournament, and tree-sort families. Additional mechanism controls are
`shell`, `introsort`, `tournament`, `tree-unbalanced`, `tree-avl`, `quick-random`,
and `odd-even-merge-network`. Network algorithms require power-of-two sizes.
The pseudo-random pivot in `quick-random` is deterministically derived from each
subproblem, avoiding hidden global random state.

Run a selected size and seed range headlessly:

```bash
scn-run-batch --sizes 128 --first-seed 1 --last-seed 1000 --label first-stage-n128
```

Select particular algorithms when required:

```bash
scn-run-batch --algorithms quick heap binary-insertion \
  --sizes 128 256 --first-seed 1 --last-seed 100 --label pilot
```

Each run writes compressed per-execution JSON Lines and a CSV summary under
`data/results/`. Large quadratic algorithms should be scheduled separately for
large input sizes; 1,000 Bubble-sort executions at `n=4096` require billions of
comparisons.

For large degree-distribution experiments, omit the expensive online transitive
closure and active-link measures:

```bash
scn-run-batch --distribution-only --sizes 1024 2048 4096 \
  --first-seed 1 --last-seed 100 --label large-distributions
```

This profile preserves sorting correctness, comparison and unique-edge counts,
SCN degrees, rank distances, endpoint participation, record movements, and
auxiliary storage. Mechanism-only fields such as information gain and active
links are zero and must be obtained from an exact run.

Every completed trial is appended immediately to
`batch-<label>-checkpoint.jsonl`, and the partial CSV summary is refreshed after
each algorithm. Repeating the identical command resumes the checkpoint and
skips completed `(algorithm, n, seed)` trials. Do not reuse a label when changing
between exact and distribution-only profiles.

## Inspecting generated datasets

Generated permutation datasets are gzip-compressed JSON Lines files. Each line
is one JSON record containing `n`, `seed`, and `permutation`.

Preview the first record without extracting the file:

```bash
gzip -dc data/generated/permutations-n128.jsonl.gz | head -n 1
```

Pretty-print the first record:

```bash
gzip -dc data/generated/permutations-n128.jsonl.gz \
  | head -n 1 \
  | python -m json.tool
```

Inspect a particular trial. Because seeds are stored in order from 1 through
1,000, line 10 contains seed 10:

```bash
gzip -dc data/generated/permutations-n128.jsonl.gz \
  | sed -n '10p' \
  | python -m json.tool
```

Extract the complete file while retaining the compressed original:

```bash
gzip -dk data/generated/permutations-n128.jsonl.gz
```

This creates `data/generated/permutations-n128.jsonl`. For larger input sizes,
previewing individual records is preferable to opening the complete extracted
file in an editor.
