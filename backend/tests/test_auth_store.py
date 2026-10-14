import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import mongomock

from app.auth.store import MongoAuthStore, SqliteAuthStore, UserExistsError

NOW = datetime(2026, 10, 15, 8, 0, tzinfo=timezone.utc)


def _user(student_id="20220001", **extra):
    return {"student_id": student_id, "password_hash": "scrypt$x", "created_at": NOW, **extra}


class AuthStoreContract:
    def make_store(self):
        raise NotImplementedError

    def setUp(self):
        self.store = self.make_store()

    def test_created_user_can_be_read_back_with_defaults(self):
        self.store.create_user(_user())
        user = self.store.get_user("20220001")
        self.assertEqual(user["password_hash"], "scrypt$x")
        self.assertFalse(user["is_admin"])
        self.assertFalse(user["is_demo"])
        self.assertEqual(user["failed_attempts"], 0)
        self.assertIsNone(user["locked_until"])

    def test_duplicate_student_id_is_rejected(self):
        self.store.create_user(_user())
        with self.assertRaises(UserExistsError):
            self.store.create_user(_user())

    def test_missing_user_is_none(self):
        self.assertIsNone(self.store.get_user("00000000"))

    def test_failed_logins_lock_account_then_reset_counter(self):
        self.store.create_user(_user())
        for _ in range(4):
            user = self.store.record_failed_login("20220001", NOW, max_attempts=5, lock_for=timedelta(minutes=15))
        self.assertEqual(user["failed_attempts"], 4)
        self.assertIsNone(user["locked_until"])

        user = self.store.record_failed_login("20220001", NOW, max_attempts=5, lock_for=timedelta(minutes=15))
        self.assertEqual(user["locked_until"], NOW + timedelta(minutes=15))
        self.assertEqual(user["failed_attempts"], 0)

    def test_successful_login_clears_failures_and_lock(self):
        self.store.create_user(_user())
        self.store.record_failed_login("20220001", NOW, max_attempts=2, lock_for=timedelta(minutes=15))
        self.store.record_failed_login("20220001", NOW, max_attempts=2, lock_for=timedelta(minutes=15))
        self.store.record_successful_login("20220001", NOW)
        user = self.store.get_user("20220001")
        self.assertEqual(user["failed_attempts"], 0)
        self.assertIsNone(user["locked_until"])
        self.assertEqual(user["last_login_at"], NOW)

    def test_delete_user_removes_account(self):
        self.store.create_user(_user())
        self.store.delete_user("20220001")
        self.assertIsNone(self.store.get_user("20220001"))

    def test_password_and_admin_flag_can_be_changed(self):
        self.store.create_user(_user())
        self.store.set_password("20220001", "scrypt$new")
        self.store.set_admin("20220001", True)
        user = self.store.get_user("20220001")
        self.assertEqual(user["password_hash"], "scrypt$new")
        self.assertTrue(user["is_admin"])

    def test_sessions_round_trip_and_delete(self):
        expires = NOW + timedelta(days=7)
        self.store.create_session("hash-a", "20220001", NOW, expires)
        self.store.create_session("hash-b", "20220001", NOW, expires)
        self.store.create_session("hash-c", "20231890", NOW, expires)

        self.assertEqual(self.store.get_session("hash-a"), {"student_id": "20220001", "expires_at": expires})
        self.store.delete_session("hash-a")
        self.assertIsNone(self.store.get_session("hash-a"))

        self.assertEqual(self.store.delete_sessions_for("20220001"), 1)
        self.assertIsNone(self.store.get_session("hash-b"))
        self.assertIsNotNone(self.store.get_session("hash-c"))


class SqliteAuthStoreTests(AuthStoreContract, unittest.TestCase):
    def make_store(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return SqliteAuthStore(Path(temp_dir.name) / "auth.sqlite3")


class SqliteSessionCleanupTests(unittest.TestCase):
    def test_creating_a_session_purges_expired_ones(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        store = SqliteAuthStore(Path(temp_dir.name) / "auth.sqlite3")
        store.create_session("old", "20220001", NOW - timedelta(days=9), NOW - timedelta(days=2))
        store.create_session("new", "20220001", NOW, NOW + timedelta(days=7))
        self.assertIsNone(store.get_session("old"))
        self.assertIsNotNone(store.get_session("new"))


class MongoAuthStoreTests(AuthStoreContract, unittest.TestCase):
    def make_store(self):
        return MongoAuthStore(mongomock.MongoClient()["advisor_test"])


if __name__ == "__main__":
    unittest.main()
