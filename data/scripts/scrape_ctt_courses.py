#!/usr/bin/env python3
"""Collect course rows (including the raw prerequisite expression) from CTT SIS.

The CTT course list is a DevExpress grid and the current portal requires a
logged-in browser session.  This script deliberately opens a visible browser
and lets the user authenticate manually; it never asks for or stores a
password.  It searches one course code at a time, so a complete crawl does
not require iterating through all 554 pages.

Playwright is an optional dependency.  Install it once with::

    <project-python> -m pip install playwright
    <project-python> -m playwright install chromium

The ``--html`` mode is dependency-free and is useful for checking a saved
page (Chrome -> Save page) before using the online mode.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


CTT_URL = "https://ctt-sis.hust.edu.vn/pub/CourseLists.aspx"
DATA_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CURRICULUM = DATA_DIR / "processed" / "curricula" / "et1_2022.json"
DEFAULT_OUTPUT = DATA_DIR / "raw" / "ctt_courses_scraped.json"

# The order is the order exposed by gvCourses's columnProp in the portal.
COLUMNS = (
    "code",
    "name",
    "load_hours",
    "credits",
    "tuition_credits",
    "department",
    "raw_condition",
    "english_name",
    "exam_factor",
)
# CTT uses both letter-prefixed codes (ET4230, MI2020) and newer codes such
# as 1DL242.  Keep validation deliberately permissive: the source table is
# authoritative and this check is only meant to skip comments/blank lines in
# a codes file.
COURSE_CODE_RE = re.compile(r"^[A-Z0-9]{2,10}$", re.IGNORECASE)
SUMMARY_RE = re.compile(
    r"Page\s+(?P<page>\d+)\s+of\s+(?P<pages>\d+)\s+\((?P<items>[\d,\.]+)\s+items\)",
    re.IGNORECASE,
)


def clean_text(value: str | None) -> str:
    """Collapse visual whitespace while retaining the condition symbols."""

    if not value:
        return ""
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def number_or_none(value: str) -> int | float | None:
    value = clean_text(value).replace(",", ".")
    if not value:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


class CourseTableParser(HTMLParser):
    """Small stdlib-only parser for one saved CTT HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row_id: str | None = None
        self._row_cells: list[str] = []
        self._cell_depth = 0
        self._cell_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        row_id = attrs_map.get("id", "") or ""
        if tag == "tr" and "_DXDataRow" in row_id:
            self._row_id = row_id
            self._row_cells = []
            self._cell_depth = 0
            self._cell_text = []
        elif tag == "td" and self._row_id is not None and self._cell_depth == 0:
            self._cell_depth = 1
            self._cell_text = []
        elif self._cell_depth:
            self._cell_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._row_id is None:
            return
        if tag == "td" and self._cell_depth == 1:
            self._row_cells.append(clean_text("".join(self._cell_text)))
            self._cell_depth = 0
            self._cell_text = []
        elif self._cell_depth:
            self._cell_depth -= 1
        if tag == "tr":
            if self._row_cells:
                self.rows.append(self._row_cells)
            self._row_id = None
            self._row_cells = []
            self._cell_depth = 0
            self._cell_text = []

    def handle_data(self, data: str) -> None:
        if self._cell_depth:
            self._cell_text.append(data)


def row_to_record(cells: Iterable[str], page: int | None = None, row_index: int | None = None) -> dict[str, Any]:
    values = [clean_text(cell) for cell in cells]
    values.extend([""] * (len(COLUMNS) - len(values)))
    values = values[: len(COLUMNS)]
    record: dict[str, Any] = {
        "code": values[0].upper(),
        "name": values[1],
        "load_hours": values[2],
        "credits": number_or_none(values[3]),
        "tuition_credits": number_or_none(values[4]),
        "department": values[5],
        # Keep this exact string.  The parser in merge_conditions.py is the
        # next stage and understands / (OR), , (AND), ! and =.
        "raw_condition": values[6],
        "english_name": values[7],
        "exam_factor": number_or_none(values[8]),
    }
    if page is not None:
        record["source_page"] = page
    if row_index is not None:
        record["source_row"] = row_index
    return record


def summary_from_text(text: str) -> dict[str, int] | None:
    match = SUMMARY_RE.search(clean_text(text))
    if not match:
        return None
    return {
        "page": int(match.group("page")),
        "pages": int(match.group("pages")),
        "items": int(match.group("items").replace(",", "").replace(".", "")),
    }


def records_from_html(path: Path) -> tuple[list[dict[str, Any]], dict[str, int] | None]:
    parser = CourseTableParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    html = path.read_text(encoding="utf-8", errors="replace")
    summary = summary_from_text(html)
    page = summary["page"] if summary else None
    records = [row_to_record(row, page=page, row_index=index) for index, row in enumerate(parser.rows)]
    return records, summary


