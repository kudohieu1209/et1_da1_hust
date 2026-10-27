# Kết quả đánh giá: final

- Thời điểm (UTC): 2026-10-27T13:25:43+00:00
- Số câu hỏi: 108; k = 4; độ trễ trung vị: 487 ms
- Chế độ: extractive_no_llm; commit: `69e42f362c1372fb792341e06d6b0bb8064c3b88`; có thay đổi chưa commit: True
- Bộ câu hỏi SHA-256: `1e112bda72944e5023b13f0a0c463174fa08041e6084449150334bc656a562a6`
- Mã nguồn và corpus SHA-256: `180439e8202ca4f5aa907e3a0914502716f48f3de4e02807f8f97516c81fb6db`
- Hồ sơ kiểm thử: dữ liệu tổng hợp từ CTĐT công khai, không dùng bảng điểm cá nhân hay MongoDB thật.
- Số ký tự ngữ cảnh truy xuất trung vị: 2247; top-k có thể bao gồm cả khoản chứa điểm được khớp.
- Lưu ý: 'Câu trả lời chứa ý chính' chấm bằng khớp cụm từ, không phải độ đúng toàn diện của LLM. Recall@k hiện đo tỷ lệ câu có ít nhất một bằng chứng khớp trong top-k.

| Nhóm | Số câu | Phân loại ý định | Trích xuất mã môn | Recall@k truy xuất | MRR@k truy xuất | Câu trả lời chứa ý chính |
|---|---:|---:|---:|---:|---:|---:|
| **Tổng** | 108 | 100.0% | 100.0% | 98.6% | 83.7% | 100.0% |
| audit | 6 | 100.0% | — | — | — | — |
| course_check | 15 | 100.0% | 100.0% | — | — | — |
| curriculum | 7 | 100.0% | — | 100.0% | 92.9% | 100.0% |
| greeting | 6 | 100.0% | — | — | — | — |
| recommendation | 6 | 100.0% | — | — | — | — |
| regulation | 45 | 100.0% | — | 100.0% | 92.4% | 100.0% |
| scholarship | 9 | 100.0% | — | 88.9% | 63.0% | 100.0% |
| simulation | 3 | 100.0% | 100.0% | — | — | — |
| tuition | 11 | 100.0% | — | 100.0% | 59.1% | 100.0% |

## Câu hỏi chưa đạt (1)

- `sch-009` Học bổng Trần Đại Nghĩa cho sinh viên có những mức nào? — không truy xuất được bằng chứng trong top-4
