"""Cô lập kiểm thử khỏi dữ liệu của backend dev đang chạy.

Chạy trước mọi module test (cả ``discover -t`` lẫn ``python -m unittest
tests.test_x``), trước khi ``app.core.config`` được import:

- ChromaDB lưu file không chịu được hai tiến trình cùng mở: test mở chung
  ``vector_db`` với server dev từng làm hỏng chỉ mục của server.
- Không bao giờ ghi vào MongoDB Atlas thật; phía Mongo dùng mongomock.
"""
import os
import tempfile
from pathlib import Path

_PROJECT_DIR = Path(__file__).resolve().parents[2]

os.environ.setdefault("VECTOR_DB_DIR", str(_PROJECT_DIR / "data" / "vector_db_test"))
os.environ["MONGODB_URI"] = ""
# Không gọi LLM thật khi kiểm thử: tất định và không tốn quota Gemini.
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
# Tài khoản tạo trong test không được lẫn vào auth.sqlite3 thật.
os.environ["AUTH_DB_PATH"] = str(Path(tempfile.mkdtemp(prefix="hust-auth-test-")) / "auth.sqlite3")
