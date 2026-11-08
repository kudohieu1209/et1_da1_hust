# Kết quả đánh giá: validation_ablation_bm25_only

- Thời điểm (UTC): 2026-11-08T07:17:04+00:00
- Số câu hỏi: 20; k = 4; độ trễ trung vị: 205 ms
- Chế độ: extractive_no_llm; truy xuất: bm25_only; commit: `b3ad366764bef9fed05ca5e9aba8ad4ee00b4bfd`; có thay đổi chưa commit: False
- Bộ câu hỏi SHA-256: `a254fbf43c43934aaffade1f5777eb9220bb4da97187854a60a3f06724429155`
- Mã nguồn và corpus SHA-256: `8c2ea1060bd55cf42a4ed4909cd5cb45b7aa0aa6491b491bae0ae912e879c31a`
- Hồ sơ kiểm thử: dữ liệu tổng hợp từ CTĐT công khai, không dùng bảng điểm cá nhân hay MongoDB thật.
- Số ký tự ngữ cảnh truy xuất trung vị: 1959; top-k có thể bao gồm cả khoản chứa điểm được khớp.
- Lưu ý: 'Câu trả lời chứa ý chính' chấm bằng khớp cụm từ, không phải độ đúng toàn diện của LLM. Recall@k hiện đo tỷ lệ câu có ít nhất một bằng chứng khớp trong top-k.

| Nhóm | Số câu | Phân loại ý định | Trích xuất mã môn | Recall@k truy xuất | MRR@k truy xuất | Câu trả lời chứa ý chính |
|---|---:|---:|---:|---:|---:|---:|
| **Tổng** | 20 | 100.0% | 100.0% | 100.0% | 77.2% | 100.0% |
| audit | 1 | 100.0% | — | — | — | — |
| course_check | 2 | 100.0% | 100.0% | — | — | — |
| curriculum | 3 | 100.0% | — | 100.0% | 75.0% | 100.0% |
| greeting | 1 | 100.0% | — | — | — | — |
| recommendation | 1 | 100.0% | — | — | — | — |
| regulation | 7 | 100.0% | — | 100.0% | 78.6% | 100.0% |
| scholarship | 2 | 100.0% | — | 100.0% | 100.0% | 100.0% |
| tuition | 3 | 100.0% | — | 100.0% | 61.1% | 100.0% |

## Câu hỏi chưa đạt (0)
