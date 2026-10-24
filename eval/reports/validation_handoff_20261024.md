# Kết quả đánh giá: validation_handoff_20261024

- Thời điểm (UTC): 2026-10-24T14:57:54+00:00
- Số câu hỏi: 20; k = 4; độ trễ trung vị: 354 ms
- Chế độ: extractive_no_llm; commit: `1619584c3b162fa96ff49c89f017d482e7cc8888`; có thay đổi chưa commit: False
- Bộ câu hỏi SHA-256: `a254fbf43c43934aaffade1f5777eb9220bb4da97187854a60a3f06724429155`
- Mã nguồn và corpus SHA-256: `b296e5f48c2c74433d96a9d0756dfd7b1450690ecf2634865db69c3b2cbd37dc`
- Hồ sơ kiểm thử: dữ liệu tổng hợp từ CTĐT công khai, không dùng bảng điểm cá nhân hay MongoDB thật.
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
