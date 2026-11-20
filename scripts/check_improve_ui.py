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


def sync_mock_timetable(student_id="20229876"):
    from app.services.data_loader import data_loader
    key = data_loader.profiles.find_key(student_id)
    profile = data_loader.profiles.get(key)
    # TKB giả có 2 môn:
    # 1. MI1111: trùng mã môn F đang học lại
    # 2. ET3290: môn mới có trong CTĐT (Đồ án thiết kế I)
    profile.setdefault("school_services", {})["timetable"] = {
        "status": "synced",
        "synced_at": "2026-11-20T10:00:00Z",
        "records": [
            {"course_code": "MI1111", "course_name": "Giải tích I"},
            {"course_code": "ET3290", "course_name": "Đồ án thiết kế I"},
        ],
        "tables": [],
    }
    data_loader.save_profile_for(student_id, profile)


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

    # Đồng bộ TKB giả
    sync_mock_timetable("20229876")
    page.reload()
    select_tab(page, TAB_NAME)
    page.get_by_test_id("current-cpa").wait_for()
    expect(page.get_by_text("Nhập bảng điểm từ CTT", exact=True)).to_be_hidden()


def verify_api(page):
    audit = response_json(page.request.get("/api/student/audit"))
    analysis = response_json(page.request.get("/api/student/improve-courses"))
    assert analysis["current_cpa"] == audit["cpa"]
    assert analysis["cpa_credits"] == 20.0
    assert analysis["cpa_points"] == 38.5
    candidates = analysis["improve_candidates"]
    assert {item["code"]: item["current_letter_grade"] for item in candidates} == {
        "MI1111": "F", "ET2050": "D", "ET3220": "D+", "MI1121": "C", "ET2040": "B",
    }
    assert analysis["honors_rule"] == {
        "retake_credits": 7.0, "basis_credits": 126.0, "threshold_credits": 6.3,
        "exceeds": True, "basis_source": "program",
    }

    # Verify upcoming courses and current term candidate flags
    upcoming_codes = [c["code"] for c in analysis["upcoming_courses"]]
    assert "ET3290" in upcoming_codes, f"ET3290 missing from upcoming: {upcoming_codes}"
    assert "MI1111" not in upcoming_codes, "MI1111 (F retake) should not appear in upcoming"

    mi1111 = next(c for c in candidates if c["code"] == "MI1111")
    assert mi1111["in_current_term"] is True
    et2050 = next(c for c in candidates if c["code"] == "ET2050")
    assert et2050["in_current_term"] is False

    proj = analysis.get("program_projection")
    assert proj is not None
    assert proj["final_cpa_credits"] == 126.0
    assert proj["remaining_credits"] == 110.0

    response = page.request.post("/api/chat", data={"message": "nên học cải thiện môn nào"})
    chat = response_json(response)
    assert response.status == 200 and chat["intent"] == "COURSE_IMPROVEMENT"
    assert all(code in chat["reply"] for code in ("MI1111", "ET2050", "ET3220"))
    assert all(code not in chat["reply"] for code in ("MI1121", "ET2040"))
    assert chat["data_context"]["total_candidates"] == 3

    brief = {
        key: analysis[key]
        for key in ("current_cpa", "cpa_credits", "cpa_points", "total_candidates", "program_projection", "honors_rule")
    }
    brief["upcoming_sample"] = [
        {key: c[key] for key in ("code", "name", "credits", "source")}
        for c in analysis["upcoming_courses"][:5]
    ]
    print("GET /api/student/improve-courses (abridged):")
    print(json.dumps(brief, ensure_ascii=False, indent=2))
    print(f"CPA: improve {analysis['current_cpa']:.2f} = audit {audit['cpa']:.2f}")
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

    # 1. Tab "Học lại & cải thiện": kiểm tra nhãn "Đang học lại kỳ này" cho môn MI1111
    retake_course = page.locator(".improve-course").filter(has_text="MI1111")
    expect(retake_course.get_by_text("Đang học lại kỳ này")).to_be_visible()

    # Thử chọn điểm cho MI1111
    target = page.get_by_role("group", name="Điểm mục tiêu cho MI1111", exact=True).get_by_role("button", name="A", exact=True)
    target.click()
    expect(target).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_test_id("simulated-cpa")).not_to_have_text(f"{cpa:.2f}")
    target.click()
    expect(page.get_by_test_id("simulated-cpa")).to_have_text(f"{cpa:.2f}")

    # 2. Mở tab con "Môn sắp học"
    upcoming_tab = page.locator(".improve-tab-chip").filter(has_text="Môn sắp học")
    upcoming_tab.click()

    # Môn mới ET3290 xuất hiện trong nhóm "Kỳ này"
    expect(page.locator("#subtab-panel-upcoming").get_by_text("ET3290")).to_be_visible()
    # Môn F (MI1111) không xuất hiện bên tab "Môn sắp học"
    expect(page.locator("#subtab-panel-upcoming").get_by_text("MI1111")).to_be_hidden()

    # Chọn điểm A cho môn mới ET3290 -> CPA mô phỏng tăng
    target_a = page.get_by_role("group", name="Điểm dự kiến cho ET3290", exact=True).get_by_role("button", name="A", exact=True)
    target_a.click()
    cpa_with_a = float(page.get_by_test_id("simulated-cpa").inner_text())
    assert cpa_with_a > cpa, f"CPA with A ({cpa_with_a}) should be > base CPA ({cpa})"

    # Chọn điểm D cho môn mới ET3290 -> CPA mô phỏng giảm
    target_d = page.get_by_role("group", name="Điểm dự kiến cho ET3290", exact=True).get_by_role("button", name="D", exact=True)
    target_d.click()
    cpa_with_d = float(page.get_by_test_id("simulated-cpa").inner_text())
    assert cpa_with_d < cpa, f"CPA with D ({cpa_with_d}) should be < base CPA ({cpa})"
    target_d.click() # deselect D
    expect(page.get_by_test_id("simulated-cpa")).to_have_text(f"{cpa:.2f}")

    # Chuyển về tab "Học lại & cải thiện"
    page.locator(".improve-tab-chip").filter(has_text="Học lại & cải thiện").click()

    # 3. Ô mục tiêu với phạm vi "Học hết CTĐT" hiện dòng "cần trung bình"
    page.get_by_role("button", name="2.50 · Khá", exact=True).click()
    page.get_by_label("Phạm vi môn mới", exact=True).select_option("program")
    expect(page.locator(".improve-goal-gpa-needed")).to_contain_text("cần trung bình")

    # Đặt lại phạm vi "none" để kiểm tra phương án học lại và cảnh báo hạ bằng
    page.get_by_label("Phạm vi môn mới", exact=True).select_option("none")

    # Kiểm tra phương án mục tiêu 3.20
    page.get_by_role("button", name="3.20 · Giỏi", exact=True).click()
    page.get_by_label("Điểm dự kiến khi học lại", exact=True).select_option("A")
    apply = page.get_by_role("button", name="Áp dụng phương án", exact=True)
    apply.click()
    expect(page.get_by_text(HONORS_WARNING, exact=True)).to_be_visible()

    # Reset với 2.50
    page.get_by_role("button", name="2.50 · Khá", exact=True).click()
    page.get_by_label("Điểm dự kiến khi học lại", exact=True).select_option("B+")
    apply.click()
    expect(page.locator(".improve-course [aria-pressed='true']").first).to_be_visible()
    assert float(page.get_by_test_id("simulated-cpa").inner_text()) >= 2.50

    # 4. Kiểm tra không bị tràn ngang ở mọi kích thước (đặc biệt 375px)
    page.locator(".improve-page").evaluate("(section) => { section.parentElement.scrollTop = 0; }")
    assert page.locator(".improve-page").evaluate(
        """section => [document.documentElement, section.parentElement, section,
            ...section.querySelectorAll('.improve-course-targets')].every(
                node => node.scrollWidth <= node.clientWidth + 1)"""
    )


