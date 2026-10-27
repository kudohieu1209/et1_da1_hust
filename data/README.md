# Data pipeline

Thư mục này phân tách ba lớp dữ liệu:

- `raw/`: bản chụp nguồn, không chỉnh sửa bằng tay.
- `processed/curricula/`: dataset CTĐT có phiên bản, sinh tự động từ nguồn.
- `documents/`: tài liệu cho RAG; chỉ index tài liệu đã xác minh.

## ET1 2022

Nguồn hiện tại là bản HTML CTT của Chương trình 1654. File nguồn có
thông tin cá nhân và bảng điểm; không được public file này. Dataset sinh ra chỉ
chứa cấu trúc CTĐT, không chứa danh tính hay kết quả học tập.

Sinh lại dataset và báo cáo:

```bash
backend/.venv/bin/python data/scripts/build_curriculum.py
backend/.venv/bin/python data/scripts/build_curriculum_document.py
backend/.venv/bin/python data/scripts/audit_curriculum_conflicts.py
```

Kiểm tra dataset:

```bash
backend/.venv/bin/python data/scripts/validate_curriculum.py
backend/.venv/bin/python -m unittest discover -s data/tests -v
```

Nguồn đích:

- `processed/curricula/et1_2022.json`
- `documents/ctt_et1_2022_verified.md` (sinh tự động cho RAG)
- `reports/et1_2022_conflicts.md`
- `schemas/curriculum.schema.json`

Không sửa trực tiếp file trong `processed/curricula/`. Mọi thay đổi phải đi từ bản
nguồn hoặc parser để hash nguồn và kết quả validation vẫn có ý nghĩa.

## Lấy danh sách học phần từ CTT SIS

`scripts/scrape_ctt_courses.py` giữ nguyên cột **HP điều kiện** (bao gồm các
ký hiệu `/`, `,`, `!`, `=`) để bước parser phía sau có thể kiểm chứng AND/OR.
Trang CTT hiện yêu cầu đăng nhập, vì vậy script mở một Chrome riêng và chờ bạn
đăng nhập thủ công; mật khẩu không đi qua script.

Cài Playwright một lần:

```bash
backend/.venv/bin/python -m pip install playwright
backend/.venv/bin/python -m playwright install chromium
```

Thu thập 117 mã môn trong dataset thử nghiệm hiện tại:

```bash
backend/.venv/bin/python data/scripts/scrape_ctt_courses.py
```

Muốn thử một mã trước (nên làm vậy khi kiểm tra quyền truy cập):

```bash
backend/.venv/bin/python data/scripts/scrape_ctt_courses.py --code ET4230
```

Kết quả mặc định nằm ở `raw/ctt_courses_scraped.json`. Có thể dùng `--all`
để quét toàn bộ danh sách 8.310 dòng; script thử xin 200 dòng/trang và tự rơi
về cấu hình 15 dòng/trang nếu máy chủ không cho đổi (dùng `--page-size 15`
nếu muốn giữ cấu hình mặc định).
Để kiểm tra file HTML đã lưu mà
không cần Playwright:

```bash
backend/.venv/bin/python data/scripts/scrape_ctt_courses.py \
  --html raw/course_conditions.html.html --all \
  --output /tmp/ctt-page.json
```

File đầu ra là bản chụp thô có `source_url`, thời điểm lấy, trang và
`raw_condition`; chưa tự động ghi đè dataset CTĐT hay áp dụng điều kiện.

## Danh mục ngành/chương trình

`scripts/scrape_hust_programs.py` lấy danh mục chương trình đại học từ trang
tuyển sinh chính thức. Snapshot hiện tại có 68 chương trình, gồm mã xét tuyển,
tên, ngôn ngữ, đơn vị đào tạo, chỉ tiêu và tổ hợp xét tuyển:

```bash
backend/.venv/bin/python data/scripts/scrape_hust_programs.py \
  --output data/raw/hust_undergraduate_programs.json
```

Nếu môi trường Python thiếu chứng chỉ CA, thêm `--insecure` khi chạy và chỉ
dùng kết quả này như một snapshot đã kiểm tra. Danh mục này không được coi là
CTĐT: API đánh dấu `curriculum_supported: true` chỉ cho chương trình đã có
JSON CTĐT được chuẩn hóa (hiện ET1 có phiên bản 2022 và 2023).

