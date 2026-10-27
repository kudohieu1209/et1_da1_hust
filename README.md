# HUST Course Advisor & Degree Audit Engine

> **Đồ án 1 (HUST - 2026.1):** Hệ thống Chatbot và Dashboard tư vấn học tập, chọn môn và rà soát tiến độ cho sinh viên Đại học Bách Khoa Hà Nội. Bản thử nghiệm hiện hỗ trợ CTĐT ET1–2022 và ET1–2023.  
> **Sinh viên thực hiện:** Mai Duy Hiếu  

---

## 📌 Giới thiệu đề tài

Hệ thống **HUST Course Advisor** là một giải pháp ứng dụng trí tuệ nhân tạo lai (**Hybrid AI Agent**) nhằm giải quyết bài toán tư vấn học tập, lựa chọn môn học và rà soát tiến độ tốt nghiệp cho sinh viên Bách Khoa:
1. **RAG Pipeline (Retrieval-Augmented Generation):** Kết hợp mô hình Gemini LLM với cơ sở dữ liệu vector ChromaDB để giải đáp quy chế đào tạo, chuẩn đầu ra và đề cương môn học chính xác có kèm trích dẫn nguồn.
2. **Deterministic Rule Engine:** Sử dụng dữ liệu CTĐT và bộ quy tắc HUST để kiểm tra điều kiện học phần, rà soát tín chỉ (Degree Audit) theo từng hồ sơ sinh viên và hỗ trợ chọn môn.
3. **Full-stack Interactive Dashboard:** Giao diện React tập trung vào chat tự nhiên, tiến độ học tập và gợi ý chọn môn theo các mô-đun của chương trình đào tạo đang được hỗ trợ.

## Tài liệu bàn giao

- Kết quả bàn giao ngày 24/10/2026: [báo cáo đánh giá 100 câu](eval/reports/handoff_20261024.md) và [20 câu diễn đạt bổ sung](eval/reports/validation_handoff_20261024.md)
- Kết quả sau khi bổ sung văn bản HUST 2026: [bộ hồi quy](eval/reports/new_documents_20261027.md) và [bộ diễn đạt bổ sung](eval/reports/validation_new_documents_20261027.md)
- Chạy kiểm thử toàn bộ: `./scripts/test_all.sh`

---

## 🏛️ Kiến trúc hệ thống (System Architecture)

```mermaid
graph TD
    User([Sinh viên HUST]) <--> UI[Frontend: React 19 + CSS Dashboard]
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
        API <--> ChatDB[(MongoDB: users, sessions, profiles, conversations, memory)]
    end
```

## Trạng thái dữ liệu hiện tại

