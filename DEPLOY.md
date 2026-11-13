# Đưa HUST Course Advisor lên Hugging Face Spaces

**Bản demo đồ án: không nhập bảng điểm hoặc mật khẩu thật.** Repo chỉ chuẩn bị
gói triển khai; các bước tạo dịch vụ và push bên dưới do chủ repo thực hiện.

1. **Tạo MongoDB Atlas Free (M0), vùng Singapore** nếu có trong lựa chọn nhà
   cung cấp. Tạo database user riêng, chỉ cấp `readWrite` cho database của app
   (mặc định `hust_course_advisor`), đặt mật khẩu mạnh và giữ kín chuỗi kết nối
   trong Connect → Drivers → Python. Trong Network Access thêm `0.0.0.0/0`
   vì IP đầu ra của Space có thể thay đổi. Quy tắc này cho phép mọi IP thử kết
   nối, làm tăng rủi ro dò mật khẩu; không cấp quyền quản trị cho user app.
   Xem [hướng dẫn Atlas](https://www.mongodb.com/docs/atlas/tutorial/deploy-free-tier-cluster/)
   và [IP access list](https://www.mongodb.com/docs/atlas/security/ip-access-list/).

2. **Tạo Space trên Hugging Face**, chọn SDK **Docker**, hardware **CPU basic
   miễn phí**. App dùng một image: Node 22 build React; Python 3.12 phục vụ cả
   API lẫn frontend ở cổng 7860. Chroma và mô hình embedding ONNX được tạo/tải
   lúc build, bằng user UID 1000; không cần MongoDB hay Gemini trong bước này.
   Khi chạy, app vẫn đồng bộ lại kho tri thức như local. Xem
   [Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker).

3. **Trong Settings → Variables and secrets**, thêm Secrets:

   | Tên | Giá trị |
   | --- | --- |
   | `MONGODB_URI` | Chuỗi Atlas do bạn tạo; mã hóa URL các ký tự đặc biệt trong mật khẩu |
   | `MONGODB_DB` | Tùy chọn; mặc định `hust_course_advisor`, phải khớp quyền database user |
   | `GEMINI_API_KEY` | Tùy chọn; bỏ trống thì trả lời trích xuất cục bộ có dẫn nguồn |
   | `CORS_ORIGINS` | `https://<user>-<space>.hf.space` (nhiều origin phân cách bằng dấu phẩy) |

   Không ghi URI/key vào repo hoặc gói đẩy. Image đặt `COOKIE_SECURE=true`,
   `PYTHON_DOTENV_DISABLED=1`; local vẫn mặc định cookie không Secure và đọc
   dotenv như trước. Uvicorn tin proxy headers của HF để xác định HTTPS;
   chỉ dùng cấu hình tin mọi proxy này khi container nằm sau proxy tin cậy.

4. **Chuẩn bị gói từ nhánh đã commit**, tại gốc repo:

   ```bash
   ./scripts/prepare_hf_space.sh /tmp/hust-advisor-space
   ```

   Đích phải ở ngoài repo, chưa tồn tại hoặc rỗng. Script chỉ copy danh sách
   file build cần thiết đã được Git theo dõi (lấy nội dung working tree hiện
   tại), thay README bằng bản có metadata Space, từ chối symlink và file lớn
   hơn 10.000.000 byte. Script không tự push và không cần token. Chạy chuỗi
   lệnh script in ra sau khi thay `<user>/<space>`; khi Git hỏi mật khẩu, dùng
   **HF access token loại write**, không dùng mật khẩu tài khoản. Lệnh có
   `push --force`, chỉ trỏ tới Space dành riêng cho app: nó thay lịch sử nhánh
   `main` của Space, không được trỏ tới repo GitHub của dự án.

5. **Mở đúng URL trực tiếp** `https://<user>-<space>.hf.space` được Space hiển
   thị. Trang `huggingface.co/spaces/...` nhúng app trong iframe; trình duyệt
   có thể chặn cookie đăng nhập ở đó. Kiểm tra trang chủ, `/docs`,
   `/api/health`, rồi đăng ký/đăng nhập bằng dữ liệu demo.

6. **Space miễn phí ngủ sau thời gian không dùng**; lần mở lại có thể chờ
   khởi động. Ổ đĩa container không bền: Chroma được dựng sẵn trong image và
   đồng bộ khi khởi động; tài khoản, phiên, hồ sơ và hội thoại lưu trên Atlas.
   Không dùng ổ đĩa container để lưu dữ liệu người dùng. Xem
   [Spaces overview](https://huggingface.co/docs/hub/spaces-overview).

7. **Cập nhật và chẩn đoán.** Sau khi sửa code, chạy kiểm thử, commit rồi tạo
   gói mới vào một thư mục rỗng và làm lại bước 4 với cùng remote Space; HF tự
   rebuild khi nhận commit. Xem **Build logs** và **Container/Run logs** trên
   trang Space. Thiếu `MONGODB_URI` làm backend dừng; kiểm tra tên Secret,
   restart sau khi sửa. Với lỗi Atlas, kiểm tra database user, mật khẩu được
   mã hóa URL, Network Access, DNS/TLS và cluster đang hoạt động. HF chỉ công
   bố hỗ trợ kết nối ra cổng 80, 443 và 8080, còn Atlas driver thường cần
   cổng 27017: **phải xác minh kết nối Atlas từ Space thật**. Nếu bị chặn,
   mở IP access list không khắc phục được; cần nền tảng cho phép kết nối
   MongoDB (hoặc hỗ trợ từ HF), không thể coi triển khai này đã live.
   Nếu build hết thời gian, xem bước pip/tải ONNX/embedding trong Build logs,
   thử rebuild khi mạng ổn định; không bỏ bước tạo vector DB. Các dependency
   hiện dùng ràng buộc phiên bản tối thiểu, nên bản mới có thể làm build
   thay đổi; cần kiểm tra lại log khi rebuild về sau.

## Dữ liệu được đưa vào image

| Đường dẫn | Lý do cần lúc build/chạy |
| --- | --- |
| `data/processed/curricula/` | 18 CTĐT có phiên bản cho tra cứu, điều kiện học phần và rà soát tiến độ |
| `data/processed/curriculum_approvals.json` | Danh sách phê duyệt để xác định phiên bản từ trích xuất nguồn |
| `data/documents/` | 14 văn bản Markdown đã phê duyệt, nguồn nạp chunks RAG lúc build và đồng bộ khi chạy |
| `data/raw/ctt_et_conditions.json` | Điều kiện đăng ký mà `DataLoader` đọc |
| `data/raw/hust_undergraduate_programs.json` | Danh mục ngành của `ProgramCatalog` |
| `data/raw/hust_program_curriculum_sources.json` | Nguồn CTĐT trong danh mục chương trình |
| `data/raw/hust_curriculum_candidates.json` | Các ứng viên CTĐT và phạm vi hỗ trợ |
| `data/raw/official_curricula/` | Bản trích xuất JSON để tra cứu CTĐT toàn trường |
| `data/raw/reviewed_curricula/` | Bản JSON đã rà soát, ghi đè trích xuất cùng ID trong `CurriculumReferences` |
| `data/vector_db/` | Được script sinh trong image; không copy index local, user 1000 có quyền ghi |

Không copy snapshot cũ `courses_et1.json`, `prerequisites_et1.json` hoặc hồ sơ
cá nhân local trong `processed`; backend dùng CTĐT có phiên bản. Các PDF thô
(kể cả `So tay sinh vien_2026.pdf`), `program_sources`, `reviewed_sources`,
`data/reviewed`, scripts thu thập dữ liệu, `eval`, `local-notes`, `tmp` không
được copy: backend đã đọc các JSON/Markdown chuẩn hóa, không mở các kho nguồn
này trong chuỗi runtime. Không đưa `.env`, venv, node_modules hay vector DB
của máy phát triển vào build context.

## Kiểm tra local

`backend/run.py` vẫn phục vụ cổng 8000; `npm --prefix frontend run dev` vẫn
proxy `/api` từ cổng 5173. Có `frontend/dist/index.html` thì backend phục vụ
SPA; nếu muốn kiểm tra nhánh dev khi đã build, đặt `FRONTEND_DIST_DIR` tới
một đường dẫn chưa tồn tại. Có thể build riêng index không cần MongoDB/key:

```bash
VECTOR_DB_DIR=/tmp/hust-vector-build backend/.venv/bin/python backend/scripts/build_vector_db.py
```

Chưa có Docker trên máy phát triển thì không thay kiểm tra build thật bằng
khẳng định image chạy được. Cần kiểm chứng build image, kết nối Atlas, proxy
HTTPS và cookie trên Space sau khi chủ repo cấu hình dịch vụ.
