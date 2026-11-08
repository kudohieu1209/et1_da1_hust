# Kết quả đánh giá: validation_final

- Thời điểm (UTC): 2026-11-08T07:04:45+00:00
- Số câu hỏi: 20; k = 4; độ trễ trung vị: 353 ms
- Chế độ: extractive_no_llm; truy xuất: hybrid; commit: `29de602c360a5b9db063e40d25fe6929e3541abb`; có thay đổi chưa commit: False
- Bộ câu hỏi SHA-256: `a254fbf43c43934aaffade1f5777eb9220bb4da97187854a60a3f06724429155`
- Mã nguồn và corpus SHA-256: `f017094a45af1cc8590ffdeef4655a055099bcc291fe40b9a8979014c4ce1fd2`
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