- Đã chuẩn hóa và kiểm tra: **ET1, CTĐT 2022 (K67)** — 126 tín chỉ, 117 học phần, 20 nhóm và 6 mô-đun; **ET1, CTĐT 2023 (K68)** — 132 tín chỉ, 79 học phần, 13 nhóm và 5 mô-đun.
- Backend chọn CTĐT theo `program_code/program_id` và `curriculum_version` của hồ sơ. K67 dùng snapshot 2022, K68 dùng snapshot 2023; không tự chuyển sang phiên bản khác.
- Nguồn chuẩn hóa: `data/processed/curricula/et1_2022.json` và `data/processed/curricula/et1_2023.json`. HTML CTT gốc có dữ liệu cá nhân, không được đưa vào dataset sinh ra hoặc công khai.
- Đã bổ sung snapshot danh mục **68 chương trình đại học** từ trang tuyển sinh chính thức: `data/raw/hust_undergraduate_programs.json`. Đây là danh mục lựa chọn/tìm kiếm; hiện ET1 có hai phiên bản CTĐT đã chuẩn hóa.
- Đã rà liên kết CTĐT trên trang chi tiết của cả 68 chương trình: `data/raw/hust_program_curriculum_sources.json`. Manifest lưu nguồn chính thức và trạng thái truy cập (snapshot hiện tại: 46 nguồn HTTP 2xx); dữ liệu này chưa được coi là CTĐT chuẩn hóa cho đến khi kiểm tra cấu trúc và điều kiện học phần.
- Đã có bước trích xuất candidate cho 6 trang CTĐT HTML (5 trang `hp-table` và FL2 dạng bảng thông thường) cùng 6/8 PDF có danh mục học phần (`data/raw/hust_curriculum_extractions.json`, `data/raw/hust_curriculum_pdf_extractions.json`).
- Đã ghép 14 candidate HTML/PDF với danh mục 8.310 học phần CTT (`data/raw/hust_curriculum_candidates.json`). ET1-2023 đã được phê duyệt qua `data/processed/curriculum_approvals.json`; các candidate còn lại vẫn `needs_review` và chưa nạp vào Rule Engine.
- **MongoDB là kho nghiệp vụ duy nhất**: `users`, `sessions`, `student_profiles`, `conversations`, `messages`, `student_memory` và bộ đếm `counters`. Backend bắt buộc có `MONGODB_URI`; không còn nhánh SQLite hay ghi hồ sơ JSON. CTĐT và tài liệu nguồn vẫn là dataset có phiên bản. ChromaDB chỉ phục vụ RAG; file SQLite nội bộ của Chroma được giữ nguyên.
- Hội thoại dùng context từ 12 tin nhắn gần nhất của đúng tài khoản; hiểu “môn đó cần gì?”, “nếu trượt thì sao?”, yêu cầu làm rõ khi có nhiều môn. Lịch sử client gửi lên không được dùng để thiết lập context.
- **Cài đặt → Ghi nhớ học tập**: tự chọn bật/tắt, sửa hoặc xóa định hướng, tải tín chỉ mong muốn và mục tiêu CPA. Mặc định tắt; chatbot không tự trích xuất mục tiêu từ tin nhắn. Gợi ý môn dùng định hướng/tín chỉ đã lưu, ưu tiên lựa chọn trong câu hỏi và luôn áp giới hạn học vụ. CPA hiện được lưu và nhắc lại, chưa có bộ mô phỏng điểm theo mục tiêu cá nhân.
- Kho RAG tin cậy hiện gồm 5 tài liệu: CTĐT ET1–2022, ET1–2023, Quy chế đào tạo theo Quyết định 5445/QĐ-ĐHBK, Sổ tay sinh viên 2026 và Quyết định học phí 2025–2026. Chỉ tài liệu có metadata `rag_status: VERIFIED` mới được lập chỉ mục; PDF cần sidecar `<tên-file>.pdf.metadata.json` có trạng thái tương ứng. Kho được đồng bộ lại khi khởi động để loại nguồn đã thu hồi phê duyệt.
- Sinh viên đăng nhập bằng **MSSV + mật khẩu** (tự đăng ký); phiên nằm trong cookie HttpOnly, mỗi người chỉ thấy hồ sơ, bảng điểm và hội thoại của mình. Bản bàn giao chạy local; chưa nghiệm thu triển khai Internet/HTTPS hay quản trị người dùng đầy đủ.

### Chuẩn bị trên máy mới

Cần **Python 3.12 trở lên**, **Node.js 22.12 trở lên** và MongoDB (local hoặc
Atlas). Không cần MongoDB hay khóa Gemini để chạy kiểm thử; ứng dụng thật cần
`MONGODB_URI`. Phạm vi thử nghiệm: ET1–2022/K67 và ET1–2023/K68.

Windows PowerShell, tại thư mục gốc sau khi clone:

```powershell
python -m venv backend/.venv-win
& backend/.venv-win/Scripts/python.exe -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
npm --prefix frontend ci
Copy-Item backend/.env.example backend/.env
# Điền MONGODB_URI vào backend/.env trước khi chạy ứng dụng.
& ./scripts/test_all.ps1
```

Linux/macOS hoặc Git Bash:

```bash
./scripts/setup.sh
cp backend/.env.example backend/.env
# Cấu hình MONGODB_URI trong .env trước khi chạy ứng dụng.
./scripts/test_all.sh
```

Git Bash trên Windows chọn `.venv-win`, Linux/macOS chọn `.venv`; không dùng
chung venv giữa hai hệ điều hành. Python và Node đã cài phải nằm trong PATH.

### MongoDB (bắt buộc cho dữ liệu nghiệp vụ)

