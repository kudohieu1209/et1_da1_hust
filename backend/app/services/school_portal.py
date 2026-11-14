"""Local, user-operated CTT sign-in. Credentials never pass through our API.

Each attempt owns a fresh browser context. Only fixed CTT URLs are read after
the user signs in; neither browser cookies nor raw HTML leave this module.
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
import secrets
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from app.core.config import CTT_BROWSER_CHANNEL, CTT_LOGIN_TIMEOUT_SECONDS
from app.core.hust_rules import GRADE_TO_SCALE4, PASSING_GRADES
from app.services.ctt_service import (
    CTT_BASE_URL, LOGIN_URL, STUDENT_GRADE_URL, STUDENT_MARKS_URL, ctt_parser,
)

logger = logging.getLogger(__name__)


class SchoolPortalError(ValueError):
    pass


def _fold(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).split()).strip(" :")


LABELS = {
    "ma so sinh vien": "student_id", "ma sinh vien": "student_id", "mssv": "student_id",
    "ho va ten": "student_name", "ho ten": "student_name", "ten sinh vien": "student_name",
    "lop sinh vien": "class_name", "lop quan ly": "class_name", "lop": "class_name",
    "lop hoc": "class_name",
    "email": "email", "email sinh vien": "email", "thu dien tu": "email",
}
ID_SUFFIXES = {
    "lblmssv": "student_id", "lbmssv": "student_id", "lblstudentid": "student_id",
    "lblstudentcode": "student_id", "lblmasinhvien": "student_id", "lbmasinhvien": "student_id",
    "lblhoten": "student_name", "lbhoten": "student_name", "lblfullname": "student_name",
    "lblstudentname": "student_name", "lbfullname": "student_name", "lbllop": "class_name",
    "lblclassname": "class_name", "lblclass": "class_name", "lblophoc": "class_name",
}


def parse_school_identity(html: str) -> dict:
    """Resolve profile labels without confusing grid headings with identity.

    IDs stay strict. Display fields compare Unicode-normalized, case-insensitive
    values; ambiguous optional fields do not invalidate an authenticated ID.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for table in soup.find_all("table", id=re.compile(r"(?:gvResults|gvCourseMarks|gvStudentProgram|gvClassGrade|gvTimetable).*DXMainTable", re.I)):
        table.decompose()
    candidates: dict[str, list[tuple[int, str]]] = {}
    stop_labels = set(LABELS) | {"gioi tinh", "ngay sinh", "khoa", "nganh", "khoa hoc", "diem", "stt", "so tin chi", "diem chu", "trang thai"}

    def add(label: str, value: str, priority: int):
        key = LABELS.get(_fold(label))
        value = unicodedata.normalize("NFC", " ".join(value.split()).strip(" :"))
        if not key or not value or len(value) > 160 or _fold(value) in stop_labels:
            return
        if key == "student_id" and not re.fullmatch(r"[0-9]{8}", value):
            return
        if key == "student_name" and (sum(c.isalpha() for c in value) < 3 or re.search(r"[0-9:@<>]", value)):
            return
        if key == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            return
        if key == "class_name" and not re.search(r"[0-9]", value):
            return
        candidates.setdefault(key, []).append((priority, value))

    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"], recursive=False)
        for index in range(len(cells) - 1):
            add(cells[index].get_text(" ", strip=True), cells[index + 1].get_text(" ", strip=True), 2)
    for tag in soup.find_all(id=True):
        suffix = tag["id"].split("_")[-1].lower()
        key = ID_SUFFIXES.get(suffix)
        if key:
            label = next(label for label, field_name in LABELS.items() if field_name == key)
            add(label, tag.get_text(" ", strip=True), 3)
    lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if ":" in line:
            label, value = line.split(":", 1)
            add(label, value or (lines[index + 1] if index + 1 < len(lines) else ""), 1)
        elif _fold(line) in LABELS and index + 1 < len(lines):
            add(line, lines[index + 1], 1)
    found = {}
    for key, values in candidates.items():
        if key == "student_id":
            selected = values  # Never conceal a genuinely different labeled MSSV.
        else:
            best_priority = max(priority for priority, _ in values)
            selected = [(priority, value) for priority, value in values if priority == best_priority]
        distinct = {value.casefold() for _, value in selected}
        if len(distinct) > 1:
            logger.warning("CTT profile label ambiguity: field=%s candidates=%d", key, len(distinct))
            if key == "student_id":
                raise SchoolPortalError("Các nhãn MSSV trên CTT không khớp. Chưa lưu dữ liệu để tránh gắn nhầm tài khoản.")
            if key == "student_name":
                raise SchoolPortalError("Chưa xác định được họ tên thống nhất từ hồ sơ CTT. Chưa lưu dữ liệu.")
            continue  # Email/class are optional; never choose an arbitrary value.
        found[key] = max(selected, key=lambda item: (not item[1].isupper(), len(item[1])))[1]
    return found


