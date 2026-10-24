"""Kết nối MongoDB dùng chung cho các kho dữ liệu.

MongoDB là kho nghiệp vụ duy nhất. Thiếu cấu hình hoặc không kết nối được
thì dừng khởi động với lỗi rõ ràng.
"""
import re
from functools import lru_cache

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


def connect_mongo_database() -> Database:
    if not MONGODB_URI:
        raise MongoConfigurationError("Thiếu MONGODB_URI. Hãy cấu hình MongoDB local hoặc Atlas trước khi khởi động.")
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
            "Kiểm tra MONGODB_URI, thông tin xác thực và kết nối tới MongoDB."
        ) from None
    print(f"[INFO] MongoDB: đã kết nối {redact_uri(MONGODB_URI)}, database '{MONGODB_DB}'.")
    return client[MONGODB_DB]


@lru_cache(maxsize=1)
def get_mongo_database() -> Database:
    return connect_mongo_database()
