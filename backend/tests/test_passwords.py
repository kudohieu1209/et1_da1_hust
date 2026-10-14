import unittest

from app.auth.passwords import (
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    PasswordPolicyError,
    hash_password,
    validate_password,
    verify_password,
)


class PasswordHashingTests(unittest.TestCase):
    def test_correct_password_verifies(self):
        stored = hash_password("mat-khau-du-dai")
        self.assertTrue(verify_password("mat-khau-du-dai", stored))

    def test_wrong_password_is_rejected(self):
        stored = hash_password("mat-khau-du-dai")
        self.assertFalse(verify_password("mat-khau-sai", stored))

    def test_same_password_gets_different_salted_hashes(self):
        self.assertNotEqual(hash_password("trung-nhau-123"), hash_password("trung-nhau-123"))

    def test_hash_never_contains_plaintext(self):
        self.assertNotIn("bi-mat-12345", hash_password("bi-mat-12345"))

    def test_malformed_stored_hash_fails_closed(self):
        for stored in ("", "plain", "scrypt$1$2$3$x$y", "bcrypt$abc", None):
            with self.subTest(stored=stored):
                self.assertFalse(verify_password("anything", stored))

    def test_vietnamese_password_round_trips(self):
        stored = hash_password("Mật khẩu có dấu 2026")
        self.assertTrue(verify_password("Mật khẩu có dấu 2026", stored))


class PasswordPolicyTests(unittest.TestCase):
    def test_rejects_short_and_overlong_passwords(self):
        with self.assertRaises(PasswordPolicyError):
            validate_password("x" * (MIN_PASSWORD_LENGTH - 1))
        with self.assertRaises(PasswordPolicyError):
            validate_password("x" * (MAX_PASSWORD_LENGTH + 1))

    def test_rejects_whitespace_only_password(self):
        with self.assertRaises(PasswordPolicyError):
            validate_password(" " * 12)

    def test_accepts_reasonable_password(self):
        validate_password("hust-advisor-2026", student_id="20220001")

    def test_rejects_common_and_identity_based_passwords(self):
        for weak in ("12345678", "password1", "matkhau123", "abc20220001"):
            with self.subTest(password=weak):
                with self.assertRaises(PasswordPolicyError):
                    validate_password(weak, student_id="20220001")


if __name__ == "__main__":
    unittest.main()
