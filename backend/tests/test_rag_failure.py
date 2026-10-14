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


if __name__ == "__main__":
    unittest.main()
