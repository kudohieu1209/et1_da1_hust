# HUST Course Advisor & Degree Audit Engine

> **Đồ án 1 (HUST - 2026.1):** Hệ thống Chatbot và Dashboard tư vấn học tập, chọn môn và rà soát tiến độ cho sinh viên Đại học Bách Khoa Hà Nội. Bản thử nghiệm hỗ trợ CTĐT ET1–2022 và ET1–2023 (đã đối chiếu thủ công) cùng 10 CTĐT nhập từ tài liệu công khai qua kiểm tra tự động.  
> **Sinh viên thực hiện:** Mai Duy Hiếu  

---

## 📌 Giới thiệu đề tài

Hệ thống **HUST Course Advisor** là một giải pháp ứng dụng trí tuệ nhân tạo lai (**Hybrid AI Agent**) nhằm giải quyết bài toán tư vấn học tập, lựa chọn môn học và rà soát tiến độ tốt nghiệp cho sinh viên Bách Khoa:
1. **RAG Pipeline (Retrieval-Augmented Generation):** Kết hợp mô hình Gemini LLM với cơ sở dữ liệu vector ChromaDB để giải đáp quy chế đào tạo, chuẩn đầu ra và đề cương môn học chính xác có kèm trích dẫn nguồn.
2. **Deterministic Rule Engine:** Sử dụng dữ liệu CTĐT và bộ quy tắc HUST để kiểm tra điều kiện học phần, rà soát tín chỉ (Degree Audit) theo từng hồ sơ sinh viên và hỗ trợ chọn môn.
3. **Full-stack Interactive Dashboard:** Giao diện React tập trung vào chat tự nhiên, tiến độ học tập và gợi ý chọn môn theo các mô-đun của chương trình đào tạo đang được hỗ trợ.

## Kết quả đánh giá

Hệ thống được đánh giá tự động trên 108 câu hỏi hồi quy và 20 câu hỏi diễn đạt khác (không dùng khi tinh chỉnh), chế độ không gọi LLM để kết quả lặp lại được:

| Bộ câu hỏi | Phân loại ý định | Truy xuất đúng văn bản (Recall@4) | Câu trả lời chứa ý chính |
|---|---:|---:|---:|
| Hồi quy (108 câu) | 100% | 98,6% | 100% |
| Diễn đạt khác (20 câu) | 100% | 100% | 100% |

Chi tiết: [bộ hồi quy](eval/reports/final.md), [bộ diễn đạt khác](eval/reports/validation_final.md). Chạy toàn bộ kiểm thử: `./scripts/test_all.sh`.

---

## 🏛️ Kiến trúc hệ thống (System Architecture)

```mermaid
graph TD
    User([Sinh viên HUST]) <--> UI[Frontend: React 19 + CSS Dashboard]
    UI <--> API[FastAPI Gateway RESTful API]
    
    subgraph Backend_Core ["Hệ thống Xử lý Trung tâm (Backend)"]
        API <--> Router[Intent Classifier & Course Entity Extractor]
        
        Router -->|Câu hỏi quy chế / Đề cương| RAG[RAG Pipeline]
        Router -->|Kiểm tra điều kiện học phần| Rule[HUST Rule Engine]
        Router -->|Rà soát tốt nghiệp / Tín chỉ| Rule
        Router -->|Gợi ý môn kỳ tới theo chuyên ngành| Rec[Course Recommender]
        
        RAG <--> Chroma[(ChromaDB Vector Store)]
        RAG <--> Gemini[Google Gemini LLM / Flash]
        
        Rule <--> CurriculumDB[(Dữ liệu CTĐT & điều kiện)]
        Rule <--> StudentData[("Hồ sơ sinh viên: Điểm, CPA, Cảnh cáo")]
        Rec <--> CurriculumDB
        API <--> ChatDB[("MongoDB: users, sessions, profiles, conversations, memory")]
    end
```

## Trạng thái dữ liệu hiện tại

