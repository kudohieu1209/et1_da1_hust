"""Kho tài khoản và phiên đăng nhập: MongoDB.

Phiên chỉ lưu ``sha256(token)``: lộ cơ sở dữ liệu cũng không dùng lại được
cookie của ai. Mọi thời điểm là datetime có múi giờ UTC.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from pymongo import ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError


class UserExistsError(Exception):
    """MSSV đã có tài khoản."""


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _user_view(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "student_id": raw["student_id"],
        "password_hash": raw["password_hash"],
        "is_admin": bool(raw.get("is_admin")),
        "is_demo": bool(raw.get("is_demo")),
        "failed_attempts": int(raw.get("failed_attempts") or 0),
        "locked_until": raw.get("locked_until"),
        "created_at": raw.get("created_at"),
        "last_login_at": raw.get("last_login_at"),
    }


class MongoAuthStore:
    """``users``: ``_id`` = MSSV. ``sessions``: ``_id`` = sha256(token), có chỉ mục
    TTL trên ``expires_at`` để MongoDB tự dọn phiên hết hạn."""

    def __init__(self, database):
        self._users = database["users"]
        self._sessions = database["sessions"]
        self._sessions.create_index([("student_id", ASCENDING)])
        self._sessions.create_index("expires_at", expireAfterSeconds=0)

    @staticmethod
    def _document_to_user(document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if document is None:
            return None
        raw = {**document, "student_id": document["_id"]}
        for key in ("locked_until", "created_at", "last_login_at"):
            raw[key] = _aware(raw.get(key))
        return _user_view(raw)

    def create_user(self, user: Dict[str, Any]) -> None:
        try:
            self._users.insert_one(
                {
                    "_id": user["student_id"],
                    "password_hash": user["password_hash"],
                    "is_admin": bool(user.get("is_admin")),
                    "is_demo": bool(user.get("is_demo")),
                    "failed_attempts": 0,
                    "locked_until": None,
                    "created_at": user["created_at"],
                    "last_login_at": None,
                }
            )
        except DuplicateKeyError as exc:
            raise UserExistsError(user["student_id"]) from exc

    def get_user(self, student_id: str) -> Optional[Dict[str, Any]]:
        return self._document_to_user(self._users.find_one({"_id": student_id}))

    def record_failed_login(
        self, student_id: str, now: datetime, max_attempts: int, lock_for: timedelta
    ) -> Optional[Dict[str, Any]]:
        document = self._users.find_one_and_update(
            {"_id": student_id}, {"$inc": {"failed_attempts": 1}}, return_document=ReturnDocument.AFTER
        )
        if document is None:
            return None
        if document["failed_attempts"] >= max_attempts:
            document = self._users.find_one_and_update(
                {"_id": student_id},
                {"$set": {"failed_attempts": 0, "locked_until": now + lock_for}},
                return_document=ReturnDocument.AFTER,
            )
        return self._document_to_user(document)

    def record_successful_login(self, student_id: str, now: datetime) -> None:
        self._users.update_one(
            {"_id": student_id}, {"$set": {"failed_attempts": 0, "locked_until": None, "last_login_at": now}}
        )

    def delete_user(self, student_id: str) -> None:
        self._users.delete_one({"_id": student_id})

    def set_password(self, student_id: str, password_hash: str) -> None:
        self._users.update_one(
            {"_id": student_id},
            {"$set": {"password_hash": password_hash, "failed_attempts": 0, "locked_until": None}},
        )

    def set_admin(self, student_id: str, is_admin: bool) -> None:
        self._users.update_one({"_id": student_id}, {"$set": {"is_admin": bool(is_admin)}})

    def create_session(self, token_hash: str, student_id: str, created_at: datetime, expires_at: datetime) -> None:
        self._sessions.insert_one(
            {"_id": token_hash, "student_id": student_id, "created_at": created_at, "expires_at": expires_at}
        )

    def get_session(self, token_hash: str) -> Optional[Dict[str, Any]]:
        document = self._sessions.find_one({"_id": token_hash})
        if document is None:
            return None
        return {"student_id": document["student_id"], "expires_at": _aware(document["expires_at"])}

    def delete_session(self, token_hash: str) -> None:
        self._sessions.delete_one({"_id": token_hash})

    def delete_sessions_for(self, student_id: str) -> int:
        return self._sessions.delete_many({"student_id": student_id}).deleted_count
