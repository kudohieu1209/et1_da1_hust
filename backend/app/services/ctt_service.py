import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup
from app.core.hust_rules import GRADE_TO_SCALE4, PASSING_GRADES

logger = logging.getLogger(__name__)

CTT_BASE_URL = "https://ctt-sis.hust.edu.vn"
LOGIN_URL = f"{CTT_BASE_URL}/Account/Login.aspx"
STUDENT_GRADE_URL = f"{CTT_BASE_URL}/Students/StudentCourseGrade.aspx"
STUDENT_MARKS_URL = f"{CTT_BASE_URL}/Students/StudentCourseMarks.aspx"
STUDENT_TIMETABLE_URL = f"{CTT_BASE_URL}/Students/Timetables.aspx"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}


class CttDevExpressParser:
    """Parser chuyên dụng bóc tách bảng dữ liệu chuẩn DevExpress ASP.NET WebForms

    của CTT-SIS Bách Khoa (như trong kiến trúc của iLoveBK).
    """

    @staticmethod
    def parse_transcript_html(html_content: str) -> Dict[str, Any]:
        """Bóc tách HTML bảng điểm (từ StudentCourseGrade.aspx hoặc copy từ trình duyệt).

        Trả về cấu trúc chuẩn hóa:
        - transcript: List[Dict] (chi tiết từng môn học kèm học kỳ, điểm thành phần)
        - semesters: List[Dict] (thống kê GPA, CPA theo từng kỳ)
        - summary: Dict (tổng kết CPA, tín chỉ)
        """
        soup = BeautifulSoup(html_content, "html.parser")
        transcript: List[Dict[str, Any]] = []
        semesters: Dict[str, Dict[str, Any]] = {}
        current_semester = "Chưa rõ"

        # Tìm bảng DevExpress chính (gvResults_DXMainTable hoặc gvCourseMarks_DXMainTable)
        tables = soup.find_all("table", id=re.compile(r"(gvResults|gvCourseMarks|gvStudentProgram).*DXMainTable"))
        if not tables:
            # Fallback: tìm bất kỳ table nào chứa class dxgvTable hoặc table thông thường
            tables = soup.find_all("table", class_=re.compile(r"dxgvTable|table"))
            if not tables:
                tables = soup.find_all("table")

        for table in tables:
            rows = [row for row in table.find_all("tr") if row.find_parent("table") is table]
            for row in rows:
                row_classes = " ".join(row.get("class", []))
                text_content = row.get_text(" ", strip=True)

                # 1. Phát hiện hàng Group Header học kỳ (Ví dụ: "Học kỳ 2023.1", "Kỳ học 20231")
                sem_match = re.search(r"(?:Học kỳ|Kỳ học|Học kì)\s*[:\-]?\s*(\d{4}[.\-_]?\d?)", text_content, re.IGNORECASE)
                if sem_match:
                    current_semester = sem_match.group(1).replace("-", ".").replace("_", ".")
                    if current_semester not in semesters:
                        semesters[current_semester] = {
                            "semester": current_semester,
                            "courses": [],
                            "gpa": None,
                            "cpa": None,
                        }

                # 2. Phát hiện hàng tổng kết GPA/CPA của học kỳ
                gpa_match = re.search(r"GPA\s*[:\-]?\s*([0-9.]+)", text_content, re.IGNORECASE)
                cpa_match = re.search(r"CPA\s*[:\-]?\s*([0-9.]+)", text_content, re.IGNORECASE)
                if current_semester in semesters and (gpa_match or cpa_match):
                    if gpa_match:
                        try:
                            semesters[current_semester]["gpa"] = float(gpa_match.group(1))
                        except ValueError:
                            pass
                    if cpa_match:
                        try:
                            semesters[current_semester]["cpa"] = float(cpa_match.group(1))
                        except ValueError:
                            pass

                # 3. Phát hiện hàng dữ liệu môn học (DevExpress data row)
                cells = row.find_all(["td", "th"], recursive=False)
                if len(cells) < 4:
                    continue

                cell_texts = [c.get_text(strip=True) for c in cells]

                # Tìm vị trí mã học phần (Định dạng HUST: 2-3 chữ cái + 4 số, VD: ET2030, IT3080)
                code_idx = -1
                for idx, txt in enumerate(cell_texts):
                    if re.match(r"^[A-Z]{2,3}\d{4}[A-Z]?$", txt.upper()):
                        code_idx = idx
                        break

                if code_idx == -1:
                    continue

                code = cell_texts[code_idx].upper()
                name = cell_texts[code_idx + 1] if code_idx + 1 < len(cell_texts) else ""

                # The credit cell follows the course name. Never mistake an exam
                # score for credits when a course is non-credit or malformed.
                credits = None
                credit_idx = -1
                for idx in range(code_idx + 2, min(code_idx + 3, len(cell_texts))):
                    try:
                        val = float(cell_texts[idx].replace(",", "."))
                        if 0.0 <= val <= 30.0:
                            credits = val
                            credit_idx = idx
                            break
                    except ValueError:
                        continue

                # Tìm điểm chữ (A+, A, B+, B, C+, C, D+, D, F)
                letter_grade = ""
                for idx in range(len(cell_texts) - 1, max(code_idx, len(cell_texts) - 6), -1):
                    txt = cell_texts[idx].upper()
                    if txt in GRADE_TO_SCALE4:
                        letter_grade = txt
                        break

                # Tìm điểm quá trình và điểm thi (nếu có trong bảng chi tiết)
                midterm_grade: Optional[float] = None
                final_grade: Optional[float] = None
                numeric_candidates = []
                for idx in range(credit_idx + 1 if credit_idx != -1 else code_idx + 2, len(cell_texts)):
                    txt = cell_texts[idx].replace(",", ".")
                    try:
                        num = float(txt)
                        if 0.0 <= num <= 10.0:
                            numeric_candidates.append(num)
                    except ValueError:
                        continue

                if len(numeric_candidates) >= 2:
                    midterm_grade = numeric_candidates[0]
                    final_grade = numeric_candidates[1]
                elif len(numeric_candidates) == 1:
                    final_grade = numeric_candidates[0]

                numeric_scale4 = GRADE_TO_SCALE4.get(letter_grade, 0.0)
                is_passed = letter_grade in PASSING_GRADES

                grade_item = {
                    "code": code,
                    "name": name,
                    "credits": credits,
                    "semester": current_semester,
                    "letter_grade": letter_grade,
                    "numeric_grade": numeric_scale4,
                    "midterm_grade": midterm_grade,
                    "final_grade": final_grade,
                    "is_passed": is_passed,
                }
                transcript.append(grade_item)
                if current_semester in semesters:
                    semesters[current_semester]["courses"].append(code)

        # Tính toán tổng hợp nếu bảng điểm không có sẵn
        passed_courses = [c for c in transcript if c["is_passed"]]
        total_passed_credits = sum(c["credits"] or 0 for c in passed_courses)

        calc_points = sum(c["numeric_grade"] * c["credits"] for c in transcript if (c["credits"] or 0) > 0)
        calc_credits = sum(c["credits"] for c in transcript if (c["credits"] or 0) > 0)
        cpa = round(calc_points / calc_credits, 2) if calc_credits > 0 else 0.0

        return {
            "transcript": transcript,
            "semesters": list(semesters.values()),
            "total_credits_accumulated": total_passed_credits,
            "cpa": cpa,
            "total_courses": len(transcript),
        }


class CttScraper:
    """Crawler kết nối và xác thực trực tiếp với CTT-SIS Bách Khoa."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[requests.Session]]:
        """Retired: credentials and CAPTCHA must be entered on the official portal."""
        return False, "Hãy kết nối CTT bằng cửa sổ đăng nhập trường trong HUST Advisor.", None

    def fetch_student_grade_page(self, session: requests.Session) -> Tuple[bool, str]:
        """Compatibility reader; only accept a positively authenticated page."""
        from app.services.school_portal import authenticated_ctt_html
        try:
            for url in (STUDENT_GRADE_URL, STUDENT_MARKS_URL):
                resp = session.get(url, timeout=self.timeout)
                if authenticated_ctt_html(resp.url, resp.text, resp.status_code) and ctt_parser.parse_transcript_html(resp.text)["transcript"]:
                    return True, resp.text
            return False, "Không xác minh được phiên hoặc bảng điểm CTT."
        except requests.RequestException:
            return False, "Không kết nối được CTT. Vui lòng thử lại."


ctt_parser = CttDevExpressParser()
ctt_scraper = CttScraper()
