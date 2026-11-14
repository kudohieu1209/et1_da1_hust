# Đăng nhập trường và đồng bộ bảng điểm

## Dùng trên PC

1. Cài thư viện backend theo `backend/requirements.txt`, rồi cài trình duyệt riêng bằng `python -m playwright install chromium` trong môi trường Python của backend. Mặc định không dùng Edge/Chrome cá nhân và không âm thầm chuyển về Edge nếu Chromium thiếu.
2. Chạy backend và frontend trên cùng PC, mở web bằng `localhost` hoặc `127.0.0.1`.
3. Chọn **Tài khoản trường**, chọn chương trình đào tạo, bấm **Tiếp tục với tài khoản trường**.
4. Trong cửa sổ CTT chính thức vừa mở, tự nhập tài khoản và hoàn tất CAPTCHA hoặc đăng nhập Office 365 theo hướng dẫn của trường.
5. Sau khi CTT xác nhận đăng nhập, HUST Advisor đọc thông tin sinh viên và bảng điểm, xác minh danh tính rồi lưu vào hồ sơ. Cửa sổ kết nối sẽ đóng. Giao diện Advisor tự chuyển vào không gian học tập.

Từ tài khoản Advisor đã đăng nhập, mở **Nhập bảng điểm → Kết nối tài khoản trường** để đồng bộ lại. MSSV trên CTT phải trùng với tài khoản Advisor hiện tại. Khi chưa đọc được dữ liệu hoặc thông tin không khớp, ứng dụng không thay bảng điểm cũ.

Tài khoản tạo lần đầu qua trường dùng đăng nhập trường cho những lần sau. Ứng dụng không tạo mật khẩu Advisor bằng mật khẩu trường. Nếu tài khoản Advisor đã tồn tại, mật khẩu Advisor hiện có vẫn được giữ nguyên.

## Phạm vi của bản triển khai

- Đây là bộ kết nối cục bộ: backend mở trình duyệt trên PC chạy backend, không phải cửa sổ trên thiết bị truy cập từ xa. Yêu cầu khởi tạo/kết thúc kết nối chỉ được phép từ loopback và origin/host cục bộ. Vite chuyển tiếp địa chỉ gốc để chặn truy cập LAN qua proxy.
- Dùng một tiến trình backend cho bộ kết nối. Phiên kết nối được giữ trong RAM; khởi động lại backend sẽ hủy phiên đang chờ. Không dùng cơ chế này cho server công khai/máy chủ dùng chung; đặt `CTT_BROWSER_LOGIN_ENABLED=false` khi triển khai kiểu đó. Tích hợp SSO cho bản web công khai cần luồng được nhà trường hỗ trợ hoặc bộ kết nối riêng chạy trên thiết bị người dùng.
- Nhận MSSV và họ tên từ các trường có nhãn trên trang trường đã xác thực. Tên lớp và email được lấy khi trang có cung cấp. Không tự đặt tên sinh viên hay tên lớp.
- Đọc bảng điểm tổng hợp hoặc điểm học phần, gồm tín chỉ, điểm chữ, học kỳ và điểm thành phần khi bảng có dữ liệu tương ứng. Điểm chữ chưa công bố không được suy ra từ điểm thi.
- Nếu phát hiện phân trang mà chưa lấy được toàn bộ, ứng dụng từ chối ghi đè bảng điểm và hướng dẫn dùng nhập thủ công. Nếu trường đổi cấu trúc HTML, xác thực hoặc không cung cấp danh tính đọc được, ứng dụng cũng báo lỗi thay vì tạo dữ liệu tạm.
- Chương trình và khóa phải có trong bộ CTĐT được dự án hỗ trợ. Bộ kết nối đọc thêm TOEIC/tiếng Anh, lịch học chính thức và tạm thời, học phí, danh sách lớp, mức cảnh báo và trạng thái GDTC/GDQP/chuẩn tiếng Anh khi CTT trả về nhãn hoặc bảng nhận diện được.
- Mỗi mục có trạng thái độc lập: đã đồng bộ, không có bản ghi trong bảng đang đọc, chưa đọc được, một phần hoặc dữ liệu lần trước. Nếu bố cục cột thay đổi, bảng văn bản gốc vẫn được hiển thị; không thay bằng dữ liệu mẫu. Lỗi một mục không làm mất bảng điểm hoặc dữ liệu thành công của mục khác.
- Lịch thi được lấy từ liên kết trang lịch thi cùng origin có trong tài khoản CTT, nếu có. Khi không có trang đó, mục **Thời khóa biểu & Lịch thi → Lịch thi** hỗ trợ tải PDF có lớp văn bản tối đa 10 MB/100 trang, xem trước và chọn ca thi trước khi lưu. Không tự gán mọi ca trong PDF cho sinh viên; PDF ảnh quét và bố cục chưa nhận diện được sẽ báo lỗi.
- Dữ liệu trước lần mở rộng này cần được cập nhật bằng nút **Đồng bộ CTT**. Không cần đăng xuất tài khoản Advisor. Sau xác thực, bộ kết nối có tối đa 10 phút để đọc các mục bổ sung; từng trang vẫn có thời gian chờ riêng.
- Các kiểm thử tự động dùng HTML và tài khoản tổng hợp. Ngày 15/11/2026, người dùng tự đăng nhập tài khoản trường trên Chromium và xác nhận đã vào được hồ sơ và bảng điểm sau khi sửa bộ đọc hồ sơ. Không đưa thông tin đăng nhập hoặc dữ liệu cá nhân thật vào bộ kiểm thử.

