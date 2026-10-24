"""Khởi tạo AuthService dùng chung: MongoDB bắt buộc."""
from app.auth.service import AuthService
from app.auth.store import MongoAuthStore
from app.services.data_loader import data_loader
from app.services.mongo_client import get_mongo_database


def create_auth_store():
    return MongoAuthStore(get_mongo_database())


# Dùng chung kho hồ sơ với DataLoader để tài khoản và hồ sơ luôn cùng một nơi.
auth_service = AuthService(create_auth_store(), data_loader.profiles)
