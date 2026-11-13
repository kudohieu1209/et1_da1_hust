# Kết quả đánh giá: validation_deploy_hybrid

- Thời điểm (UTC): 2026-11-13T11:06:39+00:00
- Số câu hỏi: 20; k = 4; độ trễ trung vị: 346 ms
- Chế độ: extractive_no_llm; truy xuất: hybrid; commit: `f548aaac192182140175f10becae3263eaa38fb8`; có thay đổi chưa commit: True
- Bộ câu hỏi SHA-256: `a254fbf43c43934aaffade1f5777eb9220bb4da97187854a60a3f06724429155`
- Mã nguồn và corpus SHA-256: `64b7a0e64667ea1ea1fc2b351927907ee3e20b633bcd7dea34f2fab9934eedcc`
- Hồ sơ kiểm thử: dữ liệu tổng hợp từ CTĐT công khai, không dùng bảng điểm cá nhân hay MongoDB thật.
- Số ký tự ngữ cảnh truy xuất trung vị: 1868; top-k có thể bao gồm cả khoản chứa điểm được khớp.
- Lưu ý: 'Câu trả lời chứa ý chính' chấm bằng khớp cụm từ, không phải độ đúng toàn diện của LLM. Recall@k hiện đo tỷ lệ câu có ít nhất một bằng chứng khớp trong top-k.

| Nhóm | Số câu | Phân loại ý định | Trích xuất mã môn | Recall@k truy xuất | MRR@k truy xuất | Câu trả lời chứa ý chính |
|---|---:|---:|---:|---:|---:|---:|
| **Tổng** | 20 | 100.0% | 100.0% | 100.0% | 80.6% | 100.0% |
| audit | 1 | 100.0% | — | — | — | — |
| course_check | 2 | 100.0% | 100.0% | — | — | — |
| curriculum | 3 | 100.0% | — | 100.0% | 75.0% | 100.0% |
| greeting | 1 | 100.0% | — | — | — | — |
| recommendation | 1 | 100.0% | — | — | — | — |
| regulation | 7 | 100.0% | — | 100.0% | 85.7% | 100.0% |
| scholarship | 2 | 100.0% | — | 100.0% | 100.0% | 100.0% |
| tuition | 3 | 100.0% | — | 100.0% | 61.1% | 100.0% |

## Câu hỏi chưa đạt (0)
