import itertools
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.auth.passwords import PasswordPolicyError
from app.auth.service import (
    AccountLockedError,
    AuthService,
    InvalidCredentialsError,
    LOCK_DURATION,
    MAX_FAILED_ATTEMPTS,
    PER_IP_FAILURE_LIMIT,
    ProfileExistsError,
    RegistrationError,
    TooManyAttemptsError,
)
from app.auth.store import SqliteAuthStore, UserExistsError
from app.services.curriculum_repository import CurriculumNotFoundError
from app.services.profile_repository import FileProfileRepository

PASSWORD = "mat-khau-2026"


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 10, 15, 8, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, delta):
        self.now += delta


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        self.store = SqliteAuthStore(root / "auth.sqlite3")
        self.profiles = FileProfileRepository(root / "students")
        self.clock = FakeClock()
        self.service = AuthService(self.store, self.profiles, clock=self.clock)
        # Mỗi lần đăng ký một IP riêng, để giới hạn đăng ký theo IP không
        # ảnh hưởng các test khác (giới hạn đó có test riêng).
        self._ips = itertools.count()

    def _register(self, student_id="20239999", **overrides):
        payload = {
            "student_id": student_id,
            "password": PASSWORD,
            "student_name": "Nguyễn Văn An",
            "class_name": "Điện tử 03 - K68",
            "program_code": "ET1",
            "client_ip": f"192.0.2.{next(self._ips)}",
            **overrides,
        }
        return self.service.register(**payload)

    # --- Đăng ký ---------------------------------------------------------
    def test_register_creates_hashed_account_profile_and_session(self):
        token = self._register()

        user = self.store.get_user("20239999")
        self.assertNotIn(PASSWORD, user["password_hash"])
        profile = self.profiles.get("20239999")
        self.assertEqual(profile["info"]["student_name"], "Nguyễn Văn An")
        self.assertEqual(profile["info"]["curriculum_version"], "2023")
        self.assertEqual(profile["transcript"], [])
        self.assertEqual(self.service.resolve_session(token), "20239999")

    def test_register_rejects_existing_account(self):
        self._register()
        with self.assertRaises(UserExistsError):
            self._register()

    def test_register_cannot_claim_existing_profile_without_account(self):
        self.profiles.save("20220001", {"info": {"student_id": "20220001"}, "transcript": []})
        with self.assertRaises(ProfileExistsError):
            self._register(student_id="20220001")
        self.assertIsNone(self.store.get_user("20220001"))

    def test_register_rejects_unsupported_curriculum_without_side_effects(self):
        with self.assertRaises(CurriculumNotFoundError):
            self._register(program_code="IT1")
        self.assertIsNone(self.store.get_user("20239999"))
        self.assertIsNone(self.profiles.get("20239999"))

    def test_register_validates_input(self):
        cases = {
            "student_id": ("2023", "abcdefgh", "../x", "٢٠٢٣٩٩٩٩"),
            "student_name": ("", "   "),
            "class_name": ("Điện tử 03",),
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(RegistrationError):
                        self._register(**{field: value})
        for weak in ("ngan", "12345678", "sv20239999!", "password123"):
            with self.subTest(password=weak):
                with self.assertRaises(PasswordPolicyError):
                    self._register(password=weak)

    def test_register_rolls_back_account_when_profile_cannot_be_saved(self):
        from unittest import mock

        with mock.patch.object(self.profiles, "save", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self._register()
        self.assertIsNone(self.store.get_user("20239999"))
        self._register()  # thử lại được sau khi lỗi

    def test_registration_is_rate_limited_per_ip(self):
        with self.assertRaises(TooManyAttemptsError):
            for index in range(50):
                self._register(student_id=f"2023{index:04d}", client_ip="7.7.7.7")

    # --- Đăng nhập -------------------------------------------------------
    def test_login_with_correct_password_creates_session(self):
        self._register()
        token = self.service.login("20239999", PASSWORD, client_ip="1.1.1.1")
        self.assertEqual(self.service.resolve_session(token), "20239999")

    def test_wrong_password_and_unknown_student_give_same_error(self):
        self._register()
        with self.assertRaises(InvalidCredentialsError):
            self.service.login("20239999", "sai-mat-khau", client_ip="1.1.1.1")
        with self.assertRaises(InvalidCredentialsError):
            self.service.login("20000000", PASSWORD, client_ip="1.1.1.1")

    def test_targeted_guessing_only_blocks_the_guessing_ip(self):
        self._register()
        for _ in range(PER_IP_FAILURE_LIMIT):
            with self.assertRaises(InvalidCredentialsError):
                self.service.login("20239999", "sai-mat-khau", client_ip="6.6.6.6")
        with self.assertRaises(TooManyAttemptsError):
            self.service.login("20239999", PASSWORD, client_ip="6.6.6.6")
        # Chủ tài khoản ở IP khác không bị khóa lây (chống khóa tài khoản người khác).
        self.assertTrue(self.service.login("20239999", PASSWORD, client_ip="1.1.1.1"))

    def test_account_locks_after_distributed_failures_then_unlocks(self):
        self._register()
        for index in range(MAX_FAILED_ATTEMPTS):
            with self.assertRaises(InvalidCredentialsError):
                self.service.login("20239999", "sai-mat-khau", client_ip=f"10.0.0.{index}")

        with self.assertRaises(AccountLockedError):
            self.service.login("20239999", PASSWORD, client_ip="1.1.1.1")

        self.clock.advance(LOCK_DURATION + timedelta(seconds=1))
        token = self.service.login("20239999", PASSWORD, client_ip="1.1.1.1")
        self.assertEqual(self.service.resolve_session(token), "20239999")

    def test_ip_rate_limit_blocks_password_spraying(self):
        self._register()
        with self.assertRaises(TooManyAttemptsError):
            for index in range(100):
                try:
                    self.service.login(f"2000{index:04d}", "sai-mat-khau", client_ip="9.9.9.9")
                except InvalidCredentialsError:
                    pass
        # IP khác không bị ảnh hưởng.
        self.assertTrue(self.service.login("20239999", PASSWORD, client_ip="1.1.1.1"))

    # --- Phiên -----------------------------------------------------------
    def test_logout_invalidates_session(self):
        token = self._register()
        self.service.logout(token)
        self.assertIsNone(self.service.resolve_session(token))

    def test_expired_session_is_rejected(self):
        token = self._register()
        self.clock.advance(timedelta(days=8))
        self.assertIsNone(self.service.resolve_session(token))

    def test_unknown_or_empty_token_resolves_to_none(self):
        for token in (None, "", "khong-ton-tai"):
            with self.subTest(token=token):
                self.assertIsNone(self.service.resolve_session(token))

    def test_session_store_never_contains_raw_token(self):
        token = self._register()
        self.assertIsNone(self.store.get_session(token))

    def test_change_password_requires_current_and_revokes_other_sessions(self):
        first = self._register()
        second = self.service.login("20239999", PASSWORD, client_ip="1.1.1.1")
        with self.assertRaises(InvalidCredentialsError):
            self.service.change_password("20239999", "sai-mat-khau", "mat-khau-moi-2026")
        with self.assertRaises(PasswordPolicyError):
            self.service.change_password("20239999", PASSWORD, "20239999abc")

        self.service.change_password("20239999", PASSWORD, "mat-khau-moi-2026")
        self.assertIsNone(self.service.resolve_session(first))
        self.assertIsNone(self.service.resolve_session(second))
        self.assertTrue(self.service.login("20239999", "mat-khau-moi-2026", client_ip="1.1.1.1"))

    def test_guessing_current_password_is_rate_limited(self):
        self._register()
        with self.assertRaises(TooManyAttemptsError):
            for _ in range(20):
                try:
                    self.service.change_password("20239999", "doan-mo", "mat-khau-moi-2026")
                except InvalidCredentialsError:
                    pass


if __name__ == "__main__":
    unittest.main()
