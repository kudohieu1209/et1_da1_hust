import tempfile
import unittest
from pathlib import Path

from app.services.conversation_service import ConversationNotFoundError, ConversationService


class ConversationServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = ConversationService(Path(self.temp_dir.name) / "chat.sqlite3")

    def tearDown(self):
        self.temp_dir.cleanup()

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

        reopened = ConversationService(self.service.db_path)
        detail = reopened.get(conversation["id"], "20220001")
        self.assertEqual(detail["title"], "Điều kiện ET4230?")
        self.assertEqual([item["role"] for item in detail["messages"]], ["user", "assistant"])
        self.assertEqual(detail["messages"][1]["sources"][0]["file_name"], "ctt_et1_2022_verified.md")

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


if __name__ == "__main__":
    unittest.main()

