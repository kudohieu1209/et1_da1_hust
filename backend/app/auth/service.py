"""Đăng ký, đăng nhập, phiên và đổi mật khẩu.

Lớp này không biết gì về HTTP: router chuyển các ngoại lệ ở đây thành mã
trạng thái (401/409/422/429). Thời gian lấy qua ``clock`` để kiểm thử được.
"""
import hashlib
import re
import secrets
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Callable, Deque, Dict, Optional

from app.auth.passwords import DUMMY_HASH, hash_password, validate_password, verify_password
from app.auth.store import UserExistsError
from app.services.curriculum_repository import curriculum_repository

SESSION_TTL = timedelta(days=7)
LOCK_DURATION = timedelta(minutes=15)
# Đoán sai 5 lần từ MỘT IP: chỉ IP đó bị chặn với MSSV đó. Nhờ vậy kẻ xấu
# không thể cố tình nhập sai để khóa tài khoản của người khác.
PER_IP_FAILURE_LIMIT = 5
# Khóa cả tài khoản chỉ khi bị đoán sai dồn dập từ nhiều IP (tấn công phân tán).
MAX_FAILED_ATTEMPTS = 20
# Chặn dò mật khẩu hàng loạt từ một IP (nhiều MSSV khác nhau).
IP_WINDOW = timedelta(minutes=5)
IP_MAX_ATTEMPTS = 20
# Đăng ký và đổi mật khẩu đều chạy scrypt (~16MB/lần) nên cũng phải giới hạn.
REGISTER_WINDOW = timedelta(hours=1)
REGISTER_MAX_PER_IP = 10
PASSWORD_CHANGE_FAILURE_LIMIT = 5

# Chỉ chữ số ASCII: "\d" của Python còn khớp chữ số Ả Rập trông giống hệt.
STUDENT_ID_PATTERN = re.compile(r"[0-9]{8}")
PROGRAM_CODE_PATTERN = re.compile(r"[A-Z0-9-]{2,12}")
MAX_NAME_LENGTH = 80
MAX_CLASS_LENGTH = 60


class AuthError(Exception):
    """Lỗi nghiệp vụ đăng nhập/đăng ký; thông điệp hiển thị được cho người dùng."""


class RegistrationError(AuthError):
    pass


class ProfileExistsError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class AccountLockedError(AuthError):
    def __init__(self, retry_after_seconds: int):
        super().__init__(f"Tài khoản tạm khóa do đăng nhập sai nhiều lần. Thử lại sau {retry_after_seconds // 60 + 1} phút.")
        self.retry_after_seconds = retry_after_seconds


class TooManyAttemptsError(AuthError):
    def __init__(self, retry_after_seconds: int):
        super().__init__("Quá nhiều yêu cầu từ thiết bị này. Vui lòng thử lại sau ít phút.")
        self.retry_after_seconds = retry_after_seconds


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SlidingWindowLimiter:
    def __init__(self, window: timedelta, max_events: int):
        self.window = window
        self.max_events = max_events
        self._events: Dict[str, Deque[datetime]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: datetime) -> Deque[datetime]:
        events = self._events.get(key)
        if events is None:
            return deque()
        while events and now - events[0] > self.window:
            events.popleft()
        if not events:
            del self._events[key]  # không giữ khóa rỗng mãi trong bộ nhớ
        return events

    def retry_after(self, key: str, now: datetime) -> Optional[int]:
        """Số giây phải chờ nếu đã chạm hạn mức, ngược lại None (không ghi nhận)."""
        with self._lock:
            events = self._prune(key, now)
            if len(events) >= self.max_events:
                return int((events[0] + self.window - now).total_seconds()) + 1
            return None

    def record(self, key: str, now: datetime) -> None:
        with self._lock:
            self._events[key].append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def hit(self, key: str, now: datetime) -> Optional[int]:
        """Ghi nhận một lần thử; trả về số giây phải chờ nếu đã vượt hạn mức."""
        wait = self.retry_after(key, now)
        if wait is None:
            self.record(key, now)
        return wait


