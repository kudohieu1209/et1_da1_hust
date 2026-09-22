# Hàng đợi kiểm duyệt CTĐT

> Báo cáo sinh tự động từ candidate công khai. Candidate chỉ được bật sau khi có bản ghi phê duyệt và dataset chuẩn hóa tương ứng.

- Sinh lúc (UTC): `2026-09-16T00:14:48.809797+00:00`
- Tổng candidate: **24**
- Candidate được nạp Rule Engine: **1**
- Candidate đã phê duyệt: **1**
- Dataset CTĐT đang chạy: `ET1-2022`, `ET1-2023`

| Candidate | Parser | Phiên bản | HP | Nhóm | Mô-đun | Tổng TC | Trạng thái | Vấn đề cần rà |
|---|---|---:|---:|---:|---:|---:|---|---|
| ED3 | hust-pdf-course-list.v1 | — | 68 | 15 | 2 | — | needs_review | `normalization_not_validated`, `missing_curriculum_version`, `missing_total_credits`, `required_credit_threshold_missing` |
| EE-E18-2023 | hust-astro-hp-table.v1 | 2023 | 72 | 12 | 4 | 132 | needs_review | `normalization_not_validated`, `course_codes_not_in_ctt`, `course_credit_mismatch`, `page_summary_differs_from_row_sum`, `required_credit_threshold_missing` |
| EE-E8-2023 | hust-astro-hp-table.v1 | 2023 | 76 | 9 | 1 | 132 | needs_review | `normalization_not_validated`, `course_codes_not_in_ctt`, `required_credit_formula_does_not_match_page_total` |
| EE-EP-2023 | hust-astro-hp-table.v1 | 2023 | 64 | 7 | 0 | 132 | needs_review | `normalization_not_validated`, `course_credit_mismatch` |
| EE1-2023 | hust-astro-hp-table.v1 | 2023 | 75 | 10 | 2 | 132 | needs_review | `normalization_not_validated`, `course_codes_not_in_ctt` |
| EE2-2023 | hust-astro-hp-table.v1 | 2023 | 71 | 11 | 3 | 132 | needs_review | `normalization_not_validated`, `course_codes_not_in_ctt` |
| ET-E16-2023 | hust-astro-hp-table.v1 | 2023 | 60 | 5 | 0 | 132 | needs_review | `normalization_not_validated`, `course_codes_not_in_ctt`, `required_credit_threshold_missing` |
| ET-E4-2023 | hust-astro-hp-table.v1 | 2023 | 55 | 7 | 2 | 132 | needs_review | `normalization_not_validated`, `required_credit_formula_does_not_match_page_total` |
| ET-E5-2023 | hust-astro-hp-table.v1 | 2023 | 78 | 7 | 0 | 132 | needs_review | `normalization_not_validated`, `required_credit_threshold_missing` |
| ET-E9-2023 | hust-astro-hp-table.v1 | 2023 | 63 | 8 | 2 | 132 | needs_review | `normalization_not_validated`, `course_codes_not_in_ctt`, `page_summary_differs_from_row_sum`, `required_credit_threshold_missing` |
| ET-LUH | hust-astro-hp-table.v1 | — | 61 | 9 | 2 | — | needs_review | `normalization_not_validated`, `missing_curriculum_version`, `missing_total_credits`, `course_codes_not_in_ctt` |
| ET1-2023 | hust-astro-hp-table.v1 | 2023 | 79 | 13 | 5 | 132 | approved | `normalization_not_validated` |
| ET2-2023 | hust-astro-hp-table.v1 | 2023 | 81 | 12 | 4 | 132 | needs_review | `normalization_not_validated`, `course_codes_not_in_ctt` |
| FL2 | hust-generic-table.v1 | — | 56 | 1 | 0 | — | needs_review | `normalization_not_validated`, `missing_curriculum_version`, `missing_total_credits`, `course_credit_mismatch`, `required_credit_threshold_missing` |
| IT-E10 | hust-pdf-course-list.v1 | — | 0 | 0 | 0 | 132 | needs_review | `normalization_not_validated`, `missing_curriculum_version` |
| IT-E15-2021 | hust-pdf-course-list.v1 | 2021 | 91 | 15 | 0 | 180 | needs_review | `normalization_not_validated`, `course_codes_not_in_ctt`, `required_credit_threshold_missing` |
| IT-E6-2020 | hust-pdf-course-list.v1 | 2020 | 77 | 10 | 2 | 148 | needs_review | `normalization_not_validated`, `required_credit_threshold_missing` |
| IT-E7-2020 | hust-pdf-course-list.v1 | 2020 | 82 | 10 | 4 | 133 | needs_review | `normalization_not_validated`, `required_credit_threshold_missing` |
| IT-EP | hust-pdf-course-list.v1 | — | 0 | 0 | 0 | 146 | needs_review | `normalization_not_validated`, `missing_curriculum_version` |
| IT1-2017 | hust-pdf-course-list.v1 | 2017 | 68 | 17 | 5 | 136 | needs_review | `normalization_not_validated`, `required_credit_threshold_missing` |
| IT2-2017 | hust-pdf-course-list.v1 | 2017 | 62 | 14 | 3 | 132 | needs_review | `normalization_not_validated`, `required_credit_threshold_missing` |
| MS1 | hust-pdf-course-list.v1 | — | 33 | 1 | 0 | 132 | needs_review | `normalization_not_validated`, `missing_curriculum_version`, `course_credit_mismatch`, `required_credit_threshold_missing` |
| MS5-2020 | hust-pdf-course-list.v1 | 2020 | 32 | 1 | 0 | 179 | needs_review | `normalization_not_validated`, `course_codes_not_in_ctt`, `course_credit_mismatch`, `required_credit_threshold_missing` |
| MS5-2020 | hust-pdf-course-list.v1 | 2020 | 12 | 1 | 0 | 180 | needs_review | `normalization_not_validated`, `course_codes_not_in_ctt`, `course_credit_mismatch`, `required_credit_threshold_missing` |

