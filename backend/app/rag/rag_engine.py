import re
from typing import List, Dict, Any, Optional
from app.rag.document_loader import document_loader
from app.rag.vector_store import preferred_document_types, requested_academic_year, vector_store
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
        1. Retrieval: Tìm kiếm các chunk quy chế bằng hybrid hoặc chỉ BM25.
        2. Augmentation & Generation: Truyền Context vào Gemini LLM để tổng hợp câu trả lời chính xác và trích dẫn điều khoản.
        """
        search_question = question
        requested_periods = []
        if "tuition_decision" in preferred_document_types(question):
            requested_periods = [f"{left}-{right}" for left, right in
                                 re.findall(r"(20\d{2})\s*[-–/]\s*(20\d{2})", question)]
            needs_resolved_period = not requested_periods
            semester_years = re.findall(r"\b(20\d{2})\.[123]\b", question)
            if not requested_periods and semester_years:
                requested_periods = [f"{year}-{int(year) + 1}" for year in semester_years]
            if not requested_periods and re.search(r"hiện tại|hiện nay|năm nay|kỳ này", question.lower()):
                requested_periods = [requested_academic_year(question)]
            if requested_periods and needs_resolved_period:
                # Resolve relative dates before retrieval so the matching fee
                # decision can outrank a similar document from a different year.
                search_question = f"{question} (năm học {', '.join(requested_periods)})"

        retrieved_chunks = self.vector_store.similarity_search(search_question, k=k)

        # A dated source only establishes fees for the academic year it covers.
        if requested_periods:
            periods = [chunk["metadata"].get("effective_period", "") for chunk in retrieved_chunks
                       if chunk["metadata"].get("document_type") == "tuition_decision"]
            available_periods = {f"{left}-{right}" for period in periods for left, right in
                                 re.findall(r"(20\d{2})\s*[-–/]\s*(20\d{2})", period)}
            if not set(requested_periods) <= available_periods:
                return {
                    "reply": "Kho chưa có văn bản học phí được xác nhận cho thời gian bạn hỏi. Các mức đã lưu chỉ áp dụng cho năm học ghi trên nguồn; hãy tra thông báo đúng năm học/học kỳ trên CTT HUST.",
                    "sources": [], "model_used": "insufficient-evidence",
                    "context_chunks_count": 0, "retrieved_chunks": [],
                }

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
                    "distance": c.get("distance", 0.0),
                    "source_url": c["metadata"].get("source_url", ""),
                    "page": c["metadata"].get("page", 0),
                    "page_end": c["metadata"].get("page_end", c["metadata"].get("page", 0)),
                    "article": c["metadata"].get("article", ""),
                    "effective_period": c["metadata"].get("effective_period", ""),
                }
                for c in retrieved_chunks
            ]
        }

    def sync_knowledge_base(self, force: bool = False) -> Dict[str, Any]:
        """Chuẩn bị chỉ mục theo chế độ truy xuất đã cấu hình."""
        return self.vector_store.sync_documents(force=force)

    def get_status(self) -> Dict[str, Any]:
        """Lấy tổng quan tình trạng của hệ thống RAG & Gemini"""
        vs_stats = self.vector_store.get_stats()
        doc_files = [f.name for f in self.loader.get_document_files()]

        return {
            "mode": self.vector_store.mode,
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
