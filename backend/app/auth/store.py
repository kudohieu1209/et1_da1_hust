"""Kho tài khoản và phiên đăng nhập: MongoDB hoặc SQLite cục bộ (offline).

Phiên chỉ lưu ``sha256(token)``: lộ cơ sở dữ liệu cũng không dùng lại được
cookie của ai. Mọi thời điểm là datetime có múi giờ UTC.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from pymongo import ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError


class UserExistsError(Exception):
    """MSSV đã có tài khoản."""


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _to_iso(value: Optional[datetime]) -> Optional[str]:
    return value.astimezone(timezone.utc).isoformat() if value else None


def _from_iso(value: Optional[str]) -> Optional[datetime]:
    return _aware(datetime.fromisoformat(value)) if value else None


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


class SqliteAuthStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    student_id TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    is_demo INTEGER NOT NULL DEFAULT 0,
                    failed_attempts INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    created_at TEXT NOT NULL,
                    last_login_at TEXT
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_student ON sessions(student_id);
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.db_path), timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _row_to_user(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        raw = dict(row)
        for key in ("locked_until", "created_at", "last_login_at"):
            raw[key] = _from_iso(raw[key])
        return _user_view(raw)

    def create_user(self, user: Dict[str, Any]) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO users(student_id, password_hash, is_admin, is_demo, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        user["student_id"],
                        user["password_hash"],
                        int(bool(user.get("is_admin"))),
                        int(bool(user.get("is_demo"))),
                        _to_iso(user["created_at"]),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise UserExistsError(user["student_id"]) from exc

    def get_user(self, student_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE student_id = ?", (student_id,)).fetchone()
        return self._row_to_user(row)

    def record_failed_login(
        self, student_id: str, now: datetime, max_attempts: int, lock_for: timedelta
    ) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            # Một giao dịch ghi: các lần đoán song song không thể cùng đọc một giá trị cũ.
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                "UPDATE users SET failed_attempts = failed_attempts + 1 WHERE student_id = ?", (student_id,)
            ).rowcount
            if not updated:
                return None
            connection.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = ? "
                "WHERE student_id = ? AND failed_attempts >= ?",
                (_to_iso(now + lock_for), student_id, max_attempts),
            )
        return self.get_user(student_id)

    def record_successful_login(self, student_id: str, now: datetime) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login_at = ? WHERE student_id = ?",
                (_to_iso(now), student_id),
            )

    def delete_user(self, student_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM users WHERE student_id = ?", (student_id,))

    def set_password(self, student_id: str, password_hash: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE users SET password_hash = ?, failed_attempts = 0, locked_until = NULL WHERE student_id = ?",
                (password_hash, student_id),
            )

    def set_admin(self, student_id: str, is_admin: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE users SET is_admin = ? WHERE student_id = ?", (int(bool(is_admin)), student_id)
            )

    def create_session(self, token_hash: str, student_id: str, created_at: datetime, expires_at: datetime) -> None:
        with self._connect() as connection:
            # SQLite không có TTL như MongoDB: dọn phiên hết hạn mỗi lần tạo phiên mới.
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (_to_iso(created_at),))
            connection.execute(
                "INSERT INTO sessions(token_hash, student_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token_hash, student_id, _to_iso(created_at), _to_iso(expires_at)),
            )

    def get_session(self, token_hash: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT student_id, expires_at FROM sessions WHERE token_hash = ?", (token_hash,)
            ).fetchone()
        if row is None:
            return None
        return {"student_id": row["student_id"], "expires_at": _from_iso(row["expires_at"])}

    def delete_session(self, token_hash: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def delete_sessions_for(self, student_id: str) -> int:
        with self._connect() as connection:
            return connection.execute("DELETE FROM sessions WHERE student_id = ?", (student_id,)).rowcount


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
