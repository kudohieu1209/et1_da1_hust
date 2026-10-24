import unittest
from app.services.data_loader import DataLoader
from app.services.profile_repository import MongoProfileRepository
from testing_support import isolated_database


class FreshCloneTests(unittest.TestCase):
    def test_starts_without_any_student_profile(self):
        loader = DataLoader(profiles=MongoProfileRepository(isolated_database()))
        self.assertEqual(loader.current_student_id, "")
        self.assertEqual(loader.get_student_profile()["transcript"], [])
        self.assertTrue(loader.get_all_courses())

    def test_scoped_profile_still_used_per_request(self):
        profiles = MongoProfileRepository(isolated_database())
        loader = DataLoader(profiles=profiles)
        profiles.save("20238888", {
            "info": {"student_id": "20238888", "class_name": "Điện tử 02 - K68", "program_code": "ET1"},
            "transcript": [], "passed_courses": [], "failed_courses": [], "total_courses_completed": 0,
        })
        with loader.profile_scope("20238888"):
            self.assertEqual(loader.current_student_id, "20238888")
            self.assertEqual(loader.get_program()["curriculum_version"], "2023")
        self.assertEqual(loader.current_student_id, "")
