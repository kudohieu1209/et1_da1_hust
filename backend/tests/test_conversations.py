import unittest

import mongomock

from app.services.conversation_service import (
    ConversationNotFoundError,
    MongoConversationService,
)


class ConversationContract:
    """Hành vi chung mà mọi kho lưu hội thoại phải đáp ứng.

    Lớp con cung cấp ``make_service`` (một kho mới) và ``reopen`` (một
    instance khác trỏ tới cùng dữ liệu, để kiểm tra tính bền vững).
    """

    def make_service(self):
        raise NotImplementedError

    def reopen(self, service):
        raise NotImplementedError

    def setUp(self):
        self.service = self.make_service()

    def test_messages_and_metadata_survive_new_service_instance(self):
        conversation = self.service.create("20220001")
        self.service.append_message(conversation["id"], "20220001", "user", "Điều kiện ET4230?")
        self.service.append_message(
            conversation["id"],
            "20220001",
            "assistant",
            "Bạn chỉ cần một nhánh.",
            sources=[{"file_name": "ctt_et1_2022_verified.md"}],
            data_context={"intent": "COURSE_ELIGIBILITY_CHECK"},
            model_used="rag-local",
        )

        detail = self.reopen(self.service).get(conversation["id"], "20220001")
        self.assertEqual(detail["title"], "Điều kiện ET4230?")
        self.assertEqual([item["role"] for item in detail["messages"]], ["user", "assistant"])
        self.assertEqual(detail["messages"][1]["sources"][0]["file_name"], "ctt_et1_2022_verified.md")
        self.assertEqual(detail["messages"][1]["data_context"], {"intent": "COURSE_ELIGIBILITY_CHECK"})
        self.assertEqual(detail["messages"][1]["model_used"], "rag-local")
        self.assertEqual(detail["messages"][0]["suggested_actions"], [])
        self.assertIsNone(detail["messages"][0]["data_context"])

    def test_owner_isolation_archive_and_delete(self):
        conversation = self.service.create("student-a")
        with self.assertRaises(ConversationNotFoundError):
            self.service.get(conversation["id"], "student-b")

        updated = self.service.update(conversation["id"], "student-a", is_pinned=True, is_archived=True)
        self.assertTrue(updated["is_pinned"])
        self.assertTrue(updated["is_archived"])
        self.assertEqual(self.service.list("student-a"), [])
        self.assertEqual(len(self.service.list("student-a", include_archived=True)), 1)

        self.service.delete(conversation["id"], "student-a")
        with self.assertRaises(ConversationNotFoundError):
            self.service.get(conversation["id"], "student-a")

    def test_delete_by_other_student_is_rejected(self):
        conversation = self.service.create("student-a")
        with self.assertRaises(ConversationNotFoundError):
            self.service.delete(conversation["id"], "student-b")
        self.assertEqual(len(self.service.list("student-a")), 1)

    def test_list_summary_counts_messages_and_shows_latest_preview(self):
        conversation = self.service.create("sv")
        self.service.append_message(conversation["id"], "sv", "user", "Câu hỏi 1")
        self.service.append_message(conversation["id"], "sv", "assistant", "Trả lời 1")

        [summary] = self.service.list("sv")
        self.assertEqual(summary["message_count"], 2)
        self.assertEqual(summary["last_message_preview"], "Trả lời 1")
        self.assertEqual(
            set(summary),
            {"id", "student_id", "title", "is_archived", "is_pinned", "created_at", "updated_at",
             "message_count", "last_message_preview"},
        )

    def test_pinned_conversations_are_listed_first(self):
        first = self.service.create("sv", "Cũ")
        self.service.create("sv", "Mới")
        self.service.update(first["id"], "sv", is_pinned=True)

        titles = [item["title"] for item in self.service.list("sv")]
        self.assertEqual(titles[0], "Cũ")

    def test_get_messages_limit_returns_most_recent(self):
        conversation = self.service.create("sv")
        for index in range(5):
            self.service.append_message(conversation["id"], "sv", "user", f"tin {index}")

        recent = self.service.get_messages(conversation["id"], "sv", limit=2)
        self.assertEqual([item["content"] for item in recent], ["tin 3", "tin 4"])
        self.assertLess(recent[0]["id"], recent[1]["id"])

    def test_title_comes_from_first_user_message_only(self):
        conversation = self.service.create("sv")
        self.service.append_message(conversation["id"], "sv", "user", "Đầu tiên")
        self.service.append_message(conversation["id"], "sv", "user", "Thứ hai")
        self.assertEqual(self.service.get(conversation["id"], "sv")["title"], "Đầu tiên")

    def test_invalid_input_is_rejected(self):
        conversation = self.service.create("sv")
        with self.assertRaises(ValueError):
            self.service.append_message(conversation["id"], "sv", "hacker", "x")
        with self.assertRaises(ValueError):
            self.service.append_message(conversation["id"], "sv", "user", "   ")
        with self.assertRaises(ValueError):
            self.service.update(conversation["id"], "sv", title="  ")
        with self.assertRaises(ValueError):
            self.service.create("  ")

    def test_ensure_creates_when_id_missing_and_rejects_foreign_id(self):
        created = self.service.ensure(None, "sv")
        self.assertEqual(self.service.ensure(created["id"], "sv")["id"], created["id"])
        with self.assertRaises(ConversationNotFoundError):
            self.service.ensure(created["id"], "khác")


class MongoConversationServiceTests(ConversationContract, unittest.TestCase):
    def make_service(self):
        self.client = mongomock.MongoClient()
        return MongoConversationService(self.client["advisor_test"])

    def reopen(self, service):
        return MongoConversationService(self.client["advisor_test"])


if __name__ == "__main__":
    unittest.main()
