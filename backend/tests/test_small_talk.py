import unittest
from unittest import mock

from app.services import chatbot_service as chatbot_module
from app.services.chatbot_service import chatbot_service, detect_small_talk


class SmallTalkDetectionTests(unittest.TestCase):
    def test_social_messages_are_small_talk(self):
        cases = {
            "bạn chúc mình ngủ tối ngon đi": "goodnight",
            "ngủ ngon nhé": "goodnight",
            "cảm ơn bạn nhiều": "thanks",
            "Cảm ơn nha!": "thanks",
            "bye bạn": "bye",
            "chúc mình qua đồ án nhé": "wish",
            "dạo này bạn khỏe không": "howareyou",
            "mình mệt quá": "feeling",
            "bạn giỏi quá": "compliment",
            "ok": "ack",
        }
        for message, category in cases.items():
            with self.subTest(message=message):
                self.assertEqual(detect_small_talk(message), category)

    def test_questions_and_requests_are_not_small_talk(self):
        for message in [
            "cảm ơn, vậy học phí bao nhiêu?",
            "mệt vì trượt môn ET3300 quá",
            "gợi ý môn kỳ tới",
            "điều kiện nhận đồ án tốt nghiệp",
            "mình buồn vì cảnh báo học tập",
            "không",
        ]:
            with self.subTest(message=message):
                self.assertIsNone(detect_small_talk(message))

    def test_course_code_is_never_small_talk(self):
        self.assertIsNone(detect_small_talk("cảm ơn", ["ET3300"]))


class SmallTalkReplyTests(unittest.TestCase):
    def test_goodnight_without_llm_uses_template_not_rag(self):
        with mock.patch.object(chatbot_module.gemini_service, "small_talk", return_value=None), \
                mock.patch.object(chatbot_module.rag_engine, "query") as rag_query:
            result = chatbot_service.process_message("bạn chúc mình ngủ tối ngon đi")
        rag_query.assert_not_called()
        self.assertEqual(result["intent"], "SMALL_TALK")
        self.assertIn("ngủ thật ngon", result["reply"])
        self.assertEqual(result["sources"], [])

    def test_llm_reply_is_used_when_available(self):
        with mock.patch.object(chatbot_module.gemini_service, "small_talk", return_value="Ngủ ngon nha! 🌙"):
            result = chatbot_service.process_message("ngủ ngon nhé")
        self.assertEqual(result["reply"], "Ngủ ngon nha! 🌙")

    def test_creator_question_gets_intro_not_rag(self):
        for message in ["bạn do ai tạo ra?", "ai làm ra bạn vậy", "bạn dùng model gì", "bạn có phải chatgpt không"]:
            with self.subTest(message=message), \
                    mock.patch.object(chatbot_module.rag_engine, "query") as rag_query:
                result = chatbot_service.process_message(message)
            rag_query.assert_not_called()
            self.assertEqual(result["intent"], "GENERAL_GREETING")
            self.assertIn("không phải kênh tư vấn chính thức", result["reply"])

    def test_off_topic_without_llm_does_not_dump_documents(self):
        fallback = {"reply": "Mình tra được các nội dung liên quan...", "sources": [{"source": "x"}],
                    "model_used": "rag-knowledge-engine"}
        with mock.patch.object(chatbot_module.rag_engine, "query", return_value=fallback):
            result = chatbot_service.process_message("hôm nay trời đẹp quá")
        self.assertEqual(result["intent"], "OUT_OF_SCOPE")
        self.assertNotIn("Mình tra được", result["reply"])

    def test_hust_question_without_llm_still_returns_documents(self):
        fallback = {"reply": "Mình tra được các nội dung liên quan...", "sources": [{"source": "x"}],
                    "model_used": "rag-knowledge-engine"}
        with mock.patch.object(chatbot_module.rag_engine, "query", return_value=fallback):
            result = chatbot_service.process_message("ký túc xá của trường ở đâu")
        self.assertEqual(result["intent"], "RAG_HUST_KNOWLEDGE")


if __name__ == "__main__":
    unittest.main()