## Chi tiết tự động

### `ED3`

- Nguồn: https://fed.hust.edu.vn/uploads/feed/dao-tao/240628_khung-ctdt-qlgd.pdf
- Tệp: `data/raw/program_sources/ED3__attachment_1.pdf`
- Mã môn không có trong CTT: —
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_pdf_1, group_pdf_5, group_pdf_6, group_pdf_7, group_pdf_9, group_pdf_10, group_pdf_11, group_pdf_12, group_pdf_13, group_pdf_14, group_pdf_15
- Chuỗi điều kiện CTT có nội dung: 31; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: —
- Lý do giữ lại: normalization_not_validated, missing_curriculum_version, missing_total_credits, required_credit_threshold_missing

### `EE-E18-2023`

- Nguồn: https://seee.hust.edu.vn/vi/dao-tao/ee-e18/
- Tệp: `data/raw/program_sources/EE-E18.html`
- Mã môn không có trong CTT: DX6000, EE6010E, EE6020E, EE6036E, EE6037E, EE6056E, EE6133E, EE6141E, EE6181E, EE6232E, EE6301E, EE6313E, EE6460E, EE6466E, LV6001, SS6013
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_khoi_1, group_khoi_2, group_khoi_3, group_khoi_4, group_khoi_5, group_khoi_7, group_khoi_8
- Chuỗi điều kiện CTT có nội dung: 8; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 132
- Lý do giữ lại: normalization_not_validated, course_codes_not_in_ctt, course_credit_mismatch, page_summary_differs_from_row_sum, required_credit_threshold_missing

### `EE-E8-2023`

- Nguồn: https://seee.hust.edu.vn/vi/dao-tao/ee-e8/
- Tệp: `data/raw/program_sources/EE-E8.html`
- Mã môn không có trong CTT: EE2022E, EE3424E, EE3491E, EE3816E, EE3826E, EE3916E, EE4166E, EE4251E, EE4331E, EE4335E, EE4343E, EE4906E
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: —
- Chuỗi điều kiện CTT có nội dung: 3; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: 140; tổng trang công bố: 132
- Lý do giữ lại: normalization_not_validated, course_codes_not_in_ctt, required_credit_formula_does_not_match_page_total

