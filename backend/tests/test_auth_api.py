"""Đăng nhập end-to-end qua HTTP: cookie phiên, phân quyền và cô lập dữ liệu.

Chạy trên hồ sơ tổng hợp và MongoDB trong bộ nhớ, không ghi vào dữ liệu thật.
"""
import json
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from app.api import router_chat, router_conversations, router_student
from app.auth import runtime
from app.auth.passwords import hash_password
from app.auth.service import PER_IP_FAILURE_LIMIT, AuthService
from app.auth.store import MongoAuthStore
from app.core.config import SESSION_COOKIE_NAME
from app.main import app
from app.services.conversation_service import MongoConversationService
from app.services.data_loader import data_loader
from app.services.profile_repository import MongoProfileRepository
from app.services.student_memory import StudentMemoryRepository
from testing_support import isolated_database, sample_profiles

K67 = "20220001"  # Sinh viên demo K67, ET1-2022
K68 = "20231890"  # Sinh viên demo K68, ET1-2023
PASSWORD = "mat-khau-demo-2026"


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        database = isolated_database()
        self.profiles = MongoProfileRepository(database)
        for key in (K67, K68):
            self.profiles.save(key, sample_profiles()[key])
        self.store = MongoAuthStore(database)
        for key in (K67, K68):
            self.store.create_user({"student_id": key, "password_hash": hash_password(PASSWORD), "created_at": _now()})
        conversations = MongoConversationService(database)
        memory = StudentMemoryRepository(database)

        for patcher in (
            mock.patch.object(data_loader, "_profiles", self.profiles),
            mock.patch.object(runtime, "auth_service", AuthService(self.store, self.profiles)),
            mock.patch.object(router_chat, "conversation_service", conversations),
            mock.patch.object(router_conversations, "conversation_service", conversations),
            mock.patch.object(router_chat, "student_memory", memory),
            mock.patch.object(router_student, "student_memory", memory),
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
    def test_followup_uses_stored_course_after_reload_and_small_talk(self):
        client = self._client(K67)
        first = client.post("/api/chat", json={"message": "Điều kiện ET3300?"}).json()
        conversation_id = first["conversation_id"]
        client.post("/api/chat", json={"message": "cảm ơn", "conversation_id": conversation_id})
        response = client.post("/api/chat", json={"message": "Nếu trượt thì sao?", "conversation_id": conversation_id})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["intent"], "IMPACT_SIMULATION")
        self.assertEqual(response.json()["data_context"]["failed_course_code"], "ET3300")

    def test_client_history_cannot_seed_new_or_empty_conversation(self):
        client = self._client(K67)
        empty = client.post("/api/conversations", json={}).json()["id"]
        for conversation_id in (None, empty):
            response = client.post("/api/chat", json={
                "message": "Môn đó cần gì?", "conversation_id": conversation_id,
                "history": [{"role": "user", "content": "ET3300?"}],
            })
            self.assertEqual(response.json()["intent"], "CONTEXT_CLARIFICATION")

    def test_memory_is_private_editable_deletable_and_used_in_new_chats(self):
        owner, other = self._client(K67), self._client(K68)
        payload = {"enabled": True, "target_track": "MOD6", "max_credits": 9, "target_cpa": 3.2}
        saved = owner.put("/api/student/memory", json=payload)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertFalse(other.get("/api/student/memory").json()["enabled"])
        response = owner.post("/api/chat", json={"message": "Gợi ý môn kỳ tới"}).json()
        self.assertEqual(response["data_context"]["target_track"], "MOD6")
        self.assertLessEqual(response["data_context"]["total_credits_suggested"], 9)
        self.assertEqual(response["data_context"]["memory_used"]["target_cpa"], 3.2)
        self.assertEqual(owner.delete("/api/student/memory").status_code, 204)
        after = owner.post("/api/chat", json={"message": "Gợi ý môn kỳ tới"}).json()
        self.assertNotIn("memory_used", after["data_context"])
        self.assertIsNone(after["data_context"]["target_track"])

    def test_memory_rejects_identity_grades_and_track_from_other_curriculum(self):
        client = self._client(K68)
        for payload in ({"student_id": K67}, {"cpa": 4}, {"target_track": "MOD6"}, {"max_credits": 31}, {"max_credits": 2.5}):
            with self.subTest(payload=payload):
                self.assertEqual(client.put("/api/student/memory", json=payload).status_code, 422)
        self.assertEqual(TestClient(app).get("/api/student/memory").status_code, 401)

    def test_explicit_chat_preferences_override_saved_defaults(self):
        client = self._client(K67)
        client.put("/api/student/memory", json={"enabled": True, "target_track": "MOD6", "max_credits": 20})
        response = client.post("/api/chat", json={"message": "Gợi ý hướng Nhúng kỳ tới tối đa 6 tín chỉ"}).json()
        self.assertEqual(response["intent"], "COURSE_RECOMMENDATION")
        self.assertEqual(response["data_context"]["target_track"], "MOD1")
        self.assertLessEqual(response["data_context"]["total_credits_suggested"], 6)
        self.assertNotIn("memory_used", response["data_context"])

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
        self.assertIn("Sinh viên demo K68", response.json()["reply"])

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
        self.assertEqual(mine["info"]["student_name"], "Sinh viên demo K67")
        self.assertEqual(self.profiles.get(K68), before_other)
        self.assertEqual(response.json()["audit"]["student_info"]["student_id"], K67)

    def test_profile_update_only_touches_own_profile(self):
        client = self._client(K68)
        response = client.post("/api/student/profile/update", json={"student_name": "Huy Phạm"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.profiles.get(K68)["info"]["student_name"], "Huy Phạm")
        self.assertEqual(self.profiles.get(K67)["info"]["student_name"], "Sinh viên demo K67")

    def test_unknown_course_requires_credit_confirmation_without_partial_save(self):
        client = self._client(K67)
        before = self.profiles.get(K67)
        payload = {"raw_text": "ET3220 Điện tử số 3 A\nZZ9999 Học phần ngoài danh mục 4 B"}
        response = client.post("/api/student/import", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "needs_confirmation")
        self.assertEqual(response.json()["unresolved_courses"][0]["code"], "ZZ9999")
        self.assertEqual(self.profiles.get(K67), before)
        response = client.post("/api/student/import", json={**payload, "course_credit_overrides": {"ZZ9999": 4}})
        self.assertEqual(response.json()["status"], "success")
        self.assertAlmostEqual(response.json()["audit"]["cpa"], 3.43, places=2)
        self.assertEqual(self.profiles.get(K68)["info"]["student_id"], K68)

    def test_invalid_credits_are_rejected_without_changing_profile(self):
        client = self._client(K67)
        before = self.profiles.get(K67)
        response = client.post("/api/student/import", json={
            "raw_text": "ZZ9999 Học phần lạ B", "course_credit_overrides": {"ZZ9999": -1},
        })
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.profiles.get(K67), before)

    def test_declared_requirements_and_warning_can_be_updated_and_cleared(self):
        client = self._client(K67)
        response = client.post("/api/student/import", json={
            "raw_text": "ET3220 Điện tử số A", "warning_level": 2,
            "non_credit_status": {"220": "completed", "230": "incomplete", "240": "unverified"},
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["audit"]["warning_level"], 2)
        response = client.post("/api/student/import", json={"raw_text": "ET3220 Điện tử số A", "warning_level": None})
        self.assertIsNone(response.json()["audit"]["warning_level"])

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
        database = isolated_database()
        self.profiles = MongoProfileRepository(database)
        service = AuthService(MongoAuthStore(database), self.profiles)
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

    def test_registration_rate_limit_is_per_ip_and_returns_retry_after(self):
        first = TestClient(app, client=("192.0.2.1", 50000))
        second = TestClient(app, client=("192.0.2.2", 50000))
        invalid = {**self.payload, "student_id": "invalid"}
        for _ in range(10):
            self.assertEqual(first.post("/api/auth/register", json=invalid).status_code, 422)
        blocked = first.post("/api/auth/register", json=invalid, headers={"X-Forwarded-For": "192.0.2.99"})
        self.assertEqual(blocked.status_code, 429)
        self.assertGreater(int(blocked.headers["Retry-After"]), 0)
        self.assertEqual(second.post("/api/auth/register", json=invalid).status_code, 422)


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


if __name__ == "__main__":
    unittest.main()
