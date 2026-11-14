"""Browser smoke checks against the built frontend with synthetic API responses.

Run from the repository root after `npm --prefix frontend run build`:
    backend/.venv-win/Scripts/python.exe scripts/check_auth_ui.py
No school credentials, real backend or personal data are used.
"""
import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp" / "auth-ui"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # A route change may cancel a static asset request.


def main():
    assert (ROOT / "frontend/dist/index.html").exists(), "Build the frontend first."
    OUTPUT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT / "frontend/dist")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    state = {"scenario": "waiting", "cancelled": 0, "finished": 0, "start_bodies": []}
    errors = []
    account = {"student_id": "20221234", "student_name": "Sinh viên kiểm thử", "class_name": "Điện tử - K67", "program_code": "ET1", "auth_provider": "ctt"}

    def api(route):
        path = route.request.url.split("/api/", 1)[1]
        method = route.request.method
        status, data = 200, {}
        if path == "auth/me":
            status, data = 401, {"detail": "Chưa đăng nhập"}
        elif path.startswith("programs"):
            data = {"programs": [{"admission_code": "ET1", "name": "Điện tử và Viễn thông", "supported_cohorts": ["K67", "K68"]}]}
        elif path == "auth/ctt/capabilities":
            data = {"available": True}
        elif path == "auth/ctt/start":
            state["start_bodies"].append(route.request.post_data_json)
            if state["scenario"] == "rate_limited":
                status, data = 429, {"detail": "Máy vừa mở nhiều cửa sổ CTT. Vui lòng đợi hết thời gian chờ."}
            else:
                status, data = 202, {"attempt_id": "synthetic-attempt", "status": "opening"}
        elif path.endswith("/status"):
            data = ({"status": "ready", "error": ""} if state["scenario"] == "success" else
                    {"status": "error", "error": "MSSV CTT khác tài khoản đang đăng nhập."} if state["scenario"] == "error" else
                    {"status": "waiting", "error": ""})
        elif path.endswith("/finish"):
            state["finished"] += 1
            data = {**account, "school_sync": {"course_count": 1}}
        elif path == "auth/ctt/synthetic-attempt" and method == "DELETE":
            state["cancelled"] += 1
            status = 204
        elif path == "auth/login":
            status, data = 401, {"detail": "MSSV hoặc mật khẩu Advisor không đúng."}
        elif path == "student/profile":
            data = {"info": account, "transcript": [{"code": "ET2030", "credits": 3, "letter_grade": "B", "is_passed": True}]}
        elif path == "student/audit":
            data = {"student_info": account, "total_credits_required": 126, "total_credits_completed": 3, "cpa": 3.0}
        elif path == "conversations":
            data = {"conversations": []}
        route.fulfill(status=status, content_type="application/json", headers={"Retry-After": "2"} if status == 429 else {},
                      body="" if status == 204 else json.dumps(data))

    try:
        with sync_playwright() as p:
            browser = None
            for channel in ("msedge", "chrome", None):
                try:
                    browser = p.chromium.launch(channel=channel, headless=True)
                    break
                except Exception:
                    pass
            assert browser is not None, "Install Edge, Chrome or Playwright Chromium."
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("**/api/**", api)
            page.goto(base)
            page.get_by_role("heading", name="Chào bạn trở lại").wait_for()
            assert state["start_bodies"] == [], "Mounting the sign-in screen must not open a school connection"
            page.locator('#school-tab').click()
            page.keyboard.press("ArrowLeft")
            assert page.locator('#advisor-tab').get_attribute("aria-selected") == "true"
            page.keyboard.press("ArrowRight")
            assert page.locator('#school-tab').get_attribute("aria-selected") == "true"
            assert page.locator('input[type="password"]').count() == 0
            page.screenshot(path=str(OUTPUT / "desktop-school.png"), full_page=True)
            page.evaluate("document.body.classList.add('light-theme')")
            page.screenshot(path=str(OUTPUT / "desktop-light.png"), full_page=True)
            page.evaluate("document.body.classList.remove('light-theme')")

            state["scenario"] = "rate_limited"
            page.get_by_role("button", name="Tiếp tục với tài khoản trường").click()
            cooldown = page.get_by_role("button", name="Thử lại sau 2 giây")
            cooldown.wait_for()
            assert cooldown.is_disabled()
            cooldown.evaluate("button => button.click()")
            assert len(state["start_bodies"]) == 1
            page.get_by_role("button", name="Thử kết nối lại").wait_for()
            state["start_bodies"].clear()
            state["scenario"] = "waiting"
            page.get_by_role("button", name="Thử kết nối lại").evaluate("button => { button.click(); button.click(); }")
            page.get_by_text("Hoàn tất đăng nhập trong cửa sổ CTT vừa mở.").wait_for()
            page.get_by_role("button", name="Hủy kết nối", exact=True).click()
            page.get_by_role("button", name="Tiếp tục với tài khoản trường").wait_for()
            page.wait_for_function("true")
            assert state["cancelled"] == 1
            assert state["start_bodies"] == [{"program_code": "ET1"}]

            page.get_by_role("button", name="Tiếp tục với tài khoản trường").click()
            page.get_by_text("Hoàn tất đăng nhập trong cửa sổ CTT vừa mở.").wait_for()
            page.locator('#advisor-tab').click()
            page.wait_for_timeout(50)
            assert state["cancelled"] == 2

            page.locator('#advisor-student-id').fill('20221234')
            page.locator('#advisor-password').fill('synthetic-password')
            page.get_by_role("button", name="Vào không gian học tập").click()
            page.get_by_role("alert").filter(has_text="MSSV hoặc mật khẩu Advisor không đúng.").wait_for()
            page.screenshot(path=str(OUTPUT / "desktop-advisor-error.png"), full_page=True)
            page.get_by_role("button", name="Tạo tài khoản", exact=True).click()
            page.locator('#advisor-full-name').wait_for()
            assert page.locator('#advisor-full-name').count() == 1
            page.screenshot(path=str(OUTPUT / "desktop-register.png"), full_page=True)

            page.set_viewport_size({"width": 390, "height": 844})
            page.get_by_role("tab", name="Tài khoản trường").click()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(OUTPUT / "mobile-school.png"), full_page=True)

            state["scenario"] = "error"
            page.get_by_role("button", name="Tiếp tục với tài khoản trường").click()
            page.get_by_role("alert").filter(has_text="MSSV CTT khác tài khoản đang đăng nhập.").wait_for()
            assert state["finished"] == 0
            state["scenario"] = "success"
            page.get_by_role("button", name="Thử kết nối lại").click()
            page.wait_for_function("!document.querySelector('.auth-screen')")
            assert state["finished"] == 1
            assert errors == [], f"Browser errors: {errors}"
            context.close()
            browser.close()
        print("PASS: no start on mount, double-click guard, Retry-After countdown, school sign-in, cancellation, wrong-identity error, retry, single-use finish, local login error, registration, mobile overflow, and Vietnamese rendering.")
        print(f"Screenshots: {OUTPUT}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
