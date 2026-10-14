"""Kết nối MongoDB dùng chung cho các kho dữ liệu.

Khi ``MONGODB_URI`` rỗng, hệ thống dùng kho cục bộ (SQLite + file JSON) để
vẫn chạy được offline. Khi đã cấu hình mà không kết nối được thì dừng ngay lúc
khởi động thay vì âm thầm ghi dữ liệu sang chỗ khác.
"""
import re
from functools import lru_cache
from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.core.config import MONGODB_DB, MONGODB_URI

CONNECT_TIMEOUT_MS = 8000


class MongoConfigurationError(RuntimeError):
    """MONGODB_URI đã đặt nhưng không kết nối/xác thực được."""


def redact_uri(uri: str) -> str:
    """Che mật khẩu trong chuỗi kết nối trước khi đưa vào log/thông báo lỗi."""
    return re.sub(r"(mongodb(?:\+srv)?://[^:/@]+):[^@]+@", r"\1:***@", uri)


@lru_cache(maxsize=1)
def get_mongo_database() -> Optional[Database]:
    if not MONGODB_URI:
        return None
    client = MongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=CONNECT_TIMEOUT_MS,
        appname="hust-course-advisor",
    )
    try:
        client.admin.command("ping")
    except PyMongoError as exc:
        client.close()
        raise MongoConfigurationError(
            f"Không kết nối được MongoDB ({redact_uri(MONGODB_URI)}): {exc.__class__.__name__}. "
            "Kiểm tra MONGODB_URI, mật khẩu và IP Access List trên Atlas, "
            "hoặc để trống MONGODB_URI để chạy bằng kho cục bộ."
        ) from None
    print(f"[INFO] MongoDB: đã kết nối {redact_uri(MONGODB_URI)}, database '{MONGODB_DB}'.")
    return client[MONGODB_DB]