def main():
    tmp_dir = Path("/tmp")
    if not tmp_dir.exists():
        try:
            tmp_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            tmp_dir = Path(tempfile.gettempdir())
    output = tmp_dir / "cpa-ui-checks"
    output.mkdir(parents=True, exist_ok=True)

    errors = []
    saved_screenshots = []
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

                # Chụp tab "Học lại & cải thiện"
                page.locator(".improve-tab-chip").filter(has_text="Học lại & cải thiện").click()
                retake_img = output / f"cpa-retake-{width}x{height}-{theme}.png"
                page.screenshot(path=str(retake_img))
                saved_screenshots.append(str(retake_img))

                # Chụp tab "Môn sắp học"
                page.locator(".improve-tab-chip").filter(has_text="Môn sắp học").click()
                upcoming_img = output / f"cpa-upcoming-{width}x{height}-{theme}.png"
                page.screenshot(path=str(upcoming_img))
                saved_screenshots.append(str(upcoming_img))

                print(f"PASS: {width}x{height} {theme} | {retake_img.name} & {upcoming_img.name}")
                context.close()
        browser.close()

    assert not errors, errors
    print("\nSaved UI screenshots:")
    for path in saved_screenshots:
        print(f" - {path}")
    print("\nPASS: upcoming courses tab, timetable sync, current term badges, grade simulation, goal scope, no horizontal scroll, and themes.")


if __name__ == "__main__":
    main()
