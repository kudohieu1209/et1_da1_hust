import json
import tempfile
import unittest
from pathlib import Path

from app.rag.document_loader import DocumentLoader
from app.rag.lexical_search import bm25_scores


class DocumentTrustTests(unittest.TestCase):
    def test_only_explicitly_verified_text_and_pdf_sidecars_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "draft.md").write_text("# Draft\nNo approval", encoding="utf-8")
            (root / "approved.md").write_text("---\nrag_status: VERIFIED\n---\n# Approved", encoding="utf-8")
            (root / "blocked.md").write_text("---\nrag_status: UNVERIFIED\n---\n# Blocked", encoding="utf-8")
            (root / "draft.pdf").touch()
            (root / "approved.pdf").touch()
            (root / "approved.pdf.metadata.json").write_text(json.dumps({"rag_status": "VERIFIED"}), encoding="utf-8")
            self.assertEqual([p.name for p in DocumentLoader(root).get_document_files()], ["approved.md", "approved.pdf"])

    def test_article_context_continues_across_pages_without_indexing_page_numbers(self):
        text = ("## Trang PDF 8\nĐiều 5. Điểm học phần\n"
                "1. Đây là nội dung điều khoản đầu tiên, được giữ nguyên để tra cứu và dẫn nguồn.\n"
                "## Trang PDF 9\n9\n\n"
                "2. Đây là nội dung điều khoản thứ hai, được giữ nguyên để tra cứu và dẫn nguồn.")
        with tempfile.TemporaryDirectory() as directory:
            chunks = DocumentLoader(Path(directory))._structured_chunks(text)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[1][1]["page"], 9)
        self.assertEqual(chunks[1][1]["article"], "Điều 5. Điểm học phần")

    def test_points_keep_wrapped_clause_context_and_education_scope(self):
        text = ("CHƯƠNG II\nĐÀO TẠO ĐẠI HỌC\nĐiều 15. Hạng tốt nghiệp\n"
                "2. Hạng tốt nghiệp của sinh viên giỏi trở lên sẽ bị\ngiảm một mức trong các trường hợp sau:\n"
                "a) Khối lượng phải học lại vượt quá 5% tổng số tín chỉ của chương trình.\n"
                "CHƯƠNG IV\nĐÀO TẠO THẠC SĨ\nĐiều 34. Tốt nghiệp thạc sĩ\n"
                "1. Học viên đáp ứng đầy đủ các điều kiện sau thì được xét công nhận tốt nghiệp.")
        with tempfile.TemporaryDirectory() as directory:
            chunks = DocumentLoader(Path(directory))._structured_chunks(text, "academic_regulation")
        point = next((content, metadata) for content, metadata in chunks if "a) Khối lượng" in content)
        self.assertIn("giảm một mức", point[0])
        self.assertEqual(point[1]["education_level"], "undergraduate")
        self.assertEqual(chunks[-1][1]["education_level"], "master")

    def test_requested_graduate_scope_does_not_leak_into_student_queries(self):
        from unittest import mock
        from app.rag.vector_store import VectorStoreManager
        manager = object.__new__(VectorStoreManager)
        manager.collection = mock.Mock()
        manager.collection.count.return_value = 2
        manager.collection.get.return_value = {
            "ids": ["student", "master"],
            "documents": ["Sinh viên bị buộc thôi học theo điều kiện đại học.",
                          "Học viên thạc sĩ bị buộc thôi học theo các điều kiện sau."],
            "metadatas": [{"education_level": "undergraduate"}, {"education_level": "master"}],
        }
        manager.collection.query.return_value = {"ids": [["master", "student"]]}
        self.assertEqual([row["id"] for row in manager.similarity_search("Sinh viên bị buộc thôi học khi nào?")], ["student"])
        self.assertEqual([row["id"] for row in manager.similarity_search("Học viên thạc sĩ bị buộc thôi học khi nào?")], ["master"])

    def test_programme_code_does_not_force_fee_questions_into_curriculum_documents(self):
        from unittest import mock
        from app.rag.vector_store import VectorStoreManager
        manager = object.__new__(VectorStoreManager)
        manager.collection = mock.Mock()
        manager.collection.count.return_value = 2
        manager.collection.get.return_value = {
            "ids": ["curriculum", "fee"],
            "documents": ["CTĐT ET1 năm 2023 có tổng 132 tín chỉ.", "Học phí ET1 năm 2025-2026 là 630 nghìn đồng/TCHP."],
            "metadatas": [{"document_type": "curriculum", "effective_period": "2023"},
                          {"document_type": "tuition_decision", "effective_period": "2025-2026"}],
        }
        manager.collection.query.return_value = {"ids": [["curriculum", "fee"]]}
        self.assertEqual(manager.similarity_search("Học phí ET1 năm 2025-2026 là bao nhiêu?")[0]["id"], "fee")

    def test_retrieved_points_expand_to_complete_clause_and_keep_page_range(self):
        from unittest import mock
        from app.rag.vector_store import VectorStoreManager
        manager = object.__new__(VectorStoreManager)
        manager.collection = mock.Mock()
        manager.collection.count.return_value = 2
        header = "Điều 15. Hạng tốt nghiệp\n2. Hạng giỏi bị giảm một mức khi:"
        common = {"file_name": "regulation.md", "article": "Điều 15. Hạng tốt nghiệp",
                  "clause": "2. Hạng giỏi bị giảm một mức khi:", "education_level": "undergraduate"}
        manager.collection.get.return_value = {
            "ids": ["retake", "discipline"],
            "documents": [header + "\n\na) Khối lượng học lại vượt quá 5% tổng số tín chỉ.",
                          header + "\n\nb) Sinh viên đã chịu kỷ luật từ cảnh cáo trở lên."],
            "metadatas": [{**common, "chunk_index": 1, "page": 16}, {**common, "chunk_index": 2, "page": 17}],
        }
        manager.collection.query.return_value = {"ids": [["retake", "discipline"]]}
        result = manager.similarity_search("Học lại nhiều có bị giảm hạng tốt nghiệp không?")
        self.assertEqual(len(result), 1)
        self.assertIn("5%", result[0]["text"])
        self.assertIn("cảnh cáo", result[0]["text"])
        self.assertEqual(result[0]["metadata"]["page"], 16)
        self.assertEqual(result[0]["metadata"]["page_end"], 17)

    def test_bm25_distinguishes_single_letter_grades_and_nfd(self):
        import unicodedata
        docs = ["Điểm R là điểm miễn học.", "Điểm W là điểm rút đăng ký học phần."]
        scores = bm25_scores(unicodedata.normalize("NFD", "Điểm W có nghĩa gì?"), docs)
        self.assertGreater(scores[1], scores[0])

    def test_revoking_all_sources_removes_stale_index_entries(self):
        from unittest import mock
        from app.rag.vector_store import VectorStoreManager
        manager = object.__new__(VectorStoreManager)
        manager.collection = mock.Mock()
        manager.collection.count.return_value = 2
        manager.collection.get.return_value = {"ids": ["old-1", "old-2"]}
        with mock.patch("app.rag.vector_store.document_loader.load_all_chunks", return_value=[]):
            manager.sync_documents()
        manager.collection.delete.assert_called_once_with(ids=["old-1", "old-2"])


if __name__ == "__main__":
    unittest.main()
