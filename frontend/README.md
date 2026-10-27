# Frontend HUST Course Advisor

React + Vite. Cần Node.js 22.12+; chạy `npm ci`, sau đó `npm run dev` tại thư mục
này. Backend chạy cổng 8000. Vite chuyển tiếp `/api` tới `127.0.0.1:8000`, nên cả
`localhost:5173` và `127.0.0.1:5173` đều dùng cookie phiên cùng địa chỉ với web.

- `npm run lint`: kiểm tra mã bằng Oxlint.
- `npm run build`: tạo bản tĩnh trong `dist/`.
- `npm run preview`: chỉ xem bản build; không thay thế reverse proxy production.

Để trống `VITE_API_BASE_URL` khi web có reverse proxy `/api` cùng origin. Nếu đặt
URL khác, backend cần cho phép đúng origin và cookie phải phù hợp quan hệ same-site
của tên miền; không chỉ thay URL là đủ. Khóa MongoDB/Gemini chỉ nằm ở backend,
không đặt trong biến `VITE_*` vì các biến này được đóng gói vào mã trình duyệt.

Hướng dẫn cài đặt, dữ liệu demo tổng hợp và giới hạn: [README gốc](../README.md). Các trang `*-preview.html` ở máy tác giả chỉ là
công cụ xem thử thiết kế, không phải luồng ứng dụng được bàn giao.
