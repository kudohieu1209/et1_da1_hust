"""POST /api/student/profile/update chỉ cho sửa thông tin hiển thị.

MSSV, lớp và CTĐT quyết định kết quả rà soát nên chỉ được lấy từ hồ sơ/bảng
điểm, không cho sửa tay qua form cài đặt.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.api import router_student
from app.auth.dependencies import current_student, student_scope
from app.main import app

ENDPOINT = "/api/student/profile/update"
TINY_PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


class ProfileUpdateApiTests(unittest.TestCase):
    def setUp(self):
        # Giả lập sinh viên đã đăng nhập; luồng đăng nhập thật nằm ở test_auth_api.
        app.dependency_overrides[current_student] = lambda: "20220001"
        app.dependency_overrides[student_scope] = lambda: "20220001"
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        patcher = mock.patch.object(
            router_student.student_service, "update_profile", return_value={"status": "success"}
        )
        self.update_profile = patcher.start()
        self.addCleanup(patcher.stop)

    def test_accepts_display_fields_and_passes_only_provided_ones(self):
        response = self.client.post(ENDPOINT, json={"student_name": "  Mai Duy Hiếu  ", "avatar_url": TINY_PNG})

        self.assertEqual(response.status_code, 200, response.text)
        self.update_profile.assert_called_once_with({"student_name": "Mai Duy Hiếu", "avatar_url": TINY_PNG}, "20220001")

    def test_empty_avatar_url_clears_uploaded_photo(self):
        response = self.client.post(ENDPOINT, json={"avatar_url": ""})
        self.assertEqual(response.status_code, 200, response.text)
        self.update_profile.assert_called_once_with({"avatar_url": ""}, "20220001")

    def test_rejects_identity_and_curriculum_fields(self):
        for field, value in (("student_id", "20239999"), ("curriculum_version", "2023"), ("class_name", "K68")):
            with self.subTest(field=field):
                response = self.client.post(ENDPOINT, json={field: value})
                self.assertEqual(response.status_code, 422)
        self.update_profile.assert_not_called()

    def test_rejects_unsafe_or_oversized_values(self):
        cases = {
            "avatar_url": "javascript:alert(1)",
            "avatar_gradient": "url(https://evil.example/x.png)",
            "student_name": "   ",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                self.assertEqual(self.client.post(ENDPOINT, json={field: value}).status_code, 422)
        oversized = "data:image/jpeg;base64," + "A" * 400_000
        self.assertEqual(self.client.post(ENDPOINT, json={"avatar_url": oversized}).status_code, 422)
        self.update_profile.assert_not_called()

    def test_accepts_preset_gradient(self):
        gradient = "linear-gradient(135deg, #d3132a, #8f1423)"
        response = self.client.post(ENDPOINT, json={"avatar_gradient": gradient})
        self.assertEqual(response.status_code, 200, response.text)


if __name__ == "__main__":
    unittest.main()