### `EE-EP-2023`

- Nguồn: https://seee.hust.edu.vn/vi/dao-tao/ee-ep/
- Tệp: `data/raw/program_sources/EE-EP.html`
- Mã môn không có trong CTT: —
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: —
- Chuỗi điều kiện CTT có nội dung: 25; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 132
- Lý do giữ lại: normalization_not_validated, course_credit_mismatch

### `EE1-2023`

- Nguồn: https://seee.hust.edu.vn/vi/dao-tao/ee1/
- Tệp: `data/raw/program_sources/EE1.html`
- Mã môn không có trong CTT: EE3041, EE3112, EE3290, EE4016, EE4125, EE4600
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: —
- Chuỗi điều kiện CTT có nội dung: 18; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: 132; tổng trang công bố: 132
- Lý do giữ lại: normalization_not_validated, course_codes_not_in_ctt

### `EE2-2023`

- Nguồn: https://seee.hust.edu.vn/vi/dao-tao/ee2/
- Tệp: `data/raw/program_sources/EE2.html`
- Mã môn không có trong CTT: EE4166, EE4333, EE4335, EE4343, EE4532
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: —
- Chuỗi điều kiện CTT có nội dung: 26; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: 132; tổng trang công bố: 132
- Lý do giữ lại: normalization_not_validated, course_codes_not_in_ctt

### `ET-E16-2023`

- Nguồn: https://seee.hust.edu.vn/vi/dao-tao/et-e16/
- Tệp: `data/raw/program_sources/ET-E16.html`
- Mã môn không có trong CTT: ET3292E, ET4740E, ET4760E
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_khoi_1, group_khoi_4, group_khoi_5
- Chuỗi điều kiện CTT có nội dung: 12; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 132
- Lý do giữ lại: normalization_not_validated, course_codes_not_in_ctt, required_credit_threshold_missing

### `ET-E4-2023`

- Nguồn: https://seee.hust.edu.vn/vi/dao-tao/et-e4/
- Tệp: `data/raw/program_sources/ET-E4.html`
- Mã môn không có trong CTT: —
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: —
- Chuỗi điều kiện CTT có nội dung: 28; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: 126; tổng trang công bố: 132
- Lý do giữ lại: normalization_not_validated, required_credit_formula_does_not_match_page_total

### `ET-E5-2023`

- Nguồn: https://seee.hust.edu.vn/vi/dao-tao/et-e5/
- Tệp: `data/raw/program_sources/ET-E5.html`
- Mã môn không có trong CTT: —
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_khoi_1, group_khoi_4, group_khoi_5
- Chuỗi điều kiện CTT có nội dung: 25; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 132
- Lý do giữ lại: normalization_not_validated, required_credit_threshold_missing

### `ET-E9-2023`

- Nguồn: https://seee.hust.edu.vn/vi/dao-tao/et-e9/
- Tệp: `data/raw/program_sources/ET-E9.html`
- Mã môn không có trong CTT: ET4792, ET4793
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_khoi_1, group_khoi_2, group_khoi_3, group_khoi_4, group_khoi_5
- Chuỗi điều kiện CTT có nội dung: 21; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 132
- Lý do giữ lại: normalization_not_validated, course_codes_not_in_ctt, page_summary_differs_from_row_sum, required_credit_threshold_missing

### `ET-LUH`

- Nguồn: https://seee.hust.edu.vn/vi/dao-tao/et-luh/
- Tệp: `data/raw/program_sources/ET-LUH.html`
- Mã môn không có trong CTT: ET2022Q, ET3242Q, ET3312Q, ET4022Q, ET4245Q, ET4291Q, ET4920Q, MI2036Q
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: —
- Chuỗi điều kiện CTT có nội dung: 6; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: 132; tổng trang công bố: —
- Lý do giữ lại: normalization_not_validated, missing_curriculum_version, missing_total_credits, course_codes_not_in_ctt

