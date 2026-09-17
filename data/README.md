# Deposited experimental data

## Observational experiment

- `results/batch-paper-final-19-algorithms-runs.jsonl.gz`: all 114,000
  per-execution records (Git LFS).
- `results/batch-paper-final-19-algorithms-summary.csv`: 114 algorithm-size
  summaries, including aggregate degree histograms.
- `results/paper-final-19-algorithms.log`: production execution log.
- `results/paper-final-statistical-validation.json`: frozen primary validation.
- `results/paper-secondary-analysis.json`: resource, family, cutoff, and block
  analyses.
- `results/paper-theory-validation.json`: exact-BST and mechanism checks.

## Temporal mechanism experiment

`results/temporal-mechanism-v1/` contains the complete 8,800-run compressed
record, algorithm-size summary, temporal snapshots, global endpoint-exposure
rates, run log, and integrity manifest. The append-only checkpoint is excluded
because it duplicates the finalized compressed run record.

## Inputs

Uniform permutations are deterministic functions of input size and seed.
`generated/*.manifest.json` stores the count and SHA-256 digest for each
generated input file. The permutations can be regenerated exactly with
`scn-generate-inputs`. `results/randomness-report.json` records the input checks.

## Integrity

After Git LFS objects have been downloaded, verify the deposited files with:

```bash
python scripts/audit_archive.py
```

The audit checks required files, gzip readability, record counts, summary-cell
counts, temporal manifest agreement, and SHA-256 hashes recorded in
`data/archive-manifest.sha256`.
