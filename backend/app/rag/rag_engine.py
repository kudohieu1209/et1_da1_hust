import os
from typing import List, Dict, Any, Optional
from app.rag.document_loader import document_loader
from app.rag.vector_store import vector_store
from app.rag.gemini_service import gemini_service

class RAGEngine:
    def __init__(self):
        self.loader = document_loader
        self.vector_store = vector_store
        self.gemini = gemini_service

    def query(
        self,
        question: str,
        k: int = 4,
        structured_data: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Thực hiện chu trình RAG hoàn chỉnh:
        1. Retrieval: Tìm kiếm các chunk văn bản quy chế liên quan nhất trong ChromaDB.
        2. Augmentation & Generation: Truyền Context vào Gemini LLM để tổng hợp câu trả lời chính xác và trích dẫn điều khoản.
        """
        # 1. Thu thập văn bản liên quan từ Vector Store
        retrieved_chunks = self.vector_store.similarity_search(question, k=k)

        # 2. Sinh câu trả lời qua Gemini LLM
        gemini_result = self.gemini.generate_response(
            user_query=question,
            context_chunks=retrieved_chunks,
            structured_data=structured_data,
            history=history
        )

        return {
            "reply": gemini_result["reply"],
            "sources": gemini_result.get("sources", []),
            "model_used": gemini_result.get("model_used", "local-rag"),
            "context_chunks_count": len(retrieved_chunks),
            "retrieved_chunks": [
                {
                    "source": c["metadata"].get("source", ""),
                    "title": c["metadata"].get("title", ""),
                    "snippet": c["text"][:200] + "...",
                    "distance": c.get("distance", 0.0)
                }
                for c in retrieved_chunks
            ]
        }

    def sync_knowledge_base(self, force: bool = False) -> Dict[str, Any]:
        """Đồng bộ lại toàn bộ tài liệu vào Vector Store"""
        return self.vector_store.sync_documents(force=force)

    def get_status(self) -> Dict[str, Any]:
        """Lấy tổng quan tình trạng của hệ thống RAG & Gemini"""
        vs_stats = self.vector_store.get_stats()
        doc_files = [f.name for f in self.loader.get_document_files()]

        return {
            "gemini": {
                "configured": self.gemini.is_configured(),
                "model": self.gemini.model_name,
                "fallback_model": self.gemini.fallback_model
            },
            "vector_store": vs_stats,
            "document_files": doc_files,
            "total_documents": len(doc_files)
        }

rag_engine = RAGEngine()