class AuthService:
    def __init__(self, store, profiles, clock: Callable[[], datetime] = _utcnow):
        self.store = store
        self.profiles = profiles
        self.clock = clock
        self._ip_limiter = SlidingWindowLimiter(IP_WINDOW, IP_MAX_ATTEMPTS)
        self._pair_failures = SlidingWindowLimiter(LOCK_DURATION, PER_IP_FAILURE_LIMIT)
        self._register_limiter = SlidingWindowLimiter(REGISTER_WINDOW, REGISTER_MAX_PER_IP)
        self._password_change_failures = SlidingWindowLimiter(LOCK_DURATION, PASSWORD_CHANGE_FAILURE_LIMIT)

    # --- Phiên ---------------------------------------------------------
    def _start_session(self, student_id: str) -> str:
        token = secrets.token_urlsafe(32)
        now = self.clock()
        self.store.create_session(hash_token(token), student_id, now, now + SESSION_TTL)
        return token

    def resolve_session(self, token: Optional[str]) -> Optional[str]:
        if not token:
            return None
        token_hash = hash_token(token)
        session = self.store.get_session(token_hash)
        if session is None:
            return None
        if session["expires_at"] <= self.clock():
            self.store.delete_session(token_hash)
            return None
        return session["student_id"]

    def logout(self, token: Optional[str]) -> None:
        if token:
            self.store.delete_session(hash_token(token))

    # --- Đăng ký -------------------------------------------------------
    @staticmethod
    def _clean(value: str, field: str, max_length: int) -> str:
        cleaned = " ".join(str(value or "").split())
        if not cleaned:
            raise RegistrationError(f"Vui lòng nhập {field}.")
        if len(cleaned) > max_length:
            raise RegistrationError(f"{field.capitalize()} tối đa {max_length} ký tự.")
        return cleaned

    def register(
        self,
        student_id: str,
        password: str,
        student_name: str,
        class_name: str,
        program_code: str,
        client_ip: str = "unknown",
    ) -> str:
        wait = self._register_limiter.hit(client_ip or "unknown", self.clock())
        if wait is not None:
            raise TooManyAttemptsError(wait)
        student_id = str(student_id or "").strip()
        if not STUDENT_ID_PATTERN.fullmatch(student_id):
            raise RegistrationError("MSSV gồm đúng 8 chữ số.")
        validate_password(password, student_id)
        name = self._clean(student_name, "họ tên", MAX_NAME_LENGTH)
        class_label = self._clean(class_name, "lớp", MAX_CLASS_LENGTH)
        program = str(program_code or "").strip().upper()
        if not PROGRAM_CODE_PATTERN.fullmatch(program):
            raise RegistrationError("Mã chương trình đào tạo không hợp lệ.")
        if not re.search(r"\bK\d{2}\b", class_label, re.IGNORECASE):
            raise RegistrationError("Tên lớp cần có khóa, ví dụ: Điện tử 03 - K68.")

        if self.store.get_user(student_id) is not None:
            raise UserExistsError(student_id)
        if self.profiles.find_key(student_id) is not None:
            # Hồ sơ có sẵn (vd. dữ liệu demo) không được để người khác "nhận".
            raise ProfileExistsError("MSSV này đã có hồ sơ trong hệ thống. Liên hệ quản trị để được cấp tài khoản.")

        profile = {
            "info": {
                "student_id": student_id,
                "student_name": name,
                "class_name": class_label,
                "program_code": program,
                "badge": "Tài khoản sinh viên",
            },
            "transcript": [],
            "passed_courses": [],
            "failed_courses": [],
            "total_courses_completed": 0,
        }
        # Ném CurriculumNotFoundError trước khi ghi gì, nếu CTĐT chưa được hỗ trợ.
        curriculum = curriculum_repository.resolve_profile(profile)
        program_info = curriculum["program"]
        profile["info"].update(
            program_id=program_info.get("program_id", program),
            program_name=program_info.get("name", ""),
            curriculum_version=str(program_info["curriculum_version"]),
        )

        self.store.create_user({"student_id": student_id, "password_hash": hash_password(password), "created_at": self.clock()})
        try:
            self.profiles.save(student_id, profile)
        except Exception:
            # Không để lại tài khoản thiếu hồ sơ (đăng nhập được nhưng không dùng được).
            self.store.delete_user(student_id)
            raise
        return self._start_session(student_id)

    # --- Đăng nhập -----------------------------------------------------
    def login(self, student_id: str, password: str, client_ip: str) -> str:
        now = self.clock()
        wait = self._ip_limiter.hit(client_ip or "unknown", now)
        if wait is not None:
            raise TooManyAttemptsError(wait)

        student_id = str(student_id or "").strip()
        user = self.store.get_user(student_id) if STUDENT_ID_PATTERN.fullmatch(student_id) else None
        if user is None:
            verify_password(password or "", DUMMY_HASH)  # cân bằng thời gian phản hồi
            raise InvalidCredentialsError("MSSV hoặc mật khẩu không đúng.")

        pair_key = f"{student_id}|{client_ip or 'unknown'}"
        wait = self._pair_failures.retry_after(pair_key, now)
        if wait is not None:
            raise TooManyAttemptsError(wait)

        locked_until = user["locked_until"]
        if locked_until and locked_until > now:
            raise AccountLockedError(int((locked_until - now).total_seconds()))

        if not verify_password(password or "", user["password_hash"]):
            self._pair_failures.record(pair_key, now)
            self.store.record_failed_login(student_id, now, MAX_FAILED_ATTEMPTS, LOCK_DURATION)
            raise InvalidCredentialsError("MSSV hoặc mật khẩu không đúng.")

        self._pair_failures.reset(pair_key)
        self.store.record_successful_login(student_id, now)
        return self._start_session(student_id)

    def change_password(self, student_id: str, current_password: str, new_password: str) -> None:
        now = self.clock()
        # Phiên bị đánh cắp không được dùng để dò mật khẩu hiện tại không giới hạn.
        wait = self._password_change_failures.retry_after(student_id, now)
        if wait is not None:
            raise TooManyAttemptsError(wait)
        user = self.store.get_user(student_id)
        if user is None or not verify_password(current_password or "", user["password_hash"]):
            self._password_change_failures.record(student_id, now)
            raise InvalidCredentialsError("Mật khẩu hiện tại không đúng.")
        validate_password(new_password, student_id)
        self._password_change_failures.reset(student_id)
        self.store.set_password(student_id, hash_password(new_password))
        # Đổi mật khẩu thì đăng xuất mọi thiết bị đang đăng nhập.
        self.store.delete_sessions_for(student_id)

    def get_user(self, student_id: str):
        return self.store.get_user(student_id)
