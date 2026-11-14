"""School login uses synthetic HTML, browser runners and isolated MongoDB only."""
import threading
import time
import unittest
import unicodedata
from datetime import timedelta
from unittest import mock

from fastapi.testclient import TestClient

from app.api import router_school_auth
from app.auth import runtime
from app.auth.passwords import hash_password, verify_password
from app.auth.service import AuthService, SlidingWindowLimiter
from app.auth.store import MongoAuthStore
from app.core.config import SESSION_COOKIE_NAME
from app.main import app
from app.services.ctt_service import CttScraper, ctt_parser
from app.services.data_loader import data_loader
from app.services.profile_repository import MongoProfileRepository
from app.services.school_account_service import complete_school_login
from app.services.school_portal import (
    SchoolLoginManager, SchoolPortalError, authenticated_ctt_html,
    build_school_snapshot, parse_school_identity, read_school_in_browser,
    _school_page_ready, _wait_for_browser_activity, _fetch_ctt_html,
)
from testing_support import isolated_database, sample_profiles

PORTAL = "https://ctt-sis.hust.edu.vn/"
LOGOUT = '<a href="/Account/Logout.aspx">Đăng xuất</a>'
IDENTITY = '''<table><tr><td>Mã số sinh viên:</td><td>20221234</td></tr>
<tr><td>Họ và tên:</td><td>Nguyễn Minh An</td></tr>
<tr><td>Lớp:</td><td>Điện tử 02 - K67</td></tr></table>'''
GRADES = '''<table id="gvResults_DXMainTable">
<tr><td>Học kỳ: 2023.1 - GPA: 3.0 - CPA: 3.0</td></tr>
<tr><td>1</td><td>ET2030</td><td>Kỹ thuật lập trình</td><td>3</td><td>7</td><td>8</td><td>B</td></tr>
<tr><td>2</td><td>ET2050</td><td>Lý thuyết mạch</td><td>3</td><td>3</td><td>3.5</td><td>F</td></tr>
<tr><td>3</td><td>ET3220</td><td>Điện tử số</td><td>3</td><td>8</td><td>9</td><td></td></tr>
</table>'''
HTML = LOGOUT + IDENTITY + GRADES
PASSWORD = "Advisor-test-password!"


def snapshot(student_id="20221234"):
    html = HTML.replace("20221234", student_id)
    return build_school_snapshot([(PORTAL, html)], html)