def authenticated_ctt_html(url: str, html: str, status: int = 200) -> bool:
    parsed = urlsplit(url)
    if status != 200 or parsed.scheme != "https" or parsed.netloc.lower() != "ctt-sis.hust.edu.vn":
        return False
    if re.search(r"/account/(?:login|logout)\.aspx", parsed.path, re.I):
        return False
    soup = BeautifulSoup(html, "html.parser")
    if soup.select_one('input[type="password"]'):
        return False
    # A real anchor, not a reference in a script or an error page.
    return any(
        urlsplit(urljoin(CTT_BASE_URL, a.get("href", ""))).netloc.lower() == "ctt-sis.hust.edu.vn"
        and re.search(r"/(?:account/)?logout\.aspx$", urlsplit(a.get("href", "")).path, re.I)
        for a in soup.find_all("a", href=True)
    )


@dataclass
class SchoolSnapshot:
    info: dict
    transcript: list[dict]
    semesters: list[dict]
    services: dict = field(default_factory=dict)


def build_school_snapshot(pages: list[tuple[str, str]], grade_html: str) -> SchoolSnapshot:
    info: dict = {}
    for url, html in pages:
        if not authenticated_ctt_html(url, html):
            raise SchoolPortalError("Phiên CTT chưa được xác thực hoặc đã hết hạn. Vui lòng đăng nhập lại.")
        parsed = parse_school_identity(html)
        if info.get("student_id") and parsed.get("student_id") not in (None, info["student_id"]):
            raise SchoolPortalError("MSSV giữa các trang CTT không khớp. Chưa lưu dữ liệu.")
        for key, value in parsed.items():
            info.setdefault(key, value)
    if not info.get("student_id") or not info.get("student_name"):
        raise SchoolPortalError("Chưa đọc được MSSV và họ tên từ CTT. Chưa tạo tài khoản hay lưu bảng điểm.")
    soup = BeautifulSoup(grade_html, "html.parser")
    # Refuse a partial transcript rather than replacing a complete saved one.
    page_numbers = {a.get_text(strip=True) for a in soup.select('[class*="dxp-num"], [class*="dxpPageNumber"]')}
    if len(page_numbers) > 1 or re.search(r"Page\s+\d+\s+of\s+[2-9]\d*", soup.get_text(" "), re.I):
        raise SchoolPortalError("CTT đang chia bảng điểm thành nhiều trang. Chưa thay bảng điểm; hãy dùng mục dán toàn bộ bảng điểm.")
    result = ctt_parser.parse_transcript_html(grade_html)
    transcript = []
    seen = set()
    for item in result["transcript"]:
        letter = item.get("letter_grade", "")
        if letter not in GRADE_TO_SCALE4:
            continue  # Unreleased grades are never guessed from an exam score.
        if item.get("credits") is None:
            raise SchoolPortalError("Không xác định được số tín chỉ của học phần từ CTT. Chưa lưu bảng điểm.")
        credits = float(item["credits"])
        if not math.isfinite(credits) or not 0 <= credits <= 30:
            raise SchoolPortalError("CTT trả về số tín chỉ không hợp lệ. Chưa lưu bảng điểm.")
        key = (item["code"], item.get("semester"), letter, item.get("midterm_grade"), item.get("final_grade"))
        if key in seen:
            continue
        seen.add(key)
        transcript.append({**item, "credits": credits, "numeric_grade": GRADE_TO_SCALE4[letter],
                           "is_passed": letter in PASSING_GRADES})
    if not transcript:
        raise SchoolPortalError("Chưa đọc được học phần có điểm chữ từ CTT. Bảng điểm hiện tại được giữ nguyên.")
    return SchoolSnapshot(info, transcript, result.get("semesters", []))


