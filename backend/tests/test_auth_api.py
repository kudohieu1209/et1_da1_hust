"""Đăng nhập end-to-end qua HTTP: cookie phiên, phân quyền và cô lập dữ liệu.

Chạy trên bản sao hồ sơ demo trong thư mục tạm (không ghi vào dữ liệu thật).
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from app.api import router_chat, router_conversations
from app.auth import runtime
from app.auth.passwords import hash_password
from app.auth.service import PER_IP_FAILURE_LIMIT, AuthService
from app.auth.store import SqliteAuthStore
from app.core.config import SESSION_COOKIE_NAME, STUDENTS_DIR
from app.main import app
from app.services.conversation_service import ConversationService
from app.services.data_loader import data_loader
from app.services.profile_repository import FileProfileRepository

K67 = "20220001"  # Mai Duy Hiếu, ET1-2022
K68 = "20231890"  # Phạm Quang Huy, ET1-2023
PASSWORD = "mat-khau-demo-2026"


class AuthApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for key in (K67, K68):
            if not (STUDENTS_DIR / f"{key}.json").exists():
                raise unittest.SkipTest(f"Thiếu hồ sơ demo cục bộ {key}.json")

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        (root / "students").mkdir()
        for key in (K67, K68):
            shutil.copy(STUDENTS_DIR / f"{key}.json", root / "students" / f"{key}.json")

        self.profiles = FileProfileRepository(root / "students")
        self.store = SqliteAuthStore(root / "auth.sqlite3")
        for key in (K67, K68):
            self.store.create_user({"student_id": key, "password_hash": hash_password(PASSWORD), "created_at": _now()})
        conversations = ConversationService(root / "chat.sqlite3")

        for patcher in (
            mock.patch.object(data_loader, "_profiles", self.profiles),
            mock.patch.object(runtime, "auth_service", AuthService(self.store, self.profiles)),
            mock.patch.object(router_chat, "conversation_service", conversations),
            mock.patch.object(router_conversations, "conversation_service", conversations),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _client(self, student_id=None):
        client = TestClient(app)
        if student_id:
            response = client.post("/api/auth/login", json={"student_id": student_id, "password": PASSWORD})
            self.assertEqual(response.status_code, 200, response.text)
        return client

    # --- Đăng nhập / phiên ------------------------------------------------
    def test_protected_endpoints_require_login(self):
        client = self._client()
        for method, path in (
            ("get", "/api/student/profile"),
            ("get", "/api/student/audit"),
            ("get", "/api/courses"),
            ("get", "/api/conversations"),
            ("get", "/api/auth/me"),
        ):
            with self.subTest(path=path):
                self.assertEqual(getattr(client, method)(path).status_code, 401)
        self.assertEqual(client.post("/api/chat", json={"message": "chào"}).status_code, 401)

    def test_login_sets_hardened_session_cookie_and_hides_secrets(self):
        client = self._client()
        response = client.post("/api/auth/login", json={"student_id": K67, "password": PASSWORD})

        self.assertEqual(response.status_code, 200)
        cookie = response.headers["set-cookie"]
        self.assertIn(f"{SESSION_COOKIE_NAME}=", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)
        self.assertNotIn("password", json.dumps(response.json()))
        self.assertEqual(response.json()["student_id"], K67)

    def test_wrong_password_is_rejected_and_account_locks(self):
        client = self._client()
        for _ in range(PER_IP_FAILURE_LIMIT):
            response = client.post("/api/auth/login", json={"student_id": K67, "password": "sai-mat-khau"})
            self.assertEqual(response.status_code, 401)
        locked = client.post("/api/auth/login", json={"student_id": K67, "password": PASSWORD})
        self.assertEqual(locked.status_code, 429)
        self.assertIn("Retry-After", locked.headers)

    def test_logout_ends_session(self):
        client = self._client(K67)
        self.assertEqual(client.get("/api/auth/me").status_code, 200)
        self.assertEqual(client.post("/api/auth/logout").status_code, 204)
        self.assertEqual(client.get("/api/auth/me").status_code, 401)

    # --- Mỗi người chỉ thấy dữ liệu của mình -------------------------------
    def test_each_session_sees_its_own_curriculum(self):
        k67 = self._client(K67).get("/api/student/audit").json()
        k68 = self._client(K68).get("/api/student/audit").json()
        self.assertEqual(k67["total_credits_required"], 126)
        self.assertEqual(k68["total_credits_required"], 132)

    def test_chat_answers_for_logged_in_student_and_ignores_spoofed_header(self):
        client = self._client(K68)
        response = client.post(
            "/api/chat", json={"message": "Tiến độ học tập của em thế nào?"}, headers={"X-Student-ID": K67}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("Phạm Quang Huy", response.json()["reply"])

    def test_conversations_are_private_even_with_spoofed_header(self):
        owner = self._client(K67)
        conversation_id = owner.post("/api/chat", json={"message": "chào bạn"}).json()["conversation_id"]

        other = self._client(K68)
        self.assertEqual(other.get(f"/api/conversations/{conversation_id}").status_code, 404)
        self.assertEqual(
            other.get(f"/api/conversations/{conversation_id}", headers={"X-Student-ID": K67}).status_code, 404
        )
        self.assertEqual(other.get("/api/conversations").json()["conversations"], [])
        self.assertEqual(other.delete(f"/api/conversations/{conversation_id}").status_code, 404)
        self.assertEqual(owner.get(f"/api/conversations/{conversation_id}").status_code, 200)

    def test_transcript_import_only_touches_own_profile(self):
        before_other = self.profiles.get(K68)
        client = self._client(K67)
        response = client.post(
            "/api/student/import",
            json={"raw_text": "ET3220 Điện tử số 3 A", "student_id": K68, "student_name": "Kẻ giả mạo"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        mine = self.profiles.get(K67)
        self.assertEqual([item["code"] for item in mine["transcript"]], ["ET3220"])
        self.assertEqual(mine["info"]["student_name"], "Mai Duy Hiếu")
        self.assertEqual(self.profiles.get(K68), before_other)
        self.assertEqual(response.json()["audit"]["student_info"]["student_id"], K67)

    def test_profile_update_only_touches_own_profile(self):
        client = self._client(K68)
        response = client.post("/api/student/profile/update", json={"student_name": "Huy Phạm"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.profiles.get(K68)["info"]["student_name"], "Huy Phạm")
        self.assertEqual(self.profiles.get(K67)["info"]["student_name"], "Mai Duy Hiếu")

    # --- Endpoint đã bỏ / quản trị / CSRF -----------------------------------
    def test_global_profile_switching_endpoints_are_gone(self):
        client = self._client(K67)
        self.assertIn(client.get("/api/student/profiles").status_code, (404, 405))
        self.assertIn(client.post("/api/student/switch", json={"student_id": K68}).status_code, (404, 405))

    def test_admin_endpoints_reject_regular_students(self):
        client = self._client(K67)
        self.assertEqual(client.post("/api/rag/sync").status_code, 403)
        self.assertEqual(client.post("/api/rag/config/api-key", json={"api_key": "x"}).status_code, 403)

    def test_cross_site_write_with_session_cookie_is_blocked(self):
        client = self._client(K67)
        response = client.post(
            "/api/chat", json={"message": "chào"}, headers={"Origin": "https://evil.example"}
        )
        self.assertEqual(response.status_code, 403)

    def test_login_from_foreign_origin_is_blocked(self):
        response = self._client().post(
            "/api/auth/login",
            json={"student_id": K67, "password": PASSWORD},
            headers={"Origin": "https://evil.example"},
        )
        self.assertEqual(response.status_code, 403)

    def test_overlong_chat_message_is_rejected(self):
        client = self._client(K67)
        self.assertEqual(client.post("/api/chat", json={"message": "x" * 5000}).status_code, 422)

    def test_change_password_logs_out_everywhere(self):
        client = self._client(K67)
        other_device = self._client(K67)
        response = client.post(
            "/api/auth/password", json={"current_password": PASSWORD, "new_password": "mat-khau-moi-2026"}
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(other_device.get("/api/auth/me").status_code, 401)
        login = self._client().post("/api/auth/login", json={"student_id": K67, "password": "mat-khau-moi-2026"})
        self.assertEqual(login.status_code, 200)


class RegisterApiTests(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        self.profiles = FileProfileRepository(root / "students")
        service = AuthService(SqliteAuthStore(root / "auth.sqlite3"), self.profiles)
        for patcher in (
            mock.patch.object(data_loader, "_profiles", self.profiles),
            mock.patch.object(runtime, "auth_service", service),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(app)
        self.payload = {
            "student_id": "20239999",
            "password": PASSWORD,
            "student_name": "Nguyễn Văn An",
            "class_name": "Điện tử 03 - K68",
            "program_code": "ET1",
        }

    def test_register_logs_in_and_new_student_has_empty_audit(self):
        response = self.client.post("/api/auth/register", json=self.payload)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["curriculum_version"], "2023")

        audit = self.client.get("/api/student/audit").json()
        self.assertEqual(audit["total_credits_required"], 132)
        self.assertEqual(audit["total_credits_accumulated"], 0)

    def test_register_errors(self):
        self.assertEqual(self.client.post("/api/auth/register", json=self.payload).status_code, 201)
        self.assertEqual(TestClient(app).post("/api/auth/register", json=self.payload).status_code, 409)
        cases = (
            {"student_id": "20238888", "program_code": "IT1"},
            {"student_id": "20238888", "password": "ngan"},
            {"student_id": "12"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                response = TestClient(app).post("/api/auth/register", json={**self.payload, **overrides})
                self.assertEqual(response.status_code, 422)

    def test_register_rejects_unknown_fields(self):
        response = self.client.post("/api/auth/register", json={**self.payload, "is_admin": True})
        self.assertEqual(response.status_code, 422)


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


if __name__ == "__main__":
    unittest.main()