class SchoolHtmlTests(unittest.TestCase):
    def test_labeled_identity_and_unicode_are_preserved(self):
        info = parse_school_identity(HTML)
        self.assertEqual(info["student_id"], "20221234")
        self.assertEqual(info["student_name"], "Nguyễn Minh An")
        self.assertEqual(info["class_name"], "Điện tử 02 - K67")

    def test_unlabeled_number_or_login_input_is_not_identity(self):
        self.assertEqual(parse_school_identity('<p>20221234</p><input name="MSSV" value="20221234">'), {})

    def test_identity_in_separate_spans_and_known_label_ids(self):
        info = parse_school_identity('<span>MSSV:</span><b>20221234</b><span id="ctl00_lblHoTen">Nguyễn Minh An</span>')
        self.assertEqual(info, {"student_name": "Nguyễn Minh An", "student_id": "20221234"})

    def test_conflicting_identity_is_rejected(self):
        with self.assertRaises(SchoolPortalError):
            parse_school_identity(IDENTITY + IDENTITY.replace("20221234", "20224567"))

    def test_profile_name_case_and_unicode_variants_do_not_conflict(self):
        upper = IDENTITY.replace("Nguyễn Minh An", "NGUYỄN MINH AN")
        decomposed = unicodedata.normalize("NFD", IDENTITY)
        result = parse_school_identity(upper + decomposed)
        self.assertEqual(result["student_id"], "20221234")
        self.assertEqual(result["student_name"], "Nguyễn Minh An")

    def test_grade_grid_headings_are_not_student_profile_fields(self):
        grid = '''<table id="gvCourseMarks_DXMainTable"><tr><td>Họ và tên</td><td>Giảng viên</td>
        <td>Lớp</td><td>Khóa</td></tr><tr><td>MSSV</td><td>20224567</td></tr></table>'''
        self.assertEqual(parse_school_identity(IDENTITY + grid), parse_school_identity(IDENTITY))

    def test_ambiguous_optional_email_and_class_do_not_block_verified_identity(self):
        html = IDENTITY + '''<table><tr><td>Lớp</td><td>Lớp 99 - K67</td></tr>
        <tr><td>Email</td><td>fixture1@example.test</td></tr><tr><td>Email</td><td>fixture2@example.test</td></tr></table>'''
        info = parse_school_identity(html)
        self.assertEqual(info["student_id"], "20221234")
        self.assertEqual(info["student_name"], "Nguyễn Minh An")
        self.assertNotIn("email", info)
        self.assertNotIn("class_name", info)

    def test_known_identity_label_ids_take_precedence_over_generic_text(self):
        html = IDENTITY + '<span id="ctl00_lblHoTen">Nguyễn Minh Bình</span>'
        self.assertEqual(parse_school_identity(html)["student_name"], "Nguyễn Minh Bình")

    def test_genuinely_conflicting_profile_names_still_fail(self):
        with self.assertRaisesRegex(SchoolPortalError, "họ tên"):
            parse_school_identity(IDENTITY + IDENTITY.replace("Nguyễn Minh An", "Nguyễn Minh Bình"))

    def test_authentication_requires_exact_https_origin_and_logout_anchor(self):
        self.assertTrue(authenticated_ctt_html(PORTAL, HTML))
        for url, html, status in [
            (PORTAL, HTML, 500),
            ("http://ctt-sis.hust.edu.vn/", HTML, 200),
            ("https://ctt-sis.hust.edu.vn.evil.test/", HTML, 200),
            (PORTAL + "Account/Login.aspx", HTML, 200),
            (PORTAL, '<script>"Logout.aspx"</script>', 200),
            (PORTAL, HTML + '<input type="password">', 200),
        ]:
            with self.subTest(url=url, status=status):
                self.assertFalse(authenticated_ctt_html(url, html, status))

    def test_no_exam_score_is_converted_to_an_unreleased_letter_grade(self):
        parsed = ctt_parser.parse_transcript_html(GRADES)
        self.assertEqual(parsed["transcript"][-1]["letter_grade"], "")
        result = snapshot()
        self.assertEqual([c["code"] for c in result.transcript], ["ET2030", "ET2050"])
        self.assertFalse(result.transcript[-1]["is_passed"])

    def test_zero_credit_course_is_not_given_its_exam_score_as_credits(self):
        html = HTML.replace('<td>3</td><td>7</td>', '<td>0</td><td>7</td>')
        self.assertEqual(build_school_snapshot([(PORTAL, html)], html).transcript[0]["credits"], 0)

    def test_missing_identity_empty_grades_and_partial_pages_are_rejected(self):
        for html in [LOGOUT + GRADES, LOGOUT + IDENTITY, HTML + '<a class="dxp-num">1</a><a class="dxp-num">2</a>']:
            with self.subTest(html=html[-70:]), self.assertRaises(SchoolPortalError):
                build_school_snapshot([(PORTAL, html)], html)

    def test_mismatched_ids_across_authenticated_pages_are_rejected(self):
        with self.assertRaises(SchoolPortalError):
            build_school_snapshot([(PORTAL, HTML), (PORTAL, HTML.replace("20221234", "20224567"))], HTML)

    def test_legacy_password_login_never_sends_network_requests(self):
        with mock.patch("app.services.ctt_service.requests.Session") as session:
            self.assertFalse(CttScraper().login("20221234", "not-a-real-password")[0])
            session.assert_not_called()

    def test_browser_failure_does_not_expose_exception_details(self):
        from playwright.sync_api import Error
        fake = mock.MagicMock()
        fake.chromium.launch.side_effect = Error("secret-url-or-token")
        with mock.patch("playwright.sync_api.sync_playwright") as launch:
            launch.return_value.__enter__.return_value = fake
            with self.assertRaises(SchoolPortalError) as exc:
                read_school_in_browser(threading.Event(), lambda _: None)
        self.assertNotIn("secret-url-or-token", str(exc.exception))

    def test_browser_reader_reads_verified_ctt_pages_without_filling_credentials(self):
        fake = mock.MagicMock()
        browser = fake.chromium.launch.return_value
        context = browser.new_context.return_value
        page = context.new_page.return_value
        page.url = PORTAL
        page.locator.return_value.count.return_value = 1
        page.evaluate.side_effect = lambda script, url=None: {"url": url, "status": 200, "html": HTML} if url else True
        context.pages = [page]
        response = mock.MagicMock()
        response.url, response.status = PORTAL, 200
        response.text.return_value = HTML
        context.request.get.return_value = response
        with mock.patch("playwright.sync_api.sync_playwright") as launch:
            launch.return_value.__enter__.return_value = fake
            result = read_school_in_browser(threading.Event(), lambda _: None)
        self.assertEqual(result.info["student_id"], "20221234")
        self.assertEqual(len(result.transcript), 2)
        page.fill.assert_not_called()
        page.click.assert_not_called()
        context.request.get.assert_not_called()
        self.assertEqual(fake.chromium.launch.call_args.kwargs["channel"], "chromium")
        browser.close.assert_called_once()

    def test_email_password_and_mfa_documents_are_never_treated_as_signed_in(self):
        for url in [PORTAL + "Account/Login.aspx", "https://login.microsoftonline.com/common/login",
                    "https://login.microsoftonline.com/common/SAS/ProcessAuth", "about:blank",
                    "https://ctt-sis.hust.edu.vn.evil.test/"]:
            with self.subTest(url=url):
                page = mock.MagicMock()
                page.url = url
                page.evaluate.return_value = True  # Even a misleading logout reference cannot pass the URL gate.
                self.assertFalse(_school_page_ready(page))
                page.evaluate.assert_not_called()

    def test_document_destroyed_during_sso_redirect_keeps_waiting(self):
        from playwright.sync_api import Error
        page = mock.MagicMock()
        page.url = PORTAL
        page.evaluate.side_effect = Error("Execution context was destroyed")
        self.assertFalse(_school_page_ready(page))

    def test_waiting_for_new_tab_timeout_is_normal(self):
        from playwright.sync_api import TimeoutError as BrowserTimeout
        context = mock.MagicMock()
        context.wait_for_event.side_effect = BrowserTimeout("no new tab")
        _wait_for_browser_activity(context, mock.MagicMock(), threading.Event())
        context.wait_for_event.assert_called_once_with("page", timeout=700)

    def test_office365_tab_handoff_does_not_read_grades_before_returning_to_ctt(self):
        from playwright.sync_api import Error, TimeoutError as BrowserTimeout
        fake = mock.MagicMock()
        browser = fake.chromium.launch.return_value
        context = browser.new_context.return_value
        login = context.new_page.return_value
        login.url = PORTAL + "Account/Login.aspx"
        login.wait_for_timeout.side_effect = Error("Target page has been closed")
        oauth = mock.MagicMock()
        oauth.url = "https://login.microsoftonline.com/common/login"
        protected = mock.MagicMock()
        protected.url = PORTAL
        protected.evaluate.return_value = True
        context.pages = [login]
        steps = []

        def handoff(*args, **kwargs):
            steps.append(len(steps) + 1)
            context.pages = {1: [oauth], 2: [], 3: [oauth], 4: [protected]}[len(steps)]
            raise BrowserTimeout("normal event wait")

        def verified_response(script, url=None):
            if url is None:
                return True
            self.assertEqual(len(steps), 4, "Grade requests must wait for Office 365 password/MFA and the return to CTT")
            return {"url": url, "status": 200, "html": HTML}

        context.wait_for_event.side_effect = handoff
        protected.evaluate.side_effect = verified_response
        stages = []
        with mock.patch("playwright.sync_api.sync_playwright") as launch:
            launch.return_value.__enter__.return_value = fake
            result = read_school_in_browser(threading.Event(), stages.append)
        self.assertEqual(result.info["student_id"], "20221234")
        self.assertEqual(stages, ["waiting", "syncing"])
        login.evaluate.assert_not_called()
        oauth.evaluate.assert_not_called()
        login.wait_for_timeout.assert_not_called()
        browser.close.assert_called_once()

    def test_email_only_stays_pending_until_user_cancels(self):
        from playwright.sync_api import TimeoutError as BrowserTimeout
        fake = mock.MagicMock()
        browser = fake.chromium.launch.return_value
        context = browser.new_context.return_value
        page = context.new_page.return_value
        page.url = "https://login.microsoftonline.com/common/login"
        context.pages = [page]
        cancel = threading.Event()
        stages = []
        def after_entering_email(*args, **kwargs):
            cancel.set()
            raise BrowserTimeout("normal event wait")
        context.wait_for_event.side_effect = after_entering_email
        with mock.patch("playwright.sync_api.sync_playwright") as launch:
            launch.return_value.__enter__.return_value = fake
            with self.assertRaisesRegex(SchoolPortalError, "Đã hủy"):
                read_school_in_browser(cancel, stages.append)
        self.assertEqual(stages, ["waiting"])
        context.request.get.assert_not_called()
        page.evaluate.assert_not_called()

    def test_browser_close_error_does_not_discard_a_verified_result(self):
        from playwright.sync_api import Error
        fake = mock.MagicMock()
        browser = fake.chromium.launch.return_value
        browser.close.side_effect = Error("already closed")
        context = browser.new_context.return_value
        page = context.new_page.return_value
        page.url = PORTAL
        page.evaluate.side_effect = lambda script, url=None: {"url": url, "status": 200, "html": HTML} if url else True
        context.pages = [page]
        response = context.request.get.return_value
        response.url, response.status = PORTAL, 200
        response.text.return_value = HTML
        with mock.patch("playwright.sync_api.sync_playwright") as launch:
            launch.return_value.__enter__.return_value = fake
            self.assertEqual(read_school_in_browser(threading.Event(), lambda _: None).info["student_id"], "20221234")

    def test_same_origin_reader_uses_the_authenticated_page_and_rejects_external_targets(self):
        page = mock.MagicMock()
        with self.assertRaises(SchoolPortalError):
            _fetch_ctt_html(page, "https://evil.test/")
        page.evaluate.assert_not_called()
        page.evaluate.return_value = {"url": PORTAL, "status": 200, "html": HTML}
        self.assertEqual(_fetch_ctt_html(page, PORTAL)["html"], HTML)
        script, target = page.evaluate.call_args.args
        self.assertIn("credentials: 'same-origin'", script)
        self.assertEqual(target, PORTAL)
        for result in [None, {"url": "https://evil.test/", "status": 200, "html": HTML},
                       {"url": PORTAL, "status": 500, "html": HTML},
                       {"url": PORTAL + "Account/Login.aspx", "status": 200, "html": HTML}]:
            page.evaluate.return_value = result
            with self.subTest(result=result and result.get("url")), self.assertRaises(SchoolPortalError):
                _fetch_ctt_html(page, PORTAL)


