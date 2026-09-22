"""Persistent conversation storage for the advisor chat.

The RAG vector store is intentionally not used for chat history. Conversation
and message records need ownership, ordering, update and delete semantics, so a
small SQLite repository is a better fit for the local/demo deployment.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from app.core.config import CHAT_DB_PATH


class ConversationNotFoundError(LookupError):
    """Raised when a conversation is missing or owned by another student."""


class ConversationService:
    def __init__(self, db_path: Path = CHAT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.db_path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT 'Đoạn chat mới',
                    is_archived INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0, 1)),
                    is_pinned INTEGER NOT NULL DEFAULT 0 CHECK (is_pinned IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_conversations_owner_updated
                    ON conversations(student_id, is_archived, updated_at DESC);

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    suggested_actions_json TEXT,
                    data_context_json TEXT,
                    sources_json TEXT,
                    model_used TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conversation_order
                    ON messages(conversation_id, created_at, id);
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _json_dumps(value: Any) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _json_loads(value: Optional[str], default: Any) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return default

    @staticmethod
    def _title_from_message(content: str) -> str:
        title = " ".join(str(content or "").split())
        if len(title) > 64:
            title = title[:61].rstrip() + "..."
        return title or "Đoạn chat mới"

    @staticmethod
    def _summary(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "student_id": row["student_id"],
            "title": row["title"],
            "is_archived": bool(row["is_archived"]),
            "is_pinned": bool(row["is_pinned"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "message_count": int(row["message_count"] or 0),
            "last_message_preview": row["last_message_preview"] or "",
        }

    def _get_owned_row(self, connection: sqlite3.Connection, conversation_id: str, student_id: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM conversations WHERE id = ? AND student_id = ?",
            (conversation_id, student_id),
        ).fetchone()
        if row is None:
            raise ConversationNotFoundError("Không tìm thấy đoạn chat hoặc đoạn chat không thuộc tài khoản này.")
        return row

    def create(self, student_id: str, title: Optional[str] = None) -> Dict[str, Any]:
        student_id = str(student_id).strip()
        if not student_id:
            raise ValueError("Thiếu mã sinh viên để tạo đoạn chat.")
        conversation_id = str(uuid.uuid4())
        now = self._now()
        conversation_title = (title or "Đoạn chat mới").strip() or "Đoạn chat mới"
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations(id, student_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, student_id, conversation_title, now, now),
            )
        return self.get(conversation_id, student_id, include_messages=False)

    def ensure(self, conversation_id: Optional[str], student_id: str) -> Dict[str, Any]:
        if conversation_id:
            return self.get(conversation_id, student_id, include_messages=False)
        return self.create(student_id)

    def list(self, student_id: str, include_archived: bool = False) -> List[Dict[str, Any]]:
        query = """
            SELECT c.*,
                   (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count,
                   (SELECT m.content FROM messages m
                      WHERE m.conversation_id = c.id
                      ORDER BY m.created_at DESC, m.id DESC LIMIT 1) AS last_message_preview
            FROM conversations c
            WHERE c.student_id = ?
        """
        params: List[Any] = [str(student_id)]
        if not include_archived:
            query += " AND c.is_archived = 0"
        query += " ORDER BY c.is_pinned DESC, c.updated_at DESC"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._summary(row) for row in rows]

    def _message_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": int(row["id"]),
            "conversation_id": row["conversation_id"],
            "role": row["role"],
            "content": row["content"],
            "suggested_actions": self._json_loads(row["suggested_actions_json"], []),
            "data_context": self._json_loads(row["data_context_json"], None),
            "sources": self._json_loads(row["sources_json"], []),
            "model_used": row["model_used"],
            "created_at": row["created_at"],
        }

    def get_messages(self, conversation_id: str, student_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            self._get_owned_row(connection, conversation_id, student_id)
            rows = connection.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (conversation_id,),
            ).fetchall()
        messages = [self._message_from_row(row) for row in rows]
        return messages[-limit:] if limit and limit > 0 else messages

    def get(self, conversation_id: str, student_id: str, include_messages: bool = True) -> Dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT c.*,
                       (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count,
                       (SELECT m.content FROM messages m
                          WHERE m.conversation_id = c.id
                          ORDER BY m.created_at DESC, m.id DESC LIMIT 1) AS last_message_preview
                FROM conversations c
                WHERE c.id = ? AND c.student_id = ?
                """,
                (conversation_id, str(student_id)),
            ).fetchone()
            if row is None:
                raise ConversationNotFoundError("Không tìm thấy đoạn chat hoặc đoạn chat không thuộc tài khoản này.")
            result = self._summary(row)
            if include_messages:
                message_rows = connection.execute(
                    "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC, id ASC",
                    (conversation_id,),
                ).fetchall()
                result["messages"] = [self._message_from_row(item) for item in message_rows]
            return result

    def append_message(
        self,
        conversation_id: str,
        student_id: str,
        role: str,
        content: str,
        *,
        suggested_actions: Optional[List[str]] = None,
        data_context: Optional[Dict[str, Any]] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        model_used: Optional[str] = None,
    ) -> Dict[str, Any]:
        if role not in {"user", "assistant", "system"}:
            raise ValueError("Vai trò tin nhắn không hợp lệ.")
        if not str(content or "").strip():
            raise ValueError("Nội dung tin nhắn không được để trống.")

        now = self._now()
        with self._connect() as connection:
            conversation = self._get_owned_row(connection, conversation_id, student_id)
            cursor = connection.execute(
                """
                INSERT INTO messages(
                    conversation_id, role, content, suggested_actions_json,
                    data_context_json, sources_json, model_used, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    role,
                    str(content),
                    self._json_dumps(suggested_actions),
                    self._json_dumps(data_context),
                    self._json_dumps(sources),
                    model_used,
                    now,
                ),
            )
            title = conversation["title"]
            if role == "user" and title == "Đoạn chat mới":
                title = self._title_from_message(content)
            connection.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, conversation_id),
            )
            row = connection.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._message_from_row(row)

    def update(
        self,
        conversation_id: str,
        student_id: str,
        *,
        title: Optional[str] = None,
        is_archived: Optional[bool] = None,
        is_pinned: Optional[bool] = None,
    ) -> Dict[str, Any]:
        changes = []
        values: List[Any] = []
        if title is not None:
            clean_title = str(title).strip()
            if not clean_title:
                raise ValueError("Tiêu đề đoạn chat không được để trống.")
            changes.append("title = ?")
            values.append(clean_title[:120])
        if is_archived is not None:
            changes.append("is_archived = ?")
            values.append(int(bool(is_archived)))
        if is_pinned is not None:
            changes.append("is_pinned = ?")
            values.append(int(bool(is_pinned)))
        if not changes:
            return self.get(conversation_id, student_id, include_messages=False)

        changes.append("updated_at = ?")
        values.append(self._now())
        values.extend([conversation_id, str(student_id)])
        with self._connect() as connection:
            self._get_owned_row(connection, conversation_id, student_id)
            connection.execute(
                f"UPDATE conversations SET {', '.join(changes)} WHERE id = ? AND student_id = ?",
                values,
            )
        return self.get(conversation_id, student_id, include_messages=False)

    def delete(self, conversation_id: str, student_id: str) -> None:
        with self._connect() as connection:
            self._get_owned_row(connection, conversation_id, student_id)
            connection.execute(
                "DELETE FROM conversations WHERE id = ? AND student_id = ?",
                (conversation_id, str(student_id)),
            )


conversation_service = ConversationService()