def _school_page_ready(page) -> bool:
    """Only inspect an authenticated CTT document, never Office 365 form data.

    Read the origin and marker together: a URL observed before navigation may
    refer to a different document by the time a locator is evaluated.
    """
    from playwright.sync_api import Error
    parsed = urlsplit(page.url)
    if (parsed.scheme != "https" or parsed.netloc.lower() != "ctt-sis.hust.edu.vn"
            or re.search(r"/account/(?:login|logout)\.aspx", parsed.path, re.I)):
        return False
    try:
        return page.evaluate("""() => {
            if (location.origin !== 'https://ctt-sis.hust.edu.vn'
                || /\\/account\\/(login|logout)\\.aspx/i.test(location.pathname)
                || document.querySelector('input[type="password"]')) return false;
            return Array.from(document.querySelectorAll('a[href]')).some(a => {
                const target = new URL(a.href, location.href);
                return target.origin === location.origin && /\\/(account\\/)?logout\\.aspx$/i.test(target.pathname);
            });
        }""") is True
    except Error:
        return False  # An OAuth redirect can destroy the previous document.


def _wait_for_browser_activity(context, browser, cancel: threading.Event):
    """Pump events on the context, which survives tabs being replaced by SSO."""
    from playwright.sync_api import Error, TimeoutError as BrowserTimeout
    try:
        context.wait_for_event("page", timeout=700)
    except BrowserTimeout:
        pass  # No new tab is normal while the user enters email/password/MFA.
    except Error:
        if not browser.is_connected():
            raise SchoolPortalError("Trình duyệt đăng nhập đã ngắt kết nối trước khi xác thực xong. Chưa lưu dữ liệu CTT.") from None
        # A closing context must not cause a busy loop; the caller also applies
        # a short grace period for an empty page list during a window handoff.
        cancel.wait(.1)


def _fetch_ctt_html(page, url: str) -> dict:
    """Read through the authenticated document, like iLoveBK's same-origin JS.

    No cookie export, separate HTTP client or password forwarding is involved.
    Both the requested origin and the returned origin remain validated.
    """
    target = urlsplit(url)
    if target.scheme != "https" or target.netloc.lower() != "ctt-sis.hust.edu.vn":
        raise SchoolPortalError("Không cho phép đọc dữ liệu ngoài cổng CTT.")
    result = page.evaluate("""async (url) => {
        const origin = 'https://ctt-sis.hust.edu.vn';
        if (location.origin !== origin || new URL(url).origin !== origin) return null;
        const response = await fetch(url, {
            credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(30000)
        });
        if (new URL(response.url).origin !== origin) return null;
        return {url: response.url, status: response.status, html: await response.text()};
    }""", url)
    if not isinstance(result, dict) or not authenticated_ctt_html(result.get("url", ""), result.get("html", ""), result.get("status", 0)):
        raise SchoolPortalError("Phiên CTT chưa được xác nhận hoặc đã hết hạn. Chưa đọc hay lưu bảng điểm.")
    return result


