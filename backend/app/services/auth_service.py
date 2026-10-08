import json
import os
import re
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from app.core.config import DATA_DIR, STUDENTS_DIR
from app.core.hust_rules import GRADE_TO_SCALE4, parse_grade_from_line
from app.services.data_loader import data_loader
from app.services.curriculum_repository import CurriculumNotFoundError

USERS_DIR = DATA_DIR / "users"
USERS_DIR.mkdir(parents=True, exist_ok=True)

class AuthService:
    def __init__(self):
        self._seed_default_users()

    def _seed_default_users(self):
        """Khởi tạo các tài khoản sinh viên Demo mặc định nếu chưa có"""
        demo_accounts = [
            {
                "student_id": "20220001",
                "student_name": "Mai Duy Hiếu",
                "class_name": "Điện tử 02 - K67",
                "program_name": "Kỹ thuật Điện tử - Viễn thông 2022",
                "persona": "Năm 4 • Cần kéo CPA lên Khá (≥2.50) • Chuẩn bị ĐATN",
                "badge": "Pilot Benchmark",
                "source_file": STUDENTS_DIR / "20220001.json"
            },
            {
                "student_id": "20223123",
                "student_name": "Trần Thị Minh Trang",
                "class_name": "Điện tử 01 - K67",
                "program_name": "Kỹ thuật Điện tử - Viễn thông 2022",
                "persona": "Năm 4 • Học lực Giỏi (CPA 3.78) • Đủ điều kiện ĐATN • Định hướng Vi mạch",
                "badge": "Học lực Giỏi",
                "source_file": STUDENTS_DIR / "20223123.json"
            },
            {
                "student_id": "20224567",
                "student_name": "Lê Hoàng Long",
                "class_name": "Điện tử 03 - K67",
                "program_name": "Kỹ thuật Điện tử - Viễn thông 2022",
                "persona": "Cảnh báo Mức 2 (CPA 1.39) • Khống chế max 14 TC • Bị chặn môn tiên quyết",
                "badge": "Cảnh báo Mức 2",
                "source_file": STUDENTS_DIR / "20224567.json"
            },
            {
                "student_id": "20231890",
                "student_name": "Phạm Quang Huy",
                "class_name": "Điện tử 01 - K68",
                "program_name": "Kỹ thuật Điện tử - Viễn thông 2023",
                "persona": "Năm 3 (K68) • CPA 2.70 • Hoàn thành cơ sở ngành • Chuẩn bị chọn chuyên ngành",
                "badge": "Sinh viên K68",
                "source_file": STUDENTS_DIR / "20231890.json"
            }
        ]

        for acc in demo_accounts:
            user_file = USERS_DIR / f"{acc['student_id']}.json"
            if not user_file.exists():
                # Nạp từ file mẫu nếu có
                if acc["source_file"].exists():
                    with open(acc["source_file"], "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = {
                        "info": {
                            "program_id": "1654",
                            "program_name": acc["program_name"],
                            "student_id": acc["student_id"],
                            "student_name": acc["student_name"],
                            "class_name": acc["class_name"],
                            "badge": acc["badge"],
                            "persona": acc["persona"]
                        },
                        "total_courses_completed": 0,
                        "passed_courses": [],
                        "failed_courses": [],
                        "transcript": []
                    }
                data["password"] = "123456" # Mật khẩu demo mặc định
                data["is_demo"] = True
                data["created_at"] = datetime.datetime.now().isoformat()
                with open(user_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

    def register(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Đăng ký tài khoản sinh viên mới.
        Tài khoản mới sẽ có bảng điểm hoàn toàn trống (Empty State) để sinh viên tự thêm.
        """
        student_id = str(payload.get("student_id", "")).strip()
        student_name = payload.get("student_name", "").strip()
        password = payload.get("password", "").strip()
        class_name = payload.get("class_name", "K68 Bách Khoa").strip()
        program_name = payload.get("program_name", "Kỹ thuật Điện tử - Viễn thông").strip()

        if not student_id or not student_name or not password:
            return {
                "success": False,
                "message": "Vui lòng điền đầy đủ MSSV, Họ và tên, và Mật khẩu!"
            }

        user_file = USERS_DIR / f"{student_id}.json"
        if user_file.exists():
            return {
                "success": False,
                "message": f"Tài khoản sinh viên MSSV {student_id} đã tồn tại! Vui lòng chọn Đăng nhập."
            }

        new_user = {
            "info": {
                "program_id": "1654",
                "program_name": program_name,
                "student_id": student_id,
                "student_name": student_name,
                "class_name": class_name,
                "badge": "Sinh viên Mới",
                "persona": f"Sinh viên {student_name} ({class_name}) - Hồ sơ mới khởi tạo"
            },
            "password": password,
            "is_demo": False,
            "created_at": datetime.datetime.now().isoformat(),
            "total_courses_completed": 0,
            "passed_courses": [],
            "failed_courses": [],
            "transcript": []
        }

        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(new_user, f, ensure_ascii=False, indent=2)

        # Lưu đồng thời vào students/ để đồng bộ
        with open(STUDENTS_DIR / f"{student_id}.json", "w", encoding="utf-8") as f:
            json.dump(new_user, f, ensure_ascii=False, indent=2)

        # Kích hoạt đúng snapshot CTĐT ngay sau khi đăng ký. Nếu chương trình
        # hoặc khóa chưa được hỗ trợ, không ghi đè snapshot đang hoạt động.
        try:
            data_loader.load_student_profile(student_id)
        except (CurriculumNotFoundError, FileNotFoundError):
            data_loader.student_profile = new_user
            data_loader.current_student_id = student_id

        return {
            "success": True,
            "message": f"Chúc mừng bạn {student_name}! Tài khoản đã được tạo thành công.",
            "user": self._clean_user_data(data_loader.get_student_profile())
        }

    def login(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Đăng nhập bằng MSSV và Mật khẩu.
        """
        student_id = str(payload.get("student_id", "")).strip()
        password = payload.get("password", "").strip()

        if not student_id or not password:
            return {
                "success": False,
                "message": "Vui lòng nhập MSSV và Mật khẩu!"
            }

        user_file = USERS_DIR / f"{student_id}.json"
        if not user_file.exists():
            return {
                "success": False,
                "message": f"Không tìm thấy tài khoản MSSV {student_id}! Vui lòng Đăng ký."
            }

        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        if user_data.get("password") != password:
            return {
                "success": False,
                "message": "Mật khẩu không chính xác! (Gợi ý tài khoản demo: mật khẩu là 123456)"
            }

        # Đăng nhập phải đồng thời kích hoạt curriculum tương ứng; nếu chỉ
        # thay student_profile thì audit/rule engine có thể dùng dữ liệu cũ.
        try:
            data_loader.load_student_profile(student_id)
            active_user = data_loader.get_student_profile()
        except (CurriculumNotFoundError, FileNotFoundError):
            data_loader.student_profile = user_data
            data_loader.current_student_id = student_id
            active_user = user_data

        return {
            "success": True,
            "message": f"Đăng nhập thành công! Chào mừng {active_user.get('info', {}).get('student_name')}.",
            "user": self._clean_user_data(active_user)
        }

    def get_current_user(self, student_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Lấy thông tin tài khoản hiện tại"""
        sid = student_id or getattr(data_loader, "current_student_id", "20220001")
        user_file = USERS_DIR / f"{sid}.json"
        if user_file.exists():
            with open(user_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return self._clean_user_data(data)
        return self._clean_user_data(data_loader.get_student_profile())

    def update_transcript(self, student_id: str, raw_text: str, courses: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Phân tích và cập nhật bảng điểm CTT cho tài khoản sinh viên.
        """
        user_file = USERS_DIR / f"{student_id}.json"
        if not user_file.exists():
            return {
                "success": False,
                "message": f"Không tìm thấy tài khoản sinh viên {student_id}!"
            }

        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        transcript = []
        passed_courses = []
        failed_courses = []

        if raw_text and raw_text.strip():
            lines = raw_text.splitlines()
            for line in lines:
                code_match = re.search(r'\b([A-Z]{2,3}\d{4}[A-Z]?)\b', line.upper())
                if code_match:
                    code = code_match.group(1)
                    grade_letter = parse_grade_from_line(line[code_match.end():])
                    if grade_letter is None:
                        # Không tự gán điểm cho dòng chưa có điểm chữ.
                        continue
                    
                    c_info = data_loader.get_course(code)
                    c_name = c_info.get("name", f"Học phần {code}") if c_info else f"Học phần {code}"
                    credits = float(c_info.get("credits", 3.0) if c_info else 3.0)
                    
                    scale4 = GRADE_TO_SCALE4.get(grade_letter, 0.0)
                    is_passed = (grade_letter != "F")
                    
                    entry = {
                        "code": code,
                        "name": c_name,
                        "credits": credits,
                        "letter_grade": grade_letter,
                        "numeric_grade": scale4,
                        "is_passed": is_passed
                    }
                    transcript.append(entry)
                    if is_passed:
                        passed_courses.append(entry)
                    else:
                        failed_courses.append(entry)

        elif courses:
            for item in courses:
                code = item.get("code")
                if code:
                    grade_letter = (item.get("letter_grade") or "").strip().upper()
                    if grade_letter not in GRADE_TO_SCALE4:
                        continue
                    scale4 = GRADE_TO_SCALE4.get(grade_letter, 0.0)
                    is_passed = (grade_letter != "F")
                    c_info = data_loader.get_course(code)
                    c_name = item.get("name") or (c_info.get("name") if c_info else f"Học phần {code}")
                    credits = float(item.get("credits") or (c_info.get("credits", 3.0) if c_info else 3.0))
                    
                    entry = {
                        "code": code,
                        "name": c_name,
                        "credits": credits,
                        "letter_grade": grade_letter,
                        "numeric_grade": scale4,
                        "is_passed": is_passed
                    }
                    transcript.append(entry)
                    if is_passed:
                        passed_courses.append(entry)
                    else:
                        failed_courses.append(entry)

        user_data["transcript"] = transcript
        user_data["passed_courses"] = passed_courses
        user_data["failed_courses"] = failed_courses
        user_data["total_courses_completed"] = len(passed_courses)

        # Lưu lại file
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)

        with open(STUDENTS_DIR / f"{student_id}.json", "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)

        # Cập nhật DataLoader
        data_loader.student_profile = user_data
        data_loader.current_student_id = student_id

        from app.services.student_service import student_service
        audit = student_service.audit_degree()

        return {
            "success": True,
            "message": f"Đã nạp và tính toán thành công bảng điểm gồm {len(transcript)} học phần!",
            "user": self._clean_user_data(user_data),
            "audit": audit
        }

    def list_demo_accounts(self) -> List[Dict[str, Any]]:
        """Lấy danh sách các tài khoản Demo để đăng nhập nhanh 1-click"""
        demos = []
        for sid in ["20220001", "20223123", "20224567", "20231890"]:
            fpath = USERS_DIR / f"{sid}.json"
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    u = json.load(f)
                    info = u.get("info", {})
                    demos.append({
                        "student_id": sid,
                        "student_name": info.get("student_name"),
                        "class_name": info.get("class_name"),
                        "badge": info.get("badge"),
                        "persona": info.get("persona"),
                        "default_password": "123456",
                        "courses_count": len(u.get("passed_courses", []))
                    })
        return demos

    def _clean_user_data(self, user_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Loại bỏ mật khẩu trước khi trả về client"""
        clean = dict(user_dict)
        clean.pop("password", None)
        return clean

# Singleton instance
auth_service = AuthService()
