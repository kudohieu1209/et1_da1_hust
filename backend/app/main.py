from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from app.core.config import CORS_ORIGINS, SESSION_COOKIE_NAME
from app.api.router_auth import router as auth_router
from app.api.router_courses import router as courses_router
from app.api.router_student import router as student_router
from app.api.router_chat import router as chat_router
from app.api.router_rag import router as rag_router
from app.api.router_conversations import router as conversations_router
from app.api.router_programs import router as programs_router
from app.rag.rag_engine import rag_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo và tự động đồng bộ tài liệu vào ChromaDB khi backend khởi động
    try:
        # Reconcile approvals and chunk metadata even when the index already exists.
        result = rag_engine.sync_knowledge_base()
        print(f"[Startup] Đã đồng bộ kho RAG đã phê duyệt: {result.get('total_chunks', 0)} chunks.")
    except Exception as e:
        print(f"[Startup] Cảnh báo đồng bộ RAG: {e}")
    yield

app = FastAPI(
    title="HUST Course Advisor & Degree Audit Engine",
    description="Hệ thống chatbot RAG và công cụ tư vấn học tập, chọn môn và rà soát tiến độ dựa trên chương trình đào tạo và điều kiện đăng ký của Đại học Bách Khoa Hà Nội.",
    version="2.0.0",
    lifespan=lifespan
)

def is_allowed_origin(origin: str | None) -> bool:
    if not origin:
        return True
    if origin in CORS_ORIGINS:
        return True
    try:
        parsed = urlsplit(origin)
        if parsed.scheme in ("http", "https") and parsed.hostname in ("localhost", "127.0.0.1"):
            return True
    except Exception:
        pass
    return False


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def reject_cross_site_writes(request: Request, call_next):
    """Chống CSRF lớp thứ hai (ngoài SameSite=Lax): request ghi dữ liệu kèm
    cookie phiên mà Origin không thuộc danh sách frontend thì bị từ chối."""
    if request.method in UNSAFE_METHODS and (
        SESSION_COOKIE_NAME in request.cookies or request.url.path.startswith("/api/auth/")
    ):
        origin = request.headers.get("origin")
        if origin and not is_allowed_origin(origin):
            return JSONResponse(status_code=403, content={"detail": "Nguồn gửi yêu cầu không được phép."})
    return await call_next(request)


# Routers
app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(student_router)
app.include_router(chat_router)
app.include_router(rag_router)
app.include_router(conversations_router)
app.include_router(programs_router)

@app.get("/")
@app.get("/api/system")
def root():
    return {
        "system": "HUST Course Advisor & RAG AI Agent",
        "scope": "Sinh viên Đại học Bách Khoa Hà Nội",
        "data_scope": "Bản thử nghiệm hiện tại đang sử dụng dữ liệu của một chương trình đào tạo.",
        "storage": "mongodb",
        "rag_status": "/api/rag/status",
        "docs_url": "/docs",
        "status": "online"
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}
