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
# tests/__init__.py tự tạo thư mục riêng cho mỗi tiến trình
# nếu VECTOR_DB_DIR chưa được đặt. Không tái sử dụng HNSW từ lần chạy trước.
# Kiểm thử dùng mongomock trong bộ nhớ và hồ sơ tổng hợp từ CTĐT công khai.
# Không kết nối MongoDB Atlas thật hay đọc bảng điểm cá nhân.
export MONGODB_URI=""
# Không gọi Gemini thật trong kiểm thử (tất định, không tốn quota).
export GEMINI_API_KEY=""
export GOOGLE_API_KEY=""
export OPENAI_API_KEY=""

# -t để test được import dưới package "tests" (chạy tests/__init__.py cô lập dữ liệu).
PYTHONPATH="$BACKEND_DIR" "$PYTHON_BIN" -m unittest discover -s "$BACKEND_DIR/tests" -t "$BACKEND_DIR" -v
PYTHONPATH="$BACKEND_DIR" "$PYTHON_BIN" -m unittest discover -s "$REPO_DIR/data/tests" -v
npm --prefix "$FRONTEND_DIR" test
npm --prefix "$FRONTEND_DIR" run lint
npm --prefix "$FRONTEND_DIR" run build
