# HUST Course Advisor & Degree Audit Engine

> **Đồ án 1 (HUST - 2026.1):** Hệ thống Chatbot và Dashboard tư vấn học tập, chọn môn và rà soát tiến độ cho sinh viên Đại học Bách Khoa Hà Nội. Bản thử nghiệm hiện hỗ trợ CTĐT ET1–2022 và ET1–2023.  
> **Sinh viên thực hiện:** Mai Duy Hiếu - MSSV: 20220001  

---

## 📌 Giới thiệu đề tài

Hệ thống **HUST Course Advisor** là một giải pháp ứng dụng trí tuệ nhân tạo lai (**Hybrid AI Agent**) nhằm giải quyết bài toán tư vấn học tập, lựa chọn môn học và rà soát tiến độ tốt nghiệp cho sinh viên Bách Khoa:
1. **RAG Pipeline (Retrieval-Augmented Generation):** Kết hợp mô hình Gemini LLM với cơ sở dữ liệu vector ChromaDB để giải đáp quy chế đào tạo, chuẩn đầu ra và đề cương môn học chính xác có kèm trích dẫn nguồn.
2. **Deterministic Rule Engine:** Sử dụng dữ liệu CTĐT và bộ quy tắc HUST để kiểm tra điều kiện học phần, rà soát tín chỉ (Degree Audit) theo từng hồ sơ sinh viên và hỗ trợ chọn môn.
3. **Full-stack Interactive Dashboard:** Giao diện React tập trung vào chat tự nhiên, tiến độ học tập và gợi ý chọn môn theo các mô-đun của chương trình đào tạo đang được hỗ trợ.

---

## 🏛️ Kiến trúc hệ thống (System Architecture)

```mermaid
graph TD
    User([Sinh viên HUST]) <--> UI[Frontend: React 19 + Tailwind/CSS Dashboard]
    UI <--> API[FastAPI Gateway RESTful API]
    
    subgraph Backend_Core [Hệ thống Xử lý Trung tâm (Backend)]
        API <--> Router[Intent Classifier & Course Entity Extractor]
        
        Router -->|Câu hỏi quy chế / Đề cương| RAG[RAG Pipeline]
        Router -->|Kiểm tra điều kiện học phần| Rule[HUST Rule Engine]
        Router -->|Rà soát tốt nghiệp / Tín chỉ| Rule
        Router -->|Gợi ý môn kỳ tới theo chuyên ngành| Rec[Course Recommender]
        
        RAG <--> Chroma[(ChromaDB Vector Store)]
        RAG <--> Gemini[Google Gemini LLM / Flash]
        
        Rule <--> CurriculumDB[(Dữ liệu CTĐT & điều kiện)]
        Rule <--> StudentData[(Hồ sơ sinh viên: Điểm, CPA, Cảnh cáo)]
        Rec <--> CurriculumDB
        API <--> ChatDB[(SQLite: conversations & messages)]
    end
```

## Trạng thái dữ liệu hiện tại

- Đã chuẩn hóa và kiểm tra: **ET1, CTĐT 2022 (K67)** — 126 tín chỉ, 117 học phần, 20 nhóm và 6 mô-đun; **ET1, CTĐT 2023 (K68)** — 132 tín chỉ, 79 học phần, 13 nhóm và 5 mô-đun.
- Backend chọn CTĐT theo `program_code/program_id` và `curriculum_version` của hồ sơ. K67 dùng snapshot 2022, K68 dùng snapshot 2023; không tự chuyển sang phiên bản khác.
- Nguồn chuẩn hóa: `project/data/processed/curricula/et1_2022.json` và `project/data/processed/curricula/et1_2023.json`. HTML CTT gốc có dữ liệu cá nhân, không được đưa vào dataset sinh ra hoặc công khai.
- Đã bổ sung snapshot danh mục **68 chương trình đại học** từ trang tuyển sinh chính thức: `project/data/raw/hust_undergraduate_programs.json`. Đây là danh mục lựa chọn/tìm kiếm; hiện ET1 có hai phiên bản CTĐT đã chuẩn hóa.
- Đã rà liên kết CTĐT trên trang chi tiết của cả 68 chương trình: `project/data/raw/hust_program_curriculum_sources.json`. Manifest lưu nguồn chính thức và trạng thái truy cập (snapshot hiện tại: 46 nguồn HTTP 2xx); dữ liệu này chưa được coi là CTĐT chuẩn hóa cho đến khi kiểm tra cấu trúc và điều kiện học phần.
- Đã có bước trích xuất candidate cho 6 trang CTĐT HTML (5 trang `hp-table` và FL2 dạng bảng thông thường) cùng 6/8 PDF có danh mục học phần (`project/data/raw/hust_curriculum_extractions.json`, `project/data/raw/hust_curriculum_pdf_extractions.json`).
- Đã ghép 14 candidate HTML/PDF với danh mục 8.310 học phần CTT (`project/data/raw/hust_curriculum_candidates.json`). ET1-2023 đã được phê duyệt qua `project/data/processed/curriculum_approvals.json`; các candidate còn lại vẫn `needs_review` và chưa nạp vào Rule Engine.
- Lịch sử hội thoại được lưu riêng trong SQLite tại `project/data/processed/chat_history.sqlite3`, gắn với MSSV; ChromaDB chỉ dùng để lưu vector RAG, không lưu hội thoại.