## Phiên và dữ liệu

- Người dùng nhập mật khẩu trực tiếp tại trường. API Advisor không nhận mật khẩu CTT. Các endpoint gửi mật khẩu cũ `/api/auth/login-ctt` và `/api/student/sync-ctt` trả `410` để client chuyển sang luồng mới.
- Mỗi lần kết nối dùng một browser context riêng, không đọc profile Chrome/Edge đang dùng. Không lưu cookie CTT, HTML thô, ảnh trang đăng nhập hay trạng thái trình duyệt vào kho dữ liệu ứng dụng.
- Sau xác thực, tải dữ liệu bằng JavaScript `fetch` với `credentials: 'same-origin'` ngay trong trang CTT đã đăng nhập. Đây là cơ chế đã tìm thấy trong các đoạn kiểm tra phiên của APK iLoveBK, thay cho HTTP client riêng. Origin của trang và phản hồi đều được kiểm tra.
- Nhật ký lỗi trình duyệt chỉ ghi giai đoạn và loại lỗi. Không ghi URL OAuth, email, nội dung biểu mẫu hay token. Thông báo mất kết nối không đồng nghĩa người dùng tự đóng cửa sổ.
- Kết quả kết nối thuộc một cookie HttpOnly riêng, có thời hạn và chỉ được hoàn tất một lần. API thăm dò trạng thái không trả MSSV, bảng điểm hay cookie trường. Hủy, hết hạn và kết thúc backend đều loại bỏ kết quả đang chờ.
- Sau xác thực, thông tin và bảng điểm được lưu vào hồ sơ của đúng MSSV trong MongoDB. Phiên Advisor dùng cookie HttpOnly hiện có. Tài khoản demo và quản trị không được tự động liên kết với CTT.
- Giới hạn hai worker trình duyệt cùng lúc và năm lần mở cửa sổ mới trên mỗi IP trong năm phút. Gửi lại yêu cầu từ cùng trình duyệt sẽ tiếp tục kết nối hiện có, không tạo thêm cửa sổ hay dùng thêm lượt. Yêu cầu không hợp lệ và xung đột không tính vào giới hạn. Khi thực sự cần chờ, giao diện đếm ngược theo `Retry-After`. Hủy kết nối vẫn tính vào giới hạn worker cho đến khi trình duyệt được đóng.

## Cấu hình

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `CTT_BROWSER_LOGIN_ENABLED` | `true` | Cho phép bộ kết nối trên PC; tắt trên server dùng chung |
| `CTT_BROWSER_CHANNEL` | `chromium` | Chromium riêng đi kèm phiên bản Playwright; có thể chỉ định channel khác để chẩn đoán |
| `CTT_LOGIN_TIMEOUT_SECONDS` | `300` | Thời gian chờ thao tác đăng nhập, giới hạn 60–600 giây |

Các thư viện và trình duyệt phải được cài trong môi trường chạy backend. Không cần tải lại APK hay giữ điện thoại kết nối để dùng tính năng.

## Kiểm thử

Từ thư mục `backend`:

```powershell
& ./.venv-win/Scripts/python.exe -m unittest tests.test_school_login -v
```

Từ thư mục gốc, kiểm tra giao diện bằng dữ liệu giả, không gọi CTT hay backend thật:

```powershell
npm --prefix frontend run build
& backend/.venv-win/Scripts/python.exe scripts/check_auth_ui.py
```

Ảnh kiểm tra được lưu trong `tmp/auth-ui/` (không đưa vào Git). Bộ kiểm thử bao gồm hủy/thử lại, lỗi MSSV, đổi tab, lỗi tài khoản Advisor, màn đăng ký và tràn ngang trên màn hình nhỏ. Bộ backend kiểm tra danh tính, quyền sở hữu phiên kết nối, hết hạn, chống dùng lại, lỗi lưu hồ sơ và cô lập dữ liệu sinh viên.

Kiểm tra các dịch vụ bổ sung:

```powershell
& backend/.venv-win/Scripts/python.exe -m unittest discover -s backend/tests -t backend -q
& backend/.venv-win/Scripts/python.exe scripts/check_student_services_ui.py
```

Các API dịch vụ chỉ đọc dữ liệu của đúng sinh viên đang đăng nhập; dữ liệu mẫu cũ đã bị loại bỏ. GDTC/GDQP được ghi nhận **hoàn thành học phần** khi đạt đủ các mã môn trong nhóm 220/230 của CTĐT tương ứng. Nhóm 0 tín chỉ vẫn xét từng môn; không kết luận hoàn thành từ tổng 0/0 TC hoặc từ một môn PE/MIL bất kỳ. Giao diện hiển thị số môn đạt và điểm chữ làm căn cứ, không tự ghi nhận đã cấp chứng chỉ. Tiếng Anh cơ sở và điểm thi tiếng Anh không tự xác nhận chuẩn đầu ra. File PDF và HTML thô không được lưu vào hồ sơ; chỉ lưu các dòng văn bản đã đọc và xác nhận.
