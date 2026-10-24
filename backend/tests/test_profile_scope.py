import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from testing_support import sample_profiles
from app.services.data_loader import data_loader


class ProfileScopeTests(unittest.TestCase):
    def setUp(self):
        data_loader.load_student_profile("20220001")

    def test_scope_restores_active_profile_when_handler_raises(self):
        with self.assertRaises(RuntimeError):
            with data_loader.profile_scope("20231890"):
                self.assertEqual(data_loader.get_program()["curriculum_version"], "2023")
                raise RuntimeError("handler failed")

        self.assertEqual(data_loader.current_student_id, "20220001")
        self.assertEqual(data_loader.get_program()["curriculum_version"], "2022")

    def test_other_threads_keep_seeing_active_profile_during_scope(self):
        seen = {}

        def read_version():
            seen["version"] = data_loader.get_program()["curriculum_version"]

        with data_loader.profile_scope("20231890"):
            reader = threading.Thread(target=read_version)
            reader.start()
            reader.join(timeout=5)
            self.assertEqual(data_loader.get_program()["curriculum_version"], "2023")

        self.assertEqual(seen["version"], "2022")

    def test_switch_in_other_thread_is_not_blocked_by_open_scope(self):
        with data_loader.profile_scope("20231890"):
            switcher = threading.Thread(target=data_loader.load_student_profile, args=("20224567",))
            switcher.start()
            switcher.join(timeout=5)

            self.assertFalse(switcher.is_alive(), "Chuyển hồ sơ bị chặn bởi scope đang mở")
            self.assertEqual(data_loader.current_student_id, "20231890")

        self.assertEqual(data_loader.current_student_id, "20224567")

    def test_resolves_profile_file_by_info_student_id(self):
        student_id = sample_profiles()["custom"]["info"]["student_id"]

        self.assertEqual(data_loader.find_profile_key(student_id), "custom")

    def test_rejects_profile_ids_that_escape_students_directory(self):
        for unsafe in ("../student_profile", "..\\students\\20220001", "", "a/b"):
            with self.subTest(student_id=unsafe):
                with self.assertRaises(FileNotFoundError):
                    data_loader.load_student_profile(unsafe)
                self.assertIsNone(data_loader.find_profile_key(unsafe))
        self.assertEqual(data_loader.current_student_id, "20220001")

    def test_unknown_student_id_resolves_to_none(self):
        self.assertIsNone(data_loader.find_profile_key("không-tồn-tại"))
        self.assertIsNone(data_loader.find_profile_key(None))


if __name__ == "__main__":
    unittest.main()
