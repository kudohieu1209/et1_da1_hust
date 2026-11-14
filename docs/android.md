# Hướng dẫn đóng gói ứng dụng Android (Capacitor) cho HUST Course Advisor

## Chạy ngay qua USB trên PC hiện tại

Bản `usbDebug` cài thành **AdvisorBK USB** (`vn.hust.advisor.usb`), song song với app thông thường. WebView mở `http://localhost:8000` qua `adb reverse`, dùng cùng backend/MongoDB và cookie phiên trên origin này. Cửa sổ CTT mở trên PC; người dùng tự nhập tài khoản và mật khẩu trên trang trường, sau đó app điện thoại nhận phiên Advisor.

1. Chạy backend trên PC, kiểm tra `http://localhost:8000/api/health`.
2. Cắm điện thoại, cho phép USB debugging.
3. Từ thư mục gốc:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_android_usb.ps1 -Build
```

Những lần sau, nếu đã có APK USB, bỏ `-Build`. Khi có nhiều thiết bị, thêm `-DeviceSerial <serial>`. Script khôi phục cổng USB, cài/cập nhật app USB và mở app. Cần JDK 21, Android SDK và Node.js để build.

Trong app chọn **Tài khoản trường**, sau đó đăng nhập trong cửa sổ CTT trên PC. Giữ cáp USB và backend chạy khi sử dụng bản thử. Đây chưa phải chế độ đăng nhập trường trực tiếp trên điện thoại hoặc dùng từ Internet.

Thiết lập HTTP chỉ áp dụng cho build `usbDebug`, giới hạn `localhost`/`127.0.0.1`; build thường và release giữ cấu hình mạng riêng. APK thử nằm tại `frontend/android/app/build/outputs/apk/usbDebug/app-usbDebug.apk`.

Tài liệu hướng dẫn đóng gói frontend React thành ứng dụng Android (.apk) bằng Capacitor theo kiến trúc **Remote Web App (Cách A)**: WebView tải trực tiếp web frontend và backend được triển khai chung một domain HTTPS qua Reverse Proxy.

---

## 1. Yêu cầu & Cấu hình Backend

Do ứng dụng sử dụng cơ chế bảo mật HttpOnly cookie (`hust_session`, `SameSite=Lax`) và kiểm tra nghiêm ngặt `Origin` chống CSRF (middleware `reject_cross_site_writes`), kiến trúc triển khai bắt buộc phải đảm bảo WebView và API chạy trên **cùng một origin HTTPS**.

- **Domain sản phẩm:** `{{APP_DOMAIN}}` (Ví dụ: `https://advisor.example.com`).
- **Biến môi trường Backend (.env):**
  ```env
  COOKIE_SECURE=true
  CORS_ORIGINS={{APP_DOMAIN}}
  SESSION_COOKIE_NAME=hust_session
  ```
- **Cấu hình Reverse Proxy cùng domain:**

  ### Ví dụ cấu hình Nginx:
  ```nginx
  server {
      listen 443 ssl http2;
      server_name {{APP_DOMAIN_HOST}}; # ví dụ: advisor.example.com

      ssl_certificate /path/to/fullchain.pem;
      ssl_certificate_key /path/to/privkey.pem;

      # 1. Định tuyến Frontend tĩnh
      location / {
          root /path/to/et1_da1_hust/frontend/dist;
          index index.html;
          try_files $uri $uri/ /index.html;
      }

      # 2. Reverse proxy /api về FastAPI backend
      location /api/ {
          proxy_pass http://127.0.0.1:8000/api/;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
  }
  ```

  ### Ví dụ cấu hình Caddy:
  ```caddy
  {{APP_DOMAIN_HOST}} {
      # Reverse proxy API
      handle /api/* {
          reverse_proxy 127.0.0.1:8000
      }

      # Phục vụ Frontend SPA
      handle {
          root * /path/to/et1_da1_hust/frontend/dist
          try_files {path} /index.html
          file_server
      }
  }
  ```

---

## 2. Cấu hình Capacitor trên Mobile

File cấu hình tại `frontend/capacitor.config.json`:
```json
{
  "appId": "vn.hust.advisor",
  "appName": "HUST Advisor",
  "webDir": "dist",
  "server": {
    "url": "{{APP_DOMAIN}}",
    "cleartext": false,
    "androidScheme": "https",
    "allowNavigation": [
      "{{APP_DOMAIN}}"
    ]
  }
}
```
> [!IMPORTANT]
> Thay thế placeholder `{{APP_DOMAIN}}` bằng URL HTTPS thực tế của hệ thống (ví dụ: `https://advisor.example.com`) trước khi đồng bộ và build bản phát hành.

