"""Cô lập kiểm thử khỏi dữ liệu của backend dev đang chạy.

Chạy trước mọi module test (cả ``discover -t`` lẫn ``python -m unittest
tests.test_x``), trước khi ``app.core.config`` được import:

- ChromaDB lưu file không chịu được hai tiến trình cùng mở: test mở chung
  ``vector_db`` với server dev từng làm hỏng chỉ mục của server.
- Không bao giờ ghi vào MongoDB Atlas thật; phía Mongo dùng mongomock.
"""
import os
from unittest import mock
from pathlib import Path
from uuid import uuid4

_PROJECT_DIR = Path(__file__).resolve().parents[2]

# A fresh index avoids both concurrent access and stale HNSW files on Windows.
os.environ.setdefault("VECTOR_DB_DIR", str(_PROJECT_DIR / "data" / "vector_db_test" / f"backend-{uuid4().hex}"))
os.environ["MONGODB_URI"] = ""
# Không gọi LLM thật khi kiểm thử: tất định và không tốn quota Gemini.
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
# Every application repository uses the same isolated MongoDB fixture.
from testing_support import isolated_database
TEST_DATABASE = isolated_database(seed=True)
_database_patch = mock.patch("app.services.mongo_client.get_mongo_database", return_value=TEST_DATABASE)
_database_patch.start()
