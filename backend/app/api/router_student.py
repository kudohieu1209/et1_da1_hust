from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime, timezone
from starlette.concurrency import run_in_threadpool
from app.auth.dependencies import current_student, student_scope
from app.services.student_service import student_service
from app.engine.recommender import course_recommender
from app.services.data_loader import data_loader
from app.services.curriculum_repository import CurriculumNotFoundError
from app.services.student_memory import student_memory
from app.services.campus_service import campus_service
from app.services.extra_student_services import extra_student_services
from app.models.schemas import (
    AdvisingMemoryUpdate,
    CampusLocationItem,
    CampusLocationResponse,
    ClassmatesResponse,
    CourseImprovementResponse,
    CourseReviewCreate,
    CourseReviewItem,
    CttHtmlParseRequest,
    DegreeAuditResponse,
    ExamScheduleResponse,
    ProfileDisplayUpdate,
    RecommendationRequest,
    RecommendationResponse,
    TimetableResponse,
    ToeicResponse,
    TranscriptImportRequest,
    TuitionResponse,
)

# Mọi endpoint chạy trong scope hồ sơ của sinh viên đang đăng nhập (cookie phiên).
router = APIRouter(
    prefix="/api/student",
    tags=["Student & Degree Audit"],
    dependencies=[Depends(student_scope)],
)


@router.get("/memory")
def get_advising_memory(student_id: str = Depends(current_student)):
    return student_memory.get(student_id)


@router.put("/memory")
def update_advising_memory(payload: AdvisingMemoryUpdate, student_id: str = Depends(current_student)):
    if payload.target_track and payload.target_track not in {track["id"] for track in data_loader.get_module_tracks()}:
        raise HTTPException(status_code=422, detail="Mô-đun không thuộc CTĐT hiện tại của bạn.")
    return student_memory.save(student_id, payload, data_loader.get_program())


@router.delete("/memory", status_code=204)
def delete_advising_memory(student_id: str = Depends(current_student)):
    student_memory.delete(student_id)

@router.get("/profile")
def get_student_profile():
    """Thông tin và bảng điểm của sinh viên đang đăng nhập."""
    return student_service.get_profile()

@router.post("/profile/update")
def update_student_profile(payload: ProfileDisplayUpdate, student_id: str = Depends(current_student)):
    """Cập nhật tên hiển thị và ảnh đại diện. MSSV/lớp/CTĐT không sửa tay được."""
    try:
        return student_service.update_profile(payload.model_dump(exclude_unset=True), student_id)
    except CurriculumNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.get("/audit", response_model=DegreeAuditResponse)
def get_degree_audit():
    """Đánh giá chi tiết tiến độ học tập (Degree Audit) và điều kiện tốt nghiệp Bách Khoa"""
    audit = student_service.audit_degree()
    return DegreeAuditResponse(**audit)

