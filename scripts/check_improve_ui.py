"""Exercise the production CPA tab with an isolated API and a synthetic account."""
import json
import os
import socket
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import uvicorn
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT = """MI1111 F
ET2050 F
ET2050 D
ET3220 D+
MI1121 C
ET2040 C
ET2040 B
MI1141 A
PE9999 A"""
TAB_NAME = "Cải thiện điểm CPA"
HONORS_WARNING = "Hạng tốt nghiệp có thể giảm một mức"


@contextmanager
def production_server():
    if not (ROOT / "frontend" / "dist" / "index.html").is_file():
        raise RuntimeError("Run npm --prefix frontend run build first.")

    backend = ROOT / "backend"
    previous_dir = Path.cwd()
    sys.path.insert(0, str(backend))
    os.chdir(backend)
    try:
        with tempfile.TemporaryDirectory(prefix="cpa-ui-vector-", ignore_cleanup_errors=True) as vector_dir:
            env = {
                "VECTOR_DB_DIR": vector_dir,
                "MONGODB_URI": "",
                "GEMINI_API_KEY": "",
                "GOOGLE_API_KEY": "",
                "COOKIE_SECURE": "false",
            }
            # Disable dotenv before importing any application module.
            with patch.dict(os.environ, env), patch("dotenv.load_dotenv", return_value=False):
                from testing_support import isolated_database

                with patch("app.services.mongo_client.get_mongo_database", return_value=isolated_database()):
                    with socket.socket() as listener:
                        listener.bind(("127.0.0.1", 0))
                        server = uvicorn.Server(uvicorn.Config("app.main:app", access_log=False))
                        worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
                        worker.start()
                        try:
                            deadline = time.monotonic() + 240
                            while not server.started:
                                if not worker.is_alive() or time.monotonic() >= deadline:
                                    raise RuntimeError("The isolated uvicorn server failed to start.")
                                time.sleep(0.1)
                            yield f"http://127.0.0.1:{listener.getsockname()[1]}"
                        finally:
                            server.should_exit = True
                            worker.join(timeout=10)
    finally:
        os.chdir(previous_dir)
        sys.path.pop(0)


def response_json(response):
    assert response.ok, f"{response.url}: HTTP {response.status} {response.text()}"
    return response.json()


def select_tab(page, name):
    if page.viewport_size["width"] <= 768:
        page.get_by_title("Mở thanh bên", exact=True).click()
    page.get_by_role("button", name=name, exact=True).click()


def import_demo_transcript(page):
    response_json(page.request.post("/api/auth/register", data={
        "student_id": "20229876",
        "password": uuid4().hex,
        "student_name": "Sinh viên kiểm thử CPA",
        "class_name": "Điện tử - K67",
        "program_code": "ET1",
    }))
    page.goto("/")
    select_tab(page, TAB_NAME)
    page.locator(".improve-page").get_by_role("button", name="Nhập bảng điểm", exact=True).click()
    page.get_by_role("button", name="Dán bảng điểm", exact=True).click()
    page.get_by_label("Nội dung bảng điểm", exact=True).fill(TRANSCRIPT)
    save = page.get_by_role("button", name="Phân tích & lưu", exact=True)
    save.click()
    page.get_by_role("spinbutton", name="PE9999 số tín chỉ", exact=True).fill("2")
    save.click()
    page.get_by_test_id("current-cpa").wait_for()
    # The CPA tab must update after importing even when it stays mounted.
    expect(page.get_by_text("Nhập bảng điểm từ CTT", exact=True)).to_be_hidden()