def _collect_school_services(page, identity_pages, cancel):
    from app.services.ctt_sections import PATHS, fold, parse_section
    synced_at = datetime.now(timezone.utc).isoformat()
    services = {}
    requirement_pages = [html for _, html in identity_pages]
    assessment_sources = [url for url, _ in identity_pages]
    exam_url = None
    assessment_urls = set()
    # Discover the student's real exam page; do not invent an API endpoint.
    for base, html in identity_pages:
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a", href=True):
            label = fold(link.get_text(" ", strip=True))
            target = urljoin(base, link["href"])
            parsed = urlsplit(target)
            safe = (parsed.scheme == "https" and parsed.netloc.lower() == "ctt-sis.hust.edu.vn"
                    and parsed.path.lower().endswith(".aspx") and not parsed.query
                    and (parsed.path.lower().startswith("/students/") or parsed.path.lower() == "/default.aspx"))
            if safe and any(x in label for x in ("thong tin sinh vien", "thong tin ca nhan", "ho so sinh vien", "thong tin hoc tap", "chung chi", "canh bao", "canh cao")):
                assessment_urls.add(target)
            if ("lich thi" in label and parsed.scheme == "https" and parsed.netloc.lower() == "ctt-sis.hust.edu.vn"
                    and parsed.path.lower().startswith("/students/") and parsed.path.lower().endswith(".aspx")):
                exam_url = target
    seen = {url for url, _ in identity_pages}
    for url in sorted(assessment_urls - seen)[:8]:
        if cancel.is_set():
            raise SchoolPortalError("Đã hủy kết nối CTT.")
        try:
            details = _fetch_ctt_html(page, url)
            if urlsplit(details['url']).path.lower() == urlsplit(url).path.lower():
                requirement_pages.append(details['html'])
                assessment_sources.append(details['url'])
        except Exception as exc:
            logger.warning("CTT assessment page failed: error_type=%s", type(exc).__name__)
    targets = {**PATHS, "exams": exam_url}
    for kind, path in targets.items():
        if cancel.is_set():
            raise SchoolPortalError("Đã hủy kết nối CTT.")
        if not path:
            services[kind] = {"status": "unavailable", "synced_at": synced_at, "source_url": "", "tables": [], "records": [],
                              "message": "Chưa thấy trang lịch thi trong tài khoản CTT. Có thể nhập PDF lịch thi do trường cung cấp."}
            continue
        url = urljoin(CTT_BASE_URL, path)
        try:
            result = _fetch_ctt_html(page, url)
            if urlsplit(result["url"]).path.lower() != urlsplit(url).path.lower():
                raise SchoolPortalError("CTT chuyển hướng khỏi trang dữ liệu được yêu cầu.")
            services[kind] = parse_section(kind, result["html"], result["url"], synced_at)
            if kind == "requirements":
                requirement_pages.append(result["html"])
                assessment_sources.append(result['url'])
        except Exception as exc:
            logger.warning("CTT service sync failed: section=%s error_type=%s", kind, type(exc).__name__)
            services[kind] = {"status": "error", "synced_at": synced_at, "source_url": url, "tables": [], "records": [],
                              "message": "Chưa đọc được mục này từ CTT. Dữ liệu lần đồng bộ trước được giữ lại nếu có."}
    assessment = parse_section("requirements", "\n".join(requirement_pages), CTT_BASE_URL + "/", synced_at)
    assessment["checked_pages"] = sorted(set(assessment_sources))
    services["warning"] = {**assessment, "status": "synced" if assessment["warning_level"] is not None else "unavailable"}
    services['warning']['message'] = '' if assessment['warning_level'] is not None else 'Chưa đọc được mức cảnh báo từ các trang CTT đã kiểm tra.'
    states = assessment["requirements"]
    services["certificates"] = {**assessment, "status": "synced" if all(x != "unverified" for x in states.values()) else "partial" if any(x != "unverified" for x in states.values()) else "unavailable"}
    services['certificates']['message'] = '' if all(x != 'unverified' for x in states.values()) else 'Chưa xác định được đầy đủ trạng thái chứng chỉ từ các trang CTT đã kiểm tra. Điểm học phần không thay thế trạng thái cấp chứng chỉ.'
    return services


