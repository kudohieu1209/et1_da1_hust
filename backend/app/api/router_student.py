from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.student_service import student_service
from app.engine.recommender import course_recommender
from app.services.data_loader import data_loader
from app.services.curriculum_repository import CurriculumNotFoundError
from app.models.schemas import DegreeAuditResponse, RecommendationRequest, RecommendationResponse

router = APIRouter(prefix="/api/student", tags=["Student & Degree Audit"])

@router.get("/profile")
def get_student_profile():
    """Lấy thông tin sinh viên và bảng điểm các môn đã học"""
    return student_service.get_profile()

@router.post("/profile/update")
def update_student_profile(payload: Dict[str, Any]):
    """Cập nhật thông tin sinh viên (họ tên, avatar, lớp, MSSV, CTĐT...)"""
    try:
        return student_service.update_profile(payload)
    except CurriculumNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.get("/audit", response_model=DegreeAuditResponse)
def get_degree_audit():
    """Đánh giá chi tiết tiến độ học tập (Degree Audit) và điều kiện tốt nghiệp Bách Khoa"""
    audit = student_service.audit_degree()
    return DegreeAuditResponse(**audit)

@router.get("/profiles")
def list_student_profiles():
    """Liệt kê danh sách các hồ sơ sinh viên Demo (Hiếu K67, Trang Giỏi, Long Cảnh báo, Huy K68,...)"""
    return student_service.list_profiles()

@router.post("/switch")
def switch_student_profile(payload: Dict[str, Any]):
    """Chuyển đổi hồ sơ sinh viên đang hoạt động"""
    student_id = payload.get("student_id", "20220001")
    try:
        return student_service.switch_student(student_id)
    except (CurriculumNotFoundError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.post("/import")
def import_student_transcript(payload: Dict[str, Any]):
    """Nhập bảng điểm cá nhân của sinh viên (từ text copy CTT hoặc JSON)"""
    try:
        return student_service.import_transcript(payload)
    except (CurriculumNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.get("/tracks")
def get_available_tracks():
    """Danh sách các mô-đun lấy từ CTĐT đang hoạt động."""
    return {"tracks": data_loader.get_module_tracks()}

@router.post("/recommend", response_model=RecommendationResponse)
def recommend_courses(req: RecommendationRequest):
    """Thuật toán gợi ý danh sách môn học tối ưu cho kỳ tiếp theo theo định hướng chuyên ngành"""
    try:
        rec = course_recommender.recommend(
            target_track=req.target_track,
            max_credits=req.max_credits,
            is_summer=req.is_summer_term or False
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RecommendationResponse(**rec)
