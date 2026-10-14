"""Dependency FastAPI: xác định sinh viên từ cookie phiên và mở scope hồ sơ.

``student_scope`` là dependency async: ContextVar của hồ sơ được đặt trong
context của request, và endpoint đồng bộ (chạy trong threadpool) nhận bản
sao context đó, nên mọi engine đọc ``data_loader`` đều thấy đúng hồ sơ.
"""
from typing import AsyncIterator

from fastapi import Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from app.auth import runtime
from app.core.config import SESSION_COOKIE_NAME
from app.services.curriculum_repository import CurriculumNotFoundError
from app.services.data_loader import data_loader

UNAUTHENTICATED = "Bạn cần đăng nhập để tiếp tục."


async def current_student(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    student_id = await run_in_threadpool(runtime.auth_service.resolve_session, token) if token else None
    if not student_id:
        raise HTTPException(status_code=401, detail=UNAUTHENTICATED)
    return student_id


async def current_admin(student_id: str = Depends(current_student)) -> str:
    user = await run_in_threadpool(runtime.auth_service.get_user, student_id)
    if not user or not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Chức năng này chỉ dành cho quản trị viên.")
    return student_id


async def student_scope(student_id: str = Depends(current_student)) -> AsyncIterator[str]:
    try:
        state = await run_in_threadpool(data_loader.load_scope_state, student_id)
    except (FileNotFoundError, CurriculumNotFoundError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    token = data_loader.enter_scope(state)
    try:
        yield student_id
    finally:
        data_loader.exit_scope(token)
