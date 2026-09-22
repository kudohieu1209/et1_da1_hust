<!-- RAG_STATUS: UNVERIFIED - Bản nháp demo, không dùng làm nguồn tư vấn. -->
# ĐỀ CƯƠNG CHI TIẾT & MÔ TẢ NỘI DUNG HỌC PHẦN (CTĐT KỸ THUẬT ĐIỆN TỬ - ET1)
*(Trường Điện - Điện tử, Đại học Bách Khoa Hà Nội)*

---

## 1. KHỐI CƠ SỞ NHÓM NGÀNH & CỐT LÕI NGÀNH

### ET2040 - Cấu kiện điện tử (Electronic Devices)
- **Số tín chỉ:** 2.0 TC (Lý thuyết: 2, Bài tập: 0.5)
- **Học kỳ gợi ý:** Kỳ 3
- **Nội dung chính:**
  + Vật lý bán dẫn cơ bản: chất bán dẫn thuần, pha tạp loại P và N, hạt tải đa số và thiểu số, cơ chế khuếch tán và trôi.
  + Cấu tạo và nguyên lý hoạt động của chuyển tiếp P-N, Diode chỉnh lưu, Diode Zener, Diode Schottky, LED và Photodiode.
  + Transistor lưỡng cực (BJT): cấu tạo NPN/PNP, các chế độ làm việc (khuếch đại, bão hòa, ngắt), các cách mắc (CE, CB, CC).
  + Transistor hiệu ứng trường (MOSFET/JFET): MOSFET kênh đặt sẵn và cảm ứng (NMOS, PMOS, CMOS), đường đặc tuyến V-I.
- **Vai trò trong CTĐT:** Là môn học nền móng cốt lõi nhất của ngành Điện tử. Môn này là điều kiện tiên quyết trực tiếp của **ET3220 (Điện tử số)** và **ET3230 (Điện tử tương tự 1)**. Nếu không qua môn này, sinh viên sẽ bị chặn toàn bộ chuỗi môn chuyên ngành phía sau!

### ET2050 - Lý thuyết mạch (Circuit Theory)
- **Số tín chỉ:** 3.0 TC
- **Học kỳ gợi ý:** Kỳ 3
- **Nội dung chính:** Các định luật Kirchhoff (KCL, KVL), phương pháp phân tích mạch điện xác lập điều hòa (dòng nhánh, điện thế nút, dòng mắt lưới), đồ thị vectơ, công suất tác dụng P, phản kháng Q và biểu kiến S, mạch cộng hưởng RLC, mạch ba pha và quá trình quá độ trong mạch R-L-C bằng biến đổi Laplace.
- **Công cụ hỗ trợ:** MATLAB, LTSpice / Multisim mô phỏng mạch điện.

### ET2060 - Tín hiệu và Hệ thống (Signals and Systems)
- **Số tín chỉ:** 3.0 TC
- **Học kỳ gợi ý:** Kỳ 4
- **Nội dung chính:**
  + Tín hiệu liên tục và rời rạc, các phép toán trên tín hiệu, tính chất của hệ thống tuyến tính dừng (LTI), tích chập (Convolution).
  + Khai triển chuỗi Fourier và biến đổi Fourier liên tục (CTFT), biến đổi Fourier rời rạc thời gian (DTFT).
  + Phân tích hệ thống trong miền tần số, đáp ứng tần số, bộ lọc lý tưởng.
  + Biến đổi Laplace cho hệ liên tục và Biến đổi Z cho hệ rời rạc, hàm truyền đạt $H(s)$ và $H(z)$, phân tích tính ổn định của hệ thống.
- **Vai trò trong CTĐT:** Tiên quyết cho môn **ET4020 (Xử lý tín hiệu số - DSP)** và các môn truyền thông, viễn thông.

### ET3300 - Kỹ thuật vi xử lý (Microprocessor Engineering)
- **Số tín chỉ:** 3.0 TC (Lý thuyết: 2.5, Thí nghiệm/Thực hành: 0.5)
- **Học kỳ gợi ý:** Kỳ 5
- **Nội dung chính:**
  + Kiến trúc phần cứng vi xử lý và vi điều khiển: Kiến trúc von Neumann và Harvard, tập lệnh RISC vs CISC, pipeline.
  + Vi điều khiển họ ARM Cortex-M (STM32) hoặc 8051/AVR: Cấu trúc thanh ghi, bộ nhớ Flash/SRAM, các cổng I/O.
  + Lập trình giao tiếp ngoại vi: Ngắt (Interrupt), Định thời (Timer/Counter), Điều chế độ rộng xung (PWM), ADC/DAC.
  + Các chuẩn giao tiếp truyền thông nối tiếp: UART/USART, SPI, I2C.
- **Công cụ & Phần mềm:** Keil C / STM32CubeIDE, KIT thí nghiệm vi điều khiển STM32F4 / 8051, Proteus mô phỏng mạch.
- **Lời khuyên chọn môn:** Môn học bắt buộc cực kỳ quan trọng cho sinh viên theo hướng Hệ thống nhúng (Embedded) và Thiết kế vi mạch.

