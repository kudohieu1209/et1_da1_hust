import unittest
from unittest import mock

from app.models.schemas import AdvisingMemoryUpdate
from app.services.chatbot_service import chatbot_service
from app.services.data_loader import data_loader
from app.services.student_memory import StudentMemoryRepository
from testing_support import isolated_database


class ConversationContextTests(unittest.TestCase):
    def setUp(self):
        data_loader.load_student_profile("20220001")

    def turn(self, query, history):
        result = chatbot_service.process_message(query, history)
        history.extend([{"role": "user", "content": query},
                        {"role": "assistant", "content": result["reply"], "data_context": result.get("data_context")}])
        return result

    def test_prerequisite_codes_in_answer_do_not_replace_user_course_focus(self):
        history = []
        self.turn("Điều kiện ET4230?", history)
        result = self.turn("Môn đó cần gì?", history)
        self.assertEqual(result["data_context"]["check_results"][0]["course_code"], "ET4230")

    def test_ambiguous_single_reference_asks_instead_of_selecting_a_course(self):
        history = []
        self.turn("Điều kiện ET4230 và ET3300?", history)
        result = self.turn("Môn đó cần gì?", history)
        self.assertEqual(result["intent"], "CONTEXT_CLARIFICATION")
        self.assertIn("ET4230", result["reply"])
        self.assertIn("ET3300", result["reply"])
        explicit = self.turn("ET3300", history)
        self.assertEqual(explicit["data_context"]["check_results"][0]["course_code"], "ET3300")

    def test_explicit_new_course_replaces_old_focus(self):
        history = []
        self.turn("Điều kiện ET4230?", history)
        self.turn("Điều kiện ET3300?", history)
        result = self.turn("Nếu trượt môn đó thì sao?", history)
        self.assertEqual(result["data_context"]["failed_course_code"], "ET3300")

    def test_plural_reference_checks_all_courses(self):
        history = []
        self.turn("ET4230 và ET3300?", history)
        result = self.turn("Cả hai môn đó học được không?", history)
        self.assertEqual({row["course_code"] for row in result["data_context"]["check_results"]}, {"ET4230", "ET3300"})

    def test_term_followup_preserves_credit_policy_topic(self):
        history = []
        with mock.patch.object(chatbot_service, "_handle_rag_query", return_value={"reply": "Quy chế", "intent": "RAG_HUST_KNOWLEDGE"}) as rag:
            self.turn("Kỳ chính được đăng ký tối đa bao nhiêu tín chỉ?", history)
            self.turn("Còn kỳ hè thì sao?", history)
            resolved = rag.call_args.args[0]
            self.assertIn("tín chỉ", resolved)
            self.assertIn("kỳ hè", resolved)
            self.assertNotIn("kỳ chính", resolved)

    def test_new_conversation_has_no_global_focus(self):
        self.turn("ET4230?", [])
        result = self.turn("Môn đó cần gì?", [])
        self.assertEqual(result["intent"], "CONTEXT_CLARIFICATION")


class StudentMemoryTests(unittest.TestCase):
    def test_disabled_or_changed_curriculum_memory_is_not_applied(self):
        memory = StudentMemoryRepository(isolated_database())
        curriculum = {"program_code": "ET1", "curriculum_version": "2022"}
        tracks = [{"id": "MOD6"}]
        memory.save("a", AdvisingMemoryUpdate(target_track="MOD6"), curriculum)
        self.assertEqual(memory.for_advising("a", curriculum, tracks), {})
        memory.save("a", AdvisingMemoryUpdate(enabled=True, target_track="MOD6"), curriculum)
        self.assertTrue(memory.for_advising("a", curriculum, tracks))
        self.assertEqual(memory.for_advising("b", curriculum, tracks), {})
        self.assertEqual(memory.for_advising("a", {**curriculum, "curriculum_version": "2023"}, tracks), {})
        self.assertEqual(memory.for_advising("a", curriculum, []), {})
