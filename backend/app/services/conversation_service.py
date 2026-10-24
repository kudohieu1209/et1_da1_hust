"""Persistent conversation storage for the advisor chat.

The RAG vector store is intentionally not used for chat history. Conversation
and message records need ownership, ordering, update and delete semantics.

MongoDB is the only application conversation store.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.services.mongo_client import get_mongo_database

DEFAULT_TITLE = "Đoạn chat mới"
NOT_FOUND_MESSAGE = "Không tìm thấy đoạn chat hoặc đoạn chat không thuộc tài khoản này."
MESSAGE_ROLES = {"user", "assistant", "system"}
MAX_TITLE_LENGTH = 120


class ConversationNotFoundError(LookupError):
    """Raised when a conversation is missing or owned by another student."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _title_from_message(content: str) -> str:
    title = " ".join(str(content or "").split())
    if len(title) > 64:
        title = title[:61].rstrip() + "..."
    return title or DEFAULT_TITLE


def _require_student_id(student_id: Any) -> str:
    cleaned = str(student_id or "").strip()
    if not cleaned:
        raise ValueError("Thiếu mã sinh viên để tạo đoạn chat.")
    return cleaned


def _validate_message(role: str, content: str) -> None:
    if role not in MESSAGE_ROLES:
        raise ValueError("Vai trò tin nhắn không hợp lệ.")
    if not str(content or "").strip():
        raise ValueError("Nội dung tin nhắn không được để trống.")


def _clean_title(title: str) -> str:
    cleaned = str(title).strip()
    if not cleaned:
        raise ValueError("Tiêu đề đoạn chat không được để trống.")
    return cleaned[:MAX_TITLE_LENGTH]


def _json_compatible(value: Any) -> Any:
    """Chuẩn hóa giá trị như khi lưu JSON (tuple→list, khóa số→chuỗi).

    Giữ dữ liệu trả về tương thích JSON, đồng thời từ chối
    sớm các giá trị không tuần tự hóa được.
    """
    if value is None:
        return None
    return json.loads(json.dumps(value, ensure_ascii=False))


