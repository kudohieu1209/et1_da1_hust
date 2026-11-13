# Deploy HUST Course Advisor lên Render

Một Web Service Docker phục vụ FastAPI và frontend React trên cùng URL HTTPS. Đích là Render Free (512 MB RAM, 0,1 CPU), phù hợp bản demo đồ án. Không nhập bảng điểm hoặc mật khẩu thật vào bản demo.

Hướng Hugging Face trong kế hoạch trước đã được bỏ: môi trường Space dự kiến dùng cần gói trả phí, còn kết nối ra ngoài chỉ qua cổng 80/443/8080 không đáp ứng MongoDB Atlas ở cổng 27017. Không còn script đóng gói Space; dùng Render và Atlas theo các bước dưới đây.

## 1. Chuẩn bị MongoDB Atlas

- Dùng cluster sẵn có **`hust-advisor`**; không cần tạo lại cluster.
- Trong Database Access, tạo user riêng **`hust-live`**, mật khẩu mạnh và quyền `readWrite` chỉ trên database **`hust_course_advisor_live`**. Database riêng tránh trộn tài khoản/hồ sơ demo với dữ liệu thử nghiệm local.
- Trong Network Access, thêm **`0.0.0.0/0`** để chấp nhận kết nối từ IP outbound của Render. Đây là mở truy cập mạng từ toàn Internet, làm tăng bề mặt tấn công; vẫn bắt buộc xác thực, dùng TLS, mật khẩu mạnh, quyền tối thiểu và không công khai URI. Khi biết các dải outbound cụ thể trong Render Dashboard, nên thu hẹp allowlist về những dải đó.
- Lấy connection string bằng Connect → Drivers. Thay user/mật khẩu trong giao diện Secrets của Render. Ký tự đặc biệt trong user/mật khẩu (như `@`, `:`, `/`, `#`) phải được URL-encode. Không lưu URI thật vào repo hoặc dán vào log.

## 2. Đưa nhánh deploy lên GitHub

Chủ repo tự chạy (phiên chuẩn bị này không push):

```bash
git switch deploy/render
git push -u origin deploy/render
```

Repo GitHub là **`kudohieu1209/et1_da1_hust`**. Không push file `.env`, token hay dữ liệu cá nhân. Không cần thay đổi nhánh `main` hoặc `deploy/hf-spaces`.

## 3. Tạo dịch vụ Render

1. Đăng nhập Render bằng GitHub và cấp quyền đọc repo `et1_da1_hust`.
2. Chọn **New → Blueprint**, chọn repo và nhánh **`deploy/render`**. Render đọc `render.yaml` ở gốc repo.
3. Kiểm tra service `hust-course-advisor`: runtime **Docker**, plan **Free**, region **Singapore**, health check **`/api/health`**.
4. Nếu tạo thủ công bằng **New → Web Service**: chọn cùng repo/nhánh, Dockerfile `./Dockerfile`, build context gốc repo, plan Free, Singapore; tắt Auto-Deploy và nhập các biến ở bước 4. Không điền start command để Render dùng CMD của image.

