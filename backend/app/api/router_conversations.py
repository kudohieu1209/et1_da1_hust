
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import current_student
from app.models.schemas import ConversationCreateRequest, ConversationUpdateRequest
from app.services.conversation_service import (
    ConversationNotFoundError,
    conversation_service,
)


router = APIRouter(prefix="/api/conversations", tags=["Conversation History"])


@router.get("")
def list_conversations(
    include_archived: bool = Query(False),
    student_id: str = Depends(current_student),
):
    """Đoạn chat của sinh viên đang đăng nhập (chủ sở hữu lấy từ phiên, không từ header)."""
    return {
        "conversations": conversation_service.list(
            student_id, include_archived=include_archived
        )
    }


@router.post("")
def create_conversation(
    req: ConversationCreateRequest,
    student_id: str = Depends(current_student),
):
    return conversation_service.create(student_id, req.title)


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, student_id: str = Depends(current_student)):
    try:
        return conversation_service.get(conversation_id, student_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{conversation_id}")
def update_conversation(
    conversation_id: str,
    req: ConversationUpdateRequest,
    student_id: str = Depends(current_student),
):
    try:
        return conversation_service.update(
            conversation_id,
            student_id,
            title=req.title,
            is_archived=req.is_archived,
            is_pinned=req.is_pinned,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, student_id: str = Depends(current_student)):
    try:
        conversation_service.delete(conversation_id, student_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "conversation_id": conversation_id}