### ET3220 - Điện tử số (Digital Electronics)
- **Số tín chỉ:** 3.0 TC
- **Học kỳ gợi ý:** Kỳ 4
- **Nội dung chính:** Đại số Boole, tối thiểu hóa hàm logic (bìa Karnaugh), thiết kế mạch logic tổ hợp (Multiplexer, Decoder, ALU, Bộ cộng), mạch logic tuần tự (Flip-Flop SR, JK, D, T, thanh ghi dịch, bộ đếm đồng bộ/bất đồng bộ), ngôn ngữ mô tả phần cứng Verilog/VHDL cơ bản, cấu trúc bộ nhớ ROM/RAM và vi mạch logic khả trình FPGA/CPLD.

### ET3230 & ET3241 - Điện tử tương tự I & II (Analog Electronics 1 & 2)
- **Số tín chỉ:** 3.0 TC mỗi môn
- **Học kỳ gợi ý:** Kỳ 4 (Phần 1) và Kỳ 5 (Phần 2)
- **Nội dung chính:** Mạch khuếch đại dùng BJT và MOSFET, phân cực DC, mô hình tín hiệu nhỏ xoay chiều (Small-signal AC model), mạch khuếch đại thuật toán (Op-Amp) lý tưởng và thực tế, mạch hồi tiếp âm, mạch lọc tích cực (Active Filters), mạch dao động tạo sóng và mạch khuếch đại công suất (Class A, B, AB).

### ET4230 - Mạng máy tính (Computer Networks)
- **Số tín chỉ:** 3.0 TC
- **Học kỳ gợi ý:** Kỳ 6
- **Nội dung chính:** Mô hình tham chiếu OSI 7 tầng và bộ giao thức TCP/IP, tầng liên kết dữ liệu (Ethernet, CSMA/CD, địa chỉ MAC), tầng mạng (Giao thức IP, định tuyến tĩnh và động OSPF/BGP, chia mạng con CIDR/VLSM), tầng giao vận (TCP cơ chế bắt tay 3 bước, điều khiển luồng, điều khiển tắc nghẽn vs UDP), tầng ứng dụng (DNS, HTTP/HTTPS, DHCP).
- **Công cụ thực hành:** Wireshark bắt gói tin, Cisco Packet Tracer cấu hình Router/Switch.

---

## 2. CÁC MÔ-ĐUN CHUYÊN NGÀNH MŨI NHỌN (ELECTIVES)

### MÔ-ĐUN 1: THIẾT KẾ VI MẠCH & BÁN DẪN (IC DESIGN & SEMICONDUCTORS)

#### ET4340 - Thiết kế VLSI (VLSI Design)
- **Số tín chỉ:** 3.0 TC
- **Định hướng:** Thiết kế vi mạch số (Digital IC Design)
- **Nội dung học tập:**
  + Quy trình thiết kế vi mạch ASIC từ RTL đến GDSII: RTL Design, Logic Synthesis, Static Timing Analysis (STA), Place & Route (P&R).
  + Ngôn ngữ mô tả phần cứng Verilog HDL nâng cao: Viết mã tổng hợp được (Synthesizable Verilog), thiết kế FSM (Máy trạng thái hữu hạn), kiểm soát xung nhịp Clock Domain Crossing (CDC).
  + Thiết kế mạch tích hợp CMOS cấp cổng: Trì hoãn truyền lan (Propagation delay), công suất tiêu tán động và tĩnh.
- **Công cụ & Phần mềm chuyên dụng:** Synopsys Design Compiler, Cadence Genus/Innovus, ModelSim/QuestaSim, FPGA Vivado.
- **Cơ hội nghề nghiệp:** Kỹ sư RTL Design, Kỹ sư Synthesis/STA tại Synopsys, Marvell, Qualcomm, Viettel High Tech, FPT Semiconductor.

#### ET4033 - Thiết kế IC tương tự (Analog IC Design)
- **Số tín chỉ:** 3.0 TC
- **Định hướng:** Thiết kế vi mạch tương tự và tín hiệu hỗn hợp (Analog/Mixed-Signal IC)
- **Nội dung học tập:** Mô hình transistor MOSFET tín hiệu nhỏ cho IC tương tự, mạch nguồn dòng gương (Current Mirror), mạch khuếch đại vi sai (Differential Amplifier), mạch Op-Amp CMOS hai tầng, mạch bù tần số và độ dự trữ pha (Phase Margin), mạch tạo điện áp chuẩn Bandgap Reference.
- **Công cụ sử dụng:** Cadence Virtuoso, Synopsys Custom Compiler, HSPICE, Spectre.

#### ET4356 - Kiểm chứng và kiểm tra vi mạch (IC Verification & Testing)
- **Số tín chỉ:** 3.0 TC
- **Nội dung:** Phương pháp kiểm chứng chức năng thiết kế vi mạch số, ngôn ngữ SystemVerilog và phương pháp luận Universal Verification Methodology (UVM), viết Testbench tự động, Assertions (SVA), độ bao phủ chức năng (Functional Coverage).

