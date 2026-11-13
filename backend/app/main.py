from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from app.core.config import CORS_ORIGINS, FRONTEND_DIST_DIR, RAG_SYNC_ON_STARTUP, SESSION_COOKIE_NAME
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
    # auto checks approved corpus without loading the embedding model.
    try:
        if rag_engine.vector_store.mode == "bm25_only":
            print("RAG: chế độ chỉ BM25.")
        if RAG_SYNC_ON_STARTUP == "never":
            print("[Startup] Bỏ qua đồng bộ RAG theo RAG_SYNC_ON_STARTUP=never.")
        else:
            result = rag_engine.sync_knowledge_base(force=RAG_SYNC_ON_STARTUP == "always")
            print(f"[Startup] RAG {result['status']}: {result.get('total_chunks', 0)} chunks.")
    except Exception as e:
        print(f"[Startup] Cảnh báo đồng bộ RAG: {e}")
    yield

app = FastAPI(
    title="HUST Course Advisor & Degree Audit Engine",
    description="Hệ thống chatbot RAG và công cụ tư vấn học tập, chọn môn và rà soát tiến độ dựa trên chương trình đào tạo và điều kiện đăng ký của Đại học Bách Khoa Hà Nội.",
    version="2.0.0",
    lifespan=lifespan
)

def is_allowed_origin(origin: str | None, request: Request) -> bool:
    if not origin:
        return True
    if origin in CORS_ORIGINS:
        return True
    try:
        parsed = urlsplit(origin)
        # Uvicorn resolves the scheme through trusted proxy headers in production.
        # Compare complete origins, including non-default ports, never suffixes.
        def authority(url):
            return (url.scheme, url.hostname, url.port or (443 if url.scheme == "https" else 80))

        if (parsed.scheme in ("http", "https") and parsed.netloc
                and not parsed.username and not parsed.password
                and not parsed.path and not parsed.query and not parsed.fragment
                and authority(parsed) == authority(urlsplit(str(request.base_url)))):
            return True
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
        if origin and not is_allowed_origin(origin, request):
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

@app.get("/api/system")
def root():
    return {
        "system": "HUST Course Advisor & RAG AI Agent",
        "scope": "Sinh viên Đại học Bách Khoa Hà Nội",
        "data_scope": "Tra cứu CTĐT đang hỗ trợ tại /api/programs?supported_only=true; danh mục ngành không đồng nghĩa với CTĐT đã được hỗ trợ.",
        "storage": "mongodb",
        "rag_status": "/api/rag/status",
        "docs_url": "/docs",
        "status": "online"
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}


def register_frontend(application: FastAPI, dist_dir: Path) -> None:
    """Register last so API/docs routes retain priority over the SPA fallback."""
    dist_dir = dist_dir.resolve()
    index = dist_dir / "index.html"
    if not index.is_file():
        application.add_api_route("/", root, methods=["GET"])
        return

    if (dist_dir / "assets").is_dir():
        application.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @application.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith(("api", "docs", "redoc", "openapi.json")):
            raise HTTPException(status_code=404)
        candidate = (dist_dir / path).resolve()
        if not candidate.is_relative_to(dist_dir):
            raise HTTPException(status_code=404)
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


register_frontend(app, FRONTEND_DIST_DIR)
