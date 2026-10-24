"""
Quy chế đào tạo và hằng số học tập Đại học Bách Khoa Hà Nội (HUST)
Áp dụng cho chương trình Cử nhân / Kỹ sư Điện tử Viễn thông (ET1)
"""

import re
from typing import Any, Dict, Optional

GRADE_TO_SCALE4 = {
    "A+": 4.0,
    "A": 4.0,
    "B+": 3.5,
    "B": 3.0,
    "C+": 2.5,
    "C": 2.0,
    "D+": 1.5,
    "D": 1.0,
    "F": 0.0
}

PASSING_GRADES = {"A+", "A", "B+", "B", "C+", "C", "D+", "D"}

# QĐ 5445/QĐ-ĐHBK (Quy chế đào tạo 2025):
# - Điều 11.2a: SV không bị cảnh báo đăng ký 12–24 TC kỳ chính, tối đa 8 TC kỳ hè.
# - Điều 19.2a: chỉ SV cảnh báo từ mức 2 trở lên bị hạn chế còn 8–14 TC kỳ chính
#   (CTĐT chuẩn; ELITECH/hợp tác quốc tế là 8–18 TC). Mức 1 không bị hạn chế.
CREDIT_LIMITS = {
    0: {"min": 12, "max": 24, "summer_max": 8, "desc": "Bình thường"},
    1: {"min": 12, "max": 24, "summer_max": 8, "desc": "Cảnh báo học tập mức 1"},
    2: {"min": 8, "max": 14, "summer_max": 8, "desc": "Cảnh báo học tập mức 2 (hạn chế khối lượng học tập)"},
    3: {"min": 8, "max": 14, "summer_max": 8, "desc": "Cảnh báo học tập mức 3 (lần thứ hai liên tiếp sẽ bị buộc thôi học)"}
}

# Điều 19.1c: số TC nợ đọng từ đầu khóa lớn hơn 24 -> cảnh báo mức 3.
MAX_DEBT_CREDITS_BEFORE_LEVEL3 = 24

_GRADE_TOKEN = re.compile(r"(?<![A-Z0-9])([ABCD]\+?|F)\s*$")


def parse_grade_from_line(line: str) -> Optional[str]:
    """Lấy điểm chữ từ một dòng bảng điểm copy từ CTT.

    Điểm chữ nằm ở cuối dòng, sau tên học phần, nên lấy token cuối cùng để
    tên như "Ngôn ngữ C" không bị đọc thành điểm C. Trả về None nếu không có
    điểm; không được tự gán điểm thay sinh viên.
    """
    matches = _GRADE_TOKEN.findall(line.upper())
    return matches[-1] if matches else None


def debt_credits(profile: Dict[str, Any]) -> float:
    """Số TC nợ đọng: học phần có điểm F mà chưa học lại đạt."""
    passed = {item["code"] for item in profile.get("passed_courses", [])}
    owed: Dict[str, float] = {}
    for item in profile.get("failed_courses", []):
        if item["code"] not in passed:
            owed[item["code"]] = float(item.get("credits", 0.0))
    return sum(owed.values())


def assess_academic_warning(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Xác định mức cảnh báo học tập theo Điều 19 QĐ 5445.

    Mức 1/2 phụ thuộc số TC không đạt trong từng học kỳ (Điều 19.1a,b), mà
    bảng điểm hiện không có thông tin học kỳ. Vì vậy ưu tiên mức cảnh báo
    khai báo trong hồ sơ (lấy từ CTT); nếu không có thì chỉ áp dụng được
    quy tắc nợ đọng > 24 TC (Điều 19.1c).
    """
    owed = debt_credits(profile)
    declared = profile.get("info", {}).get("warning_level")
    if declared is not None and str(declared).strip() != "":
        level = max(0, min(3, int(declared)))
        basis = "Mức cảnh báo khai báo trong hồ sơ (theo CTT)"
    elif owed > MAX_DEBT_CREDITS_BEFORE_LEVEL3:
        level = 3
        basis = f"Nợ đọng {owed:g} TC > {MAX_DEBT_CREDITS_BEFORE_LEVEL3} TC (Điều 19.1c QĐ 5445)"
    else:
        level = None
        basis = (
            "Không có mức cảnh báo trong hồ sơ; bảng điểm chưa có thông tin học kỳ "
            "nên chưa xét được Điều 19.1a,b"
        )
    return {"level": level, "basis": basis, "debt_credits": owed, "status": "unverified" if level is None else "determined"}


def credit_limits_for_warning(warning: Dict[str, Any]) -> Dict[str, Any]:
    """Use a conservative planning cap until the student's warning level is known."""
    if warning["level"] is None:
        return {**CREDIT_LIMITS[2], "is_provisional": True,
                "desc": "Hạn mức lập kế hoạch tạm thời; cần đối chiếu mức cảnh báo trên CTT"}
    return {**CREDIT_LIMITS[warning["level"]], "is_provisional": False}

# Academic policy constants belong here. Curriculum-specific totals (126, 132,
# ...) are loaded from the matching versioned curriculum dataset.
MIN_GRADUATION_CPA = 2.0

# Xếp loại học lực và tốt nghiệp theo Quy chế Đào tạo ĐHBK Hà Nội (thang 4.0)
def get_academic_classification(cpa: float) -> dict:
    if cpa >= 3.60:
        return {"rank": "Xuất sắc", "color": "#10b981", "min_cpa": 3.60, "desc": "CPA ≥ 3.60"}
    elif cpa >= 3.20:
        return {"rank": "Giỏi", "color": "#38bdf8", "min_cpa": 3.20, "desc": "3.20 ≤ CPA < 3.60"}
    elif cpa >= 2.50:
        return {"rank": "Khá", "color": "#818cf8", "min_cpa": 2.50, "desc": "2.50 ≤ CPA < 3.20"}
    elif cpa >= 2.00:
        return {"rank": "Trung bình", "color": "#f59e0b", "min_cpa": 2.00, "desc": "2.00 ≤ CPA < 2.50 (Đủ điều kiện tốt nghiệp)"}
    elif cpa >= 1.00:
        return {"rank": "Yếu", "color": "#ef4444", "min_cpa": 1.00, "desc": "1.00 ≤ CPA < 2.00 (Chưa đủ chuẩn tốt nghiệp)"}
    else:
        return {"rank": "Kém", "color": "#dc2626", "min_cpa": 0.0, "desc": "CPA < 1.00"}
