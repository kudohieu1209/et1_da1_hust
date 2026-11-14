"""Dịch vụ hỗ trợ các tính năng mở rộng từ kiến trúc iLoveBK:
- Thời khóa biểu chính thức & Tạm thời (Timetable & Temp Timetable)
- Lịch thi & Phòng thi (Exam Schedule)
- Tra cứu học phí & Chuẩn đầu ra Tiếng Anh TOEIC
- Tra cứu danh sách bạn cùng lớp (Classmates)
- Đánh giá & Review học phần (Course Reviews)
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.schemas import (
    ClassmateItem,
    ClassmatesResponse,
    CourseReviewCreate,
    CourseReviewItem,
    ExamScheduleItem,
    ExamScheduleResponse,
    TimetableItem,
    TimetableResponse,
    ToeicResponse,
    TuitionItem,
    TuitionResponse,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
REVIEWS_FILE = REPO_ROOT / "data" / "course_reviews.json"

# Mẫu reviews thực tế cho sinh viên HUST
INITIAL_REVIEWS = [
    {
        "id": "rev-1",
        "course_code": "MI1111",
        "course_name": "Giải tích I",
        "rating": 4,
        "difficulty": "Khó",
        "attendance": "Có điểm danh",
        "comment": "Môn đại cương tiên quyết quan trọng. Nên làm hết bài tập trong sách bài tập thầy Nguyễn Đình Huy, ôn kỹ phần tích phân suy rộng và chuỗi số. Giữa kỳ thường dễ thở hơn cuối kỳ.",
        "author": "K66 - Điện tử",
        "created_at": "2024-10-15T08:30:00Z"
    },
    {
        "id": "rev-2",
        "course_code": "PH1110",
        "course_name": "Vật lý đại cương I",
        "rating": 3,
        "difficulty": "Rất khó",
        "attendance": "Thỉnh thoảng",
        "comment": "Lý thuyết rộng, phần cơ học và nhiệt học nhiều công thức. Chú ý thí nghiệm vật lý lấy trọn 1.0 điểm cộng, đừng để mất điểm thí nghiệm.",
        "author": "K67 - Cơ điện tử",
        "created_at": "2024-11-02T14:20:00Z"
    },
    {
        "id": "rev-3",
        "course_code": "ET3210",
        "course_name": "Kỹ thuật số",
        "rating": 5,
        "difficulty": "Trung bình",
        "attendance": "Có điểm danh",
        "comment": "Môn cơ sở ngành cực hay của viện Điện tử. Thầy cô dạy rất tâm huyết, phần bìa Karnaugh và thiết kế mạch tuần hoàn FSM nếu nắm chắc thì thi trắc nghiệm điểm A rất dễ.",
        "author": "K67 - ET1",
        "created_at": "2024-12-05T09:15:00Z"
    },
    {
        "id": "rev-4",
        "course_code": "IT1110",
        "course_name": "Tin học đại cương",
        "rating": 4,
        "difficulty": "Trung bình",
        "attendance": "Không điểm danh",
        "comment": "Học lập trình C. Điểm thực hành trên máy chiếm 30%, thi trắc nghiệm thuật toán và đọc code cuối kỳ. Nên tự code bài tập trên HackerEarth hoặc LeetCode trước.",
        "author": "K68 - IT1",
        "created_at": "2025-01-10T16:45:00Z"
    },
    {
        "id": "rev-5",
        "course_code": "ET3220",
        "course_name": "Tín hiệu và hệ thống",
        "rating": 4,
        "difficulty": "Khó",
        "attendance": "Có điểm danh",
        "comment": "Toán nhiều: biến đổi Fourier, Laplace, Z. Nắm chắc bảng biến đổi và tính chất tích chập. Đề thi cuối kỳ thường theo dạng đề cương ôn tập.",
        "author": "K67 - ET-E9",
        "created_at": "2025-02-18T11:00:00Z"
    }
]


class ExtraStudentServices:
    def __init__(self):
        self._ensure_reviews_storage()

    def _ensure_reviews_storage(self):
        if not REVIEWS_FILE.exists():
            try:
                REVIEWS_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
                    json.dump(INITIAL_REVIEWS, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Could not initialize reviews file: {e}")

    def _load_reviews(self) -> List[Dict[str, Any]]:
        if not REVIEWS_FILE.exists():
            return INITIAL_REVIEWS
        try:
            with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return INITIAL_REVIEWS

    def _save_reviews(self, reviews: List[Dict[str, Any]]):
        try:
            with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
                json.dump(reviews, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving reviews: {e}")

    def _section(self, student_id: str, key: str) -> dict:
        from app.services.data_loader import data_loader
        profile_key = data_loader.profiles.find_key(student_id)
        profile = data_loader.profiles.get(profile_key) if profile_key else None
        if not profile or profile.get("info", {}).get("student_id") != student_id:
            raise ValueError("Không tìm thấy hồ sơ của tài khoản đang đăng nhập.")
        from app.services.ctt_sections import normalize_saved_section
        saved = profile.get("school_services", {}).get(key)
        if key == 'certificates':
            from app.services.curriculum_repository import curriculum_repository
            from app.services.non_credit_coursework import with_coursework
            saved = with_coursework(saved or {'records': [], 'tables': [], 'requirements': {}}, profile, curriculum_repository.resolve_profile(profile))
        if saved:
            return normalize_saved_section(key, saved)
        return {
            "status": "not_synced", "message": "Mục này chưa được đồng bộ từ CTT. Hãy kết nối lại tài khoản trường.",
            "tables": [], "records": [],
        }

    def get_sync_summary(self, student_id: str) -> dict:
        keys = ("english", "timetable", "temporary_timetable", "exams", "classmates", "tuition", "warning", "certificates")
        return {"sections": {key: self._section(student_id, key) for key in keys}}

    def get_timetable(self, student_id: str, profile=None) -> TimetableResponse:
        section = self._section(student_id, "timetable")
        temporary = self._section(student_id, "temporary_timetable")
        items = list(section.get("records", [])) + list(temporary.get("records", []))
        return TimetableResponse(**{**section, "tables": section.get("tables", []) + temporary.get("tables", []),
            "items": items, "total_classes": len(items), "has_temp": any(x.get("is_temp") for x in items)})

    def get_exam_schedule(self, student_id: str) -> ExamScheduleResponse:
        section = self._section(student_id, "exams")
        return ExamScheduleResponse(**{**section, "exams": section.get("records", []), "total": len(section.get("records", []))})

    def get_tuition(self, student_id: str) -> TuitionResponse:
        section = self._section(student_id, "tuition")
        semesters = section.get("records", [])
        debts = [row.get("debt") for row in semesters]
        total = sum(debts) if debts and all(x is not None for x in debts) else None
        return TuitionResponse(**{**section, "student_id": student_id, "current_debt": total, "semesters": semesters})

    def get_toeic_status(self, student_id: str, program_code: str = "") -> ToeicResponse:
        section = self._section(student_id, "english")
        records = section.get("records", [])
        # Prefer the latest explicitly dated result; retain full history separately.
        dated = [row for row in records if row.get("test_date")]
        latest = max(dated, key=lambda row: row["test_date"]) if dated else records[0] if len(records) == 1 else {}
        return ToeicResponse(**{**section, "student_id": student_id, "score": latest.get("score"),
            "test_date": latest.get("test_date"), "certificate_type": latest.get("certificate_type", "")})

    def get_classmates(self, class_code: str, student_id: str) -> ClassmatesResponse:
        section = self._section(student_id, "classmates")
        actual_code = section.get("class_code") or "current"
        if class_code and class_code != actual_code:
            raise ValueError("Lớp này chưa có trong dữ liệu CTT đã đồng bộ của bạn.")
        students = section.get("records", [])
        return ClassmatesResponse(**{**section, "class_code": actual_code, "course_name": section.get("course_name", ""),
            "lecturer": section.get("lecturer", ""), "room": section.get("room", ""), "students": students,
            "total": len(students), "available_classes": [{"code": actual_code, "label": section.get("class_name") or "Danh sách lớp trên CTT"}] if students else []})

    # ==================== 6. COURSE REVIEWS ====================
    def get_course_reviews(self, course_code: Optional[str] = None) -> List[CourseReviewItem]:
        """Lấy danh sách review môn học, có thể lọc theo mã môn."""
        raw = self._load_reviews()
        if course_code:
            code_upper = course_code.strip().upper()
            raw = [r for r in raw if r.get("course_code", "").upper() == code_upper]
        return [CourseReviewItem(**r) for r in raw]

    def add_course_review(self, course_code: str, data: CourseReviewCreate, author_name: str = "Sinh viên HUST") -> CourseReviewItem:
        """Thêm review mới cho môn học."""
        raw = self._load_reviews()
        item = {
            "id": f"rev-{uuid.uuid4().hex[:8]}",
            "course_code": course_code.strip().upper(),
            "course_name": None,
            "rating": data.rating,
            "difficulty": data.difficulty,
            "attendance": data.attendance,
            "comment": data.comment,
            "author": data.author or author_name,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        raw.insert(0, item)
        self._save_reviews(raw)
        return CourseReviewItem(**item)


extra_student_services = ExtraStudentServices()
