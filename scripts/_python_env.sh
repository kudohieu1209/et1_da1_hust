#!/usr/bin/env bash
# Shared helpers for setup.sh and test_all.sh.
#
# Linux/macOS dùng backend/.venv; Windows (Git Bash) dùng .venv-win để
# không ghi đè venv Linux khi cùng một ổ đĩa được mở từ hai hệ điều hành.

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_DIR/backend"
FRONTEND_DIR="$REPO_DIR/frontend"

is_windows() {
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) return 0 ;;
    *) return 1 ;;
  esac
}

default_venv_dir() {
  if is_windows; then
    echo "$BACKEND_DIR/.venv-win"
  else
    echo "$BACKEND_DIR/.venv"
  fi
}

venv_python() {
  local venv_dir="$1"
  if [[ -x "$venv_dir/Scripts/python.exe" ]]; then
    echo "$venv_dir/Scripts/python.exe"
  else
    echo "$venv_dir/bin/python"
  fi
}

# In ra Python của venv dùng được đầu tiên; PYTHON_BIN ghi đè nếu được đặt.
find_backend_python() {
  local candidate
  for candidate in \
    "${PYTHON_BIN:-}" \
    "$(venv_python "$(default_venv_dir)")" \
    "$BACKEND_DIR/.venv/bin/python" \
    "$BACKEND_DIR/.venv/Scripts/python.exe"; do
    if [[ -n "$candidate" && -x "$candidate" ]] && "$candidate" -c "" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}
