"""Kiểm thử pipeline RAG và router, chuyển từ script test_rag.py cũ.

Chất lượng truy xuất được đo đầy đủ bằng eval/run_eval.py; ở đây chỉ
giữ các ca hồi quy đã từng hỏng.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.document_loader import document_loader
from app.rag.vector_store import vector_store
from app.services.chatbot_service import chatbot_service
from app.services.data_loader import data_loader


class RagPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data_loader.load_student_profile("20220001")
        cls.sync = vector_store.sync_documents()

    def test_only_verified_documents_are_loaded(self):
        names = [path.name for path in document_loader.get_document_files()]
        self.assertGreaterEqual(len(names), 3)
        self.assertNotIn("quy_che_dao_tao_dai_hoc_hust.md", names)

    def test_vector_store_contains_chunks(self):
        self.assertGreater(self.sync["total_chunks"], 0)

    def test_scholarship_query_retrieves_scholarship_text(self):
        chunks = vector_store.similarity_search("Tiêu chuẩn xét học bổng khuyến khích học tập loại Xuất sắc", k=2)
        self.assertIn("học bổng", chunks[0]["text"].lower())

    def test_old_warning_term_retrieves_level_two_limit(self):
        chunks = vector_store.similarity_search(
            "Sinh viên bị cảnh cáo học tập mức 2 được đăng ký tối đa bao nhiêu tín chỉ?", k=2
        )
        self.assertTrue("14" in chunks[0]["text"] or "cảnh báo" in chunks[0]["text"].lower())

    def test_curriculum_year_is_not_confused(self):
        chunks = vector_store.similarity_search("Chương trình ET1 2023 cần bao nhiêu tín chỉ?", k=2)
        self.assertIn("2023", chunks[0]["metadata"].get("source", ""))
        self.assertIn("132", chunks[0]["text"])


class RouterRegressionTests(unittest.TestCase):
    def setUp(self):
        data_loader.load_student_profile("20220001")

    def test_graduation_project_regulation_uses_rag_with_sources(self):
        response = chatbot_service.process_message("Điều kiện để nhận Đồ án tốt nghiệp Cử nhân tại Bách Khoa là gì?")
        self.assertEqual(response["intent"], "RAG_HUST_KNOWLEDGE")
        self.assertTrue(response.get("sources"))

    def test_scholarship_question_uses_rag(self):
        response = chatbot_service.process_message("Sinh viên cần đạt điều kiện gì để được học bổng loại A?")
        self.assertEqual(response["intent"], "RAG_HUST_KNOWLEDGE")

    def test_design_projects_question_uses_rule_engine(self):
        response = chatbot_service.process_message("Kỳ này mình học đồ án 1 và đồ án 2 cùng lúc được không?")
        self.assertEqual(response["intent"], "COURSE_ELIGIBILITY_CHECK")

    def test_next_term_with_named_courses_checks_conditions(self):
        response = chatbot_service.process_message("Kỳ tới em muốn học vxl và dts thì cần những môn gì trước?")
        self.assertEqual(response["intent"], "COURSE_ELIGIBILITY_CHECK")
        self.assertIn("ET3300", response["reply"])
        self.assertIn("ET3220", response["reply"])


if __name__ == "__main__":
    unittest.main()
