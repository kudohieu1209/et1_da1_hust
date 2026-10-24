import hashlib
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.auth.passwords import hash_password, verify_password
from app.services.conversation_service import MongoConversationService
from legacy_storage import MigrationConflictError, import_legacy, plan_import, read_legacy
from testing_support import isolated_database


class StorageMigrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = isolated_database()
        self.password_hash = hash_password("legacy-password")
        self.snapshot = {
            "profiles": [{"key": "custom", "profile": {"info": {"student_id": "sv-a"}, "transcript": []}}],
            "users": [{"student_id": "sv-a", "password_hash": self.password_hash}],
            "conversations": [{"id": "chat-a", "student_id": "sv-a", "title": "Môn học",
                               "created_at": "2026-01-01", "updated_at": "2026-01-01"}],
            "messages": [{"id": 1, "conversation_id": "chat-a", "role": "user",
                          "content": "ET4230?", "created_at": "2026-01-01"}],
        }

    def test_import_preserves_password_and_is_idempotent(self):
        first = import_legacy(self.snapshot, self.database)
        second = import_legacy(self.snapshot, self.database)
        self.assertTrue(first["verified"])
        self.assertEqual(first["inserted"], dict.fromkeys(self.snapshot, 1))
        self.assertEqual(second["inserted"], dict.fromkeys(self.snapshot, 0))
        self.assertTrue(verify_password("legacy-password", self.database.users.find_one()["password_hash"]))
        conversation = MongoConversationService(self.database)
        self.assertEqual(conversation.get("chat-a", "sv-a")["message_count"], 1)
        added = conversation.append_message("chat-a", "sv-a", "assistant", "Trả lời")
        self.assertGreater(added["id"], 1)

    def test_existing_mongo_profile_and_password_win(self):
        self.database.student_profiles.insert_one({"_id": "sv-a", "student_id": "sv-a", "profile": {"new": True}})
        self.database.users.insert_one({"_id": "sv-a", "password_hash": "new-hash"})
        report = import_legacy(self.snapshot, self.database)
        self.assertEqual(self.database.student_profiles.find_one()["profile"], {"new": True})
        self.assertEqual(self.database.users.find_one()["password_hash"], "new-hash")
        self.assertEqual(report["differences_kept_on_mongo"]["profiles"], 1)
        self.assertEqual(self.database.student_profiles.count_documents({}), 1)

    def test_numeric_id_collision_allocates_id_without_overwrite(self):
        self.database.messages.insert_one({"id": 1, "conversation_id": "other", "content": "keep"})
        import_legacy(self.snapshot, self.database)
        import_legacy(self.snapshot, self.database)
        self.assertEqual(self.database.messages.count_documents({}), 2)
        self.assertEqual(self.database.messages.find_one({"id": 1})["content"], "keep")
        self.assertGreater(self.database.messages.find_one({"conversation_id": "chat-a"})["id"], 1)

    def test_previous_import_without_marker_is_not_duplicated(self):
        self.database.messages.insert_one(dict(self.snapshot["messages"][0]))
        self.assertEqual(import_legacy(self.snapshot, self.database)["inserted"]["messages"], 0)

    def test_owner_conflict_rejected_before_any_writes(self):
        self.database.conversations.insert_one({"_id": "chat-a", "student_id": "sv-b"})
        with self.assertRaises(MigrationConflictError):
            import_legacy(self.snapshot, self.database)
        self.assertEqual(self.database.users.count_documents({}), 0)
        self.assertEqual(self.database.student_profiles.count_documents({}), 0)
        self.assertEqual(self.database.list_collection_names(), ["conversations"])

    def test_check_does_not_write(self):
        self.assertEqual(plan_import(self.snapshot, self.database)["would_insert"]["messages"], 1)
        self.assertEqual(self.database.list_collection_names(), [])

    def test_missing_sources_do_not_create_files(self):
        self.assertEqual(read_legacy(self.root), {name: [] for name in self.snapshot})
        self.assertEqual(list(self.root.iterdir()), [])

    def test_reader_decodes_metadata_without_modifying_source(self):
        path = self.root / "chat_history.sqlite3"
        with closing(sqlite3.connect(path)) as connection:
            connection.executescript("""
                CREATE TABLE conversations (id TEXT, student_id TEXT, title TEXT, created_at TEXT, updated_at TEXT);
                INSERT INTO conversations VALUES ('chat-a','sv-a','Title','2026-01-01','2026-01-01');
                CREATE TABLE messages (id INTEGER, conversation_id TEXT, role TEXT, content TEXT, created_at TEXT,
                                       suggested_actions_json TEXT, data_context_json TEXT, sources_json TEXT);
            """)
            connection.execute("INSERT INTO messages VALUES (?,?,?,?,?,?,?,?)",
                               (1, "chat-a", "assistant", "Reply", "2026-01-01", '[]', '{"course":"ET4230"}', '[]'))
            connection.commit()
        before = hashlib.sha256(path.read_bytes()).digest()
        result = read_legacy(self.root)
        self.assertEqual(result["messages"][0]["data_context"], {"course": "ET4230"})
        self.assertEqual(result["conversations"][0]["message_count"], 1)
        self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)


if __name__ == "__main__":
    unittest.main()