@router.post("/import")
def import_student_transcript(payload: TranscriptImportRequest, student_id: str = Depends(current_student)):
    """Thay bảng điểm của sinh viên đang đăng nhập bằng nội dung copy từ CTT."""
    try:
        return student_service.import_transcript(payload.model_dump(exclude_unset=True), student_id)
    except (CurriculumNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.get("/tracks")
def get_available_tracks():
    """Danh sách các mô-đun lấy từ CTĐT của sinh viên."""
    return {"tracks": data_loader.get_module_tracks()}

@router.post("/recommend", response_model=RecommendationResponse)
def recommend_courses(req: RecommendationRequest):
    """Đề xuất danh sách học phần kỳ tiếp theo theo định hướng chuyên ngành."""
    try:
        rec = course_recommender.recommend(
            target_track=req.target_track,
            max_credits=req.max_credits,
            is_summer=req.is_summer_term or False
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RecommendationResponse(**rec)


@router.post("/sync-ctt")
def sync_ctt_transcript(student_id: str = Depends(current_student)):
    """Old clients must switch to the verified, browser-based CTT connection."""
    raise HTTPException(status_code=410, detail="Hãy chọn Kết nối tài khoản trường để đồng bộ bảng điểm; không gửi mật khẩu CTT vào ứng dụng.")


@router.post("/parse-ctt-html")
def parse_ctt_html(payload: CttHtmlParseRequest, student_id: str = Depends(current_student)):
    """Nạp bảng điểm từ mã nguồn HTML DevExpress copy từ trang CTT (An toàn bảo mật 100%)."""
    try:
        return student_service.import_transcript({"raw_text": payload.html_content}, student_id)
    except (ValueError, CurriculumNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/improve-courses", response_model=CourseImprovementResponse)
def get_course_improvements(student_id: str = Depends(current_student)):
    """Gợi ý các môn điểm thấp (D, D+, F) cần học cải thiện và dự báo mức tăng CPA."""
    res = student_service.get_course_improvements(student_id)
    return CourseImprovementResponse(**res)


@router.get("/campus-locations", response_model=CampusLocationResponse)
def get_campus_locations():
    """Danh sách các tòa nhà, giảng đường, tiện ích trong khuôn viên Bách Khoa."""
    locs = campus_service.get_all_locations()
    return CampusLocationResponse(locations=locs, total=len(locs))


@router.get("/campus-directions")
def get_campus_direction(query: str):
    """Tìm địa điểm và nhận liên kết chỉ đường Google Maps trong khuôn viên HUST."""
    loc = campus_service.find_location(query)
    if not loc:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy địa điểm '{query}' trong khuôn viên trường.")
    return {
        "location": loc,
        "direction_text": campus_service.format_direction_reply(loc),
    }


@router.get("/timetable", response_model=TimetableResponse)
def get_student_timetable(student_id: str = Depends(current_student)):
    """Thời khóa biểu chính thức và thời khóa biểu tạm thời (SIS Temp)."""
    return extra_student_services.get_timetable(student_id)


@router.get("/exams", response_model=ExamScheduleResponse)
def get_student_exams(student_id: str = Depends(current_student)):
    """Lịch thi kết thúc học phần, phòng thi và số báo danh."""
    return extra_student_services.get_exam_schedule(student_id)


class ImportedExam(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    course_code: str = Field(pattern=r"^[A-Z]{2,3}[0-9]{4}[A-Z]?$")
    course_name: str = Field("", max_length=200)
    exam_date: date
    exam_time: str = Field(..., min_length=1, max_length=40)
    room: str = Field("", max_length=100)
    class_code: str = Field("", max_length=40)
    exam_type: str = Field("", max_length=100)
    notes: str = Field("", max_length=300)


class ExamImport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exams: list[ImportedExam] = Field(..., min_length=1, max_length=500)


@router.post("/exams/preview")
async def preview_exam_file(file: UploadFile = File(...), student_id: str = Depends(current_student)):
    from app.services.exam_import import preview_exam_pdf
    try:
        content = await file.read(10 * 1024 * 1024 + 1)
        records = await run_in_threadpool(preview_exam_pdf, content)
        return {"records": records, "message": "Chọn đúng các ca thi của bạn và đối chiếu trước khi lưu."}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    finally:
        await file.close()


@router.post("/exams/import")
def save_imported_exams(payload: ExamImport, student_id: str = Depends(current_student)):
    key = data_loader.profiles.find_key(student_id)
    profile = data_loader.profiles.get(key) if key else None
    if not profile or profile.get("info", {}).get("student_id") != student_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ đang đăng nhập.")
    section = {"status": "synced", "source_type": "imported_pdf", "source_url": "", "synced_at": datetime.now(timezone.utc).isoformat(),
               "message": "Lịch thi nhập từ PDF và được sinh viên xác nhận; hãy đối chiếu thông báo chính thức.",
               "records": [record.model_dump(mode="json") for record in payload.exams], "tables": []}
    profile.setdefault("school_services", {})["exams"] = section
    data_loader.save_profile_for(student_id, profile)
    return {"status": "success", "total": len(payload.exams)}


@router.get("/tuition", response_model=TuitionResponse)
def get_student_tuition(student_id: str = Depends(current_student)):
    """Tra cứu học phí và trạng thái nợ học phí."""
    return extra_student_services.get_tuition(student_id)


@router.get("/toeic", response_model=ToeicResponse)
def get_student_toeic(student_id: str = Depends(current_student)):
    """Tra cứu điểm thi TOEIC nội bộ và kiểm tra chuẩn đầu ra ngoại ngữ."""
    return extra_student_services.get_toeic_status(student_id)


@router.get("/classmates", response_model=ClassmatesResponse)
def get_classmates(class_code: str = Query("", max_length=80, description="Mã lớp đã được đồng bộ từ CTT"), student_id: str = Depends(current_student)):
    """Tra cứu danh sách sinh viên cùng lớp học phần (StudentGroupInfo)."""
    try:
        return extra_student_services.get_classmates(class_code, student_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/school-services")
def get_school_services(student_id: str = Depends(current_student)):
    return extra_student_services.get_sync_summary(student_id)


@router.get("/reviews")
def get_course_reviews(course_code: str = Query(None, description="Mã môn học (VD: MI1111, ET3210)")):
    """Xem đánh giá và review học phần từ cộng đồng sinh viên HUST."""
    return extra_student_services.get_course_reviews(course_code)


@router.post("/reviews")
def add_course_review(
    course_code: str = Query(..., description="Mã môn học"),
    payload: CourseReviewCreate = ...,
    student_id: str = Depends(current_student)
):
    """Gửi đánh giá và kinh nghiệm học tập cho môn học."""
    return extra_student_services.add_course_review(course_code, payload, author_name=f"SV {student_id[:4]}***")
