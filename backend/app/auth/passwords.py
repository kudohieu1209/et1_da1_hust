"""Băm và kiểm tra mật khẩu bằng scrypt (thư viện chuẩn, không cần phụ thuộc).

Định dạng lưu: ``scrypt$<n>$<r>$<p>$<salt_b64>$<hash_b64>``. Tham số nằm trong
chuỗi nên có thể tăng độ khó sau này mà mật khẩu cũ vẫn kiểm tra được.
"""
import base64
import hashlib
import hmac
import secrets
from typing import Optional

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

# N=2^14, r=8, p=1: mức OWASP khuyến nghị tối thiểu cho scrypt (~16MB RAM/lần).
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
KEY_BYTES = 32
_MAX_MEMORY = 64 * 1024 * 1024
_SCHEME = "scrypt"


class PasswordPolicyError(ValueError):
    """Mật khẩu không đạt yêu cầu tối thiểu."""


# Mật khẩu hay bị đoán đầu tiên (kể cả biến thể tiếng Việt / tên trường).
COMMON_PASSWORDS = frozenset({
    "12345678", "123456789", "1234567890", "87654321", "11111111", "00000000",
    "password", "password1", "password123", "qwerty123", "qwertyuiop", "abcd1234",
    "iloveyou", "admin123", "matkhau", "matkhau1", "matkhau123", "bachkhoa",
    "bachkhoa123", "hust1234", "hust2026", "sinhvien", "sinhvien123",
})


def validate_password(password: str, student_id: Optional[str] = None) -> None:
    if not isinstance(password, str) or not password.strip():
        raise PasswordPolicyError("Mật khẩu không được để trống.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(f"Mật khẩu cần ít nhất {MIN_PASSWORD_LENGTH} ký tự.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordPolicyError(f"Mật khẩu tối đa {MAX_PASSWORD_LENGTH} ký tự.")
    if password.lower() in COMMON_PASSWORDS or len(set(password)) <= 2:
        raise PasswordPolicyError("Mật khẩu quá phổ biến, dễ bị đoán. Hãy chọn mật khẩu khác.")
    if student_id and student_id in password:
        raise PasswordPolicyError("Mật khẩu không được chứa MSSV.")


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=KEY_BYTES, maxmem=_MAX_MEMORY
    )


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"{_SCHEME}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    """So khớp thời gian hằng; chuỗi lưu hỏng/lạ luôn trả về False."""
    try:
        scheme, n, r, p, salt, digest = str(stored or "").split("$")
        if scheme != _SCHEME:
            return False
        expected = _unb64(digest)
        actual = _derive(password, _unb64(salt), int(n), int(r), int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# Dùng khi MSSV không tồn tại để thời gian phản hồi giống như sai mật khẩu,
# tránh dò MSSV nào đã đăng ký qua độ trễ.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))