---

## 3. Lệnh Build Debug APK

### Bước 1: Đồng bộ mã nguồn frontend và cấu hình Capacitor vào Android
```bash
cd frontend
npm run cap:sync
```

### Bước 2: Build Debug APK
- Trên Linux / macOS / Git Bash:
  ```bash
  cd frontend/android && ./gradlew assembleDebug
  ```
- Hoặc dùng npm script:
  ```bash
  cd frontend
  npm run android:debug
  ```
- Trên Windows PowerShell / Command Prompt:
  ```powershell
  cd frontend\android
  .\gradlew.bat assembleDebug
  ```

### Vị trí file APK sau khi build thành công:
```
frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

### Cài đặt lên điện thoại qua ADB:
1. Bật **Tùy chọn cho nhà phát triển (Developer Options)** và **Gỡ lỗi qua USB (USB Debugging)** trên điện thoại Android.
2. Cắm cáp USB vào máy tính, kiểm tra nhận diện:
   ```bash
   adb devices
   ```
3. Cài đặt file APK lên thiết bị:
   ```bash
   adb install -r frontend/android/app/build/outputs/apk/debug/app-debug.apk
   ```

---

## 4. Tạo Keystore và Build Release (assembleRelease)

Để phát hành ứng dụng hoặc cài đặt bản chính thức không cảnh báo debug:

### 1. Tạo Keystore (Không commit file này vào Git):
Chạy lệnh sau trên terminal (thay thế alias và thông tin phù hợp):
```bash
keytool -genkey -v -keystore hust-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias hustadvisor
```
*Lưu ý: Lưu trữ file `.jks` và mật khẩu cẩn thận ở nơi bảo mật.*

### 2. Thiết lập mật khẩu qua biến môi trường (KHÔNG ghi vào file cấu hình):
Thiết lập các biến môi trường trong terminal phiên làm việc hiện tại:
- **Trên Windows PowerShell:**
  ```powershell
  $env:KEYSTORE_PATH="C:\duong\dan\toi\hust-release-key.jks"
  $env:KEYSTORE_PASSWORD="mat_khau_keystore"
  $env:KEY_ALIAS="hustadvisor"
  $env:KEY_PASSWORD="mat_khau_key"
  ```
- **Trên Linux / macOS / Bash:**
  ```bash
  export KEYSTORE_PATH="/duong/dan/toi/hust-release-key.jks"
  export KEYSTORE_PASSWORD="mat_khau_keystore"
  export KEY_ALIAS="hustadvisor"
  export KEY_PASSWORD="mat_khau_key"
  ```

### 3. Cấu hình Signing trong `frontend/android/app/build.gradle` (nếu cần tự động ký khi release):
Trong khối `android { ... }`:
```groovy
signingConfigs {
    release {
        def ksPath = System.getenv("KEYSTORE_PATH")
        if (ksPath) {
            storeFile file(ksPath)
            storePassword System.getenv("KEYSTORE_PASSWORD")
            keyAlias System.getenv("KEY_ALIAS")
            keyPassword System.getenv("KEY_PASSWORD")
        }
    }
}
buildTypes {
    release {
        signingConfig signingConfigs.release
        minifyEnabled false
        proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
    }
}
```

### 4. Lệnh build Release:
```bash
cd frontend/android
./gradlew assembleRelease
# hoặc trên Windows: .\gradlew.bat assembleRelease
```
Vị trí file APK release:
```
frontend/android/app/build/outputs/apk/release/app-release.apk
```

---

## 5. Thử nghiệm nhanh trong mạng nội bộ (LAN Dev)

Chỉ sử dụng để kiểm thử tính năng trên thiết bị thật trong quá trình phát triển (khi chưa có HTTPS domain):

1. Tạo file cấu hình tạm `frontend/capacitor.config.dev.json`:
   ```json
   {
     "appId": "vn.hust.advisor",
     "appName": "HUST Advisor (Dev LAN)",
     "webDir": "dist",
     "server": {
       "url": "http://192.168.1.xxx:5173",
       "cleartext": true
     }
   }
   ```
2. Sao chép đè vào `capacitor.config.json` và chạy `npx cap sync android`.
3. Khởi động Vite với `npm run dev -- --host` và Backend với `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

> [!WARNING] Cảnh báo rủi ro bảo mật LAN Dev
> - `cleartext: true` cho phép truyền dữ liệu HTTP không mã hóa qua mạng Wi-Fi nội bộ, khiến cookie và thông tin xác thực dễ bị nghe lén (Man-in-the-Middle).
> - Tính năng này **tuyệt đối không bật** trong bản phát hành chính thức (`cleartext: false`).
