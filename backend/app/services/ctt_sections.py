"""Parse CTT service pages without manufacturing missing values.

Only text tables and explicit status labels are retained, never raw HTML,
authentication inputs, cookies or scripts. Every feature has its own status.
"""
import re
import unicodedata
from html import escape
from datetime import datetime
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup

PATHS = {
    "english": "/Students/ToeicMarks.aspx",
    "timetable": "/Students/Timetables.aspx",
    "temporary_timetable": "/Students/TimetablesTemp.aspx",
    "tuition": "/Students/CheckTuition.aspx",
    "classmates": "/Students/StudentGroupInfo.aspx",
    "requirements": "/Students/StudentProgram.aspx",
}


def fold(text):
    value = unicodedata.normalize("NFD", str(text).lower().replace("đ", "d"))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", "".join(c for c in value if not unicodedata.combining(c))).split())


def clean(text):
    return " ".join(str(text).split())


def number(value):
    value = re.sub(r"\s|VND|VNĐ|đ|₫", "", str(value), flags=re.I)
    if not value or not re.fullmatch(r"-?[0-9.,]+", value):
        return None
    if re.fullmatch(r"-?\d{1,3}(?:[.,]\d{3})+", value):
        value = value.replace(".", "").replace(",", "")
    elif "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    else:
        value = value.replace(",", ".")
    try:
        result = Decimal(value)
        return int(result) if result == result.to_integral_value() else float(result)
    except InvalidOperation:
        return None


def date_value(value):
    match = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](20\d{2})\b", str(value))
    if match:
        try:
            return datetime(int(match[3]), int(match[2]), int(match[1])).date().isoformat()
        except ValueError:
            return None
    match = re.search(r"\b20\d{2}-\d{2}-\d{2}\b", str(value))
    return match[0] if match else None


def field(row, *aliases):
    for alias in aliases:
        key = fold(alias)
        for label, value in row.items():
            if fold(label) == key:
                return value
    for alias in aliases:
        key = fold(alias)
        for label, value in row.items():
            if len(key) > 3 and fold(label).startswith(key + " "):
                return value
    return ""


