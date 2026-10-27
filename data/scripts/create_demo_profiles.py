import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STUDENTS_DIR = BASE_DIR / "processed" / "students"
STUDENTS_DIR.mkdir(parents=True, exist_ok=True)

# Load existing base profile (20220001)
base_file = BASE_DIR / "processed" / "student_profile.json"
with open(base_file, "r", encoding="utf-8") as f:
    base_profile = json.load(f)

# 1. Profile 20220001 (Sinh viên Demo - K67 Benchmark)
profile_hieu = json.loads(json.dumps(base_profile))
profile_hieu["info"]["student_id"] = "20220001"
profile_hieu["info"]["student_name"] = "Sinh viên Demo"
profile_hieu["info"]["class_name"] = "Điện tử 02 - K67"
profile_hieu["info"]["badge"] = "Pilot Benchmark"
profile_hieu["info"]["persona"] = "Năm 4 • Cần kéo CPA lên Khá (≥2.50) • Chuẩn bị ĐATN"

with open(STUDENTS_DIR / "20220001.json", "w", encoding="utf-8") as f:
    json.dump(profile_hieu, f, ensure_ascii=False, indent=2)

# 2. Profile 20223123 (Trần Thị Minh Trang - Giỏi K67, CPA 3.42, 112 TC, đủ ĐATN)
profile_trang = json.loads(json.dumps(base_profile))
profile_trang["info"] = {
    "program_id": "1654",
    "program_name": "Kỹ thuật Điện tử - Viễn thông 2022",
    "student_id": "20223123",
    "student_name": "Trần Thị Minh Trang",
    "class_name": "Điện tử 01 - K67",
    "badge": "Học lực Giỏi",
    "persona": "Năm 4 • Học lực Giỏi (CPA 3.42) • Đủ điều kiện ĐATN • Định hướng Vi mạch"
}
# Nâng điểm các môn sang A, B+
for course in profile_trang["passed_courses"]:
    if course["letter_grade"] in ["C", "C+", "D", "D+"]:
        course["letter_grade"] = "B+" if course["code"].startswith("MI") else "A"
        course["numeric_grade"] = 3.5 if course["letter_grade"] == "B+" else 4.0

# Bổ sung thêm môn Thực tập kỹ thuật ET3270 để đủ điều kiện ĐATN
profile_trang["passed_courses"].append({
    "code": "ET3270",
    "name": "Thực tập kỹ thuật",
    "credits": 2.0,
    "letter_grade": "A",
    "numeric_grade": 4.0,
    "is_passed": True
})
profile_trang["passed_courses"].append({
    "code": "ET4340",
    "name": "Thiết kế VLSI",
    "credits": 3.0,
    "letter_grade": "A",
    "numeric_grade": 4.0,
    "is_passed": True
})
profile_trang["transcript"] = list(profile_trang["passed_courses"])
profile_trang["failed_courses"] = []
profile_trang["total_courses_completed"] = len(profile_trang["passed_courses"])

with open(STUDENTS_DIR / "20223123.json", "w", encoding="utf-8") as f:
    json.dump(profile_trang, f, ensure_ascii=False, indent=2)

# 3. Profile 20224567 (Lê Hoàng Long - K67 Cảnh báo Mức 2, CPA 1.38, nợ F Giải tích 1-2, Cấu kiện)
profile_long = json.loads(json.dumps(base_profile))
profile_long["info"] = {
    "program_id": "1654",
    "program_name": "Kỹ thuật Điện tử - Viễn thông 2022",
    "student_id": "20224567",
    "student_name": "Lê Hoàng Long",
    "class_name": "Điện tử 03 - K67",
    "badge": "Cảnh báo Mức 2",
    "persona": "Cảnh báo Mức 2 (CPA 1.38) • Khống chế max 14 TC • Bị chặn môn tiên quyết",
    # Mức cảnh báo lấy từ CTT. Điều 19 QĐ 5445 xét theo TC không đạt từng học
    # kỳ, dữ liệu demo không có học kỳ nên khai báo trực tiếp.
    "warning_level": 2,
}
# Giảm điểm thành D, D+ và tạo môn nợ F
long_passed = []
long_failed = []
long_transcript = []

for course in profile_long["passed_courses"][:30]:
    c_copy = dict(course)
    if c_copy["code"] in ["MI1111", "MI1121", "ET2040", "PH1111"]:
        # Môn rớt
        c_copy["letter_grade"] = "F"
        c_copy["numeric_grade"] = 0.0
        c_copy["is_passed"] = False
        long_failed.append(c_copy)
        long_transcript.append(c_copy)
    else:
        # Môn qua điểm thấp
        if c_copy["letter_grade"] in ["A", "B+", "B"]:
            c_copy["letter_grade"] = "D+"
            c_copy["numeric_grade"] = 1.5
        long_passed.append(c_copy)
        long_transcript.append(c_copy)

profile_long["passed_courses"] = long_passed
profile_long["failed_courses"] = long_failed
profile_long["transcript"] = long_transcript
profile_long["total_courses_completed"] = len(long_passed)

with open(STUDENTS_DIR / "20224567.json", "w", encoding="utf-8") as f:
    json.dump(profile_long, f, ensure_ascii=False, indent=2)

# 4. Profile 20231890 (Phạm Quang Huy - K68 Năm 3, CPA 2.85, 68 TC, vừa xong khối cơ sở)
profile_huy = json.loads(json.dumps(base_profile))
profile_huy["info"] = {
    "program_id": "1654",
    "program_name": "Kỹ thuật Điện tử - Viễn thông 2023",
    "student_id": "20231890",
    "student_name": "Phạm Quang Huy",
    "class_name": "Điện tử 01 - K68",
    "badge": "Sinh viên K68",
    "persona": "Năm 3 (K68) • CPA 2.85 • Hoàn thành cơ sở ngành • Chuẩn bị chọn chuyên ngành"
}
profile_huy["info"]["curriculum_version"] = "2023"
# Chỉ giữ lại các môn học năm 1 và năm 2 (kỳ 1 đến kỳ 4)
huy_courses = []
for course in base_profile["passed_courses"]:
    if course["code"].startswith(("SSH", "PE", "MI1", "PH1", "IT1", "EM", "ET2")):
        c_h = dict(course)
        if c_h["letter_grade"] in ["D", "D+"]:
            c_h["letter_grade"] = "B"
            c_h["numeric_grade"] = 3.0
        huy_courses.append(c_h)

profile_huy["passed_courses"] = huy_courses
profile_huy["transcript"] = list(huy_courses)
profile_huy["failed_courses"] = []
profile_huy["total_courses_completed"] = len(huy_courses)

with open(STUDENTS_DIR / "20231890.json", "w", encoding="utf-8") as f:
    json.dump(profile_huy, f, ensure_ascii=False, indent=2)

print("Đã tạo thành công 4 hồ sơ sinh viên demo trong data/processed/students/!")