class SchoolLoginApiTests(unittest.TestCase):
    def setUp(self):
        self.database = isolated_database()
        self.profiles = MongoProfileRepository(self.database)
        self.store = MongoAuthStore(self.database)
        self.auth = AuthService(self.store, self.profiles)
        for sid in ("20220001", "20231890"):
            self.profiles.save(sid, sample_profiles()[sid])
            self.store.create_user({"student_id": sid, "password_hash": hash_password(PASSWORD), "created_at": self.auth.clock()})
        self.manager = SchoolLoginManager(runner=lambda cancel, notify: snapshot())
        for patcher in (
            mock.patch.object(data_loader, "_profiles", self.profiles),
            mock.patch.object(runtime, "auth_service", self.auth),
            mock.patch.object(router_school_auth, "school_login_manager", self.manager),
            mock.patch.object(router_school_auth, "start_limiter", SlidingWindowLimiter(timedelta(minutes=5), 20)),
            mock.patch.object(router_school_auth, "CTT_BROWSER_LOGIN_ENABLED", True),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.manager.close)
        self.client = self._client()

    def _client(self, address="127.0.0.1"):
        return TestClient(app, base_url="http://localhost", client=(address, 50000))

    def _start(self, client=None):
        client = client or self.client
        response = client.post("/api/auth/ctt/start", json={"program_code": "ET1"})
        self.assertEqual(response.status_code, 202, response.text)
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("SameSite=strict", response.headers["set-cookie"])
        self.assertEqual(response.headers["cache-control"], "no-store")
        attempt_id = response.json()["attempt_id"]
        for _ in range(60):
            state = client.get(f"/api/auth/ctt/{attempt_id}/status").json()
            if state["status"] in {"ready", "error"}:
                return attempt_id, state
            time.sleep(.005)
        self.fail("Test browser runner did not finish")

    def test_first_school_login_creates_verified_profile_and_http_only_session(self):
        attempt, state = self._start()
        self.assertEqual(state, {"status": "ready", "error": ""})
        self.assertNotIn("20221234", str(state))
        response = self.client.post(f"/api/auth/ctt/{attempt}/finish")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(SESSION_COOKIE_NAME, response.headers["set-cookie"])
        self.assertEqual(response.json()["student_name"], "Nguyễn Minh An")
        self.assertEqual(response.json()["auth_provider"], "ctt")
        self.assertEqual(response.json()["school_sync"]["course_count"], 2)
        self.assertNotIn("password", response.text)
        user = self.store.get_user("20221234")
        self.assertEqual(user["auth_provider"], "ctt")
        profile = self.client.get("/api/student/profile").json()
        self.assertEqual(profile["info"]["student_id"], "20221234")
        self.assertEqual(len(profile["transcript"]), 2)
        self.assertEqual(self.client.post(f"/api/auth/ctt/{attempt}/finish").status_code, 404)

    def test_existing_local_password_is_preserved_and_other_profiles_unchanged(self):
        self.manager.runner = lambda cancel, notify: snapshot("20220001")
        before = self.profiles.get("20231890")
        attempt, _ = self._start()
        self.assertEqual(self.client.post(f"/api/auth/ctt/{attempt}/finish").status_code, 200)
        self.assertTrue(verify_password(PASSWORD, self.store.get_user("20220001")["password_hash"]))
        self.assertEqual(self.profiles.get("20231890"), before)

    def test_another_browser_cannot_read_or_finish_an_attempt(self):
        attempt, _ = self._start()
        other = self._client()
        self.assertEqual(other.get(f"/api/auth/ctt/{attempt}/status").status_code, 404)
        self.assertEqual(other.post(f"/api/auth/ctt/{attempt}/finish").status_code, 404)
        self.assertEqual(other.delete(f"/api/auth/ctt/{attempt}").status_code, 404)
        self.assertIsNone(self.store.get_user("20221234"))

    def test_cancel_discards_result_without_creating_account(self):
        attempt, _ = self._start()
        self.assertEqual(self.client.delete(f"/api/auth/ctt/{attempt}").status_code, 204)
        self.assertEqual(self.client.post(f"/api/auth/ctt/{attempt}/finish").status_code, 404)
        self.assertIsNone(self.store.get_user("20221234"))

    def test_expired_attempt_cannot_be_finished(self):
        now = [0.0]
        self.manager.clock = lambda: now[0]
        attempt, _ = self._start()
        now[0] = 1000
        self.assertEqual(self.client.post(f"/api/auth/ctt/{attempt}/finish").status_code, 404)
        self.assertIsNone(self.store.get_user("20221234"))

    def test_signed_in_account_cannot_import_a_different_school_identity(self):
        self.client.post("/api/auth/login", json={"student_id": "20220001", "password": PASSWORD})
        before = self.profiles.get("20220001")
        attempt, state = self._start()
        self.assertEqual(state["status"], "error")
        self.assertEqual(self.client.post(f"/api/auth/ctt/{attempt}/finish").status_code, 409)
        self.assertEqual(self.profiles.get("20220001"), before)
        self.assertIsNone(self.store.get_user("20221234"))

    def test_changing_advisor_account_during_sign_in_rejects_the_result(self):
        attempt, _ = self._start()
        self.client.post("/api/auth/login", json={"student_id": "20231890", "password": PASSWORD})
        response = self.client.post(f"/api/auth/ctt/{attempt}/finish")
        self.assertEqual(response.status_code, 409)
        self.assertIsNone(self.store.get_user("20221234"))

    def test_unsupported_curriculum_does_not_create_account_or_profile(self):
        data = snapshot()
        data.info["class_name"] = "Điện tử 02 - K60"
        self.manager.runner = lambda cancel, notify: data
        attempt, _ = self._start()
        self.assertEqual(self.client.post(f"/api/auth/ctt/{attempt}/finish").status_code, 422)
        self.assertIsNone(self.profiles.get("20221234"))
        self.assertIsNone(self.store.get_user("20221234"))
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_failed_profile_write_rolls_back_a_new_user(self):
        with mock.patch.object(data_loader, "save_profile_for", side_effect=RuntimeError("db-unavailable")):
            with self.assertRaises(RuntimeError):
                complete_school_login(self.auth, snapshot(), "ET1")
        self.assertIsNone(self.store.get_user("20221234"))
        self.assertIsNone(self.profiles.get("20221234"))

    def test_school_accounts_do_not_accept_the_advisor_password_route(self):
        attempt, _ = self._start()
        self.client.post(f"/api/auth/ctt/{attempt}/finish")
        self.assertEqual(self.client.post("/api/auth/password", json={
            "current_password": PASSWORD, "new_password": "new-advisor-password!",
        }).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/login", json={
            "student_id": "20221234", "password": PASSWORD,
        }).status_code, 401)

    def test_remote_clients_and_forwarded_remote_clients_cannot_open_desktop_browser(self):
        for client, headers in [(self._client("192.0.2.1"), {}), (self.client, {"X-Forwarded-For": "192.0.2.1"}),
                                (self.client, {"Origin": "https://evil.test"})]:
            with self.subTest(headers=headers):
                self.assertEqual(client.post("/api/auth/ctt/start", json={}, headers=headers).status_code, 403)

    def test_start_is_rate_limited_before_opening_more_browsers(self):
        limiter = SlidingWindowLimiter(timedelta(minutes=5), 1)
        with mock.patch.object(router_school_auth, "start_limiter", limiter):
            attempt, _ = self._start()
            self.client.delete(f"/api/auth/ctt/{attempt}")
            response = self.client.post("/api/auth/ctt/start", json={})
            self.assertEqual(response.status_code, 429)
            self.assertIn("Retry-After", response.headers)

    def test_repeated_start_resumes_same_window_even_when_new_window_quota_is_used(self):
        limiter = SlidingWindowLimiter(timedelta(minutes=5), 1)
        with mock.patch.object(router_school_auth, "start_limiter", limiter):
            attempt, _ = self._start()
            for _ in range(8):
                response = self.client.post("/api/auth/ctt/start", json={"program_code": "ET1"})
                self.assertEqual(response.status_code, 202, response.text)
                self.assertEqual(response.json()["attempt_id"], attempt)
            self.assertEqual(self.client.post(f"/api/auth/ctt/{attempt}/finish").status_code, 200)

    def test_invalid_program_requests_do_not_use_window_quota(self):
        limiter = SlidingWindowLimiter(timedelta(minutes=5), 1)
        with mock.patch.object(router_school_auth, "start_limiter", limiter):
            for _ in range(8):
                self.assertEqual(self.client.post("/api/auth/ctt/start", json={"program_code": "ZZZ"}).status_code, 422)
            self._start()

    def test_resume_cannot_change_identity_and_conflicts_do_not_consume_quota(self):
        limiter = SlidingWindowLimiter(timedelta(minutes=5), 2)
        with mock.patch.object(router_school_auth, "start_limiter", limiter):
            attempt, _ = self._start()
            self.client.post("/api/auth/login", json={"student_id": "20220001", "password": PASSWORD})
            for _ in range(8):
                self.assertEqual(self.client.post("/api/auth/ctt/start", json={"program_code": "ET1"}).status_code, 409)
            self.client.delete(f"/api/auth/ctt/{attempt}")
            _, state = self._start()
            self.assertEqual(state["status"], "error")  # Synthetic CTT identity differs, but a new window is allowed.

    def test_legacy_password_endpoint_is_explicitly_retired(self):
        self.assertEqual(self.client.post("/api/auth/login-ctt", json={"password": "never-forward-this"}).status_code, 410)

    def test_browser_exception_does_not_leak_sensitive_details(self):
        def broken(cancel, notify):
            raise RuntimeError("token=should-not-appear")
        self.manager.runner = broken
        attempt, state = self._start()
        self.assertEqual(state["status"], "error")
        self.assertNotIn("token=", state["error"])
        self.assertIsNone(self.store.get_user("20221234"))


