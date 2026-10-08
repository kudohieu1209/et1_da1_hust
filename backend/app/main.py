from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import CORS_ORIGINS
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
        status = rag_engine.get_status()
        if status["vector_store"]["total_chunks"] == 0:
            print("[Startup] Vector DB rỗng, tự động đồng bộ tài liệu từ data/documents/...")
            rag_engine.sync_knowledge_base()
        else:
            print(f"[Startup] Vector DB sẵn sàng với {status['vector_store']['total_chunks']} chunks.")
    except Exception as e:
        print(f"[Startup] Cảnh báo đồng bộ RAG: {e}")
    yield

app = FastAPI(
    title="HUST Course Advisor & Degree Audit Engine",
    description="Hệ thống chatbot RAG và công cụ tư vấn học tập, chọn môn và rà soát tiến độ dựa trên chương trình đào tạo và điều kiện đăng ký của Đại học Bách Khoa Hà Nội.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(courses_router)
app.include_router(student_router)
app.include_router(chat_router)
app.include_router(rag_router)
app.include_router(conversations_router)
app.include_router(programs_router)

@app.get("/")
def root():
    return {
        "system": "HUST Course Advisor & RAG AI Agent",
        "scope": "Sinh viên Đại học Bách Khoa Hà Nội",
        "data_scope": "Bản thử nghiệm hiện tại đang sử dụng dữ liệu của một chương trình đào tạo.",
        "rag_status": "/api/rag/status",
        "docs_url": "/docs",
        "status": "online"
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}
