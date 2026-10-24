from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import current_student, student_scope
from app.services.student_service import student_service
from app.engine.recommender import course_recommender
from app.services.data_loader import data_loader
from app.services.curriculum_repository import CurriculumNotFoundError
from app.services.student_memory import student_memory
from app.models.schemas import (
    AdvisingMemoryUpdate,
    DegreeAuditResponse,
    ProfileDisplayUpdate,
    RecommendationRequest,
    RecommendationResponse,
    TranscriptImportRequest,
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
