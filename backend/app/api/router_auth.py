from fastapi import APIRouter, Header, HTTPException, Depends
from typing import Dict, Any, Optional
from app.services.auth_service import auth_service

router = APIRouter(prefix="/api/auth", tags=["Authentication & User Management"])

@router.post("/register")
def register_user(payload: Dict[str, Any]):
    """Đăng ký tài khoản sinh viên mới (khởi tạo với bảng điểm trống)"""
    res = auth_service.register(payload)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.post("/login")
def login_user(payload: Dict[str, Any]):
    """Đăng nhập bằng MSSV và Mật khẩu"""
    res = auth_service.login(payload)
    if not res.get("success"):
        raise HTTPException(status_code=401, detail=res.get("message"))
    return res

@router.get("/me")
def get_current_user_profile(x_student_id: Optional[str] = Header(None)):
    """Lấy thông tin tài khoản hiện tại"""
    user = auth_service.get_current_user(x_student_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản sinh viên!")
    return user

@router.get("/demo-accounts")
def get_demo_accounts():
    """Lấy danh sách các tài khoản Demo để đăng nhập nhanh 1-click"""
    return {"demo_accounts": auth_service.list_demo_accounts()}

@router.post("/transcript")
def update_user_transcript(payload: Dict[str, Any], x_student_id: Optional[str] = Header(None)):
    """
    Cập nhật / Nạp bảng điểm CTT cho tài khoản sinh viên đang đăng nhập.
    Sau khi nạp, toàn bộ Degree Audit và môn học sẽ tự động được tính toán.
    """
    student_id = payload.get("student_id") or x_student_id
    if not student_id:
        raise HTTPException(status_code=400, detail="Thiếu mã sinh viên (MSSV)!")

    raw_text = payload.get("raw_text", "")
    courses = payload.get("courses")
    res = auth_service.update_transcript(student_id=student_id, raw_text=raw_text, courses=courses)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.post("/logout")
def logout_user():
    """Đăng xuất khỏi hệ thống"""
    return {"success": True, "message": "Đã đăng xuất thành công!"}