def load_codes(codes_file: Path | None, explicit_codes: list[str], curriculum: Path) -> list[str]:
    if explicit_codes:
        source: Iterable[str] = explicit_codes
    elif codes_file:
        source = codes_file.read_text(encoding="utf-8").splitlines()
    else:
        data = json.loads(curriculum.read_text(encoding="utf-8"))
        source = (course.get("code", "") for course in data.get("courses", []))

    codes: list[str] = []
    seen: set[str] = set()
    for value in source:
        code = clean_text(value).upper().split("#", 1)[0].strip()
        if not code or code in seen or not COURSE_CODE_RE.match(code):
            continue
        seen.add(code)
        codes.append(code)
    return codes


def parse_dom_rows(page: Any, page_number: int | None = None) -> list[dict[str, Any]]:
    """Read visible data rows.  ``page`` is a Playwright Page object."""

    rows = page.locator("table[id$='_DXMainTable'] tr[id*='_DXDataRow']")
    result: list[dict[str, Any]] = []
    for index in range(rows.count()):
        cells = rows.nth(index).locator(":scope > td").all_text_contents()
        result.append(row_to_record(cells, page=page_number, row_index=index))
    return result


def is_login_url(url: str) -> bool:
    return "/Account/Login" in url or "/login" in url.lower()


def wait_for_manual_login(page: Any, timeout_seconds: int) -> None:
    if not is_login_url(page.url):
        return
    print("CTT đang yêu cầu đăng nhập. Hãy đăng nhập trên cửa sổ trình duyệt đang mở.")
    print("Script sẽ tiếp tục khi trang chuyển về CourseLists.aspx.")
    deadline = time.monotonic() + timeout_seconds
    while is_login_url(page.url):
        if time.monotonic() >= deadline:
            raise RuntimeError("Hết thời gian chờ đăng nhập; hãy chạy lại với --login-timeout lớn hơn.")
        page.wait_for_timeout(1000)


def wait_for_grid(page: Any, timeout_ms: int = 60000) -> None:
    page.wait_for_selector("table[id$='_DXMainTable']", timeout=timeout_ms)


def current_summary(page: Any) -> dict[str, int] | None:
    summary_locator = page.locator(".dxp-summary")
    if summary_locator.count() == 0:
        return None
    text = summary_locator.first.text_content() or ""
    return summary_from_text(text)


def filter_by_code(page: Any, code: str, timeout_ms: int = 30000) -> list[dict[str, Any]]:
    """Use the portal's own filter (Contains([CourseID], ...))."""

    table = page.locator("table[id$='_DXMainTable']")
    before = table.inner_html()
    code_input = page.locator("input[id$='_tbCourseID']").first
    submit = page.locator("div[id$='_btSubmit']").first
    code_input.fill(code)
    submit.click()
    try:
        page.wait_for_function(
            """({selector, before}) => {
                const table = document.querySelector(selector);
                return table && table.innerHTML !== before;
            }""",
            {"selector": "table[id$='_DXMainTable']", "before": before},
            timeout=timeout_ms,
        )
    except Exception:
        # Some portal versions reuse identical markup for a one-row result;
        # allow a short settle period and validate by reading the actual row.
        page.wait_for_timeout(500)
    page.wait_for_timeout(150)
    summary = current_summary(page)
    page_number = summary["page"] if summary else None
    return [row for row in parse_dom_rows(page, page_number=page_number) if row["code"] == code]


def set_grid_page_size(page: Any, page_size: int, timeout_ms: int = 30000) -> bool:
    """Ask the DevExpress pager for a larger page size when crawling all rows."""

    if page_size <= 0:
        return False
    table = page.locator("table[id$='_DXMainTable']")
    before = table.inner_html()
    changed = page.evaluate(
        """(size) => {
            try {
                if (!window.ASPx) return false;
                const gridEl = document.querySelector("table[id$='_gvCourses']");
                const grid = gridEl && ASPx.GetControlCollection().Get(gridEl.id);
                // This works even when the optional page-size input is hidden
                // by the current CTT responsive layout.
                if (grid && grid.doPagerOnClick) {
                    grid.doPagerOnClick("PSP" + Number(size));
                    return true;
                }
                const pagerEl = document.querySelector("div[id$='_DXPagerBottom']");
                const pager = pagerEl && ASPx.GetControlCollection().Get(pagerEl.id);
                if (!pager || !pager.ChangePageSizeValue || !pager.OnPageSizeValueChanged) return false;
                if (pager.pageSizeSelectedItem && Number(pager.pageSizeSelectedItem.value) === Number(size)) return true;
                pager.ChangePageSizeValue(Number(size));
                pager.OnPageSizeValueChanged();
                return true;
            } catch (error) {
                return false;
            }
        }""",
        page_size,
    )
    if not changed:
        return False
    try:
        page.wait_for_function(
            """({selector, before}) => {
                const table = document.querySelector(selector);
                return table && table.innerHTML !== before;
            }""",
            {"selector": "table[id$='_DXMainTable']", "before": before},
            timeout=timeout_ms,
        )
    except Exception:
        # If the requested size was already active, no callback is emitted.
        page.wait_for_timeout(300)
    # A few CTT deployments expose the client callback but ignore PSP<n> on
    # the server.  Verify the rendered row count instead of claiming success.
    page.wait_for_timeout(500)
    rendered_rows = page.locator("table[id$='_DXMainTable'] tr[id*='_DXDataRow']").count()
    summary = current_summary(page)
    expected_rows = min(page_size, summary["items"]) if summary else page_size
    return rendered_rows >= expected_rows


