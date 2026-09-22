from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from app.models.schemas import ConversationCreateRequest, ConversationUpdateRequest
from app.services.conversation_service import (
    ConversationNotFoundError,
    conversation_service,
)
from app.services.data_loader import data_loader


router = APIRouter(prefix="/api/conversations", tags=["Conversation History"])


def _resolve_student_id(x_student_id: Optional[str]) -> str:
    return (x_student_id or data_loader.current_student_id or "demo").strip()


@router.get("")
def list_conversations(
    include_archived: bool = Query(False),
    x_student_id: Optional[str] = Header(None),
):
    """List the signed-in student's non-archived conversations."""
    return {
        "conversations": conversation_service.list(
            _resolve_student_id(x_student_id), include_archived=include_archived
        )
    }


@router.post("")
def create_conversation(
    req: ConversationCreateRequest,
    x_student_id: Optional[str] = Header(None),
):
    return conversation_service.create(_resolve_student_id(x_student_id), req.title)


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, x_student_id: Optional[str] = Header(None)):
    try:
        return conversation_service.get(conversation_id, _resolve_student_id(x_student_id))
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{conversation_id}")
def update_conversation(
    conversation_id: str,
    req: ConversationUpdateRequest,
    x_student_id: Optional[str] = Header(None),
):
    try:
        return conversation_service.update(
            conversation_id,
            _resolve_student_id(x_student_id),
            title=req.title,
            is_archived=req.is_archived,
            is_pinned=req.is_pinned,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, x_student_id: Optional[str] = Header(None)):
    try:
        conversation_service.delete(conversation_id, _resolve_student_id(x_student_id))
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "conversation_id": conversation_id}