1. Tạo cluster miễn phí **MongoDB Atlas M0**, tạo database user riêng cho ứng dụng
   và chỉ thêm IP máy của bạn vào *Network Access* (không mở `0.0.0.0/0`, vì hồ sơ
   chứa bảng điểm cá nhân).
2. Điền `MONGODB_URI` (Connect → Drivers → Python) và `MONGODB_DB` vào
   `backend/.env` (xem `.env.example`).
3. Chuyển dữ liệu cục bộ hiện có lên MongoDB (chạy lại nhiều lần vẫn an toàn):

```bash
cd backend
./.venv/bin/python migrate_to_mongodb.py --dry-run
./.venv/bin/python migrate_to_mongodb.py --check
./.venv/bin/python migrate_to_mongodb.py
```

`--dry-run` chỉ đếm nguồn cục bộ; `--check` đối chiếu MongoDB mà không ghi. Lệnh
import giữ bản trên MongoDB khi có khác biệt, chuyển tài khoản kèm hash mật khẩu
nếu còn thiếu, không chuyển phiên đăng nhập. Trùng ID khác chủ sở hữu bị từ chối
trước khi ghi. Nguồn không bị sửa/xóa; chạy lại không nhân đôi tin nhắn, kể cả
bản đã import trước khi có `migration_key`. Có thể dùng `--source <thư-mục>` để
đọc bản sao lưu chứa `students/`, `auth.sqlite3`, `chat_history.sqlite3`.

Thiếu URI hoặc không kết nối được thì backend dừng khởi động và báo lỗi.
`GET /` trả `storage: mongodb`. Có thể dùng MongoDB local hoặc Atlas.
Kiểm thử và eval dùng **mongomock trong bộ nhớ với hồ sơ tổng hợp** từ CTĐT công
khai; không cần MongoDB thật, không đọc bảng điểm cá nhân. SQLite chỉ còn trong
công cụ đọc dữ liệu cũ `legacy_storage.py` và phần nội bộ ChromaDB.

### Tài khoản và đăng nhập

- Mở web sẽ gặp màn **Đăng nhập / Đăng ký**. Đăng ký cần MSSV (8 chữ số), họ tên, lớp có khóa (`K67`/`K68`) và mật khẩu ≥ 8 ký tự; xong sẽ được mời dán bảng điểm từ CTT.
- Đăng xuất: menu tài khoản ở góc dưới thanh bên → **Đăng xuất**. Đổi mật khẩu: **Cài đặt → Tài khoản**.
- Local hỗ trợ cả `http://localhost:5173` và `http://127.0.0.1:5173`: để trống `VITE_API_BASE_URL` để Vite chuyển tiếp `/api` tới backend cổng 8000. Cookie phiên được giữ cùng địa chỉ với web.
- Nếu có học phần ngoài danh mục, hệ thống giữ nguyên bảng điểm cũ và yêu cầu xác nhận số tín chỉ trước khi lưu. Trong hộp nhập bảng điểm, sinh viên cũng có thể khai báo mức cảnh báo và trạng thái Ngoại ngữ/GDTC/GDQP theo CTT. Khi chưa biết mức cảnh báo, kế hoạch tạm giới hạn 14 TC/kỳ chính; đây là lựa chọn lập kế hoạch của ứng dụng, không phải kết luận hạn mức đăng ký chính thức.
- Khi chạy sau reverse proxy, chỉ cấu hình Uvicorn tin các IP proxy do bạn quản lý (`--forwarded-allow-ips`); API lấy IP từ ASGI request, không tự tin header `X-Forwarded-For` do client gửi.

**Demo trên máy mới, không cần hồ sơ cá nhân:**

1. Cấu hình MongoDB, chạy backend và frontend theo hướng dẫn bên dưới.
2. Tự đăng ký một tài khoản thử, ví dụ MSSV `10000001`, tên `Sinh viên demo`,
   lớp `Điện tử 03 - K67`, chương trình `ET1`; tự chọn mật khẩu.
3. Có thể dùng bảng điểm giả sau để thử nhập liệu (không phải bảng điểm thật):

```text
MI1111 Giải tích I 4 A
MI1141 Đại số 4 B
ET3220 Điện tử số 3 A
```

