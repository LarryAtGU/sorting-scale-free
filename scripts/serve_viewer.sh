#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIRECTORY}/.." && pwd)"
PYTHON_EXECUTABLE="${PROJECT_ROOT}/.venv/bin/python"
PORT="${1:-8765}"

if [[ ! -x "${PYTHON_EXECUTABLE}" ]]; then
  echo "Error: project virtual environment not found." >&2
  echo "Run ./scripts/install_dependencies.sh first." >&2
  exit 1
fi

if [[ ! -f "${PROJECT_ROOT}/visualization/viewer.html" ]]; then
  echo "Error: visualization/viewer.html was not found." >&2
  exit 1
fi

echo "Serving the visualization and restricted experiment controls."
echo "Open: http://127.0.0.1:${PORT}/viewer.html"
echo "Press Ctrl-C to stop."
cd "${PROJECT_ROOT}"
exec "${PYTHON_EXECUTABLE}" -m scn_sorting.viewer_server --port "${PORT}" --root "${PROJECT_ROOT}"
