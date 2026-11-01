# Phạm vi dữ liệu CTĐT đang có trong ứng dụng

Sinh lại bằng `python data/scripts/write_curriculum_review_report.py`. Đây là trạng thái xử lý dữ liệu, không phải danh sách việc giao cho người dùng review.

- 68 ngành đại học đều có mục tra cứu tài liệu đã thu thập qua giao diện và `/api/programs/{code}/curricula`.
- 18 phiên bản CTĐT đã chuẩn hóa để rà soát tiến độ theo khóa.
- Nguồn thiếu khung đầy đủ vẫn xem được học phần và ghi chú; không bị bỏ ngoài ứng dụng.
- Môn chưa có điều kiện trong snapshot CTT không được tự kết luận đủ điều kiện đăng ký.

| Tài liệu | Sử dụng hiện tại | Phạm vi còn thiếu trong nguồn |
|---|---|---|
| [BF-E12-2025](../raw/official_curricula/BF-E12-2025.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [BF-E19-2023](../raw/official_curricula/BF-E19-2023.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [BF-E19-2025](../raw/official_curricula/BF-E19-2025.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [BF1-2022](../raw/official_curricula/BF1-2022.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [BF2-2023](../raw/official_curricula/BF2-2023.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [BF2-2025](../raw/reviewed_curricula/BF2-2025.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [CH-E11-2023](../raw/official_curricula/CH-E11-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [CH-E20-2023](../raw/official_curricula/CH-E20-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [CH1-2023](../raw/official_curricula/CH1-2023.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [CH1-2025](../raw/official_curricula/CH1-2025.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [CH2-2022](../raw/official_curricula/CH2-2022.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [E-EE1-undated](../raw/official_curricula/E-EE1-undated.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [E-EE2-undated](../raw/official_curricula/E-EE2-undated.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [E-ET-E-undated](../raw/official_curricula/E-ET-E-undated.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [E-ET-IC-undated](../raw/official_curricula/E-ET-IC-undated.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [E-ET-T-undated](../raw/official_curricula/E-ET-T-undated.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [ED2-2023](../raw/official_curricula/ED2-2023.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [ED2-2024](../raw/official_curricula/ED2-2024.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [ED2-2025](../raw/official_curricula/ED2-2025.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [ED3-2024](../raw/official_curricula/ED3-2024.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [ED5-2023](../raw/official_curricula/ED5-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [EE-E18-2023](../raw/official_curricula/EE-E18-2023.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [EE-E8-2023](../raw/official_curricula/EE-E8-2023.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [EE-EP-2023](../raw/official_curricula/EE-EP-2023.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [EE-TN-2023](../raw/official_curricula/EE-TN-2023.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [EE1-2023](../raw/official_curricula/EE1-2023.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [EE2-2023](../raw/official_curricula/EE2-2023.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [EM-E13-2022](../raw/official_curricula/EM-E13-2022.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [EM-E14-2022](../raw/official_curricula/EM-E14-2022.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [EM-E14-2025](../raw/official_curricula/EM-E14-2025.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [EM-E17-2023](../raw/official_curricula/EM-E17-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [EM1-2023](../raw/official_curricula/EM1-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [EM2-2023](../raw/official_curricula/EM2-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [EM3-2023](../raw/official_curricula/EM3-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [EM5-2022](../raw/official_curricula/EM5-2022.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [EM5-2023](../raw/official_curricula/EM5-2023.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [EM5-2025](../raw/official_curricula/EM5-2025.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [ET-E16-2023](../raw/official_curricula/ET-E16-2023.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [ET-E4-2023](../raw/official_curricula/ET-E4-2023.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [ET-E5-2023](../raw/official_curricula/ET-E5-2023.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [ET-E9-2023](../raw/official_curricula/ET-E9-2023.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [ET-LUH-2023](../raw/official_curricula/ET-LUH-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [ET-TN-2023](../raw/official_curricula/ET-TN-2023.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [ET1-2022](../raw/official_curricula/ET1-2022.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [ET1-2023](../raw/official_curricula/ET1-2023.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [ET2-2023](../raw/official_curricula/ET2-2023.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [EV1-2022](../raw/official_curricula/EV1-2022.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [EV1-2025](../raw/reviewed_curricula/EV1-2025.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [EV2-2022](../raw/official_curricula/EV2-2022.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [EV2-2025](../raw/reviewed_curricula/EV2-2025.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [FL1-2025](../raw/official_curricula/FL1-2025.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [FL2-2022](../raw/official_curricula/FL2-2022.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [FL3-2025](../raw/reviewed_curricula/FL3-2025.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [FL4-2023](../raw/official_curricula/FL4-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [HE1-2023](../raw/official_curricula/HE1-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [IT-E10-2023](../raw/official_curricula/IT-E10-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [IT-E10-2024](../raw/official_curricula/IT-E10-2024.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [IT-E10-2025](../raw/official_curricula/IT-E10-2025.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [IT-E15-2024](../raw/official_curricula/IT-E15-2024.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [IT-E15-2025](../raw/official_curricula/IT-E15-2025.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [IT-E6-2023](../raw/official_curricula/IT-E6-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. |
| [IT-E6-2024](../raw/official_curricula/IT-E6-2024.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [IT-E7-2023](../raw/official_curricula/IT-E7-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. |
| [IT-E7-2024](../raw/official_curricula/IT-E7-2024.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [IT-EP-2024](../raw/official_curricula/IT-EP-2024.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [IT-EP-2025](../raw/official_curricula/IT-EP-2025.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [IT1-2023](../raw/official_curricula/IT1-2023.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [IT1-2024](../raw/official_curricula/IT1-2024.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [IT1-2025](../raw/official_curricula/IT1-2025.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [IT2-2023](../raw/official_curricula/IT2-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [IT2-2024](../raw/official_curricula/IT2-2024.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [M-EE1-2022](../raw/official_curricula/M-EE1-2022.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [M-EE2-2022](../raw/official_curricula/M-EE2-2022.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [M-ET-E-2022](../raw/official_curricula/M-ET-E-2022.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [M-ET-T-2022](../raw/official_curricula/M-ET-T-2022.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [M-ET2-2022](../raw/official_curricula/M-ET2-2022.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [ME-E1-2023](../raw/official_curricula/ME-E1-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. |
| [ME-GU-2025](../raw/official_curricula/ME-GU-2025.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [ME-LUH-2023](../raw/official_curricula/ME-LUH-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. |
| [ME-NUT-2023](../raw/official_curricula/ME-NUT-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [ME1-2025](../raw/reviewed_curricula/ME1-2025.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [ME2-2023](../raw/official_curricula/ME2-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [MI-E22-2023](../raw/official_curricula/MI-E22-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [MI1-2023](../raw/official_curricula/MI1-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [MI1-2025](../raw/official_curricula/MI1-2025.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [MI2-2023](../raw/official_curricula/MI2-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [MI2-2025](../raw/official_curricula/MI2-2025.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [MS-E3-2023](../raw/official_curricula/MS-E3-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. |
| [MS1-2023](../raw/reviewed_curricula/MS1-2023.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [MS2-2023](../raw/official_curricula/MS2-2023.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [MS3-2023](../raw/official_curricula/MS3-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [MS5-2022](../raw/official_curricula/MS5-2022.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. |
| [MS5-2023](../raw/official_curricula/MS5-2023.json) | Đã đưa vào tra cứu | Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng. |
| [P-EE1-2022](../raw/official_curricula/P-EE1-2022.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [P-EE2-2022](../raw/official_curricula/P-EE2-2022.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [P-ET-E-2022](../raw/official_curricula/P-ET-E-2022.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [P-ET-T-2022](../raw/official_curricula/P-ET-T-2022.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [P-ET2-undated](../raw/official_curricula/P-ET2-undated.json) | Ngoài danh mục đại học | Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học. |
| [PH1-2023](../raw/official_curricula/PH1-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. |
| [PH2-2023](../raw/official_curricula/PH2-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. |
| [PH3-2023](../raw/official_curricula/PH3-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. |
| [TE-E2-2023](../raw/official_curricula/TE-E2-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [TE-EP-2023](../raw/official_curricula/TE-EP-2023.json) | Đã dùng để rà soát tiến độ | Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu. |
| [TE-EP-2025](../raw/official_curricula/TE-EP-2025.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [TE1-2023](../raw/official_curricula/TE1-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [TE2-2023](../raw/official_curricula/TE2-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [TE3-2025](../raw/official_curricula/TE3-2025.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [TROY-IT-2023](../raw/official_curricula/TROY-IT-2023.json) | Đã đưa vào tra cứu | Nguồn chưa xác định phiên bản/khóa áp dụng. Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |
| [TX1-2023](../raw/official_curricula/TX1-2023.json) | Đã đưa vào tra cứu | Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ. |

## Các khung đã dùng cho tiến độ

| Mã | Phiên bản | Tổng TC | Học phần | Khóa áp dụng |
|---|---|---:|---:|---|
| BF1 | 2022 | 132 | 78 | K68, K69 |
| BF2 | 2025 | 132 | 85 | K70 |
| BF-E19 | 2023 | 132 | 70 | K68, K69 |
| BF-E19 | 2025 | 132 | 62 | K70 |
| ED2 | 2024 | 132 | 71 | K68 |
| EE1 | 2023 | 132 | 75 | K68 |
| EE2 | 2023 | 132 | 71 | K68 |
| ET1 | 2022 | 126 | 117 | K67 |
| ET1 | 2023 | 132 | 79 | K68 |
| ET2 | 2023 | 132 | 81 | K68 |
| EV1 | 2025 | 132 | 75 | K70 |
| EV2 | 2022 | 132 | 69 | K68, K69 |
| EV2 | 2025 | 132 | 75 | K70 |
| FL2 | 2022 | 131 | 56 | K67 |
| FL3 | 2025 | 136 | 74 | K70 |
| ME1 | 2025 | 132 | 80 | K70 |
| MS1 | 2023 | 132 | 95 | K67, K68, K69, K70 |
| TE-EP | 2023 | 140 | 66 | K68, K69 |