### `ET1-2023`

- Nguồn: https://seee.hust.edu.vn/vi/dao-tao/et1/
- Tệp: `data/raw/program_sources/ET1.html`
- Mã môn không có trong CTT: —
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: —
- Chuỗi điều kiện CTT có nội dung: 29; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: 132; tổng trang công bố: 132
- Phê duyệt: project-owner — 2026-09-16T00:00:00+00:00

### `ET2-2023`

- Nguồn: https://seee.hust.edu.vn/vi/dao-tao/et2/
- Tệp: `data/raw/program_sources/ET2.html`
- Mã môn không có trong CTT: BF4611, BF4612, ET3047, ET3303, ET4503, ET4713
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: —
- Chuỗi điều kiện CTT có nội dung: 17; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: 132; tổng trang công bố: 132
- Lý do giữ lại: normalization_not_validated, course_codes_not_in_ctt

### `FL2`

- Nguồn: https://sofl.hust.edu.vn/nganh-fl2
- Tệp: `data/raw/program_sources/FL2.html`
- Mã môn không có trong CTT: —
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_table_1
- Chuỗi điều kiện CTT có nội dung: 25; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: —
- Lý do giữ lại: normalization_not_validated, missing_curriculum_version, missing_total_credits, course_credit_mismatch, required_credit_threshold_missing

### `IT-E10`

- Nguồn: https://soict.hust.edu.vn/wp-content/uploads/Tho%CC%82ng-tin-chu%CC%9Bo%CC%9Bng-tri%CC%80nh-DS-AI_2025_vn.pdf
- Tệp: `data/raw/program_sources/IT-E10__attachment_1.pdf`
- Mã môn không có trong CTT: —
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: —
- Chuỗi điều kiện CTT có nội dung: 0; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 132
- Lý do giữ lại: normalization_not_validated, missing_curriculum_version

### `IT-E15-2021`

- Nguồn: https://soict.hust.edu.vn/wp-content/uploads/CNTT-Chu%CC%9Bo%CC%9Bng-tri%CC%80nh-da%CC%80o-ta%CC%A3o-An-toa%CC%80n-Kho%CC%82ng-gian-so%CC%82%CC%81-Cyber-Security_v30032025.pdf
- Tệp: `data/raw/program_sources/IT-E15__attachment_1.pdf`
- Mã môn không có trong CTT: IT4220E, IT4244E, IT4509E, IT4922E, IT5002E, IT5009E, IT5010E, IT5016E, IT5017E, IT5018E, IT5122E, IT5123E, IT5260E, IT5425E
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_pdf_1, group_pdf_5, group_pdf_6, group_pdf_7, group_pdf_8, group_pdf_9, group_pdf_10, group_pdf_11, group_pdf_12, group_pdf_13, group_pdf_14, group_pdf_15
- Chuỗi điều kiện CTT có nội dung: 11; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 180
- Lý do giữ lại: normalization_not_validated, course_codes_not_in_ctt, required_credit_threshold_missing

### `IT-E6-2020`

- Nguồn: https://soict.hust.edu.vn/wp-content/uploads/Bachelor-Hedspi-program.pdf
- Tệp: `data/raw/program_sources/IT-E6__attachment_1.pdf`
- Mã môn không có trong CTT: —
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_pdf_1, group_pdf_4, group_pdf_5, group_pdf_6, group_pdf_7, group_pdf_8, group_pdf_9, group_pdf_10
- Chuỗi điều kiện CTT có nội dung: 20; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 148
- Lý do giữ lại: normalization_not_validated, required_credit_threshold_missing

### `IT-E7-2020`

