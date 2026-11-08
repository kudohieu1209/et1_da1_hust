# Kết quả đánh giá: ablation_bm25_only

- Thời điểm (UTC): 2026-11-08T07:05:53+00:00
- Số câu hỏi: 108; k = 4; độ trễ trung vị: 203 ms
- Chế độ: extractive_no_llm; truy xuất: bm25_only; commit: `29de602c360a5b9db063e40d25fe6929e3541abb`; có thay đổi chưa commit: False
- Bộ câu hỏi SHA-256: `1e112bda72944e5023b13f0a0c463174fa08041e6084449150334bc656a562a6`
- Mã nguồn và corpus SHA-256: `f017094a45af1cc8590ffdeef4655a055099bcc291fe40b9a8979014c4ce1fd2`
- Hồ sơ kiểm thử: dữ liệu tổng hợp từ CTĐT công khai, không dùng bảng điểm cá nhân hay MongoDB thật.
- Số ký tự ngữ cảnh truy xuất trung vị: 2156; top-k có thể bao gồm cả khoản chứa điểm được khớp.
- Lưu ý: 'Câu trả lời chứa ý chính' chấm bằng khớp cụm từ, không phải độ đúng toàn diện của LLM. Recall@k hiện đo tỷ lệ câu có ít nhất một bằng chứng khớp trong top-k.

| Nhóm | Số câu | Phân loại ý định | Trích xuất mã môn | Recall@k truy xuất | MRR@k truy xuất | Câu trả lời chứa ý chính |
|---|---:|---:|---:|---:|---:|---:|
| **Tổng** | 108 | 100.0% | 100.0% | 100.0% | 85.3% | 100.0% |
| audit | 6 | 100.0% | — | — | — | — |
| course_check | 15 | 100.0% | 100.0% | — | — | — |
| curriculum | 7 | 100.0% | — | 100.0% | 92.9% | 100.0% |
| greeting | 6 | 100.0% | — | — | — | — |
| recommendation | 6 | 100.0% | — | — | — | — |
| regulation | 45 | 100.0% | — | 100.0% | 91.9% | 100.0% |
| scholarship | 9 | 100.0% | — | 100.0% | 78.7% | 100.0% |
| simulation | 3 | 100.0% | 100.0% | — | — | — |
| tuition | 11 | 100.0% | — | 100.0% | 59.1% | 100.0% |

## Câu hỏi chưa đạt (0)