#### ET4358 - Cơ sở công nghệ vi điện tử (Microelectronic Technology Fundamentals)
- **Số tín chỉ:** 3.0 TC
- **Nội dung:** Công nghệ chế tạo chất bán dẫn trong phòng sạch: Oxy hóa nhiệt, quang khắc (Photolithography), khắc axit (Etching), cấy ion (Ion Implantation), lắng đọng màng mỏng (CVD/PVD), công nghệ đóng gói IC và kiểm thử wafer.

---

### MÔ-ĐUN 2: HỆ THỐNG NHÚNG VÀ IOT (EMBEDDED SYSTEMS & IOT)

#### ET4361 - Hệ thống nhúng và thiết kế giao tiếp nhúng (Embedded Systems Design)
- **Số tín chỉ:** 3.0 TC
- **Nội dung:** Thiết kế phần cứng hệ thống nhúng với SoC/FPGA, hệ điều hành thời gian thực (FreeRTOS): Nhiệm vụ (Task), Lập lịch (Scheduler), Hàng đợi (Queue), Semaphore, Mutex; Giao tiếp nhúng chuyên dụng: CAN bus, SPI tốc độ cao, I2S truyền âm thanh số, thiết kế mạch in nhiều lớp (Altium Designer).
- **Công cụ:** FreeRTOS, ESP32, STM32, Altium Designer.

#### ET4291 - Hệ điều hành và Hệ điều hành nhúng (Embedded Linux)
- **Số tín chỉ:** 3.0 TC
- **Nội dung:** Cấu trúc nhân Linux Kernel, lập trình C hệ thống (POSIX API, System Calls, đa luồng Pthreads, IPC), xây dựng Linux nhúng cho board mạch (Raspberry Pi / BeagleBone) với Yocto Project / Buildroot, viết Linux Device Driver cơ bản (Character Device Driver, GPIO Driver).

---

### MÔ-ĐUN 3: MẠNG VÀ HỆ THỐNG VIỄN THÔNG (TELECOM & NETWORKS)

#### ET4250 - Hệ thống viễn thông (Telecommunication Systems)
- **Số tín chỉ:** 3.0 TC
- **Nội dung:** Các phương pháp điều chế số: ASK, FSK, PSK, QAM, kỹ thuật ghép kênh phân chia theo tần số trực giao (OFDM), mã hóa kênh kiểm soát lỗi (Hamming, Reed-Solomon, LDPC), kiến trúc mạng di động 4G LTE và 5G NR, mạng truyền dẫn quang WDM.

#### ET4070 - Cơ sở truyền số liệu (Data Communications)
- **Số tín chỉ:** 3.0 TC
- **Nội dung:** Mã hóa đường truyền (Line Coding: NRZ, Manchester, AMI), đồng bộ khung và phát hiện lỗi (CRC), các giao thức điều khiển liên kết dữ liệu (Stop-and-Wait, Go-Back-N, Selective Repeat), các kỹ thuật chuyển mạch (chuyển mạch kênh, chuyển mạch gói).

---

## 3. CÁC ĐỒ ÁN VÀ THỰC TẬP THỰC HÀNH

### ET3290 - Đồ án thiết kế I (Design Project 1)
- **Số tín chỉ:** 2.0 TC
- **Điều kiện đăng ký:** Song hành với `ET3260=` (Kỹ thuật phần mềm ứng dụng) hoặc đã học trước `ET3260`.
- **Yêu cầu sản phẩm:** Sinh viên làm theo nhóm 2 - 3 người, thiết kế và chế tạo một sản phẩm phần cứng điện tử hoàn chỉnh (mạch nguồn, vi điều khiển, cảm biến, giao tiếp không dây Bluetooth/WiFi/LoRa) hoặc một ứng dụng nhúng/IoT.

### ET4010 - Đồ án thiết kế II (Design Project 2)
- **Số tín chỉ:** 2.0 TC
- **Điều kiện đăng ký:** Môn mở tự do (Không có môn tiên quyết trên CTT Bách Khoa).
- **Quy định quan trọng:** Sinh viên **hoàn toàn có thể học ET3290 và ET4010 cùng một học kỳ** nếu sắp xếp được thời gian với thầy cô hướng dẫn. Đồ án 2 thường yêu cầu mức độ thuật toán và chuyên môn sâu hơn (xử lý ảnh nhúng, thiết kế vi mạch FPGA, mô phỏng truyền thông).

### ET4900 - Đồ án tốt nghiệp Cử nhân (Bachelor Capstone Project)
- **Số tín chỉ:** 6.0 TC
- **Điều kiện giao đồ án:**
  + Tích lũy tối thiểu **110 tín chỉ**.
  + Không bị Cảnh cáo học tập mức 2 tại thời điểm xét.
  + Đã hoàn thành các môn cốt lõi: Đồ án thiết kế 1 (`ET3290`), Đồ án thiết kế 2 (`ET4010`), Thực tập kỹ thuật (`ET3270`).
- **Thời gian thực hiện:** 1 học kỳ chính (khoảng 15 tuần làm việc độc lập dưới sự hướng dẫn của 1 giảng viên và bảo vệ trước Hội đồng).
