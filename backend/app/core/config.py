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
# MongoDB lưu hội thoại và hồ sơ sinh viên. Để trống để dùng kho cục bộ:
# SQLite cho hội thoại, file students/*.json cho hồ sơ (chế độ offline).
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
MONGODB_DB = os.getenv("MONGODB_DB", "hust_course_advisor").strip() or "hust_course_advisor"
# Kho hội thoại cục bộ khi không cấu hình MongoDB (ChromaDB chỉ phục vụ RAG).
CHAT_DB_PATH = DATA_DIR / "chat_history.sqlite3"
# Tài khoản + phiên đăng nhập khi không cấu hình MongoDB.
AUTH_DB_PATH = Path(os.getenv("AUTH_DB_PATH") or DATA_DIR / "auth.sqlite3")

# Cookie phiên đăng nhập (HttpOnly, SameSite=Lax). Đặt COOKIE_SECURE=true khi
# chạy sau HTTPS để cookie không bao giờ đi qua HTTP thường.
SESSION_COOKIE_NAME = "hust_session"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes"}

STUDENT_PROFILE_FILE = DATA_DIR / "student_profile.json"
STUDENTS_DIR = DATA_DIR / "students"
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
GEMINI_EMBEDDING_MODEL = "text-embedding-004"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Danh sách origin của frontend, phân tách bằng dấu phẩy. Không dùng "*" vì
# CORSMiddleware bật allow_credentials.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
