"""Real Chromium check of same-origin session reads against intercepted fixtures.

No real school login, credentials, personal data or backend are used.
Run with the backend Python after `python -m playwright install chromium`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from playwright.sync_api import sync_playwright
from app.services.school_portal import _fetch_ctt_html, _school_page_ready, SchoolPortalError

ORIGIN = "https://ctt-sis.hust.edu.vn"
HTML = '<a href="/Account/Logout.aspx">Logout</a><table><tr><td>MSSV</td><td>20221234</td></tr></table>'


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chromium", headless=True)
        try:
            context = browser.new_context()
            context.add_cookies([{"name": "synthetic_session", "value": "fixture-only", "url": ORIGIN}])
            requests = []
            def respond(route):
                request = route.request
                requests.append((request.url, request.headers.get("cookie", "")))
                route.fulfill(status=200, content_type="text/html", body=HTML)
            context.route(ORIGIN + "/**", respond)
            page = context.new_page()
            page.goto(ORIGIN + "/Account/Login.aspx")
            assert not _school_page_ready(page)
            page.goto(ORIGIN + "/")
            assert _school_page_ready(page)
            result = _fetch_ctt_html(page, ORIGIN + "/Students/StudentCourseGrade.aspx")
            assert result["html"] == HTML
            assert requests[-1][0].endswith("StudentCourseGrade.aspx")
            assert "synthetic_session=fixture-only" in requests[-1][1]
            count = len(requests)
            try:
                _fetch_ctt_html(page, "https://outside.invalid/")
                raise AssertionError("External targets must be rejected")
            except SchoolPortalError:
                pass
            assert len(requests) == count
            print("PASS: bundled Chromium; login-page gate; same-origin fetch uses browser session; external target blocked.")
            print("Browser version:", browser.version)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
