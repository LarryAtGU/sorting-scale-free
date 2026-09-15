#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIRECTORY}/.." && pwd)"
VENV_DIRECTORY="${PROJECT_ROOT}/.venv"

find_python() {
  local candidate
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "${candidate}" >/dev/null 2>&1 && \
      "${candidate}" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'
    then
      command -v "${candidate}"
      return 0
    fi
  done
  return 1
}

PYTHON_EXECUTABLE="$(find_python || true)"
if [[ -z "${PYTHON_EXECUTABLE}" ]]; then
  echo "Error: Python 3.11 or newer is required but was not found." >&2
  echo "Install Python 3.11+ and run this script again." >&2
  exit 1
fi

echo "Using $(${PYTHON_EXECUTABLE} --version) at ${PYTHON_EXECUTABLE}"

if [[ ! -x "${VENV_DIRECTORY}/bin/python" ]]; then
  echo "Creating virtual environment: ${VENV_DIRECTORY}"
  "${PYTHON_EXECUTABLE}" -m venv "${VENV_DIRECTORY}"
else
  echo "Using existing virtual environment: ${VENV_DIRECTORY}"
fi

VENV_PYTHON="${VENV_DIRECTORY}/bin/python"

echo "Updating packaging tools"
"${VENV_PYTHON}" -m pip install --upgrade pip setuptools wheel

echo "Installing the project and development dependencies"
"${VENV_PYTHON}" -m pip install --editable "${PROJECT_ROOT}[dev]"

echo "Running tests"
cd "${PROJECT_ROOT}"
"${VENV_PYTHON}" -m pytest

echo
echo "Installation complete."
echo "Activate the environment with:"
echo "  source \"${VENV_DIRECTORY}/bin/activate\""

