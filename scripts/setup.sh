#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_DIR/project/backend"
FRONTEND_DIR="$REPO_DIR/project/frontend"

python3 -m venv "$BACKEND_DIR/.venv"
"$BACKEND_DIR/.venv/bin/python" -m pip install --upgrade pip
"$BACKEND_DIR/.venv/bin/python" -m pip install -r "$BACKEND_DIR/requirements.txt"
npm --prefix "$FRONTEND_DIR" install

echo "Setup complete. Copy project/backend/.env.example to project/backend/.env if you want Gemini responses."
