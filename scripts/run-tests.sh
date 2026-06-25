#!/usr/bin/env bash
#
# run-tests.sh — the ONE canonical command to build eyerate's combined test
# environment and run the full suite.
#
# eyerate's full suite needs a combined environment: eyerate's own runtime deps
# (yfinance, curl_cffi) PLUS the matika stack (fastapi, sqlalchemy, httpx, ...),
# which matika provides as a SIBLING clone — matika source is placed on
# PYTHONPATH, and its deps come from matika's own lock. This script is the single
# DECLARED, runnable source for that environment: it performs the same three-layer
# install both locally and in CI (.github/workflows/test.yml invokes this script),
# so the declared config IS the config that runs (no divergence).
#
# All three layers read from DECLARATIONS — never a hardcoded dep list:
#   1. matika's locked runtime deps  (uv export --directory ../matika --frozen)
#   2. eyerate's runtime deps        (uv pip install -r pyproject.toml)
#   3. eyerate's test tooling        (uv pip install --group dev)
#
# Layout requirement: the matika clone MUST sit beside the eyerate checkout
# (../matika). The integration tier exec_modules matika's conftest via a
# sibling-relative path, so a checkout/worktree that is not a matika sibling
# (e.g. under /tmp) makes all integration tests ERROR at collection.
#
# Usage:
#   scripts/run-tests.sh                  # full suite
#   scripts/run-tests.sh -v               # extra pytest args are passed through
#   scripts/run-tests.sh tests/scripts/   # run a subset
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EYERATE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MATIKA_DIR="$(cd "${EYERATE_ROOT}/.." && pwd)/matika"
VENV_DIR="${EYERATE_ROOT}/.venv"
VENV_PY="${VENV_DIR}/bin/python"

if [ ! -d "${MATIKA_DIR}" ]; then
  echo "ERROR: matika sibling clone not found at ${MATIKA_DIR}" >&2
  echo "       eyerate's test suite requires the matika clone beside this checkout." >&2
  exit 1
fi

# Layer 0: ensure the venv exists. Created on the declared Python (3.14).
if [ ! -x "${VENV_PY}" ]; then
  echo "==> Creating venv at ${VENV_DIR}"
  uv venv "${VENV_DIR}" --python python3.14
fi

# Layer 1: matika's EXACT locked runtime deps, for reproducibility. matika source
# is provided via PYTHONPATH (not installed as a package), so strip the "-e ."
# self-install line from its export.
MATIKA_LOCK_TXT="$(mktemp -t matika-locked.XXXXXX)"
trap 'rm -f "${MATIKA_LOCK_TXT}"' EXIT
echo "==> Layer 1: installing matika's locked deps (from ${MATIKA_DIR})"
uv export --directory "${MATIKA_DIR}" --frozen --no-hashes --no-dev \
  | grep -v "^-e " > "${MATIKA_LOCK_TXT}"
uv pip install --python "${VENV_PY}" -r "${MATIKA_LOCK_TXT}"

# Layer 2: eyerate's runtime deps (yfinance, curl_cffi).
echo "==> Layer 2: installing eyerate runtime deps"
uv pip install --python "${VENV_PY}" -r "${EYERATE_ROOT}/pyproject.toml"

# Layer 3: eyerate's test tooling from the canonical [dependency-groups] dev.
# The subshell cd is required because --group resolves pyproject.toml from the
# current directory.
echo "==> Layer 3: installing eyerate dev group (test tooling)"
(cd "${EYERATE_ROOT}" && uv pip install --python "${VENV_PY}" --group dev)

# Run the suite from the eyerate root so that PYTHONPATH=src:../matika/src and
# the integration tier's sibling-relative conftest exec both resolve.
echo "==> Running pytest"
cd "${EYERATE_ROOT}"
export PYTHONPATH="src:../matika/src"
export SECRET_KEY="${SECRET_KEY:-test-only-secret-key-never-use-in-production}"

if [ "$#" -eq 0 ]; then
  exec "${VENV_PY}" -m pytest tests/
else
  exec "${VENV_PY}" -m pytest "$@"
fi
