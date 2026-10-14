"""Đăng ký / đăng nhập / đăng xuất bằng MSSV + mật khẩu.

Phiên trả về qua cookie HttpOnly (JavaScript không đọc được), frontend chỉ cần
gọi API với ``credentials: 'include'``.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from app.auth import runtime
from app.auth.dependencies import current_student
from app.auth.passwords import PasswordPolicyError
from app.auth.service import (
    SESSION_TTL,
    AccountLockedError,
    InvalidCredentialsError,
    ProfileExistsError,
    RegistrationError,
    TooManyAttemptsError,
)
from app.auth.store import UserExistsError
from app.core.config import COOKIE_SECURE, SESSION_COOKIE_NAME
from app.services.curriculum_repository import CurriculumNotFoundError

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(_Strict):
    student_id: str = Field(..., max_length=16)
    password: str = Field(..., max_length=256)
    student_name: str = Field(..., max_length=120)
    class_name: str = Field(..., max_length=120)
    program_code: str = Field("ET1", max_length=16)


class LoginRequest(_Strict):
    student_id: str = Field(..., max_length=16)
    password: str = Field(..., max_length=256)


class ChangePasswordRequest(_Strict):
    current_password: str = Field(..., max_length=256)
    new_password: str = Field(..., max_length=256)


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=COOKIE_SECURE)


def _account_view(student_id: str) -> dict:
    """Thông tin tài khoản cho giao diện; không bao giờ chứa password_hash."""
    user = runtime.auth_service.get_user(student_id) or {}
    profiles = runtime.auth_service.profiles
    key = profiles.find_key(student_id)
    info = (profiles.get(key) or {}).get("info", {}) if key else {}
    return {
        "student_id": student_id,
        "student_name": info.get("student_name", ""),
        "class_name": info.get("class_name", ""),
        "program_code": info.get("program_code") or info.get("program_id", ""),
        "curriculum_version": info.get("curriculum_version", ""),
        "is_admin": bool(user.get("is_admin")),
        "is_demo": bool(user.get("is_demo")),
    }


@router.post("/register", status_code=201)
async def register(payload: RegisterRequest, response: Response):
    try:
        token = await run_in_threadpool(runtime.auth_service.register, **payload.model_dump())
    except UserExistsError as exc:
        raise HTTPException(status_code=409, detail="MSSV này đã có tài khoản. Hãy đăng nhập.") from exc
    except ProfileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (RegistrationError, PasswordPolicyError, CurriculumNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _set_session_cookie(response, token)
    return await run_in_threadpool(_account_view, payload.student_id.strip())


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    try:
        token = await run_in_threadpool(
            runtime.auth_service.login, payload.student_id, payload.password, client_ip
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except (AccountLockedError, TooManyAttemptsError) as exc:
        raise HTTPException(
            status_code=429, detail=str(exc), headers={"Retry-After": str(exc.retry_after_seconds)}
        ) from exc
    _set_session_cookie(response, token)
    return await run_in_threadpool(_account_view, payload.student_id.strip())


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    token: Optional[str] = request.cookies.get(SESSION_COOKIE_NAME)
    await run_in_threadpool(runtime.auth_service.logout, token)
    _clear_session_cookie(response)
    response.status_code = 204
    return response


@router.get("/me")
async def me(student_id: str = Depends(current_student)):
    return await run_in_threadpool(_account_view, student_id)


@router.post("/password", status_code=204)
async def change_password(payload: ChangePasswordRequest, response: Response, student_id: str = Depends(current_student)):
    try:
        await run_in_threadpool(
            runtime.auth_service.change_password, student_id, payload.current_password, payload.new_password
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Mọi phiên (kể cả phiên này) đã bị thu hồi: xóa cookie để giao diện về màn đăng nhập.
    _clear_session_cookie(response)
    response.status_code = 204
    return response
