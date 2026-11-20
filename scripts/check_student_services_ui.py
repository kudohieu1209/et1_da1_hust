"""Verify the student services, graduation evidence and exam import with synthetic data."""

import functools
import json
import tempfile
import threading
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from check_auth_ui import ROOT, QuietHandler


def section(records=None, **extra):
    return {
        "status": "synced", "synced_at": "2026-11-15T00:00:00Z",
        "source_url": "https://ctt-sis.hust.edu.vn/",
        "records": records or [], "tables": [], **extra,
    }


def select_tab(page, title, mobile=False):
    if mobile:
        page.get_by_title("Mở thanh bên", exact=True).click()
    page.get_by_role("button", name=title, exact=True).click()


def assert_no_horizontal_scroll(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    overflowing = page.locator(".services-page, .services-table-wrap:visible, .english-standard-card:visible").evaluate_all(
        "(nodes) => nodes.filter(node => node.scrollWidth > node.clientWidth + 1).map(node => node.className)"
    )
    assert not overflowing, overflowing


def capture(page, locator, output, name, width, height):
    locator.scroll_into_view_if_needed()
    path = output / f"{name}.png"
    page.screenshot(path=str(path))
    assert path.stat().st_size > 0
    assert page.viewport_size == {"width": width, "height": height}


def main():
    dist = ROOT / "frontend" / "dist"
    assert (dist / "index.html").is_file(), "Build the frontend first."
    output = Path(tempfile.mkdtemp(prefix="da1-student-services-ui-"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(dist)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    account = {"student_id": "20261234", "student_name": "Sinh viên kiểm thử", "class_name": "Điện tử 03 - K71",
               "program_code": "ET1", "auth_provider": "ctt"}
    latest = {"score": 0, "test_date": "2026-11-15", "certificate_type": "Bài thi tổng hợp", "listening": 0, "reading": 0}
    deadline = (date.today() - timedelta(days=3)).isoformat()
    sections = {
        "english": section([latest]),
        "tuition": section(
            [{"semester": "2026.1", "tuition_fee": 9850000, "paid": 9000000, "debt": 850000,
              "deadline": deadline, "status": "Chưa nộp đủ"}],
            charges=[{"course_code": "ET2030", "course_name": "Lập trình", "unit_fee": 500000,
                      "fee_credits": 3, "coefficient": 1, "amount": 1600000}],
            payments=[{"label": "Học phí kỳ 2026.1", "actual_amount": 9000000}],
            tables=[{"id": "tuition", "headers": ["Học kỳ"], "rows": [["2026.1"]]}],
        ),
        "classmates": section([
            {"student_id": "20261235", "student_name": "Nguyễn Gia Bảo", "class_name": "Điện tử 03 - K71"},
            {"student_id": "20261236", "student_name": "Vũ Hoàng Anh", "class_name": "Điện tử 03 - K71"},
        ]),
        "warning": section(warning_level=0),
        "certificates": section(requirements={"240": "unverified"}, coursework={
            "220": {"passed_count": 1, "required_count": 2, "source_group_code": "220",
                    "records": [{"course_code": "PE1014", "course_name": "Thể chất", "letter_grade": "D", "is_passed": True}],
                    "note": "Đối chiếu điểm chữ với học phần trong nhóm CTĐT."},
        }),
        "timetable": section([{"id": "fixture", "course_code": "ET2030", "course_name": "Lập trình",
                               "class_code": "123456", "day_of_week": 8, "start_period": 1, "end_period": 3,
                               "room": "D3-201", "weeks": "1-16"}]),
        "temporary_timetable": section(status="empty"),
        "exams": section(status="unavailable", message="Chưa thấy trang lịch thi trong CTT. Có thể nhập PDF."),
    }
    preview = [
        {"course_code": "ET2030", "course_name": "Lập trình", "class_code": "123456", "exam_date": "2026-12-15",
         "exam_time": "07:30", "room": "D3-201", "exam_type": "", "notes": ""},
        {"course_code": "ET2050", "course_name": "Lý thuyết mạch", "class_code": "999999", "exam_date": "2026-12-16",
         "exam_time": "09:30", "room": "D5-201", "exam_type": "", "notes": ""},
    ]
    cohort = 71
    saved, errors = [], []
    services_title = "Tiện ích CTT (Học phí, TOEIC, Lớp)"
    audit_title = "Tiến độ học tập & CPA"

    def api(route):
        path = route.request.url.split("/api/", 1)[1]
        data = {}
        if path == "auth/me":
            data = account
        elif path == "student/profile":
            data = {"info": account, "transcript": [{"code": "ET2030", "credits": 3, "letter_grade": "B", "is_passed": True}],
                    "school_sync": {"synced_at": "fixture"}}
        elif path == "student/audit":
            data = {"student_info": account, "cpa": 3, "total_credits_required": 126, "total_credits_accumulated": 3}
        elif path == "student/school-services":
            data = {"sections": sections}
        elif path == "student/english-standard":
            data = {
                "cohort": cohort, "track": "standard", "ctt_status": "unverified", "history": [latest],
                "latest": latest, "estimated_level": None, "notes": [], "has_data": True,
                "rule": {"decision": "10828/QĐ-ĐHBK"} if cohort == 71 else None,
                "required": {
                    "graduation": {"level": 3, "source": "quy_dinh_ngoai_ngu_k71_verified.md:477-481",
                                   "quote": "3 trở lên theo Bảng 2.1, Phụ lục II"},
                    "registration_by_semester": [{"semesters": [1, 2], "placement_table": "3.1", "courses": []}],
                } if cohort == 71 else None,
            }
        elif path == "conversations":
            data = {"conversations": []}
        elif path == "student/exams/preview":
            data = {"records": preview}
        elif path == "student/exams/import":
            payload = route.request.post_data_json
            saved.append(payload)
            sections["exams"] = section(payload["exams"], source_type="imported_pdf")
            data = {"status": "success", "total": len(payload["exams"])}
        route.fulfill(content_type="application/json", body=json.dumps(data))

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chromium", headless=True)
            for width, height in ((375, 812), (1280, 800)):
                for theme in ("light", "dark"):
                    mobile = width == 375
                    cohort = 71
                    page = browser.new_page(viewport={"width": width, "height": height})
                    page.add_init_script(f"""
                        localStorage.setItem('hust_advisor_theme_explicit', 'true');
                        localStorage.setItem('hust_advisor_theme', '{theme}');
                        localStorage.setItem('hust_advisor_lang', 'vi');
                    """)
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.route("**/api/**", api)
                    page.goto(f"http://127.0.0.1:{server.server_port}")
                    select_tab(page, services_title, mobile)
                    expect(page.locator(".school-data-tabs button")).to_have_text(["Học phí", "Bạn cùng lớp"])
                    expect(page.get_by_role("button", name="Học phí", exact=True)).to_have_attribute("aria-pressed", "true")
                    expect(page.get_by_role("combobox", name="Học kỳ", exact=True)).to_have_value("2026.1")
                    expect(page.get_by_text("9.850.000 đ", exact=True)).to_be_visible()
                    expect(page.get_by_text("850.000 đ", exact=True)).to_be_visible()
                    expect(page.locator(".services-charge-badge")).to_contain_text("Lệch 100.000 đ")
                    expect(page.locator(".services-reminder")).to_contain_text("Quá hạn")
                    expect(page.get_by_text("Tổng theo học phần lệch", exact=False)).to_be_visible()
                    expect(page.get_by_role("heading", name="Các khoản thu theo CTT")).to_be_visible()
                    assert page.locator("details.school-data-source[open]").count() == 0
                    assert page.locator("body").evaluate("(body) => body.classList.contains('light-theme')") == (theme == "light")
                    assert_no_horizontal_scroll(page)
                    capture(page, page.get_by_role("heading", name="Tóm tắt học phí theo kỳ"), output,
                            f"tuition-summary-{width}x{height}-{theme}", width, height)
                    capture(page, page.locator(".services-charge-badge"), output,
                            f"tuition-charges-{width}x{height}-{theme}", width, height)

                    page.get_by_role("button", name="Bạn cùng lớp", exact=True).click()
                    expect(page.get_by_role("cell", name="Vũ Hoàng Anh", exact=True)).to_be_visible()
                    names = page.locator(".services-table tbody tr td:nth-child(2) > span:last-child")
                    expect(names).to_have_text(["Vũ Hoàng Anh", "Nguyễn Gia Bảo"])
                    search = page.get_by_role("searchbox")
                    search.fill("bảo")
                    expect(page.get_by_text("1 kết quả", exact=True)).to_be_visible()
                    expect(page.get_by_role("cell", name="Nguyễn Gia Bảo", exact=True)).to_be_visible()
                    expect(page.get_by_role("cell", name="Vũ Hoàng Anh", exact=True)).to_have_count(0)
                    assert_no_horizontal_scroll(page)
                    capture(page, search, output, f"classmates-{width}x{height}-{theme}", width, height)

                    select_tab(page, audit_title, mobile)
                    card = page.locator("section.english-standard-card")
                    expect(card.get_by_role("heading", name="Chuẩn tiếng Anh", exact=True)).to_be_visible()
                    expect(card.get_by_text("Tối thiểu Bậc 3", exact=True)).to_be_visible()
                    expect(card.get_by_role("strong").filter(has_text="0")).to_have_text("0")
                    expect(card.get_by_role("button", name="Đồng bộ CTT", exact=True)).to_have_count(0)
                    card.get_by_text("Yêu cầu đăng ký theo kỳ", exact=False).click()
                    expect(card.get_by_text("Xếp lớp theo Bảng 3.1", exact=True)).to_be_visible()
                    card.get_by_text("Lịch sử thi", exact=False).click()
                    expect(card.get_by_role("cell", name="Bài thi tổng hợp", exact=True)).to_be_visible()
                    page.get_by_text("Căn cứ GDTC/GDQP", exact=True).click()
                    expect(page.get_by_role("heading", name="Căn cứ GDTC", exact=True)).to_be_visible()
                    assert_no_horizontal_scroll(page)
                    capture(page, card.get_by_role("heading", name="Chuẩn tiếng Anh", exact=True), output,
                            f"english-k71-{width}x{height}-{theme}", width, height)

                    cohort = 67
                    select_tab(page, services_title, mobile)
                    select_tab(page, audit_title, mobile)
                    expect(card.get_by_text("Kho tài liệu chưa có quy định ngoại ngữ cho khóa K67.", exact=False)).to_be_visible()
                    expect(card.get_by_text("Tối thiểu Bậc", exact=False)).to_have_count(0)
                    if (width, theme) == (1280, "dark"):
                        terms = sections["tuition"]["records"]
                        terms.insert(0, {"semester": "2025.3", "tuition_fee": 1000000, "paid": 1000000, "debt": 0})
                        select_tab(page, services_title)
                        picker = page.get_by_role("combobox", name="Học kỳ", exact=True)
                        expect(picker).to_have_value("2026.1")
                        picker.select_option("2025.3")
                        expect(page.get_by_text("Chưa có hạn", exact=True)).to_be_visible()
                        expect(page.locator(".services-reminder")).to_have_count(0)
                        expect(page.get_by_text("Tổng theo học phần lệch", exact=False)).to_have_count(0)
                        terms.pop(0)
                        select_tab(page, "Thời khóa biểu & Lịch thi")
                        expect(page.get_by_role("heading", name="Chủ Nhật", exact=True)).to_be_visible()
                        expect(page.get_by_text("ET2030 · Lập trình", exact=True)).to_be_visible()
                        page.get_by_role("button", name="Lịch thi", exact=True).click()
                        page.get_by_label("Chọn PDF lịch thi").set_input_files(
                            {"name": "fixture.pdf", "mimeType": "application/pdf", "buffer": b"%PDF-fixture"})
                        expect(page.get_by_role("checkbox", name="Chọn ca thi 1")).to_be_visible()
                        assert not saved
                        page.get_by_role("checkbox", name="Chọn ca thi 1").check()
                        page.get_by_role("button", name="Xác nhận và lưu 1 ca thi đã chọn").click()
                        expect(page.get_by_text("Nhập PDF đã xác nhận", exact=True)).to_be_visible()
                        assert [exam["class_code"] for exam in saved[0]["exams"]] == ["123456"]
                    page.close()
            assert not errors, errors
            browser.close()
        print("PASS: tuition summary, discrepancy and reminder, classmates search, K71 and K67 English requirements, GDTC evidence, mobile width, Sunday timetable and explicit exam confirmation.")
        print("Screenshots:", output)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
