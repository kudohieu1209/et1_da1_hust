"""Chép dữ liệu kho cục bộ (SQLite + students/*.json) sang MongoDB.

Chạy lại nhiều lần vẫn an toàn: mọi bản ghi được upsert theo khóa gốc (id
hội thoại, id tin nhắn, khóa hồ sơ) nên không nhân bản và giữ nguyên liên kết.
"""
import sqlite3
from pathlib import Path
from typing import Dict

from app.services.conversation_service import ConversationService, MongoConversationService


def migrate_profiles(source, target) -> int:
    count = 0
    for key, profile in source.list():
        target.save(key, profile)
        count += 1
    return count


def _read_sqlite(sqlite_path: Path):
    connection = sqlite3.connect(f"file:{Path(sqlite_path).as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        conversations = connection.execute("SELECT id, student_id FROM conversations").fetchall()
        return [(row["id"], row["student_id"]) for row in conversations]
    finally:
        connection.close()


def migrate_conversations(sqlite_path: Path, database) -> Dict[str, int]:
    """Đọc qua API của ``ConversationService`` để dữ liệu chuyển đi đúng định dạng
    mà ``MongoConversationService`` trả về (đã được contract test đối chiếu)."""
    if not Path(sqlite_path).exists():
        return {"conversations": 0, "messages": 0}

    source = ConversationService(sqlite_path)
    MongoConversationService(database)  # tạo chỉ mục trước khi ghi
    conversations = database["conversations"]
    messages = database["messages"]
    migrated = {"conversations": 0, "messages": 0}
    max_message_id = 0

    for conversation_id, student_id in _read_sqlite(sqlite_path):
        detail = source.get(conversation_id, student_id)
        items = detail.pop("messages")
        detail["_id"] = detail.pop("id")
        conversations.replace_one({"_id": detail["_id"]}, detail, upsert=True)
        migrated["conversations"] += 1
        for message in items:
            messages.replace_one({"id": message["id"]}, message, upsert=True)
            max_message_id = max(max_message_id, message["id"])
            migrated["messages"] += 1

    # Tin nhắn mới trên Mongo phải nhận id lớn hơn mọi id đã chuyển sang.
    database["counters"].update_one({"_id": "messages"}, {"$max": {"seq": max_message_id}}, upsert=True)
    return migrated