def read_school_in_browser(cancel: threading.Event, notify: Callable[[str], None]) -> SchoolSnapshot:
    """The user performs all authentication, including CAPTCHA and Office 365."""
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError:
        raise SchoolPortalError("Máy chủ chưa cài Playwright. Xem hướng dẫn kết nối CTT trong README.") from None
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=False, channel=CTT_BROWSER_CHANNEL, timeout=15000)
        except Error:
            raise SchoolPortalError("Không mở được trình duyệt đăng nhập riêng. Chạy trong môi trường backend: python -m playwright install chromium.") from None
        phase = "opening"
        intentional_close = False
        def disconnected(*_):
            if not intentional_close:
                # Only lifecycle metadata; no URL, page contents or identity.
                logger.warning("CTT browser disconnected before cleanup: phase=%s", phase)
        browser.on("disconnected", disconnected)
        try:
            context = browser.new_context(locale="vi-VN", accept_downloads=False)
            page = context.new_page()
            page.goto(LOGIN_URL, wait_until="commit", timeout=45000)
            phase = "waiting"
            notify("waiting")
            deadline = time.monotonic() + CTT_LOGIN_TIMEOUT_SECONDS
            empty_since = None
            while not cancel.is_set() and time.monotonic() < deadline:
                if not browser.is_connected():
                    raise SchoolPortalError("Trình duyệt đăng nhập đã ngắt kết nối trước khi xác thực xong. Chưa lưu dữ liệu CTT.")
                pages_now = list(context.pages)
                if pages_now:
                    empty_since = None
                else:
                    empty_since = empty_since if empty_since is not None else time.monotonic()
                    if time.monotonic() - empty_since >= 5:
                        raise SchoolPortalError("Không còn cửa sổ đăng nhập đang mở. Bạn có thể kết nối lại.")
                signed_in_page = next((candidate for candidate in pages_now if _school_page_ready(candidate)), None)
                if signed_in_page is not None:
                    phase = "syncing"
                    notify("syncing")
                    pages = []
                    grade_html = None
                    # Same-origin fetch runs inside the signed-in CTT document,
                    # matching the session-check pattern recovered from iLoveBK.
                    for url in (CTT_BASE_URL + "/", STUDENT_GRADE_URL, STUDENT_MARKS_URL):
                        if cancel.is_set():
                            raise SchoolPortalError("Đã hủy kết nối CTT.")
                        try:
                            result = _fetch_ctt_html(signed_in_page, url)
                        except SchoolPortalError:
                            if url == CTT_BASE_URL + "/":
                                raise
                            continue
                        html = result["html"]
                        pages.append((result["url"], html))
                        if url == CTT_BASE_URL + "/" and not {"student_id", "student_name"} <= parse_school_identity(html).keys():
                            home = BeautifulSoup(html, "html.parser")
                            for link in home.find_all("a", href=True):
                                destination = urljoin(result["url"], link["href"])
                                target = urlsplit(destination)
                                label = _fold(link.get_text(" ", strip=True))
                                if (target.scheme != "https" or target.netloc.lower() != "ctt-sis.hust.edu.vn"
                                        or not target.path.lower().startswith("/students/") or not target.path.lower().endswith(".aspx")
                                        or label not in {"thong tin sinh vien", "thong tin ca nhan", "ho so sinh vien"}):
                                    continue
                                try:
                                    details = _fetch_ctt_html(signed_in_page, destination)
                                    pages.append((details["url"], details["html"]))
                                except SchoolPortalError:
                                    pass
                                break
                        if url != CTT_BASE_URL + "/" and any(c["letter_grade"] in GRADE_TO_SCALE4 for c in ctt_parser.parse_transcript_html(html)["transcript"]):
                            grade_html = html
                            break
                    if grade_html is None:
                        raise SchoolPortalError("Không lấy được bảng điểm từ CTT. Chưa lưu dữ liệu.")
                    snapshot = build_school_snapshot(pages, grade_html)
                    snapshot.services = _collect_school_services(signed_in_page, pages, cancel)
                    return snapshot
                _wait_for_browser_activity(context, browser, cancel)
            raise SchoolPortalError("Đã hủy kết nối CTT." if cancel.is_set() else "Hết thời gian chờ đăng nhập. Vui lòng thử lại.")
        except SchoolPortalError:
            raise
        except Error as exc:
            # Operational metadata only: no exception text, URLs, email, tokens
            # or form contents are recorded.
            logger.warning("CTT browser failure: phase=%s error_type=%s", phase, type(exc).__name__)
            if not browser.is_connected():
                raise SchoolPortalError("Trình duyệt đăng nhập đã ngắt kết nối trước khi xác thực xong. Chưa lưu dữ liệu CTT.") from None
            if phase == "opening":
                raise SchoolPortalError("Không mở được trang đăng nhập CTT. Kiểm tra kết nối và thử lại.") from None
            raise SchoolPortalError("Đã qua bước đăng nhập nhưng chưa đọc được dữ liệu CTT. Vui lòng thử kết nối lại.") from None
        finally:
            intentional_close = True
            try:
                browser.close()
            except Error:
                pass  # Closing an already closed window must not replace the result/error.


@dataclass
class _Attempt:
    owner: str
    program_code: str
    expected_student_id: str | None
    expires: float
    status: str = "opening"
    error: str = ""
    snapshot: SchoolSnapshot | None = None
    cancel: threading.Event = field(default_factory=threading.Event)