Chạy lại pipeline và kiểm thử:

```bash
python3 project/data/scripts/build_curriculum.py
python3 project/data/scripts/validate_curriculum.py project/data/processed/curricula/et1_2022.json
python3 project/data/scripts/build_curriculum_document.py
cd project/backend
./venv/bin/python -m unittest discover -s tests -v
./venv/bin/python test_backend.py
```

Danh mục chương trình có thể xem qua `GET /api/programs` (lọc bằng `?search=`
hoặc chỉ chương trình đã có CTĐT bằng `?supported_only=true`).

Lấy dữ liệu học phần và chuỗi điều kiện trực tiếp từ CTT SIS (script sẽ mở
Chrome để bạn đăng nhập thủ công):

```bash
project/backend/venv/bin/python project/data/scripts/scrape_ctt_courses.py --code ET4230
```

Xem thêm các tùy chọn và chế độ đọc HTML đã lưu tại
[`project/data/README.md`](project/data/README.md).

Tạo lại báo cáo candidate CTĐT công khai (review-only):

```bash
project/backend/venv/bin/python project/data/scripts/build_hust_curriculum_candidates.py
```

Phê duyệt và sinh lại dataset ET1–2023 sau khi rà nguồn:

```bash
project/backend/venv/bin/python project/data/scripts/promote_hust_curriculum_candidate.py \
  --candidate ET1-2023
```

---

## 🚀 Cấu trúc thư mục

```text
ĐA1/
├── project/
│   ├── backend/               # FastAPI Backend Service
│   │   ├── app/
│   │   │   ├── api/           # Các RESTful API Routers (chat, conversations, courses, student, rag, auth)
│   │   │   ├── core/          # Quy chế HUST (hust_rules.py), Cấu hình (config.py)
│   │   │   ├── engine/        # Rule Engine, Recommender (Graph là phần mở rộng)
│   │   │   ├── rag/           # RAG Engine, Document Loader, Chroma Vector Store, Gemini Service
│   │   │   └── services/      # Chatbot, Conversation, Data Loader, Student Service
│   │   ├── requirements.txt   # Các thư viện Python phụ thuộc
│   │   └── run.py             # Script khởi động Backend server
│   ├── data/                  # Cơ sở dữ liệu và kho tri thức
│   │   ├── documents/         # Văn bản quy chế, CTĐT, đề cương chi tiết (Markdown)
│   │   ├── processed/         # Dữ liệu JSON chuẩn hóa (117 môn học, cây tiên quyết, profile)
│   │   └── scripts/           # Scripts tạo demo profiles, crawl/chuẩn hóa dữ liệu
│   └── frontend/              # Ứng dụng Web React (Vite)
│       └── src/
│           ├── components/    # ChatTab, AuditTab, RecommendTab, Modals
│           └── App.jsx        # Giao diện chính điều hướng Tabs
└── docs/                      # Tài liệu đồ án, báo cáo và slide thuyết trình
```

---

## 🛠️ Hướng dẫn cài đặt và chạy thử

### 1. Khởi động Backend (FastAPI)
```bash
cd project/backend
# Kích hoạt môi trường ảo (nếu có)
source venv/bin/activate  # Trên Linux/macOS
# Cài đặt thư viện
pip install -r requirements.txt
# Chạy server
python run.py
```
* Backend sẽ chạy tại: `http://localhost:8000`
* Swagger API Docs: `http://localhost:8000/docs`

### 2. Khởi động Frontend (React + Vite)
```bash
cd project/frontend
npm install
npm run dev
```
* Giao diện Web sẽ chạy tại: `http://localhost:5173`

---

## 🎯 Kịch bản Demo tiêu biểu phục vụ Báo cáo

1. **Hỏi đáp tự nhiên có từ lóng sinh viên:** *"Kỳ tới em muốn học vxl và dts thì cần những môn gì trước?"* -> Hệ thống tự bóc tách mã môn `ET3300` và `ET3220`, kiểm tra điều kiện học trước và trả lời chính xác.
2. **Kiểm tra điều kiện học phần:** *"Điều kiện học môn Hệ điều hành là gì?"* -> Rule Engine giải thích các phương án điều kiện và đối chiếu với bảng điểm cá nhân.
3. **Tra cứu quy chế đào tạo (RAG):** *"Quy định cảnh cáo học tập mức 1 được đăng ký tối đa bao nhiêu tín chỉ?"* -> RAG trích dẫn chính xác Điều khoản trong Quy chế Đào tạo ĐHBK Hà Nội.
4. **Rà soát tốt nghiệp (Audit Tab):** Tiến độ được tính theo đúng phiên bản CTĐT; ET1–2022 có 126 tín chỉ, ET1–2023 có 132 tín chỉ, còn Ngoại ngữ/GDTC/GDQP được theo dõi tách biệt.

5. **Lịch sử hội thoại:** Gửi vài câu hỏi, tải lại trang hoặc chọn một mục trong “Gần đây” để kiểm tra hội thoại được khôi phục từ SQLite. Các nút ghim, lưu trữ và xóa cập nhật bản ghi hội thoại tương ứng.
