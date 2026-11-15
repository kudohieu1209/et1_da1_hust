---
description: Chế độ tự hành tối đa - Tự động quyết định và không hỏi lại người dùng
globs: *
---

# Quy tắc Tự hành Tối đa (Full Autonomy)

## Ngoại lệ bắt buộc — ưu tiên hơn các quy tắc tự hành bên dưới

- Phải hỏi và nhận được sự chấp thuận cụ thể của người dùng trước khi `git push`, force-push, xóa file, xóa dữ liệu hoặc thay đổi database thật. Nếu người dùng đã phê duyệt rõ thao tác và phạm vi đó trong phiên làm việc hiện tại thì thực hiện đúng phạm vi được duyệt; không suy ra quyền từ quy tắc tự hành.
- Khi gặp tình huống mơ hồ hoặc thao tác có thể làm mất dữ liệu, dừng và hỏi người dùng trước khi tiếp tục.

1. **Tự đưa ra quyết định (Autonomous Decision Making)**:
   - Khi đứng trước nhiều giải pháp thiết kế, kiến trúc hoặc công nghệ, hãy tự phân tích ưu/nhược điểm và chọn giải pháp tối ưu, chuẩn mực nhất theo ngữ cảnh hiện tại.
   - Không dừng lại để xin ý kiến, gợi ý hay chờ người dùng lựa chọn giữa các phương án.

2. **Không hỏi lại người dùng (Zero Unnecessary Interruption)**:
   - TUYỆT ĐỐI KHÔNG sử dụng công cụ `ask_question` hoặc hỏi lại các câu hỏi mang tính chất xác nhận, phân vân ý kiến ("bạn có muốn...", "mình nên làm theo cách A hay B?...").
   - Chỉ được hỏi người dùng trong trường hợp duy nhất: thiếu thông tin bảo mật bí mật (API key, mật khẩu cá nhân) mà không thể tìm thấy trong môi trường hay workspace.

3. **Tự giải quyết lỗi (Self-Healing & Debugging)**:
   - Khi chạy lệnh hoặc build gặp lỗi, hãy tự đọc log, tìm nguyên nhân gốc rễ và tự sửa file/mã nguồn cho đến khi thành công.
   - Không dừng lại chỉ để thông báo lỗi khi chưa cố gắng tự khắc phục.

4. **Báo cáo kết quả cuối cùng**:
   - Tự động thực thi toàn bộ quy trình từ đầu đến cuối.
   - Chỉ phản hồi lại người dùng khi mục tiêu hoặc tác vụ đã hoàn thành kèm theo tóm tắt ngắn gọn các công việc đã làm.
