import unittest
from datetime import date
from unittest import mock

from app.rag.document_loader import DOCUMENT_DISPLAY_NAMES, document_loader
from app.rag.gemini_service import clean_display_source
from app.rag.vector_store import VectorStoreManager, lexical_text, preferred_document_types, requested_academic_year


def _manager(rows, semantic_order):
    manager = object.__new__(VectorStoreManager)
    manager.collection = mock.Mock()
    manager.collection.count.return_value = len(rows)
    manager.collection.get.return_value = {
        "ids": [row[0] for row in rows],
        "documents": [row[1] for row in rows],
        "metadatas": [row[2] for row in rows],
    }
    manager.collection.query.return_value = {"ids": [semantic_order]}
    return manager


class PreferredTypeTests(unittest.TestCase):
    def test_topics_map_to_their_document_types(self):
        cases = {
            "Học phí ngành ET1 bao nhiêu?": {"tuition_decision"},
            "Điều kiện miễn giảm học phí là gì?": {"tuition_support_regulation"},
            "Sinh viên K71 cần chứng chỉ TOEIC bao nhiêu?": {"language_regulation"},
            "Điểm rèn luyện loại tốt là bao nhiêu?": {"conduct_regulation"},
            "Hạn rút học phần học kỳ 1 là khi nào?": {"academic_calendar"},
            "Hình thức kỷ luật khiển trách áp dụng khi nào?": {"student_affairs_regulation"},
            "Bị cảnh báo học tập mức 2 thì sao?": {"academic_regulation"},
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(preferred_document_types(query), expected)

    def test_scholarship_questions_pick_the_governing_document(self):
        both = {"student_handbook", "scholarship_regulation"}
        self.assertEqual(preferred_document_types("Học bổng Trần Đại Nghĩa xét thế nào?"), both)
        self.assertEqual(preferred_document_types("Học bổng khuyến khích học tập loại A"), {"student_handbook"})
        self.assertEqual(preferred_document_types("Học bổng trao đổi sinh viên cần điều kiện gì?"), both)
        self.assertEqual(preferred_document_types("Bị kỷ luật khiển trách có được học bổng không?"),
                         {"student_handbook"})

    def test_academic_year_comes_from_query_or_calendar(self):
        self.assertEqual(requested_academic_year("học phí 2025 - 2026"), "2025-2026")
        self.assertEqual(requested_academic_year("học phí", date(2026, 10, 27)), "2026-2027")
        self.assertEqual(requested_academic_year("học phí", date(2027, 3, 1)), "2026-2027")


class LexicalTextTests(unittest.TestCase):
    SOURCE = "Quy định Học bổng Trần Đại Nghĩa"

    def test_article_chunk_gains_missing_document_name_words(self):
        row = {"text": "Học bổng có 2 mức.", "metadata": {"source": self.SOURCE, "title": "Điều 8. Mức Học bổng"}}
        self.assertEqual(lexical_text(row).splitlines()[0], "Quy định Trần Đại Nghĩa")

    def test_name_already_in_chunk_is_not_repeated(self):
        row = {"text": "Hội đồng xét Học bổng Trần Đại Nghĩa theo quy định.", "metadata": {"source": self.SOURCE}}
        self.assertEqual(lexical_text(row).splitlines()[0], "")


class TuitionYearRankingTests(unittest.TestCase):
    TEXT = "Học phí ngành ET1 Kỹ thuật Điện tử - Viễn thông theo tín chỉ học phí."

    def setUp(self):
        self.manager = _manager([
            ("fee_2025", self.TEXT, {"document_type": "tuition_decision", "effective_period": "Năm học 2025-2026"}),
            ("fee_2026", self.TEXT, {"document_type": "tuition_decision", "effective_period": "Năm học 2026-2027"}),
        ], ["fee_2025", "fee_2026"])

    def test_explicit_year_selects_matching_decision(self):
        self.assertEqual(self.manager.similarity_search("Học phí ET1 năm 2026-2027", k=2)[0]["id"], "fee_2026")
        self.assertEqual(self.manager.similarity_search("Học phí ET1 năm 2025-2026", k=2)[0]["id"], "fee_2025")

    def test_programme_code_does_not_restrict_tuition_to_curricula(self):
        self.assertEqual(len(self.manager.similarity_search("Học phí ET1 năm 2026-2027", k=2)), 2)


class NewDocumentIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunks = document_loader.load_all_chunks()

    def _metadata(self, file_name):
        return [chunk.metadata for chunk in self.chunks if chunk.metadata["file_name"] == file_name]

    def test_new_documents_are_indexed_with_type_and_display_name(self):
        expected = {
            "hoc_phi_2026_2027_verified.md": "tuition_decision",
            "quy_dinh_ngoai_ngu_k71_verified.md": "language_regulation",
            "quy_dinh_ren_luyen_2026_verified.md": "conduct_regulation",
            "quy_che_cong_tac_sinh_vien_2026_verified.md": "student_affairs_regulation",
            "quy_dinh_mien_giam_hoc_phi_verified.md": "tuition_support_regulation",
            "quy_dinh_hoc_bong_tran_dai_nghia_verified.md": "scholarship_regulation",
            "ke_hoach_nam_hoc_2026_2027_verified.md": "academic_calendar",
        }
        for file_name, document_type in expected.items():
            with self.subTest(file_name=file_name):
                metadata = self._metadata(file_name)
                self.assertTrue(metadata)
                self.assertEqual({meta["document_type"] for meta in metadata}, {document_type})
                self.assertEqual({meta["source"] for meta in metadata}, {DOCUMENT_DISPLAY_NAMES[file_name]})

    def test_tuition_parts_scope_fees_by_training_mode(self):
        chunks = [chunk for chunk in self.chunks if chunk.metadata["file_name"] == "hoc_phi_2025_2026_verified.md"]

        def level(snippet):
            return next(chunk.metadata["education_level"] for chunk in chunks if snippet in chunk.text)

        self.assertEqual(level("KT Cơ điện tử, KT điện tử-viễn thông"), "general")
        self.assertEqual(level("II. Chương trình đào tạo hình thức vừa làm vừa học"), "continuing")
        self.assertEqual(level("III. Chương trình đào tạo sau đại học"), "postgraduate")
        # "Phụ lục này" in running text must not reset the appendix scope.
        self.assertEqual(level("Phụ lục này. Điều này do Giám đốc"), "general")

    def test_hand_transcribed_calendar_cites_pdf_page_one(self):
        # The editorial note before the first page heading has no PDF page.
        pages = {chunk.metadata["page"] for chunk in self.chunks
                 if chunk.metadata["file_name"] == "ke_hoach_nam_hoc_2026_2027_verified.md" and "Tuần" in chunk.text}
        self.assertEqual(pages, {1})


class DisplaySourceTests(unittest.TestCase):
    def test_display_names_pass_through_unchanged(self):
        name = DOCUMENT_DISPLAY_NAMES["quy_che_cong_tac_sinh_vien_2026_verified.md"]
        self.assertEqual(clean_display_source(name), name)

    def test_file_names_map_to_display_names(self):
        self.assertEqual(clean_display_source("quy_dinh_ren_luyen_2026_verified.md"),
                         DOCUMENT_DISPLAY_NAMES["quy_dinh_ren_luyen_2026_verified.md"])


if __name__ == "__main__":
    unittest.main()