- Đã chuẩn hóa và kiểm tra: **ET1, CTĐT 2022 (K67)** — 126 tín chỉ, 117 học phần, 20 nhóm và 6 mô-đun; **ET1, CTĐT 2023 (K68)** — 132 tín chỉ, 79 học phần, 13 nhóm và 5 mô-đun.
- Backend chọn CTĐT theo mã ngành và khóa nhập học của hồ sơ (K## ↔ năm 1955+##). Dataset có trường `applies_to_cohorts` chỉ phục vụ đúng các khóa đó; dataset không có trường này phục vụ khóa trùng năm phiên bản (ET1: K67 → 2022, K68 → 2023). Không tự chuyển sang phiên bản khác; hai dataset cùng phục vụ một khóa bị từ chối khi nạp.
- Nhập từ tài liệu CTĐT công khai, **kiểm tra tự động, chưa đối chiếu thủ công**: BF1–2022 (K68, K69), BF-E19–2023 (K68, K69), BF-E19–2025 (K70), ED2–2024 (K68), EE1–2023 (K68), EE2–2023 (K68), ET2–2023 (K68), EV2–2022 (K68, K69), FL2–2022 (K67, 131 TC), TE-EP–2023 (K68, K69; 140 TC phần cử nhân). Mỗi dataset ghi nhãn này ở cảnh báo đầu tiên, và giao diện hiển thị lại khi rà soát tiến độ. Kết quả đầy đủ, gồm 81 tài liệu chưa đạt và lý do, ở `data/reports/official_curricula_import.md`.
- Nguồn chuẩn hóa: `data/processed/curricula/et1_2022.json` và `data/processed/curricula/et1_2023.json`. HTML CTT gốc có dữ liệu cá nhân, không được đưa vào dataset sinh ra hoặc công khai.
- Đã bổ sung snapshot danh mục **68 chương trình đại học** từ trang tuyển sinh chính thức: `data/raw/hust_undergraduate_programs.json`. Đây là danh mục lựa chọn/tìm kiếm; trường `supported_cohorts` cho biết các khóa đã có CTĐT được nạp, và màn hình đăng ký lấy danh sách ngành từ đây.
- Đã rà liên kết CTĐT trên trang chi tiết của cả 68 chương trình: `data/raw/hust_program_curriculum_sources.json`. Manifest lưu nguồn chính thức và trạng thái truy cập (snapshot hiện tại: 46 nguồn HTTP 2xx); dữ liệu này chưa được coi là CTĐT chuẩn hóa cho đến khi kiểm tra cấu trúc và điều kiện học phần.
- Đã có bước trích xuất candidate cho 6 trang CTĐT HTML (5 trang `hp-table` và FL2 dạng bảng thông thường) cùng 6/8 PDF có danh mục học phần (`data/raw/hust_curriculum_extractions.json`, `data/raw/hust_curriculum_pdf_extractions.json`).
- Đã ghép 14 candidate HTML/PDF với danh mục 8.310 học phần CTT (`data/raw/hust_curriculum_candidates.json`). ET1-2023 đã được phê duyệt qua `data/processed/curriculum_approvals.json`; các candidate còn lại vẫn `needs_review` và chưa nạp vào Rule Engine.
- **MongoDB là kho nghiệp vụ duy nhất**: `users`, `sessions`, `student_profiles`, `conversations`, `messages`, `student_memory` và bộ đếm `counters`. Backend bắt buộc có `MONGODB_URI`; không còn nhánh SQLite hay ghi hồ sơ JSON. CTĐT và tài liệu nguồn vẫn là dataset có phiên bản. ChromaDB chỉ phục vụ RAG; file SQLite nội bộ của Chroma được giữ nguyên.
- Hội thoại dùng context từ 12 tin nhắn gần nhất của đúng tài khoản; hiểu “môn đó cần gì?”, “nếu trượt thì sao?”, yêu cầu làm rõ khi có nhiều môn. Lịch sử client gửi lên không được dùng để thiết lập context.
- **Cài đặt → Ghi nhớ học tập**: tự chọn bật/tắt, sửa hoặc xóa định hướng, tải tín chỉ mong muốn và mục tiêu CPA. Mặc định tắt; chatbot không tự trích xuất mục tiêu từ tin nhắn. Gợi ý môn dùng định hướng/tín chỉ đã lưu, ưu tiên lựa chọn trong câu hỏi và luôn áp giới hạn học vụ. CPA hiện được lưu và nhắc lại, chưa có bộ mô phỏng điểm theo mục tiêu cá nhân.
- Kho RAG tin cậy hiện gồm 14 tài liệu: CTĐT ET1–2022, ET1–2023, Quy chế đào tạo theo Quyết định 5445/QĐ-ĐHBK, Sổ tay sinh viên 2026, Quyết định học phí 2025–2026 và 2026–2027, Kế hoạch năm học 2026–2027, Quy chế công tác sinh viên, Quy định đánh giá rèn luyện, Quy định chuẩn ngoại ngữ K70 và K71, Quy định miễn giảm học phí, Quy định học bổng Trần Đại Nghĩa và học bổng trao đổi. Các văn bản quy chế, học phí, học bổng áp dụng cho sinh viên mọi ngành; chỉ phần CTĐT là riêng ET1. Chỉ tài liệu có metadata `rag_status: VERIFIED` mới được lập chỉ mục; PDF cần sidecar `<tên-file>.pdf.metadata.json` có trạng thái tương ứng. Kho được đồng bộ lại khi khởi động để loại nguồn đã thu hồi phê duyệt.
- Sinh viên đăng nhập bằng **MSSV + mật khẩu** (tự đăng ký); phiên nằm trong cookie HttpOnly, mỗi người chỉ thấy hồ sơ, bảng điểm và hội thoại của mình. Hiện chạy trên máy cục bộ; chưa triển khai Internet/HTTPS hay trang quản trị người dùng.

### Chuẩn bị trên máy mới

Cần **Python 3.12 trở lên**, **Node.js 22.12 trở lên** và MongoDB (local hoặc
Atlas). Không cần MongoDB hay khóa Gemini để chạy kiểm thử; ứng dụng thật cần
`MONGODB_URI`. Phạm vi thử nghiệm: ET1–2022/K67, ET1–2023/K68 và 10 CTĐT nhập tự động nêu trên.

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

`eval/golden_questions.jsonl` gồm **108 câu hỏi hồi quy**, có bằng chứng/ý chính đối chiếu
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
`eval/reports/baseline.md` là kết quả trước khi cải tiến truy xuất (96 câu), dùng để so sánh với `final.md`.
“Chứa ý chính” là khớp cụm từ tự động, không phải chấm toàn diện chất lượng LLM.

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

Nhập lại các CTĐT công khai đã trích xuất (mỗi ngành một tệp JSON). Chỉ tài liệu qua mọi kiểm tra (tổng ngưỡng các khối bằng tổng công bố, số TC khớp danh mục CTT, không trùng khóa) mới được ghi vào `data/processed/curricula/` và `curriculum_approvals.json`:

```bash
backend/.venv/bin/python data/scripts/import_official_curricula.py \
  --input-dir <thư-mục-JSON-trích-xuất>
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

## 🎯 Một số tình huống sử dụng

| Tình huống | Ví dụ câu hỏi của sinh viên | Cách hệ thống xử lý |
|---|---|---|
| Hỏi bằng tên viết tắt | “Kỳ tới em muốn học vxl và dts thì cần những môn gì trước?” | Nhận ra `ET3300` (Kỹ thuật vi xử lý) và `ET3220` (Điện tử số), tra điều kiện học trước trong CTĐT. |
| Kiểm tra điều kiện học phần | “Điều kiện học môn Hệ điều hành là gì?” | Rule Engine liệt kê các phương án điều kiện và đối chiếu với bảng điểm của sinh viên. |
| Tra cứu quy chế | “Đang bị cảnh báo học tập mức 1 được đăng ký tối đa bao nhiêu tín chỉ?” | Truy xuất điều khoản trong Quy chế đào tạo và trả lời kèm nguồn, số trang. |
| Học phí, học bổng | “Học phí ngành ET1 năm 2026–2027 là bao nhiêu?”, “Học bổng Trần Đại Nghĩa xét thế nào?” | Chọn đúng văn bản và năm học áp dụng, trích dẫn quyết định tương ứng. |
| Rà soát tiến độ tốt nghiệp | Mở tab Tiến độ | Tính theo đúng phiên bản CTĐT của khóa (ET1–2022: 126 TC, ET1–2023: 132 TC); Ngoại ngữ, GDTC, GDQP theo dõi riêng. |
| Hội thoại nhiều lượt | “Môn đó cần gì?”, “Nếu trượt thì sao?” | Hiểu ngữ cảnh từ các tin nhắn trước; lịch sử được lưu theo tài khoản và có thể ghim, lưu trữ, xóa. |

## Kết quả đạt được và hướng phát triển

**Đã thực hiện**

- Đăng nhập bằng MSSV, mỗi sinh viên chỉ xem được hồ sơ và hội thoại của mình.
- Nhập bảng điểm, có bước xác nhận khi dữ liệu thiếu.
- Kiểm tra điều kiện học phần và rà soát tiến độ theo phiên bản CTĐT.
- Hỏi đáp quy chế, học phí, học bổng, rèn luyện, ngoại ngữ có trích dẫn nguồn từ 14 văn bản chính thức của trường.
- Lưu lịch sử hội thoại và ghi nhớ học tập do sinh viên tự quản lý.

**Giới hạn hiện tại**

- Rule Engine có CTĐT đối chiếu thủ công của ET1 (2022 và 2023) và 10 CTĐT chỉ qua kiểm tra tự động; các ngành còn lại chưa có CTĐT đủ tin cậy. Phần hỏi đáp quy chế dùng được cho sinh viên mọi ngành.
- Hệ thống chạy trên máy cục bộ, chưa triển khai công khai qua Internet.

**Hướng phát triển**

- Bổ sung tổng tín chỉ, phiên bản và khóa áp dụng cho các tài liệu chưa đạt, rồi đối chiếu thủ công các CTĐT nhập tự động.
- Để LLM tự gọi công cụ (Tool Calling) thay cho bộ phân loại ý định.
- Lập kế hoạch học tập nhiều kỳ, mô phỏng CPA theo mục tiêu và cảnh báo học vụ chủ động.
