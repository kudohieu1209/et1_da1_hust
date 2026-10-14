#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_python_env.sh"

VENV_DIR="$(default_venv_dir)"

# Trên Windows, "python3" có thể là stub của Microsoft Store: tồn tại nhưng
# không chạy. Chọn trình thông dịch đầu tiên thực sự chạy được.
BOOTSTRAP_PYTHON=""
for candidate in "${PYTHON:-}" python3 python py; do
  if [[ -n "$candidate" ]] && "$candidate" -c "import venv" >/dev/null 2>&1; then
    BOOTSTRAP_PYTHON="$candidate"
    break
  fi
done
if [[ -z "$BOOTSTRAP_PYTHON" ]]; then
  echo "Không tìm thấy Python 3 có module venv. Cài Python hoặc đặt biến PYTHON." >&2
  exit 1
fi

"$BOOTSTRAP_PYTHON" -m venv "$VENV_DIR"
VENV_PYTHON="$(venv_python "$VENV_DIR")"
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r "$BACKEND_DIR/requirements.txt" -r "$BACKEND_DIR/requirements-dev.txt"
npm --prefix "$FRONTEND_DIR" install

echo "Setup complete ($VENV_DIR). Copy project/backend/.env.example to project/backend/.env if you want Gemini responses."
