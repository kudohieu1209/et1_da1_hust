"""Kho vector lỗi không được làm sập /api/chat.

Lỗi 500 không kèm header CORS nên trình duyệt báo "không kết nối được
backend", che mất nguyên nhân thật. Chatbot phải trả lời rõ là kho tài liệu
đang gặp sự cố, các chức năng dựa trên CTĐT vẫn dùng được.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.rag_engine import rag_engine
from app.services.chatbot_service import chatbot_service
from app.services.data_loader import data_loader


class RagFailureTests(unittest.TestCase):
    def setUp(self):
        data_loader.load_student_profile("20220001")

    def test_vector_store_error_returns_explanatory_reply(self):
        with mock.patch.object(rag_engine.vector_store, "similarity_search", side_effect=RuntimeError("hnsw index")):
            response = chatbot_service.process_message("Học kỳ chính được đăng ký tối đa bao nhiêu tín chỉ?")

        self.assertEqual(response["intent"], "RAG_HUST_KNOWLEDGE")
        self.assertEqual(response["model_used"], "rag-unavailable")
        self.assertIn("kho tài liệu", response["reply"].lower())
        self.assertEqual(response["sources"], [])
        self.assertNotIn("hnsw", response["reply"])

    def test_rule_engine_answers_still_work_when_rag_is_down(self):
        with mock.patch.object(rag_engine.vector_store, "similarity_search", side_effect=RuntimeError("down")):
            response = chatbot_service.process_message("Tiến độ học tập của em thế nào?")
        self.assertEqual(response["intent"], "DEGREE_AUDIT")

    def test_old_fee_document_is_not_used_to_assert_a_new_years_fee(self):
        chunk = {"text": "Học phí 630 nghìn đồng", "metadata": {
            "document_type": "tuition_decision", "effective_period": "Năm học 2025-2026",
        }}
        with mock.patch.object(rag_engine.vector_store, "similarity_search", return_value=[chunk]), \
                mock.patch.object(rag_engine.gemini, "generate_response") as generate:
            response = rag_engine.query("Học phí năm học 2026-2027 là bao nhiêu?")
        generate.assert_not_called()
        self.assertEqual(response["model_used"], "insufficient-evidence")
        self.assertEqual(response["sources"], [])
        self.assertNotIn("630", response["reply"])

    def test_current_tuition_uses_the_matching_academic_year(self):
        for question in ("Học phí ET1 năm nay bao nhiêu?", "Học phí hiện tại bao nhiêu?",
                         "Học phí kỳ này bao nhiêu?", "Học phí học kỳ 2026.1 bao nhiêu?"):
            with self.subTest(question=question):
                chunk = {"text": "Học phí ET1", "metadata": {
                    "document_type": "tuition_decision", "effective_period": "Năm học 2026–2027",
                }}
                with mock.patch.object(rag_engine.vector_store, "similarity_search", return_value=[chunk]) as search, \
                        mock.patch("app.rag.rag_engine.requested_academic_year", return_value="2026-2027"), \
                        mock.patch.object(rag_engine.gemini, "generate_response", return_value={
                            "reply": "Có nguồn đúng năm học", "model_used": "test", "sources": [],
                        }) as generate:
                    response = rag_engine.query(question)
                self.assertEqual(response["model_used"], "test")
                self.assertIn("2026-2027", search.call_args.args[0])
                self.assertEqual(generate.call_args.kwargs["user_query"], question)

    def test_current_tuition_rejects_only_outdated_evidence(self):
        chunk = {"text": "Học phí cũ", "metadata": {
            "document_type": "tuition_decision", "effective_period": "Năm học 2025-2026",
        }}
        with mock.patch.object(rag_engine.vector_store, "similarity_search", return_value=[chunk]), \
                mock.patch("app.rag.rag_engine.requested_academic_year", return_value="2026-2027"), \
                mock.patch.object(rag_engine.gemini, "generate_response") as generate:
            response = rag_engine.query("Học phí năm nay bao nhiêu?")
        generate.assert_not_called()
        self.assertEqual(response["model_used"], "insufficient-evidence")

    def test_current_fee_support_does_not_require_a_tuition_schedule(self):
        chunk = {"text": "Điều kiện miễn giảm học phí", "metadata": {
            "document_type": "tuition_support_regulation",
        }}
        with mock.patch.object(rag_engine.vector_store, "similarity_search", return_value=[chunk]), \
                mock.patch.object(rag_engine.gemini, "generate_response", return_value={
                    "reply": "Điều kiện miễn giảm", "sources": [],
                }) as generate:
            rag_engine.query("Năm nay điều kiện miễn giảm học phí là gì?")
        generate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
