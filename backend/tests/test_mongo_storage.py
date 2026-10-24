"""DataLoader chạy trên kho hồ sơ MongoDB và cấu hình kết nối MongoDB."""
import sys
import unittest
from pathlib import Path
from unittest import mock

import mongomock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from testing_support import sample_profiles
from app.services import mongo_client
from app.services.data_loader import DataLoader
from app.services.profile_repository import MongoProfileRepository

K67_ID = "20220001"
K68_ID = "20231890"


def _local_profile(key):
    return sample_profiles()[key]


class DataLoaderOnMongoTests(unittest.TestCase):
    def setUp(self):
        self.database = mongomock.MongoClient()["advisor_test"]
        self.repository = MongoProfileRepository(self.database)
        self.repository.save(K67_ID, _local_profile(K67_ID))
        self.repository.save(K68_ID, _local_profile(K68_ID))
        self.loader = DataLoader(profiles=self.repository)

    def test_loads_default_profile_and_curriculum_from_mongo(self):
        self.assertEqual(self.loader.current_student_id, K67_ID)
        self.assertEqual(self.loader.get_program()["curriculum_version"], "2022")

    def test_switch_and_scope_resolve_profiles_from_mongo(self):
        with self.loader.profile_scope(K68_ID):
            self.assertEqual(self.loader.get_program()["curriculum_version"], "2023")
        self.loader.load_student_profile(K68_ID)
        self.assertEqual(self.loader.current_student_id, K68_ID)

    def test_lists_profiles_stored_in_mongo(self):
        ids = [key for key, _ in self.loader.profiles.list()]
        self.assertEqual(ids, [K67_ID, K68_ID])

    def test_profile_updates_are_persisted_to_mongo(self):
        self.loader.update_profile_info_for(K67_ID, {"student_name": "Tên mới"})

        stored = self.database["student_profiles"].find_one({"_id": K67_ID})
        self.assertEqual(stored["profile"]["info"]["student_name"], "Tên mới")
        self.assertEqual(DataLoader(profiles=self.repository).student_profile["info"]["student_name"], "Tên mới")

    def test_saved_profile_is_visible_inside_open_scope(self):
        with self.loader.profile_scope(K68_ID):
            updated = _local_profile(K68_ID)
            updated["info"] = {**updated["info"], "student_name": "Đổi trong scope"}
            self.loader.save_profile_for(K68_ID, updated)
            self.assertEqual(self.loader.student_profile["info"]["student_name"], "Đổi trong scope")
        stored = self.database["student_profiles"].find_one({"_id": K68_ID})
        self.assertEqual(stored["profile"]["info"]["student_name"], "Đổi trong scope")


class MongoClientConfigTests(unittest.TestCase):
    def tearDown(self):
        mongo_client.get_mongo_database.cache_clear()

    def test_redacts_password_in_connection_string(self):
        uri = "mongodb+srv://advisor:S3cret!@cluster0.abcd.mongodb.net/?retryWrites=true"
        redacted = mongo_client.redact_uri(uri)
        self.assertNotIn("S3cret", redacted)
        self.assertIn("advisor:***@cluster0", redacted)

    def test_empty_uri_is_a_configuration_error(self):
        mongo_client.get_mongo_database.cache_clear()
        with mock.patch.object(mongo_client, "MONGODB_URI", ""):
            with self.assertRaises(mongo_client.MongoConfigurationError):
                mongo_client.connect_mongo_database()

    def test_unreachable_server_fails_fast_without_leaking_password(self):
        mongo_client.get_mongo_database.cache_clear()
        uri = "mongodb://advisor:S3cret@127.0.0.1:1/?directConnection=true"
        with mock.patch.object(mongo_client, "MONGODB_URI", uri), \
                mock.patch.object(mongo_client, "CONNECT_TIMEOUT_MS", 200):
            with self.assertRaises(mongo_client.MongoConfigurationError) as raised:
                mongo_client.connect_mongo_database()
        self.assertNotIn("S3cret", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
