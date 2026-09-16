# Scripts

## Install development dependencies

From the project root, run:

```bash
./scripts/install_dependencies.sh
```

The script finds Python 3.11 or newer, creates `.venv`, installs the project and
its development dependencies, and runs the test suite. It is safe to run again
to update an existing environment.

After installation, activate the environment with:

```bash
source .venv/bin/activate
```

The installed `scn-generate-inputs` command generates deterministic permutation
datasets.

## Reproduce the frozen statistical validation

From the project root, run:

```bash
.venv/bin/python scripts/validate_frozen_results.py
.venv/bin/python scripts/make_paper_figures.py
```

The first command reads the frozen 19-algorithm summary and writes
`data/results/paper-final-statistical-validation.json`. The second recreates the
four manuscript figures in the sibling `over-leaf/figures/` directory. The
validation rules were frozen in `docs/statistical-validation-protocol.md` before
the reported values were calculated.
# Temporal mechanism experiment

The frozen representative-exposure experiment is resumable and reads
`configs/temporal-mechanism-v1.json` by default:

```bash
./scripts/run_temporal_mechanism.sh
```

For the prescribed smoke test (all algorithms, `n=128`, seeds 1--3), use:

```bash
./scripts/run_temporal_mechanism.sh --sizes 128 --first-seed 1 --last-seed 3 \
  --output data/results/temporal-mechanism-v1-smoke
```

The runner appends each execution to `checkpoint.jsonl`, so rerunning the same
command resumes completed work. Production outputs include compressed raw runs,
an algorithm-size summary, the aggregated attachment kernel, and temporal
snapshots.