Để rà các liên kết CTĐT mà từng trang ngành trỏ tới, chạy:

```bash
backend/.venv/bin/python data/scripts/discover_hust_curriculum_sources.py \
  --insecure --output data/raw/hust_program_curriculum_sources.json
```

Manifest này đã ghi nhận liên kết nguồn cho 68/68 ngành và trạng thái truy cập,
loại nguồn (HTML/PDF/bảng tính), số bảng và số mã học phần quan sát được. Ở
snapshot hiện tại có 46 nguồn trả HTTP 2xx; các nguồn còn lại trả 403/404 hoặc
không phân giải được, nên cần rà lại liên kết tại website viện/khoa. Đây chỉ là
bước thu thập nguồn; mỗi CTĐT vẫn phải được chuẩn hóa, đối chiếu điều kiện học
phần và kiểm tra trước khi đưa vào `processed/curricula/`.

Một số trang khoa chỉ là trang giới thiệu và gắn PDF/XLSX ở bên trong. Có thể
tải thêm tối đa 5 tệp đính kèm có đuôi tài liệu cho mỗi nguồn HTML:

```bash
backend/.venv/bin/python data/scripts/download_hust_curriculum_sources.py \
  --insecure --follow-attachments \
  --output data/raw/hust_program_curriculum_downloads.json \
  --output-dir data/raw/program_sources
```

PDF được đọc bảo thủ ở riêng một bước:

```bash
backend/.venv/bin/python data/scripts/extract_hust_curriculum_pdfs.py \
  --output data/raw/hust_curriculum_pdf_extractions.json
```

Với các trang HTML dùng bảng `hp-table`, có thể trích xuất candidate bằng:

```bash
backend/.venv/bin/python data/scripts/extract_hust_curriculum_tables.py \
  --output data/raw/hust_curriculum_extractions.json
```

Snapshot hiện đã trích xuất được 6 trang HTML (ET1, ET-E4, ET-E9, ET-E16,
ET-LUH và FL2) cùng 6/8 PDF có danh mục học phần,
bao gồm mã môn, tên, tín chỉ, học kỳ và nhóm/mô-đun. ET1-2023 đã được chuẩn hóa
và nạp vào Rule Engine sau bước phê duyệt rõ ràng; các candidate khác vẫn là dữ
liệu thô để đối chiếu vì thiếu phiên bản CTĐT, công thức tốt nghiệp hoặc điều kiện đăng ký.

Để ghép các candidate này với danh mục học phần CTT và tạo báo cáo kiểm tra tự
động (không kích hoạt luật), chạy:

```bash
backend/.venv/bin/python data/scripts/build_hust_curriculum_candidates.py \
  --output data/raw/hust_curriculum_candidates.json
```

File `raw/hust_curriculum_candidates.json` (hiện 14 candidate HTML/PDF) ghi rõ mã môn không có trong CTT,
chênh lệch tín chỉ, ngưỡng tín chỉ bắt buộc còn thiếu, độ phủ điều kiện đăng ký
và công thức tín chỉ suy ra. ET1-2023 có phê duyệt trong
`processed/curriculum_approvals.json` và dataset tại
`processed/curricula/et1_2023.json`; các candidate còn lại vẫn có trạng thái
`needs_review`/`rule_engine_eligible: false`.

Bước phê duyệt có kiểm soát cho candidate đã rà xong được ghi trong
`processed/curriculum_approvals.json`. Hiện ET1-2023 đã được sinh thành dataset
được hỗ trợ bằng lệnh:

```bash
backend/.venv/bin/python data/scripts/promote_hust_curriculum_candidate.py \
  --candidate ET1-2023 \
  --output data/processed/curricula/et1_2023.json
```

Bản tóm tắt dễ đọc cho quá trình duyệt nằm ở
`reports/curriculum_candidates_review.md`.

Các tài liệu demo cũ có marker `RAG_STATUS: UNVERIFIED` được giữ lại để
đối chiếu, nhưng `DocumentLoader` sẽ không đưa chúng vào kho vector.


Ghi chú snapshot công khai: `raw/program_sources/TROY-IT.html` là trang Google
Drive đã lưu; các client API key nhúng từ trang gốc đã được ẩn. File này là bản
tham khảo ngoại tuyến, không phải nguồn CTĐT đã được phê duyệt cho Rule Engine.
