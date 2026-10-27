import unittest

import mongomock

from app.services.profile_repository import MongoProfileRepository


def _profile(student_id, name="SV"):
    return {"info": {"student_id": student_id, "student_name": name}, "transcript": [{"code": "ET3220"}]}


class ProfileRepositoryContract:
    def make_repository(self):
        raise NotImplementedError

    def setUp(self):
        self.repository = self.make_repository()

    def test_saved_profile_round_trips_exactly(self):
        profile = _profile("20220001", "Nguyễn Văn A")
        self.repository.save("20220001", profile)
        self.assertEqual(self.repository.get("20220001"), profile)

    def test_missing_profile_returns_none(self):
        self.assertIsNone(self.repository.get("không-có"))

    def test_save_overwrites_existing_profile(self):
        self.repository.save("custom", _profile("1", "Cũ"))
        self.repository.save("custom", _profile("2", "Mới"))
        self.assertEqual(self.repository.get("custom")["info"]["student_name"], "Mới")
        self.assertEqual(len(self.repository.list()), 1)

    def test_find_key_matches_key_then_inner_student_id(self):
        self.repository.save("20220001", _profile("20220001"))
        self.repository.save("custom", _profile("20228888"))

        self.assertEqual(self.repository.find_key("20220001"), "20220001")
        self.assertEqual(self.repository.find_key("20228888"), "custom")
        self.assertIsNone(self.repository.find_key("99999999"))

    def test_list_is_sorted_by_key(self):
        self.repository.save("b", _profile("2"))
        self.repository.save("a", _profile("1"))
        self.assertEqual([key for key, _ in self.repository.list()], ["a", "b"])

    def test_unsafe_keys_are_rejected(self):
        for unsafe in ("../x", "a/b", "a\\b", "", "x" * 40, "abc\n"):
            with self.subTest(key=unsafe):
                self.assertIsNone(self.repository.get(unsafe))
                self.assertIsNone(self.repository.find_key(unsafe))
                with self.assertRaises(ValueError):
                    self.repository.save(unsafe, _profile("1"))


class MongoProfileRepositoryTests(ProfileRepositoryContract, unittest.TestCase):
    def make_repository(self):
        return MongoProfileRepository(mongomock.MongoClient()["advisor_test"])


if __name__ == "__main__":
    unittest.main()
