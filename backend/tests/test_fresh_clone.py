import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.services import data_loader as data_loader_module
from app.services.data_loader import DataLoader
from app.services.profile_repository import FileProfileRepository


class FreshCloneTests(unittest.TestCase):
    """Clone mới không có hồ sơ demo (bị .gitignore) vẫn phải khởi động được."""

    def test_starts_without_any_student_profile(self):
        with tempfile.TemporaryDirectory() as empty_dir:
            missing = Path(empty_dir) / "student_profile.json"
            with mock.patch.object(data_loader_module, "STUDENT_PROFILE_FILE", missing):
                loader = DataLoader(profiles=FileProfileRepository(Path(empty_dir)))
        self.assertEqual(loader.current_student_id, "")
        self.assertEqual(loader.get_student_profile()["transcript"], [])
        self.assertTrue(loader.get_all_courses())

    def test_scoped_profile_still_used_per_request(self):
        with tempfile.TemporaryDirectory() as empty_dir:
            profiles = FileProfileRepository(Path(empty_dir))
            missing = Path(empty_dir) / "student_profile.json"
            with mock.patch.object(data_loader_module, "STUDENT_PROFILE_FILE", missing):
                loader = DataLoader(profiles=profiles)
            profiles.save("20238888", {
                "info": {"student_id": "20238888", "class_name": "Điện tử 02 - K68", "program_code": "ET1"},
                "transcript": [], "passed_courses": [], "failed_courses": [], "total_courses_completed": 0,
            })
            token = loader.enter_scope(loader.load_scope_state("20238888"))
            try:
                self.assertEqual(loader.current_student_id, "20238888")
                self.assertEqual(loader.get_program()["curriculum_version"], "2023")
            finally:
                loader.exit_scope(token)
        self.assertEqual(loader.current_student_id, "")


if __name__ == "__main__":
    unittest.main()
