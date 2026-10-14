#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_python_env.sh"

if ! PYTHON_BIN="$(find_backend_python)"; then
  echo "Không tìm thấy venv backend dùng được. Chạy scripts/setup.sh trước." >&2
  exit 1
fi
export PYTHONIOENCODING=utf-8
# Vector DB riêng cho kiểm thử: không tranh chấp file với backend dev đang chạy
# và không ghi đè chỉ mục mà backend dev đang dùng.
DEFAULT_TEST_VECTOR_DB="$REPO_DIR/project/data/vector_db_test"
if [[ -z "${VECTOR_DB_DIR:-}" ]]; then
  # Dựng lại chỉ mục test mỗi lần: ChromaDB trên Windows thỉnh thoảng để lại
  # chỉ mục HNSW không đọc được giữa các tiến trình. Chỉ xóa thư mục test
  # mặc định của script, không bao giờ đụng tới vector_db của backend dev.
  rm -rf "$DEFAULT_TEST_VECTOR_DB"
fi
export VECTOR_DB_DIR="${VECTOR_DB_DIR:-$DEFAULT_TEST_VECTOR_DB}"
# Kiểm thử dùng kho cục bộ: tất định và không ghi vào MongoDB Atlas thật.
# Phía MongoDB được kiểm bằng mongomock trong các contract test.
export MONGODB_URI=""
# Không gọi Gemini thật trong kiểm thử (tất định, không tốn quota).
export GEMINI_API_KEY=""

# -t để test được import dưới package "tests" (chạy tests/__init__.py cô lập dữ liệu).
PYTHONPATH="$BACKEND_DIR" "$PYTHON_BIN" -m unittest discover -s "$BACKEND_DIR/tests" -t "$BACKEND_DIR" -v
PYTHONPATH="$BACKEND_DIR" "$PYTHON_BIN" -m unittest discover -s "$REPO_DIR/project/data/tests" -v
"$PYTHON_BIN" -m unittest discover -s "$REPO_DIR/project/eval/tests" -v
# Bộ đánh giá định lượng: thất bại nếu chỉ số tụt dưới project/eval/thresholds.json.
"$PYTHON_BIN" "$REPO_DIR/project/eval/run_eval.py" --label latest --check
npm --prefix "$FRONTEND_DIR" run lint
npm --prefix "$FRONTEND_DIR" run build
