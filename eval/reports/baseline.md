# Kết quả đánh giá: baseline

- Thời điểm: 2026-10-15T01:07:22
- Số câu hỏi: 96; k = 4; độ trễ trung vị: 166 ms

| Nhóm | Số câu | Phân loại ý định | Trích xuất mã môn | Recall@k truy xuất | MRR@k truy xuất | Câu trả lời chứa ý chính |
|---|---:|---:|---:|---:|---:|---:|
| **Tổng** | 96 | 95.8% | 100.0% | 79.7% | 62.6% | 77.4% |
| audit | 6 | 83.3% | — | — | — | — |
| course_check | 14 | 92.9% | 100.0% | — | — | — |
| curriculum | 7 | 100.0% | — | 57.1% | 50.0% | 50.0% |
| greeting | 3 | 66.7% | — | — | — | — |
| recommendation | 6 | 100.0% | — | — | — | — |
| regulation | 40 | 97.5% | — | 85.0% | 68.1% | 79.5% |
| scholarship | 8 | 100.0% | — | 87.5% | 62.5% | 100.0% |
| simulation | 3 | 100.0% | 100.0% | — | — | — |
| tuition | 9 | 100.0% | — | 66.7% | 48.1% | 66.7% |

## Câu hỏi chưa đạt (20)

- `reg-007` Trường hợp nào sinh viên bị buộc thôi học? — thiếu ý ['mức 3 lần thứ hai liên tiếp']
- `reg-014` Điểm W là gì? — không truy xuất được bằng chứng trong top-4; thiếu ý ['rút đăng ký']
- `reg-015` Theo quy chế, điểm R có nghĩa là gì? — không truy xuất được bằng chứng trong top-4; thiếu ý ['miễn học']
- `reg-020` Điểm trung bình tích lũy được tính theo quy định nào? — không truy xuất được bằng chứng trong top-4; thiếu ý ['thang 4']
- `reg-021` Tích lũy bao nhiêu tín chỉ thì được xếp trình độ năm thứ ba? — không truy xuất được bằng chứng trong top-4; thiếu ý ['64 - 95']
- `reg-023` Điều kiện để được xét công nhận tốt nghiệp đại học là gì? — không truy xuất được bằng chứng trong top-4; thiếu ý ['chuẩn ngoại ngữ đầu ra']
- `reg-027` Muốn chuyển sang chương trình đào tạo khác thì cần CPA bao nhiêu? — ý định `DEGREE_AUDIT` ≠ `RAG_HUST_KNOWLEDGE`; thiếu ý ['2,5']
- `reg-033` Chương trình cử nhân được phép chậm tiến độ tối đa bao nhiêu học kỳ? — không truy xuất được bằng chứng trong top-4; thiếu ý ['5 học kỳ chính']
- `tui-003` Học phí ngành Kỹ thuật y sinh năm học 2025-2026? — không truy xuất được bằng chứng trong top-4; thiếu ý ['600']
- `tui-004` Học phí các chương trình đào tạo tài năng là bao nhiêu? — thiếu ý ['650']
- `tui-006` Học phí tiến sĩ một năm là bao nhiêu? — không truy xuất được bằng chứng trong top-4; thiếu ý ['26 triệu']
- `tui-007` Học phí được tính dựa trên cái gì? — không truy xuất được bằng chứng trong top-4
- `sch-008` Học bổng loại C được bao nhiêu tiền? — không truy xuất được bằng chứng trong top-4
- `cur-003` Chương trình đào tạo ET1 2023 có mấy mô đun chuyên sâu? — không truy xuất được bằng chứng trong top-4; thiếu ý ['5 mô-đun']
- `cur-004` Chương trình đào tạo ET1 2022 có mấy mô đun? — không truy xuất được bằng chứng trong top-4; thiếu ý ['6 mô-đun']
- `cur-005` Mô đun 5 của CTĐT ET1 2023 gồm những học phần nào? — không truy xuất được bằng chứng trong top-4
- `cur-007` Thực tập và tốt nghiệp của CTĐT ET1 2023 bao nhiêu tín chỉ? — thiếu ý ['8 TC']
- `chk-011` Mình học được mạng máy tính chưa? — ý định `RAG_HUST_KNOWLEDGE` ≠ `COURSE_ELIGIBILITY_CHECK`
- `aud-002` Em còn thiếu bao nhiêu tín chỉ để tốt nghiệp? — ý định `RAG_HUST_KNOWLEDGE` ≠ `DEGREE_AUDIT`
- `gre-003` Xin chào! — ý định `RAG_HUST_KNOWLEDGE` ≠ `GENERAL_GREETING`
