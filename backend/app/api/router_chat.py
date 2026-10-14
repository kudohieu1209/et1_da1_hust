from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import current_student, student_scope
from app.services.chatbot_service import chatbot_service
from app.models.schemas import ChatRequest, ChatResponse
from app.services.conversation_service import ConversationNotFoundError, conversation_service

# Trả lời theo hồ sơ của sinh viên đang đăng nhập (scope mở bởi student_scope).
router = APIRouter(prefix="/api/chat", tags=["Chatbot Agent"], dependencies=[Depends(student_scope)])

@router.post("", response_model=ChatResponse)
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

    if stored_messages:
        history_data = [
            {"role": item["role"], "content": item["content"]}
            for item in stored_messages
        ]
    else:
        # Backward compatibility for clients that still send history. The
        # current question is not repeated in the context because it is saved
        # immediately after the response is generated.
        history_data = [{"role": m.role, "content": m.content} for m in req.history] if req.history else []
        if history_data and history_data[-1]["role"] == "user" and history_data[-1]["content"] == req.message:
            history_data.pop()

    result = chatbot_service.process_message(req.message, history_data)
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
