# Kết quả đánh giá: validation_reliability

- Thời điểm (UTC): 2026-10-23T08:20:52+00:00
- Số câu hỏi: 20; k = 4; độ trễ trung vị: 268 ms
- Chế độ: extractive_no_llm; commit: `884e0181977d08257b42a1ae32c8aee073b9caa1`; có thay đổi chưa commit: True
- Bộ câu hỏi SHA-256: `a254fbf43c43934aaffade1f5777eb9220bb4da97187854a60a3f06724429155`
- Mã nguồn và corpus SHA-256: `f5d4d7fea606e6b494895c30f9ea0823e8be25a1c41dfe9473dd492a72f39658`
- Số ký tự ngữ cảnh truy xuất trung vị: 2208; top-k có thể bao gồm cả khoản chứa điểm được khớp.
- Lưu ý: 'Câu trả lời chứa ý chính' chấm bằng khớp cụm từ, không phải độ đúng toàn diện của LLM. Recall@k hiện đo tỷ lệ câu có ít nhất một bằng chứng khớp trong top-k.

| Nhóm | Số câu | Phân loại ý định | Trích xuất mã môn | Recall@k truy xuất | MRR@k truy xuất | Câu trả lời chứa ý chính |
|---|---:|---:|---:|---:|---:|---:|
| **Tổng** | 20 | 100.0% | 100.0% | 93.3% | 70.6% | 92.9% |
| audit | 1 | 100.0% | — | — | — | — |
| course_check | 2 | 100.0% | 100.0% | — | — | — |
| curriculum | 3 | 100.0% | — | 100.0% | 61.1% | 100.0% |
| greeting | 1 | 100.0% | — | — | — | — |
| recommendation | 1 | 100.0% | — | — | — | — |
| regulation | 7 | 100.0% | — | 100.0% | 92.9% | 100.0% |
| scholarship | 2 | 100.0% | — | 100.0% | 62.5% | 100.0% |
| tuition | 3 | 100.0% | — | 66.7% | 33.3% | 66.7% |

## Câu hỏi chưa đạt (1)

- `val-010` Cho mình tra mức học phí đào tạo tiến sĩ theo quyết định năm 2025–2026. — không truy xuất được bằng chứng trong top-4; thiếu ý ['26 triệu']