def read_tables(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    grids = soup.find_all("table", id=re.compile(r"DXMainTable$", re.I))
    candidates = grids or [t for t in soup.find_all("table") if not t.find("table")]
    tables = []
    for table in candidates:
        rows = []
        header_index = None
        for tr in table.find_all("tr"):
            if tr.find_parent("table") is not table:
                continue
            cells = tr.find_all(["td", "th"], recursive=False)
            if not cells:
                continue
            texts = [clean(cell.get_text(" ", strip=True)) for cell in cells]
            if len(texts) < 2:
                continue
            classes = " ".join(tr.get("class", [])) + " " + " ".join(" ".join(c.get("class", [])) for c in cells)
            if re.search(r"dxgvGroup|dxgvFooter|dxgvPager|dxgvDetail", classes, re.I):
                continue
            if header_index is None and (any(c.name == "th" for c in cells) or re.search(r"dxgvHeader", classes, re.I)):
                header_index = len(rows)
            rows.append(texts)
        if not rows:
            continue
        if header_index is None:
            # Native CTT tables sometimes omit TH/header CSS; recognize labels.
            labels = ("ma hoc phan", "ten hoc phan", "hoc ky", "ngay thi", "ma sinh vien", "mssv", "ho va ten", "hoc phi", "so tien", "diem", "thu", "tuan", "phong", "stt")
            header_index = next((i for i, row in enumerate(rows[:6]) if sum(any(fold(x) == term or fold(x).startswith(term + " ") for term in labels) for x in row) >= 2), None)
        if header_index is None:
            continue
        headers = rows[header_index]
        data_rows = [row for row in rows[header_index + 1:] if len(row) == len(headers) and row != headers]
        if not grids and not data_rows:
            continue
        tables.append({"id": table.get("id", ""), "headers": headers, "rows": data_rows})
    return tables


def table_records(tables):
    return [dict(zip(t["headers"], row)) for t in tables for row in t["rows"]]


def label_pairs(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    pairs = []
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"], recursive=False)
        for i in range(len(cells) - 1):
            left, right = cells[i].get_text(" ", strip=True), cells[i + 1].get_text(" ", strip=True)
            if not right:
                checkbox = cells[i + 1].select_one('input[type="checkbox"][disabled]')
                if checkbox:
                    right = "Đã hoàn thành" if checkbox.has_attr("checked") else "Chưa hoàn thành"
                else:
                    right = " ".join(str(tag.get("alt") or tag.get("aria-label") or tag.get("title") or "") for tag in cells[i + 1].select('[alt], [aria-label], [title]'))
            if len(left) < 100 and len(right) < 200:
                pairs.append((clean(left).rstrip(":"), clean(right)))
    lines = [clean(x) for x in soup.get_text("\n", strip=True).splitlines() if clean(x)]
    for i, line in enumerate(lines):
        if ":" in line:
            label, value = line.split(":", 1)
            if len(label) < 100:
                pairs.append((label, value.strip() or (lines[i + 1] if i + 1 < len(lines) else "")))
        elif assessment_label(line) and i + 1 < len(lines):
            pairs.append((line, lines[i + 1]))
    return pairs


def assessment_label(text):
    key = fold(text).strip()
    return key in {"gdtc", "gdqp", "gdqp an", "giao duc the chat", "giao duc quoc phong"} or len(key) < 85 and any(x in key for x in (
        "canh bao", "canh cao", "chung chi gdtc", "chung chi gdqp",
        "chung chi giao duc the chat", "chung chi giao duc quoc phong",
        "chuan dau ra tieng anh", "chuan dau ra ngoai ngu"))


def completion(text):
    text = fold(text)
    if any(x in text for x in ("chua dat", "khong dat", "chua hoan thanh", "chua co", "khong co")):
        return "incomplete"
    if text in {"dat", "da dat", "hoan thanh", "da hoan thanh", "co", "da co", "da co chung chi", "da duoc cap", "du dieu kien"}:
        return "completed"
    return "unverified"


def parse_warning_level(value):
    text = fold(value)
    match = re.fullmatch(r"(?:(?:canh bao|canh cao)(?: hoc tap)?\s*)?(?:muc\s*|m\s*)?([0-3])", text)
    if match:
        return int(match[1])
    if text in {"khong", "binh thuong", "khong canh bao", "khong bi canh bao", "khong canh cao", "khong bi canh cao"}:
        return 0
    return None


def parse_requirements(html):
    soup = BeautifulSoup(html, "html.parser")
    for grid in soup.find_all('table', id=re.compile(r'DXMainTable$', re.I)):
        grid.decompose()  # Course grades do not establish certificate issuance.
    html = str(soup)
    statuses = {key: [] for key in ("220", "230", "240")}
    warnings = []
    evidence = []
    for label, value in label_pairs(html):
        key = fold(label)
        if assessment_label(label) and len(value) <= 80 and not assessment_label(value):
            evidence.append({"label": label, "value": value})
        if any(x in key for x in ("canh bao", "canh cao")):
            level = parse_warning_level(value)
            if level is not None:
                warnings.append(level)
        kind = "220" if ("gdtc" in key or "giao duc the chat" in key) else "230" if ("gdqp" in key or "giao duc quoc phong" in key or "quoc phong an ninh" in key) else "240" if ("chuan dau ra" in key and ("tieng anh" in key or "ngoai ngu" in key)) else None
        if kind:
            status = completion(value)
            if status != "unverified":
                statuses[kind].append(status)
    result = {key: next(iter(set(values))) if len(set(values)) == 1 else "unverified" for key, values in statuses.items()}
    return {"requirements": result, "warning_level": warnings[0] if len(set(warnings)) == 1 else None,
            "evidence": [dict(item) for item in {tuple(x.items()) for x in evidence}]}


def parse_section(kind, html, source_url, synced_at):
    tables = read_tables(html)
    rows = table_records(tables)
    soup = BeautifulSoup(html, "html.parser")
    text = fold(soup.get_text(" ", strip=True))
    empty = any(x in text for x in ("khong co du lieu", "khong co ban ghi", "chua co du lieu", "no data to display", "no records"))
    page_numbers = {a.get_text(strip=True) for a in soup.select('[class*="dxp-num"], [class*="dxpPageNumber"]')}
    status = "partial" if len(page_numbers) > 1 else "synced" if rows else "empty" if tables or empty else "unavailable"
    result = {"status": status, "source_url": source_url, "synced_at": synced_at, "tables": tables,
              "message": "CTT đang chia dữ liệu thành nhiều trang; dữ liệu có thể chưa đầy đủ." if status == "partial" else "" if status in {"synced", "empty"} else "Chưa nhận diện được bảng dữ liệu của mục này trên CTT.", "records": []}
    if kind in {"timetable", "temporary_timetable"}:
        for i, row in enumerate(rows):
            code = field(row, "Mã học phần", "Mã HP", "Mã môn học")
            day = field(row, "Thứ", "Ngày học")
            time_text = field(row, "Thời gian", "Giờ học", "Giờ")
            if not day:
                combined_day = re.search(r"(?:thu\s*([2-7])|\b(cn|chu nhat)\b)", fold(time_text))
                if combined_day:
                    day = combined_day[1] or "CN"
            periods = field(row, "Tiết học", "Tiết", "Kíp học")
            start = number(field(row, "Tiết bắt đầu", "Từ tiết"))
            end = number(field(row, "Tiết kết thúc", "Đến tiết"))
            digits = re.findall(r"\d+", periods)
            if start is None and digits and ":" not in periods:
                start, end = int(digits[0]), int(digits[-1])
            day_match = re.search(r"\b([2-7])\b", day)
            day_number = 8 if fold(day) in {"cn", "chu nhat", "8"} else int(day_match[1]) if day_match else None
            clock = re.search(r"\b([0-2]?\d)[:h]([0-5]?\d)\s*[-–]\s*([0-2]?\d)[:h]([0-5]?\d)\b", time_text)
            clock_valid = clock and int(clock[1]) < 24 and int(clock[3]) < 24
            periods_valid = isinstance(start, int) and isinstance(end, int) and 1 <= start <= end <= 20
            class_text = field(row, "Lớp học")
            if not code and class_text:
                # Temporary timetable's separate registration grid supplies course identity.
                matches = [r for r in rows if field(r, "Mã HP", "Mã học phần") and field(r, "Mã lớp")
                           and re.search(r"(?<!\w)" + re.escape(field(r, "Mã lớp")) + r"(?!\w)", class_text)]
                if len(matches) == 1:
                    row = {**matches[0], **row}
                    code = field(row, "Mã HP", "Mã học phần")
            if code and day_number and (periods_valid or clock_valid):
                result["records"].append({"id": f"ctt-{kind}-{i}", "course_code": code, "course_name": field(row, "Tên học phần", "Tên HP", "Tên môn học", "Tên lớp"),
                    "class_code": field(row, "Mã lớp", "Mã lớp học", "Lớp học"), "room": field(row, "Phòng học", "Địa điểm", "Phòng"),
                    "day_of_week": day_number, "start_period": start, "end_period": end, "time_str": field(row, "Thời gian", "Giờ học", "Giờ"),
                    "weeks": field(row, "Tuần học", "Tuần"), "lecturer": field(row, "Giảng viên", "Giáo viên"), "is_temp": kind == "temporary_timetable"})
    elif kind == "english":
        for row in rows:
            score = number(field(row, "Điểm tổng", "Tổng điểm", "Điểm TOEIC", "Điểm thi", "Điểm", "Kết quả"))
            listening, reading = number(field(row, "Điểm nghe", "Điểm nghe hiểu", "Nghe", "Listening")), number(field(row, "Điểm đọc", "Điểm đọc hiểu", "Đọc", "Reading"))
            writing, speaking = number(field(row, "Điểm viết", "Writing")), number(field(row, "Điểm nói", "Speaking"))
            if score is None and listening is not None and reading is not None and writing is None and speaking is None:
                score = listening + reading
            if score is not None:
                result["records"].append({"score": score, "listening": listening, "reading": reading, "writing": writing, "speaking": speaking, "test_date": date_value(field(row, "Ngày thi", "Ngày kiểm tra")),
                                          "certificate_type": field(row, "Loại chứng chỉ", "Chứng chỉ", "Loại thi", "Kỳ thi") or "Điểm tiếng Anh trên CTT"})
    elif kind == "tuition":
        result.update(charges=[], payments=[])
        for row in rows:
            code = field(row, "Mã HP", "Mã học phần")
            if code and field(row, "Tổng tiền học phần"):
                result["charges"].append({"course_code": code, "course_name": field(row, "Tên HP", "Tên học phần"),
                    "unit_fee": number(field(row, "Số tiền/1 TC học phí")), "fee_credits": number(field(row, "Số TC học phí")),
                    "coefficient": number(field(row, "Hệ số học phí lớp")), "amount": number(field(row, "Tổng tiền học phần")),
                    "registration_status": field(row, "Trạng thái đăng ký"), "registration_type": field(row, "Loại đăng ký"), "notes": field(row, "Ghi chú")})
            if field(row, "Loại tiền"):
                result["payments"].append({"label": field(row, "Loại tiền"), "amount": number(field(row, "Số tiền")),
                    "coefficient": number(field(row, "Hệ số đóng")), "actual_amount": number(field(row, "Thực đóng")),
                    "updated_at": field(row, "Ngày cập nhật"), "notes": field(row, "Ghi chú")})
            semester = field(row, "Học kỳ", "Học kì", "Kỳ học", "Kỳ thu")
            fee = number(field(row, "Phải đóng", "Phải nộp", "Học phí", "Số tiền phải nộp", "Tổng thu"))
            paid = number(field(row, "Đã đóng", "Đã nộp", "Đã thu", "Số tiền đã nộp"))
            debt = number(field(row, "Còn nợ", "Còn phải đóng", "Còn phải nộp", "Nợ", "Số tiền còn nợ"))
            if re.search(r"20\d{2}[./-]?[123]", semester) and any(x is not None for x in (fee, paid, debt)):
                result["records"].append({"semester": semester, "tuition_fee": fee, "paid": paid, "debt": debt,
                    "deadline": date_value(field(row, "Hạn nộp", "Hạn đóng", "Thời hạn")), "status": field(row, "Trạng thái", "Tình trạng")})
    elif kind == "classmates":
        for row in rows:
            student_id = field(row, "MSSV", "Mã số sinh viên", "Mã sinh viên", "Mã SV")
            family = field(row, "Họ và đệm", "Họ đệm") or clean(field(row, "Họ") + " " + field(row, "Đệm"))
            name = field(row, "Họ và tên", "Họ tên", "Tên sinh viên") or clean(family + " " + field(row, "Tên"))
            if re.fullmatch(r"[0-9]{8}", student_id) and name:
                result["records"].append({"student_id": student_id, "student_name": name, "class_name": field(row, "Tên lớp", "Lớp sinh viên", "Lớp quản lý", "Lớp"),
                                          "email": field(row, "Email", "Thư điện tử") or None})
    elif kind == "exams":
        for row in rows:
            code = field(row, "Mã học phần", "Mã HP", "Mã môn")
            day = date_value(field(row, "Ngày thi", "Ngày"))
            if code and day:
                result["records"].append({"course_code": code, "course_name": field(row, "Tên học phần", "Tên HP", "Tên môn"), "exam_date": day,
                    "exam_time": field(row, "Giờ thi", "Giờ", "Ca thi", "Kíp thi"), "room": field(row, "Phòng thi", "Phòng"),
                    "exam_type": field(row, "Hình thức thi", "Hình thức"), "student_index": field(row, "Số báo danh", "SBD") or None, "notes": field(row, "Ghi chú")})
    elif kind == "requirements":
        result.update(parse_requirements(html))
        known = result["warning_level"] is not None or any(s != "unverified" for s in result["requirements"].values())
        result["status"] = "synced" if known else "unavailable"
        result["tables"] = []  # Do not mix curriculum grids with certificates.
        result["message"] = "" if known else "CTT chưa trả về trạng thái chứng chỉ hoặc mức cảnh báo nhận diện được."
    # A recognized raw table is still useful when a column layout changes.
    if rows and not (result["records"] or result.get("charges") or result.get("payments")) and kind != "requirements":
        result["status"] = "partial"
        result["message"] = "Đã lấy được bảng CTT; một số cột chưa chuẩn hóa. Xem bảng gốc bên dưới."
    result["parser_version"] = 2
    return result


def normalize_saved_section(kind, section):
    """Upgrade text tables on read without another login or changing saved data."""
    if kind == 'certificates' and section.get('status') == 'unavailable':
        return {**section, 'message': 'Chưa xác định được trạng thái cấp chứng chỉ từ các trang CTT đã kiểm tra. Trạng thái này không có nghĩa là chưa đạt.'}
    if kind == 'warning' and section.get('warning_level') is None:
        levels = {parse_warning_level(item.get('value', '')) for item in section.get('evidence', [])
                  if any(x in fold(item.get('label', '')) for x in ('canh bao', 'canh cao'))}
        levels.discard(None)
        if len(levels) == 1:
            return {**section, 'warning_level': levels.pop(), 'status': 'synced', 'message': '', 'parser_version': 3}
        return section
    if kind not in {"english", "tuition", "classmates", "timetable", "temporary_timetable"} or section.get("parser_version", 0) >= 2 or not section.get("tables"):
        return section
    html = "".join('<table id="saved%d_DXMainTable"><tr>%s</tr>%s</table>' % (
        i, ''.join('<th>%s</th>' % escape(str(x)) for x in t['headers']),
        ''.join('<tr>%s</tr>' % ''.join('<td>%s</td>' % escape(str(x)) for x in row) for row in t['rows']))
        for i, t in enumerate(section['tables']))
    parsed = parse_section(kind, html, section.get('source_url', ''), section.get('synced_at'))
    result = {**section, **parsed, 'tables': section['tables']}
    if section.get('status') == 'stale' or 'chia dữ liệu' in section.get('message', ''):
        result.update(status=section['status'], message=section.get('message', ''))
    return result
