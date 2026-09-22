"""
Quy chế đào tạo và hằng số học tập Đại học Bách Khoa Hà Nội (HUST)
Áp dụng cho chương trình Cử nhân / Kỹ sư Điện tử Viễn thông (ET1)
"""

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

CREDIT_LIMITS = {
    0: {"min": 12, "max": 24, "summer_max": 8, "desc": "Bình thường"},
    1: {"min": 10, "max": 18, "summer_max": 6, "desc": "Cảnh cáo mức 1"},
    2: {"min": 8, "max": 14, "summer_max": 4, "desc": "Cảnh cáo mức 2"},
    3: {"min": 0, "max": 0, "summer_max": 0, "desc": "Cảnh cáo mức 3 (Buộc thôi học / Xét kỷ luật)"}
}

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