class SchoolManagerTests(unittest.TestCase):
    def test_busy_workers_do_not_use_new_window_quota(self):
        release = threading.Event()
        def pending(cancel, notify):
            release.wait(2)
            raise SchoolPortalError("cancelled")
        manager = SchoolLoginManager(runner=pending)
        count = mock.Mock()
        try:
            first = manager.start("owner-1", "ET1", None, before_start=count)
            self.assertEqual(manager.start("owner-1", "ET1", None, before_start=count), first)
            manager.start("owner-2", "ET1", None, before_start=count)
            for _ in range(8):
                with self.assertRaises(SchoolPortalError):
                    manager.start("owner-3", "ET1", None, before_start=count)
            self.assertEqual(count.call_count, 2)
        finally:
            release.set()
            manager.close()

    def test_cancelled_workers_still_count_towards_the_browser_limit_until_closed(self):
        release = threading.Event()
        def pending(cancel, notify):
            release.wait(2)
            raise SchoolPortalError("cancelled")
        manager = SchoolLoginManager(runner=pending)
        try:
            for index in range(2):
                owner = f"owner-{index}"
                attempt = manager.start(owner, "ET1", None)
                manager.cancel(attempt, owner)
            with self.assertRaises(SchoolPortalError):
                manager.start("owner-3", "ET1", None)
        finally:
            release.set()
            manager.close()