4. Thử “Tiến độ học tập”, “Điều kiện ET4230?”, rồi “Môn đó cần gì?”. Vào
   **Cài đặt → Ghi nhớ học tập** để đặt mục tiêu, mở chat mới và hỏi gợi ý môn.

Không có mật khẩu dùng chung hay tài khoản cá nhân được đóng gói trong repo.
`seed_demo_accounts.py` là công cụ quản trị tùy chọn cho hồ sơ đã tồn tại trong
MongoDB; không cần chạy để demo bằng tài khoản tự đăng ký. Không sao chép bảng
điểm cá nhân vào repo công khai.

### Đánh giá định lượng

`eval/golden_questions.jsonl` gồm **100 câu hỏi hồi quy**, có bằng chứng/ý chính đối chiếu
với các văn bản đã kiểm chứng (quy chế, học phí, học bổng, CTĐT) và các câu
kiểm tra điều kiện, gợi ý môn, rà soát tiến độ. Bộ chạy đo độ chính xác phân loại
ý định, trích xuất mã môn, Recall@k/MRR của truy xuất và tỉ lệ câu trả lời chứa ý
chính; mặc định tắt LLM để kết quả tất định.

```bash
backend/.venv/bin/python eval/run_eval.py --label latest     # ghi eval/reports/
backend/.venv/bin/python eval/run_eval.py --check            # thoát mã 1 nếu thụt lùi
```

Ngưỡng chống thụt lùi nằm ở `eval/thresholds.json`; chỉ nâng ngưỡng khi
một thay đổi đã cải thiện chỉ số.

Test/eval mặc định tạo một chỉ mục riêng cho mỗi tiến trình trong
`data/vector_db_test/`, không dùng chỉ mục của backend. Khi đặt
`VECTOR_DB_DIR` thủ công, không trỏ tới chỉ mục đang được ứng dụng sử dụng.
Báo cáo baseline 96 câu ngày 15/10 được giữ để tham khảo lịch sử; không phải
kết quả của bộ 100 câu hiện tại. “Chứa ý chính” chỉ là khớp cụm từ tự động,
không phải chấm toàn diện chất lượng LLM. Tập bổ sung vẫn còn ca chưa đạt về
học phí tiến sĩ; xem báo cáo bàn giao để biết giới hạn.

Tái tạo tài liệu RAG đã kiểm chứng từ PDF gốc:

```bash
python3 data/scripts/build_verified_rag_documents.py
```

Danh mục chương trình có thể xem qua `GET /api/programs` (lọc bằng `?search=`
hoặc chỉ chương trình đã có CTĐT bằng `?supported_only=true`).

Lấy dữ liệu học phần và chuỗi điều kiện trực tiếp từ CTT SIS (script sẽ mở
Chrome để bạn đăng nhập thủ công):

```bash
backend/.venv/bin/python data/scripts/scrape_ctt_courses.py --code ET4230
```

Xem thêm các tùy chọn và chế độ đọc HTML đã lưu tại
[`data/README.md`](data/README.md).

Tạo lại báo cáo candidate CTĐT công khai (review-only):

```bash
backend/.venv/bin/python data/scripts/build_hust_curriculum_candidates.py
```

Phê duyệt và sinh lại dataset ET1–2023 sau khi rà nguồn:

```bash
backend/.venv/bin/python data/scripts/promote_hust_curriculum_candidate.py \
  --candidate ET1-2023
```

---

## 🚀 Cấu trúc thư mục

```text
.
├── backend/                   # FastAPI Backend Service
│   ├── app/
│   │   ├── api/               # Các RESTful API Routers (chat, conversations, courses, student, rag, auth)
│   │   ├── core/              # Quy chế HUST (hust_rules.py), Cấu hình (config.py)
│   │   ├── engine/            # Rule Engine, Recommender (Graph là phần mở rộng)
│   │   ├── rag/               # RAG Engine, Document Loader, Chroma Vector Store, Gemini Service
│   │   └── services/          # Chatbot, Conversation, Data Loader, Student Service
│   ├── requirements.txt       # Các thư viện Python phụ thuộc
│   └── run.py                 # Script khởi động Backend server
├── data/                      # Cơ sở dữ liệu và kho tri thức
│   ├── documents/             # Văn bản quy chế, CTĐT, đề cương chi tiết (Markdown)
│   ├── processed/             # CTĐT JSON có phiên bản (không chứa hồ sơ cá nhân)
│   └── scripts/               # Scripts tạo demo profiles, crawl/chuẩn hóa dữ liệu
├── eval/                      # Bộ câu hỏi đánh giá, ngưỡng và báo cáo
├── frontend/                  # Ứng dụng Web React (Vite)
│   └── src/
│       ├── components/        # ChatTab, AuditTab, RecommendTab, Modals
│       └── App.jsx            # Giao diện chính điều hướng Tabs
└── scripts/                   # Cài đặt và chạy toàn bộ kiểm thử
```

