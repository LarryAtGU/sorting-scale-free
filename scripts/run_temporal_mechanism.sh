#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing .venv. Run scripts/install_dependencies.sh first." >&2
  exit 1
fi

exec .venv/bin/python -m scn_sorting.experiments.mechanism_batch "$@"
