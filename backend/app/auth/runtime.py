"""Khởi tạo AuthService dùng chung: MongoDB nếu có MONGODB_URI, ngược lại SQLite."""
from app.auth.service import AuthService
from app.auth.store import MongoAuthStore, SqliteAuthStore
from app.core.config import AUTH_DB_PATH
from app.services.data_loader import data_loader
from app.services.mongo_client import get_mongo_database


def create_auth_store():
    database = get_mongo_database()
    if database is not None:
        return MongoAuthStore(database)
    return SqliteAuthStore(AUTH_DB_PATH)


# Dùng chung kho hồ sơ với DataLoader để tài khoản và hồ sơ luôn cùng một nơi.
auth_service = AuthService(create_auth_store(), data_loader.profiles)
