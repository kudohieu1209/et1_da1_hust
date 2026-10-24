# Kết quả đánh giá: mongo_context_memory

- Thời điểm (UTC): 2026-10-23T08:56:03+00:00
- Số câu hỏi: 100; k = 4; độ trễ trung vị: 215 ms
- Chế độ: extractive_no_llm; commit: `884e0181977d08257b42a1ae32c8aee073b9caa1`; có thay đổi chưa commit: True
- Bộ câu hỏi SHA-256: `f521b6b6a6bf48c54e8470ac5035f8a5ebf8f05a9a911ea7792326a4d63e915c`
- Mã nguồn và corpus SHA-256: `b6d9278d4855ac856d18ce0afb82e1bf5ffded04fec86336da4c6e862c0a005a`
- Hồ sơ kiểm thử: dữ liệu tổng hợp từ CTĐT công khai, không dùng bảng điểm cá nhân hay MongoDB thật.
- Số ký tự ngữ cảnh truy xuất trung vị: 2246; top-k có thể bao gồm cả khoản chứa điểm được khớp.
- Lưu ý: 'Câu trả lời chứa ý chính' chấm bằng khớp cụm từ, không phải độ đúng toàn diện của LLM. Recall@k hiện đo tỷ lệ câu có ít nhất một bằng chứng khớp trong top-k.

| Nhóm | Số câu | Phân loại ý định | Trích xuất mã môn | Recall@k truy xuất | MRR@k truy xuất | Câu trả lời chứa ý chính |
|---|---:|---:|---:|---:|---:|---:|
| **Tổng** | 100 | 100.0% | 100.0% | 100.0% | 80.7% | 100.0% |
| audit | 6 | 100.0% | — | — | — | — |
| course_check | 15 | 100.0% | 100.0% | — | — | — |
| curriculum | 7 | 100.0% | — | 100.0% | 71.4% | 100.0% |
| greeting | 6 | 100.0% | — | — | — | — |
| recommendation | 6 | 100.0% | — | — | — | — |
| regulation | 40 | 100.0% | — | 100.0% | 91.7% | 100.0% |
| scholarship | 8 | 100.0% | — | 100.0% | 58.3% | 100.0% |
| simulation | 3 | 100.0% | 100.0% | — | — | — |
| tuition | 9 | 100.0% | — | 100.0% | 59.3% | 100.0% |

## Câu hỏi chưa đạt (0)