class MongoConversationService:
    """Kho hội thoại trên MongoDB.

    - ``conversations``: mỗi đoạn chat một document; ``message_count`` và
      ``last_message_preview`` được ghi sẵn để liệt kê không cần đếm lại.
    - ``messages``: tin nhắn tách riêng vì ``data_context`` có thể lớn; ``id``
      là số nguyên tăng dần lấy từ ``counters`` để giữ thứ tự ổn định.
    """

    def __init__(self, database):
        self._conversations = database["conversations"]
        self._messages = database["messages"]
        self._counters = database["counters"]
        self._conversations.create_index(
            [("student_id", ASCENDING), ("is_archived", ASCENDING), ("updated_at", DESCENDING)]
        )
        self._messages.create_index([("conversation_id", ASCENDING), ("created_at", ASCENDING), ("id", ASCENDING)])
        self._messages.create_index("id", unique=True)

    def _next_message_id(self) -> int:
        counter = self._counters.find_one_and_update(
            {"_id": "messages"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(counter["seq"])

    def _owned(self, conversation_id: str, student_id: str) -> Dict[str, Any]:
        document = self._conversations.find_one(
            {"_id": str(conversation_id), "student_id": str(student_id)}
        )
        if document is None:
            raise ConversationNotFoundError(NOT_FOUND_MESSAGE)
        return document

    @staticmethod
    def _summary(document: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": document["_id"],
            "student_id": document["student_id"],
            "title": document["title"],
            "is_archived": bool(document.get("is_archived")),
            "is_pinned": bool(document.get("is_pinned")),
            "created_at": document["created_at"],
            "updated_at": document["updated_at"],
            "message_count": int(document.get("message_count") or 0),
            "last_message_preview": document.get("last_message_preview") or "",
        }

    @staticmethod
    def _message(document: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": int(document["id"]),
            "conversation_id": document["conversation_id"],
            "role": document["role"],
            "content": document["content"],
            "suggested_actions": document.get("suggested_actions") or [],
            "data_context": document.get("data_context"),
            "sources": document.get("sources") or [],
            "model_used": document.get("model_used"),
            "created_at": document["created_at"],
        }

    def _ordered_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        cursor = self._messages.find({"conversation_id": conversation_id}).sort(
            [("created_at", ASCENDING), ("id", ASCENDING)]
        )
        return [self._message(item) for item in cursor]

    def create(self, student_id: str, title: Optional[str] = None) -> Dict[str, Any]:
        now = _now()
        document = {
            "_id": str(uuid.uuid4()),
            "student_id": _require_student_id(student_id),
            "title": (title or DEFAULT_TITLE).strip() or DEFAULT_TITLE,
            "is_archived": False,
            "is_pinned": False,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "last_message_preview": "",
        }
        self._conversations.insert_one(document)
        return self._summary(document)

    def ensure(self, conversation_id: Optional[str], student_id: str) -> Dict[str, Any]:
        if conversation_id:
            return self.get(conversation_id, student_id, include_messages=False)
        return self.create(student_id)

    def list(self, student_id: str, include_archived: bool = False) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"student_id": str(student_id)}
        if not include_archived:
            query["is_archived"] = False
        cursor = self._conversations.find(query).sort(
            [("is_pinned", DESCENDING), ("updated_at", DESCENDING)]
        )
        return [self._summary(item) for item in cursor]

    def get_messages(self, conversation_id: str, student_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        self._owned(conversation_id, student_id)
        if limit and limit > 0:
            cursor = self._messages.find({"conversation_id": str(conversation_id)}).sort(
                [("created_at", DESCENDING), ("id", DESCENDING)]
            ).limit(limit)
            return list(reversed([self._message(item) for item in cursor]))
        return self._ordered_messages(conversation_id)

    def get(self, conversation_id: str, student_id: str, include_messages: bool = True) -> Dict[str, Any]:
        result = self._summary(self._owned(conversation_id, student_id))
        if include_messages:
            result["messages"] = self._ordered_messages(conversation_id)
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
        _validate_message(role, content)
        conversation = self._owned(conversation_id, student_id)
        now = _now()
        document = {
            "id": self._next_message_id(),
            "conversation_id": conversation["_id"],
            "role": role,
            "content": str(content),
            "suggested_actions": _json_compatible(suggested_actions),
            "data_context": _json_compatible(data_context),
            "sources": _json_compatible(sources),
            "model_used": model_used,
            "created_at": now,
        }
        self._messages.insert_one(document)

        changes: Dict[str, Any] = {"updated_at": now, "last_message_preview": document["content"]}
        if role == "user" and conversation["title"] == DEFAULT_TITLE:
            changes["title"] = _title_from_message(content)
        self._conversations.update_one(
            {"_id": conversation["_id"]}, {"$set": changes, "$inc": {"message_count": 1}}
        )
        return self._message(document)

    def update(
        self,
        conversation_id: str,
        student_id: str,
        *,
        title: Optional[str] = None,
        is_archived: Optional[bool] = None,
        is_pinned: Optional[bool] = None,
    ) -> Dict[str, Any]:
        changes: Dict[str, Any] = {}
        if title is not None:
            changes["title"] = _clean_title(title)
        if is_archived is not None:
            changes["is_archived"] = bool(is_archived)
        if is_pinned is not None:
            changes["is_pinned"] = bool(is_pinned)
        self._owned(conversation_id, student_id)
        if changes:
            changes["updated_at"] = _now()
            self._conversations.update_one(
                {"_id": str(conversation_id), "student_id": str(student_id)}, {"$set": changes}
            )
        return self.get(conversation_id, student_id, include_messages=False)

    def delete(self, conversation_id: str, student_id: str) -> None:
        self._owned(conversation_id, student_id)
        self._conversations.delete_one({"_id": str(conversation_id), "student_id": str(student_id)})
        self._messages.delete_many({"conversation_id": str(conversation_id)})


def create_conversation_service():
    return MongoConversationService(get_mongo_database())


conversation_service = create_conversation_service()