def scrape_filtered(page: Any, codes: list[str], delay: float, retries: int = 2) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    missing: list[str] = []
    for index, code in enumerate(codes, 1):
        matches: list[dict[str, Any]] = []
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                matches = filter_by_code(page, code)
                last_error = None
            except Exception as exc:  # keep the other codes useful if one callback fails
                last_error = exc
                matches = []
            if matches:
                break
            if attempt < retries:
                print(f"[{index}/{len(codes)}] {code}: chưa có kết quả, thử lại {attempt + 1}/{retries}...", file=sys.stderr)
                page.wait_for_timeout(750)
        if last_error is not None and not matches:
            print(f"[{index}/{len(codes)}] {code}: lỗi callback ({last_error})", file=sys.stderr)
        if matches:
            records.extend(matches)
            suffix = f" ({len(matches)} dòng)" if len(matches) > 1 else ""
            print(f"[{index}/{len(codes)}] {code}: OK{suffix}")
        else:
            missing.append(code)
            print(f"[{index}/{len(codes)}] {code}: không tìm thấy", file=sys.stderr)
        if delay:
            time.sleep(delay)
    return records, missing


def scrape_all_pages(page: Any, max_pages: int, delay: float, page_size: int = 200) -> tuple[list[dict[str, Any]], list[str]]:
    if page_size > 0:
        if set_grid_page_size(page, page_size):
            print(f"Đã chuyển kích thước trang sang {page_size} dòng để giảm số callback.")
        else:
            print("Không đổi được kích thước trang; tiếp tục với kích thước CTT hiện tại.", file=sys.stderr)
    records: list[dict[str, Any]] = []
    summary = current_summary(page)
    total_pages = summary["pages"] if summary else 0
    if max_pages > 0:
        total_pages = min(total_pages or max_pages, max_pages)
    if not total_pages:
        raise RuntimeError("Không đọc được tổng số trang từ pager CTT.")

    for expected_page in range(1, total_pages + 1):
        summary = current_summary(page)
        actual_page = summary["page"] if summary else expected_page
        page_records = parse_dom_rows(page, page_number=actual_page)
        records.extend(page_records)
        print(f"Trang {actual_page}/{total_pages}: {len(page_records)} dòng")
        if expected_page == total_pages:
            break
        next_button = page.locator("a[id$='_DXPagerBottom_PBN']").first
        before = page.locator("table[id$='_DXMainTable']").inner_html()
        next_button.click()
        try:
            page.wait_for_function(
                """({selector, before}) => {
                    const table = document.querySelector(selector);
                    return table && table.innerHTML !== before;
                }""",
                {"selector": "table[id$='_DXMainTable']", "before": before},
                timeout=30000,
            )
        except Exception:
            page.wait_for_timeout(500)
        if delay:
            time.sleep(delay)
    return records, []


