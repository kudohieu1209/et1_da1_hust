"""User-operated local browser connection to the official HUST portal."""
import importlib.util
import ipaddress
import secrets
from datetime import timedelta
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from app.api.router_auth import _account_view, _set_session_cookie
from app.auth import runtime
from app.auth.service import SlidingWindowLimiter
from app.core.config import COOKIE_SECURE, CTT_BROWSER_LOGIN_ENABLED, CTT_LOGIN_TIMEOUT_SECONDS, SESSION_COOKIE_NAME
from app.services.curriculum_repository import CurriculumNotFoundError, curriculum_repository
from app.services.school_account_service import complete_school_login
from app.services.school_portal import SchoolPortalError, school_login_manager

router = APIRouter(prefix="/api/auth/ctt", tags=["School sign-in"])
OWNER_COOKIE = "hust_ctt_connect"
start_limiter = SlidingWindowLimiter(timedelta(minutes=5), 5)


class SchoolStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    program_code: str = Field("ET1", min_length=2, max_length=12, pattern=r"^[A-Z0-9-]+$")


def _local_request(request: Request) -> bool:
    def loopback(address):
        ip = ipaddress.ip_address(address)
        return ip.is_loopback or bool(getattr(ip, "ipv4_mapped", None) and ip.ipv4_mapped.is_loopback)
    try:
        local = loopback(request.client.host)
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded and not all(loopback(ip.strip()) for ip in forwarded.split(",")):
            return False
        origin = request.headers.get("origin")
        origin_host = urlsplit(origin).hostname if origin else request.url.hostname
        return local and request.url.hostname in {"localhost", "127.0.0.1", "::1"} and origin_host in {"localhost", "127.0.0.1", "::1"}
    except (ValueError, AttributeError):
        return False


def _require_local(request: Request):
    if not CTT_BROWSER_LOGIN_ENABLED or not _local_request(request):
        raise HTTPException(status_code=403, detail="Kết nối CTT bằng trình duyệt chỉ dùng khi mở HUST Advisor trên chính PC chạy backend. Bạn vẫn có thể dùng tài khoản Advisor và nhập bảng điểm.")


async def _current_account(request: Request):
    return await run_in_threadpool(runtime.auth_service.resolve_session, request.cookies.get(SESSION_COOKIE_NAME))


@router.get("/capabilities")
def capabilities(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"available": CTT_BROWSER_LOGIN_ENABLED and _local_request(request) and importlib.util.find_spec("playwright") is not None,
            "local_only": True, "timeout_seconds": CTT_LOGIN_TIMEOUT_SECONDS}


@router.post("/start", status_code=202)
async def start(payload: SchoolStartRequest, request: Request, response: Response):
    _require_local(request)
    if payload.program_code not in {code for code, _ in curriculum_repository.available_keys}:
        raise HTTPException(status_code=422, detail="Chương trình đào tạo chưa được hỗ trợ.")
    expected_id = await _current_account(request)
    owner = request.cookies.get(OWNER_COOKIE) or secrets.token_urlsafe(32)

    def count_new_window():
        wait = start_limiter.hit(request.client.host, runtime.auth_service.clock())
        if wait is not None:
            raise HTTPException(status_code=429, detail="Máy vừa mở nhiều cửa sổ CTT. Vui lòng đợi hết thời gian chờ rồi mở cửa sổ mới.",
                                headers={"Retry-After": str(wait)})

    try:
        attempt_id = school_login_manager.start(owner, payload.program_code, expected_id, before_start=count_new_window)
    except SchoolPortalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    response.set_cookie(OWNER_COOKIE, owner, httponly=True, secure=COOKIE_SECURE, samesite="strict",
                        max_age=CTT_LOGIN_TIMEOUT_SECONDS + 120, path="/api/auth/ctt")
    response.headers["Cache-Control"] = "no-store"
    return {"attempt_id": attempt_id, "status": "opening", "expires_in": CTT_LOGIN_TIMEOUT_SECONDS}


@router.get("/{attempt_id}/status")
def status(attempt_id: str, request: Request, response: Response):
    _require_local(request)
    response.headers["Cache-Control"] = "no-store"
    try:
        return school_login_manager.status(attempt_id, request.cookies.get(OWNER_COOKIE, ""))
    except KeyError:
        raise HTTPException(status_code=404, detail="Kết nối CTT không tồn tại hoặc đã hết hạn. Vui lòng mở lại.") from None


@router.post("/{attempt_id}/finish")
async def finish(attempt_id: str, request: Request, response: Response):
    _require_local(request)
    try:
        attempt = school_login_manager.take(attempt_id, request.cookies.get(OWNER_COOKIE, ""))
    except KeyError:
        raise HTTPException(status_code=404, detail="Kết nối CTT không tồn tại hoặc đã dùng. Vui lòng mở lại.") from None
    except SchoolPortalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    current = await _current_account(request)
    school_id = attempt.snapshot.info["student_id"]
    if (attempt.expected_student_id and current != attempt.expected_student_id) or (current and current != school_id):
        attempt.snapshot = None
        raise HTTPException(status_code=409, detail="Tài khoản Advisor đã thay đổi trong lúc kết nối. Chưa lưu dữ liệu CTT.")
    try:
        token, sync = await run_in_threadpool(complete_school_login, runtime.auth_service, attempt.snapshot,
                                             attempt.program_code, attempt.expected_student_id)
    except (SchoolPortalError, CurriculumNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    finally:
        attempt.snapshot = None
    _set_session_cookie(response, token)
    response.headers["Cache-Control"] = "no-store"
    return {**(await run_in_threadpool(_account_view, school_id)), "school_sync": sync}


@router.delete("/{attempt_id}", status_code=204)
def cancel(attempt_id: str, request: Request):
    _require_local(request)
    try:
        school_login_manager.cancel(attempt_id, request.cookies.get(OWNER_COOKIE, ""))
    except KeyError:
        raise HTTPException(status_code=404, detail="Kết nối CTT đã kết thúc.") from None
    return Response(status_code=204)
