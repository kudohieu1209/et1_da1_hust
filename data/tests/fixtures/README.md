# Fixture parser CTĐT ET1–2022

`ctt_et1_2022_curriculum_only.html` giữ các dòng cấu trúc CTĐT từ bản xuất CTT:
tiêu đề chương trình, công thức tốt nghiệp, nhóm và danh mục học phần. Đây là
đầu vào kiểm thử tĩnh cho parser, không sinh ngược từ JSON mà parser tạo ra.

Đã bỏ HTML ngoài các bảng cần thiết, scripts, session/ViewState, danh tính và
các cột kết quả học tập: tín chỉ đã học, mã học phần thực học, điểm chữ/điểm số.
Danh tính `10000001 / SINH VIÊN GIẢ LẬP` trong tiêu đề là giá trị giả để test
rằng parser không sao chép danh tính vào dataset.

Fixture giúp test chạy từ clone sạch, không cần file HTML CTT cá nhân bị ignore.
Không dùng fixture làm nguồn phê duyệt CTĐT mới; provenance của dataset nghiệp
vụ vẫn nằm trong `processed/curricula/et1_2022.json`.
