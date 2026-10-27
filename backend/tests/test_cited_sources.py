import unittest
from types import SimpleNamespace
from unittest import mock

from app.rag.gemini_service import GeminiService, split_cited_sources
from app.services.chatbot_service import rag_suggestions


def _chunk(source):
    return {"text": "...", "metadata": {"source": source, "title": source, "page": 1}}


def _service_replying(text):
    service = GeminiService.__new__(GeminiService)
    service.api_key, service.model_name, service.fallback_model = "test", "gemini-test", None
    service.client = mock.Mock()
    service.client.models.generate_content.return_value = SimpleNamespace(text=text)
    return service


CHUNKS = [_chunk("quy_che_dao_tao_2025_verified.md"), _chunk("hoc_phi_2025_2026_verified.md")]


class SplitCitedSourcesTests(unittest.TestCase):
    def test_tag_is_removed_and_parsed(self):
        self.assertEqual(split_cited_sources("Trả lời.\n[[NGUON: 1, 3]]"), ("Trả lời.", {1, 3}))

    def test_zero_means_no_source(self):
        self.assertEqual(split_cited_sources("Chào bạn!\n`[[NGUON: 0]]`"), ("Chào bạn!", set()))

    def test_missing_tag_keeps_legacy_behaviour(self):
        self.assertEqual(split_cited_sources("Trả lời."), ("Trả lời.", None))


class GenerateResponseSourceTests(unittest.TestCase):
    def test_answer_without_documents_has_no_sources(self):
        result = _service_replying("Mình là HUST Advisor.\n[[NGUON: 0]]").generate_response("bạn là gì", CHUNKS)
        self.assertEqual(result["sources"], [])
        self.assertNotIn("NGUON", result["reply"])

    def test_only_cited_sources_are_returned(self):
        result = _service_replying("Theo quyết định học phí...\n[[NGUON: 2]]").generate_response("học phí", CHUNKS)
        self.assertEqual(len(result["sources"]), 1)
        self.assertNotIn("Quy chế", result["sources"][0]["source"])

    def test_untagged_answer_keeps_all_sources(self):
        result = _service_replying("Căn cứ Điều 9...").generate_response("học phí", CHUNKS)
        self.assertEqual(len(result["sources"]), 2)


class RagSuggestionTests(unittest.TestCase):
    def test_tuition_question_gets_tuition_suggestions(self):
        suggestions = rag_suggestions("học phí ngành ET1 bao nhiêu")
        self.assertTrue(all("Vi mạch" not in item for item in suggestions))
        self.assertIn("Không nộp học phí đúng hạn bị xử lý thế nào?", suggestions)

    def test_current_question_is_not_suggested_again(self):
        suggestions = rag_suggestions("Khi nào bị cảnh báo học tập?")
        self.assertNotIn("Khi nào bị cảnh báo học tập?", suggestions)
        self.assertIn("Trường hợp nào bị buộc thôi học?", suggestions)

    def test_unknown_topic_uses_default(self):
        self.assertEqual(len(rag_suggestions("ký túc xá ở đâu")), 4)
        self.assertLessEqual(max(len(rag_suggestions(q)) for q in ["học bổng", "đồ án", "đăng ký"]), 4)


if __name__ == "__main__":
    unittest.main()