- Nguồn: https://soict.hust.edu.vn/wp-content/uploads/Bachelor-Global-ICT-program.pdf
- Tệp: `data/raw/program_sources/IT-E7__attachment_1.pdf`
- Mã môn không có trong CTT: —
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_pdf_1, group_pdf_4, group_pdf_5, group_pdf_6, group_pdf_7, group_pdf_8, group_pdf_9, group_pdf_10
- Chuỗi điều kiện CTT có nội dung: 28; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 133
- Lý do giữ lại: normalization_not_validated, required_credit_threshold_missing

### `IT-EP`

- Nguồn: https://soict.hust.edu.vn/wp-content/uploads/IT-EP-K70.pdf
- Tệp: `data/raw/program_sources/IT-EP__attachment_1.pdf`
- Mã môn không có trong CTT: —
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: —
- Chuỗi điều kiện CTT có nội dung: 0; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 146
- Lý do giữ lại: normalization_not_validated, missing_curriculum_version

### `IT1-2017`

- Nguồn: https://soict.hust.edu.vn/wp-content/uploads/CTDT-CN.KHMT-K70-V2025.03.28.pdf
- Tệp: `data/raw/program_sources/IT1__attachment_1.pdf`
- Mã môn không có trong CTT: —
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_pdf_1, group_pdf_7, group_pdf_8, group_pdf_9, group_pdf_10, group_pdf_11, group_pdf_12, group_pdf_13, group_pdf_14, group_pdf_15, group_pdf_16, group_pdf_17
- Chuỗi điều kiện CTT có nội dung: 28; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 136
- Lý do giữ lại: normalization_not_validated, required_credit_threshold_missing

### `IT2-2017`

- Nguồn: https://soict.hust.edu.vn/wp-content/uploads/Bachelor-Computer-Engineering-program.pdf
- Tệp: `data/raw/program_sources/IT2__attachment_1.pdf`
- Mã môn không có trong CTT: —
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_pdf_1, group_pdf_5, group_pdf_6, group_pdf_7, group_pdf_8, group_pdf_9, group_pdf_10, group_pdf_11, group_pdf_12, group_pdf_13, group_pdf_14
- Chuỗi điều kiện CTT có nội dung: 28; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 132
- Lý do giữ lại: normalization_not_validated, required_credit_threshold_missing

### `MS1`

- Nguồn: https://smse.hust.edu.vn/uploads/smse/dao-tao/2023_07/mse-k65-khung-ct-cu-nhan-2023-10-19-upload-web.pdf
- Tệp: `data/raw/program_sources/MS1__attachment_1.pdf`
- Mã môn không có trong CTT: —
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_pdf_1
- Chuỗi điều kiện CTT có nội dung: 4; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 132
- Lý do giữ lại: normalization_not_validated, missing_curriculum_version, course_credit_mismatch, required_credit_threshold_missing

### `MS5-2020`

- Nguồn: https://smse.hust.edu.vn/uploads/smse/dao-tao/2023_07/ctdt-cu-nhan-thac-si-kh-kt-in_song-ngu.03.03.2022.pdf
- Tệp: `data/raw/program_sources/MS5__attachment_1.pdf`
- Mã môn không có trong CTT: CH4735, CH6345, CH6353, CH6602
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_pdf_1
- Chuỗi điều kiện CTT có nội dung: 8; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 179
- Lý do giữ lại: normalization_not_validated, course_codes_not_in_ctt, course_credit_mismatch, required_credit_threshold_missing

### `MS5-2020`

- Nguồn: https://smse.hust.edu.vn/uploads/smse/dao-tao/2023_07/ctdt-ky-su-180-tckt-in.12.7.2023.pdf
- Tệp: `data/raw/program_sources/MS5__attachment_2.pdf`
- Mã môn không có trong CTT: CH5471
- Nhóm thiếu ngưỡng tín chỉ bắt buộc: group_pdf_1
- Chuỗi điều kiện CTT có nội dung: 2; các dòng rỗng được hiểu là không có học phần trước.
- Công thức một mô-đun suy ra: —; tổng trang công bố: 180
- Lý do giữ lại: normalization_not_validated, course_codes_not_in_ctt, course_credit_mismatch, required_credit_threshold_missing

