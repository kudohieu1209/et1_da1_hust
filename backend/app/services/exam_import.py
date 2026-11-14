"""Read text-based exam PDFs into a reviewable preview, never auto-assign seats."""
import io
import re

from app.services.ctt_sections import date_value, fold


def preview_exam_pdf(content: bytes) -> list[dict]:
    from pypdf import PdfReader
    if not content.startswith(b"%PDF-") or len(content) > 10 * 1024 * 1024:
        raise ValueError("Chỉ nhận PDF tối đa 10 MB.")
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted or len(reader.pages) > 100:
            raise ValueError("PDF được bảo vệ hoặc quá 100 trang. Hãy dùng bản lịch thi có thể đọc văn bản.")
        texts = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
    except ValueError:
        raise
    except Exception:
        raise ValueError("Không đọc được PDF lịch thi. Hãy dùng PDF có lớp văn bản, không phải ảnh quét.") from None
    if sum(map(len, texts)) > 2_000_000:
        raise ValueError("PDF chứa quá nhiều văn bản. Hãy tách phần lịch thi cần nhập.")
    rows = []
    seen = set()
    for line in "\n".join(texts).splitlines():
        code = re.search(r"\b[A-Z]{2,3}\d{4}[A-Z]?\b", line)
        date = date_value(line)
        clock = re.search(r"\b([0-2]?\d):([0-5]\d)\b", line)
        if clock and int(clock[1]) > 23:
            clock = None
        slot = re.search(r"(?:Ca|Kíp)\s*\d+", line, re.I)
        if not code or not date or not (clock or slot):
            continue
        exam_time = clock[0] if clock else slot[0]
        room = re.search(r"\b[A-Z]{1,2}\d{1,2}[-.]\d{2,3}\b", line)
        class_code = re.search(r"\b\d{5,6}\b", line)
        signature = (code[0], date, exam_time, room[0] if room else "", class_code[0] if class_code else "")
        if signature in seen:
            continue
        seen.add(signature)
        tail = line[code.end():]
        name = re.split(r"\s{2,}|\t|\d{1,2}[/.-]\d{1,2}[/.-]20\d{2}", tail.strip(), maxsplit=1)[0]
        rows.append({"course_code": code[0], "course_name": name if not re.fullmatch(r"\d+", name) else "", "exam_date": date,
                     "exam_time": exam_time, "room": room[0] if room else "", "class_code": class_code[0] if class_code else "",
                     "exam_type": "Trắc nghiệm" if "trac nghiem" in fold(line) else "Tự luận" if "tu luan" in fold(line) else "",
                     "notes": "Nhập từ PDF; sinh viên cần đối chiếu đúng lớp/ca thi."})
        if len(rows) >= 500:
            break
    if not rows:
        raise ValueError("Chưa đọc được dòng có mã học phần, ngày và giờ/ca thi. PDF có thể là ảnh quét hoặc bố cục chưa được hỗ trợ.")
    return rows