def write_output(path: Path, records: list[dict[str, Any]], source_url: str, mode: str, missing: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "ctt-course-list.v1",
        "source_url": source_url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "count": len(records),
        "missing_codes": missing or [],
        "courses": sorted(records, key=lambda item: item.get("code", "")),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Thu thập mã môn và HP điều kiện từ CTT SIS.")
    parser.add_argument("--html", type=Path, help="Phân tích một file HTML đã lưu, không mở trình duyệt.")
    parser.add_argument("--url", default=CTT_URL, help=f"URL CTT (mặc định: {CTT_URL})")
    parser.add_argument("--curriculum", type=Path, default=DEFAULT_CURRICULUM, help="JSON CTĐT dùng để lấy danh sách mã môn.")
    parser.add_argument("--codes-file", type=Path, help="File mã môn, mỗi dòng một mã; dòng bắt đầu bằng # bị bỏ qua.")
    parser.add_argument("--code", action="append", default=[], help="Chỉ lấy một mã; có thể lặp lại nhiều lần.")
    parser.add_argument("--all", action="store_true", help="Lấy mọi dòng; mặc định chỉ lấy mã trong CTĐT.")
    parser.add_argument("--max-pages", type=int, default=0, help="Giới hạn số trang khi dùng --all (0 = toàn bộ).")
    parser.add_argument("--page-size", type=int, default=200, help="Số dòng/trang khi dùng --all (CTT cho tối đa 200).")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="File JSON đầu ra.")
    parser.add_argument("--delay", type=float, default=0.25, help="Số giây nghỉ giữa các callback (mặc định 0.25).")
    parser.add_argument("--retries", type=int, default=2, help="Số lần thử lại khi một mã chưa trả về dòng (mặc định 2).")
    parser.add_argument("--headless", action="store_true", help="Ẩn trình duyệt; chỉ dùng khi phiên đăng nhập đã có sẵn.")
    parser.add_argument("--user-data-dir", type=Path, help="Hồ sơ Chrome riêng để giữ phiên đăng nhập (tùy chọn).")
    parser.add_argument("--login-timeout", type=int, default=300, help="Thời gian chờ đăng nhập, giây (mặc định 300).")
    return parser.parse_args()


def run_html_mode(args: argparse.Namespace) -> int:
    records, summary = records_from_html(args.html)
    selected = records
    missing: list[str] = []
    # A saved page is only one page of the grid.  Without an explicit filter,
    # preserve every row in that file; silently applying the whole curriculum
    # here would look like a complete crawl while returning mostly nothing.
    if args.code or args.codes_file:
        codes = load_codes(args.codes_file, args.code, args.curriculum)
        by_code = {row["code"]: row for row in records}
        selected = [by_code[code] for code in codes if code in by_code]
        missing = [code for code in codes if code not in by_code]
    write_output(args.output, selected, args.html.resolve().as_uri(), "saved_html", missing)
    print(f"Đã ghi {len(selected)} dòng vào {args.output}")
    if summary:
        print(f"File là trang {summary['page']}/{summary['pages']} ({summary['items']} mục); --html chỉ đọc đúng trang này.")
    if missing:
        print(f"Chưa có trong file này: {len(missing)} mã (đây có thể chỉ là một trang).", file=sys.stderr)
    return 0


def run_browser_mode(args: argparse.Namespace) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Thiếu Playwright. Cài một lần bằng:", file=sys.stderr)
        print(f"  {sys.executable} -m pip install playwright", file=sys.stderr)
        print(f"  {sys.executable} -m playwright install chromium", file=sys.stderr)
        return 2

    codes = [] if args.all else load_codes(args.codes_file, args.code, args.curriculum)
    if not args.all and not codes:
        raise RuntimeError("Không có mã môn để lọc; dùng --all hoặc cung cấp --curriculum/--codes-file.")

    with sync_playwright() as playwright:
        browser = None
        if args.user_data_dir:
            args.user_data_dir.mkdir(parents=True, exist_ok=True)
            context = playwright.chromium.launch_persistent_context(
                str(args.user_data_dir), headless=args.headless
            )
        else:
            browser = playwright.chromium.launch(headless=args.headless)
            context = browser.new_context()
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            wait_for_manual_login(page, args.login_timeout)
            try:
                wait_for_grid(page, timeout_ms=10000)
            except Exception:
                # A successful login may land on the portal home page instead
                # of preserving ReturnUrl.  Re-open the requested list once.
                page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
                wait_for_manual_login(page, args.login_timeout)
                wait_for_grid(page)
            if args.all:
                records, missing = scrape_all_pages(page, args.max_pages, args.delay, args.page_size)
                mode = "browser_all"
            else:
                records, missing = scrape_filtered(page, codes, args.delay, max(0, args.retries))
                mode = "browser_filtered"
            write_output(args.output, records, args.url, mode, missing)
            print(f"Đã ghi {len(records)} dòng vào {args.output}")
            if missing:
                print(f"Không tìm thấy/lỗi {len(missing)} mã; xem missing_codes trong JSON.", file=sys.stderr)
        finally:
            context.close()
            if browser:
                browser.close()
    return 0


def main() -> int:
    args = parse_args()
    try:
        if args.html:
            if not args.html.exists():
                print(f"Không tìm thấy file HTML: {args.html}", file=sys.stderr)
                return 2
            return run_html_mode(args)
        return run_browser_mode(args)
    except KeyboardInterrupt:
        print("Đã dừng theo yêu cầu.", file=sys.stderr)
        return 130
    except RuntimeError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
