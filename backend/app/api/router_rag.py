from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.rag.rag_engine import rag_engine
from app.rag.gemini_service import gemini_service
from app.auth.dependencies import current_admin, llm_rate_limit

router = APIRouter(prefix="/api/rag", tags=["RAG & AI Engine"])

class RAGQueryRequest(BaseModel):
    query: str
    k: Optional[int] = Field(default=4, ge=1, le=10)

class ConfigKeyRequest(BaseModel):
    api_key: str

@router.get("/status")
def get_rag_status():
    """Lấy trạng thái của hệ thống RAG, ChromaDB và Gemini LLM"""
    return rag_engine.get_status()

@router.post("/sync", dependencies=[Depends(current_admin)])
def sync_knowledge_base(force: Optional[bool] = False):
    """Quét và đồng bộ tài liệu từ thư mục data/documents vào ChromaDB"""
    result = rag_engine.sync_knowledge_base(force=force)
    return result

@router.post("/query", dependencies=[Depends(llm_rate_limit)])
def query_rag(req: RAGQueryRequest):
    """Truy vấn trực tiếp kiến thức quy chế qua RAG + Gemini"""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query không được để trống")
    return rag_engine.query(req.query, k=req.k or 4)

@router.post("/config/api-key", dependencies=[Depends(current_admin)])
def configure_gemini_key(req: ConfigKeyRequest):
    """Cập nhật Gemini API Key từ giao diện người dùng"""
    success = gemini_service.update_api_key(req.api_key)
    return {
        "success": success,
        "configured": gemini_service.is_configured(),
        "model": gemini_service.model_name
    }
