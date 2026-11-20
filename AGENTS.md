# Quy tắc làm việc với git (mọi session, mọi agent)

Dự án được mở ở nhiều session và trên cả Windows lẫn Linux (dual boot, ổ `D:`).
Các quy tắc sau giúp session sau luôn thấy việc mà session trước đã làm.

1. **Chỉ một thư mục làm việc: `DA1/project`.** Không tạo `git worktree`.
   Worktree ghi đường dẫn tuyệt đối (`D:/...`), nên khi chuyển sang hệ điều hành kia thì nó hỏng.
2. **`main` là nguồn sự thật duy nhất.** Đầu session: `git checkout main && git pull`.
3. Nếu cần nhánh riêng thì tạo nhánh ngắn từ `main` mới nhất.
   **Gộp lại vào `main` và xóa nhánh ngay trong session đó**, không để nhánh tồn đọng.
4. **Cuối session phải commit và push `main`.** Không để thay đổi chưa commit.
5. `deploy/render` là nhánh Render deploy. Chỉ cập nhật bằng fast-forward theo `main`:
   `git branch -f deploy/render main && git push origin deploy/render`.
6. Trước khi báo xong, kiểm tra `git status -sb` phải là `## main...origin/main`, không ahead/behind.

Chạy test:
- Frontend: `cd frontend && npm test`.
- Backend: `cd backend && <venv>/python -m unittest discover -s tests -t .`.
  Linux dùng `.venv`, Windows dùng `.venv-win`.