Blueprint giữ `autoDeploy: false` theo kế hoạch. [Tài liệu Blueprint](https://render.com/docs/blueprint-spec) hiện vẫn hỗ trợ trường này nhưng đánh dấu deprecated (trường thay thế là `autoDeployTrigger: off`); `region: singapore` là giá trị hợp lệ. [Tài liệu vùng](https://render.com/docs/regions) và [giới hạn Free](https://render.com/docs/free) không nêu hạn chế Singapore cho Free Web Service.

## 4. Điền biến môi trường

| Biến | Giá trị / ý nghĩa |
|---|---|
| `MONGODB_URI` | **Bắt buộc**, connection string Atlas của user `hust-live`; nhập dưới dạng secret, không commit. |
| `MONGODB_DB` | `hust_course_advisor_live` (Blueprint đã đặt). |
| `GEMINI_API_KEY` | Tuỳ chọn, có thể để trống. Khi chưa có key, app trả lời bằng trích xuất cục bộ và dẫn nguồn. Blueprint dùng `sync: false`; nếu giao diện yêu cầu nhập trước khi tạo, có thể bỏ mục key này rồi thêm sau trong Environment. |
| `COOKIE_SECURE` | `true` trên Render; cookie chỉ gửi qua HTTPS. |
| `RAG_VECTOR_SEARCH` | `off` trong Docker/Render: chỉ BM25, không import ChromaDB hoặc nạp ONNX/embedding. Local mặc định `on` (hybrid). Chỉ chấp nhận `on` / `off`. |
| `RAG_SYNC_ON_STARTUP` | `auto` (mặc định) / `always`: với BM25 chỉ nạp chunk đã duyệt vào RAM, không embed; `never` nạp lười khi truy vấn hoặc xem trạng thái lần đầu. Với hybrid: `auto` đối soát manifest, `always` nhúng lại toàn bộ, `never` bỏ đồng bộ lúc khởi động. |
| `RENDER_EXTERNAL_URL` | Render tự đặt URL công khai; app tự thêm URL vào CORS và danh sách origin hợp lệ cho CSRF. Không cần tự đặt. |
| `CORS_ORIGINS` | Tuỳ chọn, danh sách origin bổ sung ngăn cách dấu phẩy; cơ chế cùng origin vẫn hoạt động. |
| `PORT` | Render tự cấp (thường `10000`); CMD dùng biến này, mặc định `7860` khi chạy image nơi khác. |

Không đưa secret vào Docker build arguments. Image không tạo vector DB hoặc cache embedding; dotenv đã tắt. Chỉ các biến môi trường runtime mới cần thông tin Atlas.

## 5. Deploy và kiểm tra

- Bấm tạo Blueprint / Deploy. Xem **Events → build log**: frontend và dependencies phải build thành công; không có bước tạo vector DB hoặc tải mô hình.
- Image chạy dưới user UID 1000, không cần vector DB hay persistent disk cho RAG. Vẫn giữ dependencies Chroma và `libstdc++6` để hỗ trợ bật lại hybrid khi cần; chúng không được import trong chế độ chỉ BM25.
- Xem **Logs** lúc chạy: phải thấy **`RAG: chế độ chỉ BM25`**, hiện tại 1.449 chunk đã duyệt, sau đó `Application startup complete`. `/api/rag/status` báo `mode: bm25_only`, số chunk và nguồn, không báo lỗi vector DB.
- Mở **`https://<tên>.onrender.com`**, đăng ký tài khoản giả và thử ít nhất 5 câu hỏi quy chế. Kiểm tra `/api/health` trả `{"status":"healthy"}`, `/api/system` trả JSON, `/docs` vẫn hiển thị Swagger, tải lại một route frontend không lỗi 404.
- Kiểm tra mục Metrics / log về RAM. Mục tiêu đo local sau truy vấn BM25 là peak RSS dưới 250 MB; giới hạn container còn phải chứa các chi phí runtime khác, nên đây không phải bảo đảm chạy được trên 512 MB.

Docker chạy đúng **1 worker**, không reload, bật proxy headers và tin proxy phía Render để nhận đúng HTTPS. Không phơi trực tiếp cổng container ra Internet ở một hạ tầng có proxy không đáng tin.

SDK Gemini chỉ được nạp khi có key hoặc khi thực sự gọi Gemini; chế độ trích xuất cục bộ không phải giữ SDK này trong RAM. RAM sẽ tăng nếu bật key, cần đo lại trên service thật.

Ngoài giới hạn arena, image đặt `MALLOC_TRIM_THRESHOLD_=131072` để glibc trả các vùng nhớ rảnh sau những bước xử lý lớn sớm hơn; đánh đổi có thể là thêm chi phí cấp phát bộ nhớ.

## 6. Ngủ, cập nhật và phương án dự phòng

[Render Free](https://render.com/docs/free) ngủ sau 15 phút không có traffic; lần mở lại có thể chờ khoảng 1 phút. File phát sinh trong container mất khi restart/redeploy/ngủ. Tài khoản và hồ sơ nằm trên Atlas nên được giữ; chỉ mục BM25 được dựng lại từ tài liệu đã duyệt trong image. Thay đổi corpus cần đưa vào lần build tiếp theo.

Khi sửa code: commit/push nhánh deploy rồi chọn **Manual Deploy → Deploy latest commit**. Auto-Deploy đã tắt. Xem cả build log lẫn runtime log sau mỗi lần cập nhật. Free có giới hạn giờ chạy, bandwidth và build pipeline theo workspace; theo dõi Billing/usage.

Nếu log báo **out of memory** hoặc service restart khi hỏi RAG: kiểm tra `RAG_VECTOR_SEARCH=off`, log chế độ chỉ BM25 và giữ một worker. Image đã đặt các giới hạn luồng/allocator trong Dockerfile. Nếu vẫn vượt RAM, đo lại khi bật Gemini và chuyển sang instance trả phí đủ RAM hoặc nơi chạy khác.

### Chất lượng và bật lại hybrid

Bản live dùng chỉ BM25 vì giới hạn RAM: hybrid đo trước đây peak khoảng 416 MB, riêng ONNX/embedding khoảng 250 MB, quá sát mức 512 MB của Render Free. Bộ hồi quy 108 câu: MRR BM25 **85,3%**, hybrid **84,3%**; bộ 20 câu diễn đạt khác: BM25 **77,2%**, hybrid **80,6%**. Recall@4, ý định và ý chính đều **100%** ở cả hai chế độ. Đây là đánh giá trích xuất cục bộ, không bảo đảm độ đúng của mọi câu trả lời LLM.

Khi có máy đủ RAM, bật lại hybrid bằng cách đổi `RAG_VECTOR_SEARCH=on` trong Dockerfile **và** Environment/Blueprint Render, rồi thêm bước sau vào Dockerfile sau `USER user` và `WORKDIR /home/user/app/backend` (trước `EXPOSE`):

```dockerfile
RUN python scripts/build_vector_db.py
```

Script có sẵn, không cần MongoDB/Gemini, tạo vector DB + manifest và cache mô hình dưới user runtime. Giữ `RAG_SYNC_ON_STARTUP=auto` để khởi động bỏ qua embedding khi index khớp; xác nhận `/api/rag/status` báo `hybrid`. Đo RAM lại trước khi đưa lên live. Local theo README vẫn mặc định hybrid, không cần thay biến cấu hình.

## 7. Lỗi thường gặp

- **Thiếu `MONGODB_URI`**: backend dừng ngay khi khởi tạo kho nghiệp vụ. Thêm secret rồi deploy lại.
- **Atlas chặn IP / timeout**: kiểm tra Network Access, cluster đang hoạt động và các dải outbound của service Render. Chạy trên Render vẫn cần Atlas cho phép truy cập mạng.
- **Sai mật khẩu / authentication failed**: kiểm tra user `hust-live`, quyền trên database live, URL-encode ký tự đặc biệt trong URI và `authSource` theo URI Atlas cung cấp.
- **Đăng nhập không giữ phiên**: mở đúng URL HTTPS của app; giữ `COOKIE_SECURE=true`. App và API dùng cùng origin.
- **Khởi động vẫn nhúng toàn bộ**: bản BM25 phải đặt `RAG_VECTOR_SEARCH=off`. Nếu chủ động bật hybrid, kiểm tra manifest `corpus_manifest.json` được tạo khi build, cùng model/phiên bản Chroma giữa build và run, số chunk và corpus không bị thay, `VECTOR_DB_DIR` không bị ghi đè sang thư mục rỗng.
- **Health check không lên**: xem lỗi import/Atlas/startup, xác nhận Render có `PORT`, CMD không bị override và health check `/api/health`.

## Dữ liệu trong image và chạy local

Docker chỉ copy dữ liệu công khai backend thật sự đọc:

- `data/documents/`: tài liệu được loader kiểm tra phê duyệt để làm RAG.
- `data/processed/curricula/` và `data/processed/curriculum_approvals.json`: CTĐT và trạng thái duyệt.
- `data/raw/ctt_et_conditions.json`: điều kiện học phần.
- `data/raw/hust_undergraduate_programs.json`, `hust_program_curriculum_sources.json`, `hust_curriculum_candidates.json`: danh mục ngành và nguồn/ứng viên CTĐT.
- `data/raw/official_curricula/` và `data/raw/reviewed_curricula/`: bản nguồn công khai mà endpoint tài liệu CTĐT phục vụ.

Không đưa `backend/.env`, dữ liệu cá nhân, bản PDF sổ tay 110 MB, `data/raw/program_sources/`, `data/raw/reviewed_sources/`, `eval/`, `local-notes/`, `tmp/`, test hay venv vào image. `.dockerignore` chặn các phần này.

Hành vi local theo README giữ nguyên: `backend/run.py` chạy cổng 8000 với reload, Vite cổng 5173 proxy `/api`, cookie mặc định không bắt buộc HTTPS. Không cần đặt các biến riêng của Docker khi chạy local; mặc định `auto` vẫn đối soát corpus và đồng bộ nếu có thay đổi.
