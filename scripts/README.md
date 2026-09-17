# Reproduction scripts

- `install_dependencies.sh`: create/update `.venv`, install dependencies, tests.
- `run_temporal_mechanism.sh`: execute or resume the frozen temporal experiment.
- `validate_frozen_results.py`: reproduce the frozen primary tail validation.
- `analyze_secondary.py`: reproduce resource, family, cutoff, and block analyses.
- `analyze_theory_validation.py`: reproduce exact-BST and mechanism checks.
- `make_vector_paper_figures.py`: create all ten manuscript figures as vector PDF.
- `audit_archive.py`: verify the deposited dataset and integrity manifest.

Run analysis scripts from the repository root after activating `.venv`. The
complete command sequence is documented in the top-level `README.md`.
