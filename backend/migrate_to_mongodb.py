"""Chuyển hồ sơ sinh viên và lịch sử hội thoại từ kho cục bộ lên MongoDB.

    # Đặt MONGODB_URI trong project/backend/.env trước, rồi:
    python migrate_to_mongodb.py --dry-run   # chỉ đếm, không ghi
    python migrate_to_mongodb.py

Chạy lại nhiều lần vẫn an toàn (upsert theo khóa gốc). File cục bộ được giữ
nguyên để làm bản sao lưu và cho chế độ offline.
"""
import argparse
import sqlite3
import sys

from app.core.config import CHAT_DB_PATH, MONGODB_DB, MONGODB_URI, STUDENTS_DIR
from app.services.mongo_client import MongoConfigurationError, get_mongo_database, redact_uri
from app.services.profile_repository import FileProfileRepository, MongoProfileRepository
from app.services.storage_migration import migrate_conversations, migrate_profiles


def _count_local() -> dict:
    profiles = len(FileProfileRepository(STUDENTS_DIR).list())
    conversations = messages = 0
    if CHAT_DB_PATH.exists():
        connection = sqlite3.connect(f"file:{CHAT_DB_PATH.as_posix()}?mode=ro", uri=True)
        try:
            conversations = connection.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            messages = connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        finally:
            connection.close()
    return {"profiles": profiles, "conversations": conversations, "messages": messages}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Chỉ đếm dữ liệu cục bộ, không kết nối/ghi MongoDB")
    args = parser.parse_args()

    local = _count_local()
    print(f"Dữ liệu cục bộ: {local['profiles']} hồ sơ, {local['conversations']} hội thoại, {local['messages']} tin nhắn.")
    if args.dry_run:
        return 0
    if not MONGODB_URI:
        print("Chưa đặt MONGODB_URI trong .env; không có nơi để chuyển dữ liệu tới.", file=sys.stderr)
        return 1

    try:
        database = get_mongo_database()
    except MongoConfigurationError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Đích: {redact_uri(MONGODB_URI)} / {MONGODB_DB}")
    profile_count = migrate_profiles(FileProfileRepository(STUDENTS_DIR), MongoProfileRepository(database))
    conversation_report = migrate_conversations(CHAT_DB_PATH, database)
    print(
        f"Đã chuyển {profile_count} hồ sơ, {conversation_report['conversations']} hội thoại, "
        f"{conversation_report['messages']} tin nhắn."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