def verify_api(page):
    audit = response_json(page.request.get("/api/student/audit"))
    analysis = response_json(page.request.get("/api/student/improve-courses"))
    assert analysis["current_cpa"] == audit["cpa"]
    assert analysis["cpa_credits"] == 20.0
    candidates = analysis["improve_candidates"]
    assert {item["code"]: item["current_letter_grade"] for item in candidates} == {
        "MI1111": "F", "ET2050": "D", "ET3220": "D+", "MI1121": "C", "ET2040": "B",
    }
    assert analysis["honors_rule"] == {
        "retake_credits": 7.0, "basis_credits": 126.0, "threshold_credits": 6.3,
        "exceeds": True, "basis_source": "program",
    }

    response = page.request.post("/api/chat", data={"message": "nên học cải thiện môn nào"})
    chat = response_json(response)
    assert response.status == 200 and chat["intent"] == "COURSE_IMPROVEMENT"
    assert all(code in chat["reply"] for code in ("MI1111", "ET2050", "ET3220"))
    assert all(code not in chat["reply"] for code in ("MI1121", "ET2040"))
    assert chat["data_context"]["total_candidates"] == 3

    brief = {key: analysis[key] for key in ("current_cpa", "cpa_credits", "total_candidates", "honors_rule")}
    brief["improve_candidates"] = [
        {key: course[key] for key in ("code", "current_letter_grade", "category", "max_delta_cpa")}
        for course in candidates
    ]
    print("GET /api/student/improve-courses (abridged):")
    print(json.dumps(brief, ensure_ascii=False, indent=2))
    print(f"CPA: improve {analysis['current_cpa']:.2f} = audit {audit['cpa']:.2f}")
    print(f"POST /api/chat: HTTP {response.status}\n{chat['reply']}")
    return audit["cpa"]


def verify_ui(page, cpa):
    select_tab(page, "Tiến độ học tập & CPA")
    audit_value = page.locator(".gemini-pill").filter(has_text="CPA:").get_by_text(f"{cpa:.2f}", exact=True)
    expect(audit_value).to_be_visible()
    displayed_cpa = audit_value.inner_text()
    select_tab(page, TAB_NAME)
    expect(page.get_by_test_id("current-cpa")).to_have_text(displayed_cpa)
    expect(page.get_by_test_id("simulated-cpa")).to_have_text(f"{cpa:.2f}")
    expect(page.get_by_text(HONORS_WARNING, exact=True)).to_be_hidden()

    target = page.get_by_role("group", name="Điểm mục tiêu cho MI1111", exact=True).get_by_role("button", name="A", exact=True)
    target.click()
    expect(target).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_test_id("simulated-cpa")).not_to_have_text(f"{cpa:.2f}")
    target.click()
    expect(page.get_by_test_id("simulated-cpa")).to_have_text(f"{cpa:.2f}")

    page.get_by_role("button", name="3.20 · Giỏi", exact=True).click()
    page.get_by_label("Điểm dự kiến khi học lại", exact=True).select_option("A")
    apply = page.get_by_role("button", name="Áp dụng phương án", exact=True)
    apply.click()
    expect(page.get_by_text(HONORS_WARNING, exact=True)).to_be_visible()

    page.get_by_role("button", name="2.50 · Khá", exact=True).click()
    page.get_by_label("Điểm dự kiến khi học lại", exact=True).select_option("B+")
    apply.click()
    expect(page.locator(".improve-course [aria-pressed='true']").first).to_be_visible()
    assert float(page.get_by_test_id("simulated-cpa").inner_text()) >= 2.50
    assert page.get_by_role("spinbutton", name="CPA mục tiêu", exact=True).input_value() == "2.50"
    page.locator(".improve-page").evaluate("(section) => { section.parentElement.scrollTop = 0; }")
    assert page.locator(".improve-page").evaluate(
        """section => [document.documentElement, section.parentElement, section,
            ...section.querySelectorAll('.improve-course-targets')].every(
                node => node.scrollWidth <= node.clientWidth + 1)"""
    )


def main():
    output = Path(tempfile.mkdtemp(prefix="cpa-improve-ui-"))
    errors = []
    with production_server() as url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chromium", headless=True)
        context = browser.new_context(base_url=url, viewport={"width": 1280, "height": 800})
        context.set_default_timeout(8_000)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        import_demo_transcript(page)
        cpa = verify_api(page)
        saved_session = context.storage_state()
        context.close()

        for width, height in ((375, 812), (1280, 800)):
            for theme in ("light", "dark"):
                context = browser.new_context(
                    base_url=url, storage_state=saved_session, color_scheme=theme,
                    viewport={"width": width, "height": height},
                )
                context.set_default_timeout(8_000)
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto("/")
                expect(page.locator("body.light-theme")).to_have_count(int(theme == "light"))
                verify_ui(page, cpa)
                image = output / f"cpa-{width}x{height}-{theme}.png"
                page.screenshot(path=str(image))
                print(f"PASS: {width}x{height} {theme} | {image}")
                context.close()
        browser.close()

    assert not errors, errors
    print("PASS: import refresh, audit parity, grade toggle, CPA goal, honors warning, layout and chatbot.")


if __name__ == "__main__":
    main()