---

## 🛠️ Hướng dẫn cài đặt và chạy thử

### 0. Cài đặt
```bash
./scripts/setup.sh
cp backend/.env.example backend/.env  # bắt buộc cấu hình MongoDB
```

MongoDB là bắt buộc. Không cần Gemini API key để demo: hệ thống sẽ dùng chế độ trích xuất cục bộ có dẫn nguồn. Nếu có key, điền `GEMINI_API_KEY` và model trong `.env`.

### 1. Khởi động Backend (FastAPI)

PowerShell trên Windows:

```powershell
cd backend
& ./.venv-win/Scripts/python.exe run.py
```

Linux/macOS:

```bash
cd backend
./.venv/bin/python run.py
```

Git Bash trên Windows dùng `./.venv-win/Scripts/python.exe run.py`.
* Backend sẽ chạy tại: `http://localhost:8000`
* Swagger API Docs: `http://localhost:8000/docs`

### 2. Khởi động Frontend (React + Vite)
```bash
cd frontend
npm ci
npm run dev
```
* Giao diện Web sẽ chạy tại: `http://localhost:5173`
* Local mặc định chuyển tiếp `/api` tới `http://127.0.0.1:8000` qua Vite. Nếu cần đổi backend, sửa `server.proxy` trong `vite.config.js`; chỉ đặt `VITE_API_BASE_URL` khi muốn gọi API trực tiếp và đã cấu hình cookie/CORS phù hợp. Khi deploy, cần reverse proxy `/api` hoặc cấu hình URL API riêng.

---

## 🎯 Kịch bản Demo tiêu biểu phục vụ Báo cáo

1. **Hỏi đáp tự nhiên có từ lóng sinh viên:** *"Kỳ tới em muốn học vxl và dts thì cần những môn gì trước?"* -> Hệ thống tự bóc tách mã môn `ET3300` và `ET3220`, kiểm tra điều kiện học trước và trả lời chính xác.
2. **Kiểm tra điều kiện học phần:** *"Điều kiện học môn Hệ điều hành là gì?"* -> Rule Engine giải thích các phương án điều kiện và đối chiếu với bảng điểm cá nhân.
3. **Tra cứu quy chế đào tạo (RAG):** *"Quy định cảnh cáo học tập mức 1 được đăng ký tối đa bao nhiêu tín chỉ?"* -> RAG trích dẫn chính xác Điều khoản trong Quy chế Đào tạo ĐHBK Hà Nội.
4. **Rà soát tốt nghiệp (Audit Tab):** Tiến độ được tính theo đúng phiên bản CTĐT; ET1–2022 có 126 tín chỉ, ET1–2023 có 132 tín chỉ, còn Ngoại ngữ/GDTC/GDQP được theo dõi tách biệt.

5. **Lịch sử hội thoại:** Gửi vài câu hỏi, tải lại trang hoặc chọn một mục trong “Gần đây” để kiểm tra hội thoại được khôi phục từ MongoDB. Các nút ghim, lưu trữ và xóa cập nhật bản ghi hội thoại tương ứng.


## Phạm vi bàn giao

Đã có tài khoản/phiên riêng, nhập bảng điểm có xác nhận dữ liệu thiếu, kiểm tra
điều kiện học phần, audit theo phiên bản CTĐT, RAG có nguồn, lịch sử/context và
memory do sinh viên quản lý. Tool Calling do LLM điều phối, planner nhiều kỳ,
mô phỏng CPA theo mục tiêu cá nhân và smart alerts là hướng phát triển tiếp.
