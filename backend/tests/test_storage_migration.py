import tempfile
import unittest
from pathlib import Path

import mongomock

from app.services.conversation_service import ConversationService, MongoConversationService
from app.services.profile_repository import FileProfileRepository, MongoProfileRepository
from app.services.storage_migration import migrate_conversations, migrate_profiles


class StorageMigrationTests(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        self.sqlite = ConversationService(root / "chat.sqlite3")
        self.files = FileProfileRepository(root / "students")
        self.database = mongomock.MongoClient()["advisor_test"]

    def _seed_conversations(self):
        first = self.sqlite.create("sv-a")
        self.sqlite.append_message(first["id"], "sv-a", "user", "Điều kiện ET4230?")
        self.sqlite.append_message(
            first["id"], "sv-a", "assistant", "Cần ET3220.",
            sources=[{"source": "CTĐT"}], data_context={"intent": "X"}, model_used="local",
        )
        self.sqlite.update(first["id"], "sv-a", is_pinned=True)
        second = self.sqlite.create("sv-b", "Trống")
        return first, second

    def test_conversations_are_identical_after_migration(self):
        first, second = self._seed_conversations()

        report = migrate_conversations(self.sqlite.db_path, self.database)

        mongo = MongoConversationService(self.database)
        self.assertEqual(report, {"conversations": 2, "messages": 2})
        self.assertEqual(mongo.get(first["id"], "sv-a"), self.sqlite.get(first["id"], "sv-a"))
        self.assertEqual(mongo.list("sv-a"), self.sqlite.list("sv-a"))
        self.assertEqual(mongo.get(second["id"], "sv-b"), self.sqlite.get(second["id"], "sv-b"))

    def test_running_migration_twice_does_not_duplicate(self):
        self._seed_conversations()
        migrate_conversations(self.sqlite.db_path, self.database)
        migrate_conversations(self.sqlite.db_path, self.database)

        self.assertEqual(self.database["conversations"].count_documents({}), 2)
        self.assertEqual(self.database["messages"].count_documents({}), 2)

    def test_new_messages_after_migration_get_higher_ids(self):
        first, _ = self._seed_conversations()
        migrate_conversations(self.sqlite.db_path, self.database)

        mongo = MongoConversationService(self.database)
        added = mongo.append_message(first["id"], "sv-a", "user", "Tiếp")
        migrated_ids = [item["id"] for item in self.sqlite.get_messages(first["id"], "sv-a")]
        self.assertGreater(added["id"], max(migrated_ids))

    def test_missing_sqlite_file_migrates_nothing(self):
        report = migrate_conversations(Path(self.sqlite.db_path).with_name("không-có.sqlite3"), self.database)
        self.assertEqual(report, {"conversations": 0, "messages": 0})

    def test_profiles_are_copied_and_overwrite_is_idempotent(self):
        self.files.save("20220001", {"info": {"student_id": "20220001"}, "transcript": []})
        self.files.save("custom", {"info": {"student_id": "20228888"}, "transcript": [{"code": "ET3220"}]})
        target = MongoProfileRepository(self.database)

        self.assertEqual(migrate_profiles(self.files, target), 2)
        self.assertEqual(migrate_profiles(self.files, target), 2)

        self.assertEqual(target.list(), self.files.list())
        self.assertEqual(target.find_key("20228888"), "custom")


if __name__ == "__main__":
    unittest.main()
