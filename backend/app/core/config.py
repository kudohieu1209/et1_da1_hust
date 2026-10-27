import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR = BASE_DIR.parent

# Tải biến môi trường từ file .env ở backend hoặc project root
load_dotenv(BASE_DIR / ".env")
load_dotenv(PROJECT_DIR / ".env")

DATA_DIR = PROJECT_DIR / "data" / "processed"
CURRICULA_DIR = DATA_DIR / "curricula"
DOCUMENTS_DIR = PROJECT_DIR / "data" / "documents"
# ChromaDB lưu file cục bộ không an toàn khi nhiều tiến trình cùng mở, nên
# kiểm thử/đánh giá trỏ biến này sang thư mục riêng khi backend dev đang chạy.
VECTOR_DB_DIR = Path(os.getenv("VECTOR_DB_DIR") or PROJECT_DIR / "data" / "vector_db")
# MongoDB là kho nghiệp vụ duy nhất; ChromaDB chỉ phục vụ chỉ mục RAG.
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
MONGODB_DB = os.getenv("MONGODB_DB", "hust_course_advisor").strip() or "hust_course_advisor"

# Cookie phiên đăng nhập (HttpOnly, SameSite=Lax). Đặt COOKIE_SECURE=true khi
# chạy sau HTTPS để cookie không bao giờ đi qua HTTP thường.
SESSION_COOKIE_NAME = "hust_session"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes"}

RAW_CONDITIONS_FILE = PROJECT_DIR / "data" / "raw" / "ctt_et_conditions.json"
PROGRAM_CATALOG_FILE = PROJECT_DIR / "data" / "raw" / "hust_undergraduate_programs.json"
PROGRAM_SOURCES_FILE = PROJECT_DIR / "data" / "raw" / "hust_program_curriculum_sources.json"
PROGRAM_CANDIDATES_FILE = PROJECT_DIR / "data" / "raw" / "hust_curriculum_candidates.json"

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

# Cấu hình Gemini LLM
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "")
# Giới hạn thời gian mỗi lần gọi Gemini để request chat không treo vô hạn.
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "45"))
GEMINI_EMBEDDING_MODEL = "text-embedding-004"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Danh sách origin của frontend, phân tách bằng dấu phẩy. Không dùng "*" vì
# CORSMiddleware bật allow_credentials.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:5174",
    ).split(",")
    if origin.strip()
]
