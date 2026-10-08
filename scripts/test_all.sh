#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_DIR/project/backend"
FRONTEND_DIR="$REPO_DIR/project/frontend"
PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing $PYTHON_BIN. Run scripts/setup.sh first." >&2
  exit 1
fi

PYTHONPATH="$BACKEND_DIR" "$PYTHON_BIN" -m unittest discover -s "$BACKEND_DIR/tests" -v
PYTHONPATH="$BACKEND_DIR" "$PYTHON_BIN" -m unittest discover -s "$REPO_DIR/project/data/tests" -v
PYTHONPATH="$BACKEND_DIR" "$PYTHON_BIN" "$BACKEND_DIR/test_backend.py"
PYTHONPATH="$BACKEND_DIR" "$PYTHON_BIN" "$BACKEND_DIR/test_rag.py"
npm --prefix "$FRONTEND_DIR" run lint
npm --prefix "$FRONTEND_DIR" run build