class SchoolLoginManager:
    """Bounded, one-time results bound to a separate HttpOnly browser cookie.

    This local connector runs in one backend process. No shared desktop or
    externally reachable browser-control endpoint is exposed.
    """
    def __init__(self, runner=read_school_in_browser, clock=time.monotonic):
        self.runner = runner
        self.clock = clock
        self._lock = threading.RLock()
        self._attempts: dict[str, _Attempt] = {}
        self._running = 0

    @staticmethod
    def _owner(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def _prune(self):
        for key, attempt in list(self._attempts.items()):
            if self.clock() >= attempt.expires:
                attempt.cancel.set()
                attempt.snapshot = None
                del self._attempts[key]

    def start(self, owner: str, program_code: str, expected_student_id: str | None,
              before_start: Callable[[], None] | None = None) -> str:
        with self._lock:
            self._prune()
            owner_hash = self._owner(owner)
            for existing_id, existing in list(self._attempts.items()):
                if existing.owner != owner_hash:
                    continue
                if existing.status == "error":
                    existing.cancel.set()
                    existing.snapshot = None
                    del self._attempts[existing_id]
                    continue
                if existing.program_code != program_code or existing.expected_student_id != expected_student_id:
                    raise SchoolPortalError("Đang có kết nối CTT cho lựa chọn trước. Hãy hủy kết nối đó trước khi đổi tài khoản hoặc chương trình.")
                # Reloads, lost responses and repeated clicks resume the same
                # owned browser. They neither launch a worker nor use quota.
                return existing_id
            if len(self._attempts) >= 2 or self._running >= 2:
                raise SchoolPortalError("Máy đang có phiên kết nối CTT khác. Vui lòng thử lại sau.")
            if before_start:
                before_start()
            attempt_id = secrets.token_urlsafe(32)
            attempt = _Attempt(owner_hash, program_code, expected_student_id,
                               self.clock() + CTT_LOGIN_TIMEOUT_SECONDS + 60)
            self._attempts[attempt_id] = attempt
            self._running += 1
            threading.Thread(target=self._run, args=(attempt_id, attempt), daemon=True,
                             name="ctt-school-login").start()
            return attempt_id

    def _run(self, attempt_id: str, attempt: _Attempt):
        def notify(status):
            with self._lock:
                if self._attempts.get(attempt_id) is attempt and not attempt.cancel.is_set():
                    attempt.status = status
                    if status == "syncing":
                        attempt.expires = max(attempt.expires, self.clock() + 600)
        try:
            snapshot = self.runner(attempt.cancel, notify)
            if attempt.expected_student_id and snapshot.info["student_id"] != attempt.expected_student_id:
                raise SchoolPortalError("Tài khoản CTT khác MSSV đang đăng nhập HUST Advisor. Chưa thay đổi dữ liệu.")
            with self._lock:
                if self._attempts.get(attempt_id) is attempt and not attempt.cancel.is_set():
                    attempt.snapshot, attempt.status = snapshot, "ready"
        except SchoolPortalError as exc:
            with self._lock:
                attempt.status, attempt.error = "error", str(exc)
        except Exception:
            # Never expose URLs, page text, cookies or credentials through errors/logs.
            with self._lock:
                attempt.status, attempt.error = "error", "Kết nối CTT gặp lỗi. Vui lòng thử lại."
        finally:
            with self._lock:
                self._running -= 1
                attempt.expires = min(attempt.expires, self.clock() + 90)
            timer = threading.Timer(90, self._expire, args=(attempt_id, attempt))
            timer.daemon = True
            timer.start()

    def _expire(self, attempt_id: str, attempt: _Attempt):
        with self._lock:
            if self._attempts.get(attempt_id) is attempt:
                attempt.cancel.set()
                attempt.snapshot = None
                del self._attempts[attempt_id]

    def _get(self, attempt_id: str, owner: str) -> _Attempt:
        self._prune()
        attempt = self._attempts.get(attempt_id)
        if not owner or attempt is None or not secrets.compare_digest(attempt.owner, self._owner(owner)):
            raise KeyError("Kết nối CTT không tồn tại hoặc đã hết hạn. Vui lòng mở lại.")
        return attempt

    def status(self, attempt_id: str, owner: str) -> dict:
        with self._lock:
            attempt = self._get(attempt_id, owner)
            return {"status": attempt.status, "error": attempt.error}

    def take(self, attempt_id: str, owner: str) -> _Attempt:
        with self._lock:
            attempt = self._get(attempt_id, owner)
            if attempt.status != "ready" or attempt.snapshot is None:
                raise SchoolPortalError(attempt.error or "Bạn chưa hoàn tất đăng nhập trên trang trường.")
            del self._attempts[attempt_id]
            return attempt

    def cancel(self, attempt_id: str, owner: str):
        with self._lock:
            attempt = self._get(attempt_id, owner)
            attempt.cancel.set()
            attempt.snapshot = None
            del self._attempts[attempt_id]

    def close(self):
        with self._lock:
            for attempt in self._attempts.values():
                attempt.cancel.set()
                attempt.snapshot = None
            self._attempts.clear()


school_login_manager = SchoolLoginManager()
