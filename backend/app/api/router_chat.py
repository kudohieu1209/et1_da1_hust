from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import current_student, llm_rate_limit, student_scope
from app.services.chatbot_service import chatbot_service
from app.models.schemas import ChatRequest, ChatResponse
from app.services.conversation_service import ConversationNotFoundError, conversation_service
from app.services.student_memory import student_memory
from app.services.data_loader import data_loader

# Trả lời theo hồ sơ của sinh viên đang đăng nhập (scope mở bởi student_scope).
router = APIRouter(prefix="/api/chat", tags=["Chatbot Agent"], dependencies=[Depends(student_scope)])

@router.post("", response_model=ChatResponse, dependencies=[Depends(llm_rate_limit)])
def chat_with_bot(req: ChatRequest, student_id: str = Depends(current_student)):
    """
    Endpoint tương tác với Chatbot tư vấn chọn môn học HUST:
    Tích hợp Natural Language Understanding + Deterministic HUST Rule Engine.
    """
    conversation = None
    stored_messages = []
    try:
        if req.conversation_id:
            conversation = conversation_service.ensure(req.conversation_id, student_id)
            stored_messages = conversation_service.get_messages(
                conversation["id"], student_id, limit=12
            )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Only owned, persisted messages establish context. Client-supplied history
    # cannot seed another conversation or fabricate assistant tool results.
    history_data = [
        {"role": item["role"], "content": item["content"], "data_context": item.get("data_context")}
        for item in stored_messages
    ]

    preferences = student_memory.for_advising(student_id, data_loader.get_program(), data_loader.get_module_tracks())
    result = chatbot_service.process_message(req.message, history_data, preferences=preferences)
    try:
        # Chỉ tạo bản ghi khi chatbot xử lý thành công, tránh để các đoạn chat
        # rỗng xuất hiện trong Sidebar nếu backend/LLM gặp lỗi.
        if conversation is None:
            conversation = conversation_service.create(student_id)
        conversation_service.append_message(
            conversation["id"], student_id, "user", req.message
        )
        conversation_service.append_message(
            conversation["id"],
            student_id,
            "assistant",
            result.get("reply", ""),
            suggested_actions=result.get("suggested_actions", []),
            data_context=result.get("data_context"),
            sources=result.get("sources", []),
            model_used=result.get("model_used"),
        )
    except (ConversationNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result["conversation_id"] = conversation["id"]
    return ChatResponse(**result)
