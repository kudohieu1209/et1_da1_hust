#!/usr/bin/env python3
"""Build the trusted Markdown corpus from official HUST PDF sources.

The generated files keep page boundaries so the RAG layer can cite the
official document and page instead of relying on hand-written summaries.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_DIR / "data" / "raw"
DOCUMENTS_DIR = PROJECT_DIR / "data" / "documents"


def extract_page(pdf_path: Path, page_number: int) -> str:
    result = subprocess.run(
        [
            "pdftotext",
            "-enc",
            "UTF-8",
            "-layout",
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            str(pdf_path),
            "-",
        ],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
    text = result.stdout.replace("\f", "").strip()
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def build_document(
    *,
    pdf_name: str,
    output_name: str,
    title: str,
    source_url: str,
    document_type: str,
    effective_period: str,
    pages: range,
    note: str,
    curated_summary: str = "",
    curated_page: int = 0,
    page_fixes: dict[int, tuple[tuple[str, str], ...]] | None = None,
) -> None:
    pdf_path = RAW_DIR / pdf_name
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    front_matter = [
        "---",
        "rag_status: VERIFIED",
        f'title: "{title}"',
        f'document_type: "{document_type}"',
        f'effective_period: "{effective_period}"',
        f'source_url: "{source_url}"',
        f'source_file: "{pdf_name}"',
        "---",
        "",
        f"# {title}",
        "",
        note,
        "",
    ]
    if curated_summary and curated_page:
        # Layout-heavy sources (calendar grids) are transcribed by hand and kept
        # under their page heading so citations still point at the PDF page.
        front_matter.extend([f"## Trang PDF {curated_page}", "", curated_summary.strip(), ""])
    elif curated_summary:
        front_matter.extend(["## Thông tin tra cứu chính", "", curated_summary.strip(), ""])
    sections = []
    for page_number in pages:
        page_text = extract_page(pdf_path, page_number)
        for pattern, replacement in (page_fixes or {}).get(page_number, ()):
            # Tables whose cells pdftotext misaligns are rewritten from the
            # rendered page; fail loudly if the source layout ever changes.
            page_text, count = re.subn(pattern, lambda _: replacement, page_text, flags=re.S)
            if count != 1:
                raise ValueError(f"{pdf_name} page {page_number}: fix matched {count} times: {pattern!r}")
        if page_text:
            sections.extend(
                [
                    f"## Trang PDF {page_number}",
                    "",
                    page_text,
                    "",
                ]
            )

    output_path = DOCUMENTS_DIR / output_name
    output_path.write_text("\n".join(front_matter + sections).strip() + "\n", encoding="utf-8")
    print(f"Generated {output_path.relative_to(PROJECT_DIR)}")


CTT_FILES = "https://ctt.hust.edu.vn/Upload/Nguy%E1%BB%85n%20Qu%E1%BB%91c%20%C4%90%E1%BA%A1t/files"
CTSV_DRIVE = "https://drive.google.com/file/d/{}/view"

ACADEMIC_CALENDAR_2026_2027 = """
Bản chép tay các mốc trong bảng "Khung kế hoạch năm học 2026-2027" (phụ lục kèm quyết định, số quyết định để trống trên bản công bố). Mỗi tuần tính từ thứ Hai ghi ở cột "Ngày đầu tuần". Ký hiệu trong bảng: H - tuần học kỳ chính; T - thi giữa kỳ và kết thúc học phần; QPAN - Giáo dục Quốc phòng và An ninh; GH - gia hạn thời gian học; BVTN - bảo vệ tốt nghiệp; D - dự trữ.

### Học kỳ 1 (2026.1)

- Tuần 1, từ 31/8/2026: Năm học mới 2026-2027; K71 nhập học, sinh hoạt đầu khóa.
- Tuần 2, từ 7/9/2026: Tuần đầu học kỳ 1 (2026.1).
- Tuần 4, từ 21/9/2026: Hạn đăng ký xét tốt nghiệp đợt 2025.3.
- Tuần 5, từ 28/9/2026: Đăng ký học phần muốn học học kỳ 2 (2026.2).
- Tuần 6, từ 5/10/2026: Hạn rút học phần học kỳ 1.
- Tuần 10, từ 2/11/2026: Thi giữa kỳ học kỳ 1 cho K67-K70.
- Tuần 11, từ 9/11/2026: Mở đăng ký kỹ sư chuyên sâu học kỳ 1.
- Tuần 14, từ 30/11/2026: Hạn đăng ký kỹ sư chuyên sâu học kỳ 1.
- Tuần 15, từ 7/12/2026: Đăng ký lớp học kỳ 2.
- Tuần 16, từ 14/12/2026: Bắt đầu đánh giá rèn luyện học kỳ 1.
- Tuần 18, từ 28/12/2026: Điều chỉnh đăng ký lớp học kỳ 2.
- Tuần thi học kỳ 1: K68, K69, K70 thi từ tuần 19 (từ 4/1/2027) đến hết tuần 21; K71 thi tuần 20-21 (từ 11/1/2027 đến 24/1/2027).
- Tuần 20, từ 11/1/2027: Đăng ký thêm vào lớp học kỳ 2.

### Học kỳ 2 (2026.2)

- Tuần 22, từ 25/1/2027: Tuần học đầu học kỳ 2 (2026.2).
- Tuần 23-24, từ 1/2/2027 đến 14/2/2027: Nghỉ Tết Nguyên đán Đinh Mùi.
- Tuần 26, từ 22/2/2027: Kết thúc đánh giá rèn luyện học kỳ 1.
- Tuần 27, từ 1/3/2027: Hạn đăng ký xét tốt nghiệp đợt 2026.1.
- Tuần 28, từ 8/3/2027: Đăng ký học phần muốn học 2026.3 và 2027.1.
- Tuần 30, từ 22/3/2027: Hạn rút học phần học kỳ 2.
- Tuần 32, từ 5/4/2027: Thi giữa học kỳ 2 cho K67-K70.
- Tuần 33, từ 12/4/2027: Mở đăng ký kỹ sư chuyên sâu học kỳ 2.
- Tuần 36, từ 3/5/2027: Hạn đăng ký kỹ sư chuyên sâu học kỳ 2.
- Tuần 38, từ 17/5/2027: Bắt đầu đánh giá rèn luyện học kỳ 2.
- Tuần 39, từ 24/5/2027: Đăng ký lớp học kỳ hè 2026.3.
- Tuần thi học kỳ 2: K68, K69, K70 thi từ tuần 41 (từ 7/6/2027) đến hết tuần 43; K71 thi tuần 42-43 (từ 14/6/2027 đến 27/6/2027).
- Tuần 43, từ 21/6/2027: Đăng ký thêm vào lớp học kỳ hè.

### Học kỳ hè (2026.3) và chuyển sang năm học 2027-2028

- Tuần 44, từ 28/6/2027: Tuần học đầu kỳ 2026.3; đăng ký lớp 2027.1.
- Tuần 45, từ 5/7/2027: Mở đăng ký kỹ sư chuyên sâu học kỳ hè (bản gốc ghi "HK hè 2027.3").
- Tuần 46, từ 12/7/2027: Hạn đăng ký xét tốt nghiệp đợt 2026.2; điều chỉnh đăng ký lớp kỳ 2027.1.
- Tuần 47, từ 19/7/2027: Hạn đăng ký kỹ sư chuyên sâu học kỳ hè (bản gốc ghi "HK hè 2027.3").
- Tuần 48, từ 26/7/2027: Đăng ký thêm vào lớp kỳ 2027.1.
- Tuần 49, từ 2/8/2027: Kết thúc đánh giá rèn luyện học kỳ 2.
- Từ 23/8/2027: Năm học mới 2027-2028 (dự kiến).
- Từ 30/8/2027: Tuần đầu học kỳ 1 năm 2027-2028 (2027.1, dự kiến).

Chú ý đối với K71: mỗi kỳ chính gồm 15 tuần học trực tiếp và 1,5 tuần trực tuyến; không có học kỳ hè. K71 học Giáo dục Quốc phòng và An ninh theo nhóm, xen kẽ giữa các tuần; lịch theo nhóm xem trực tiếp trong bảng PDF.

### Tốt nghiệp đại học

| Đợt xét | Hạn đăng ký xét TN và hạn xét điểm ngoại ngữ TN | Nhận bằng TN | Tổ chức phát bằng TN (dự kiến) |
|---|---|---|---|
| 2025.3 | 27/9/2026 | Từ 7/11/2026 | 24-25/4/2027 |
| 2026.1 | 7/3/2027 | Từ 24/4/2027 | 24-25/4/2027 |
| 2026.2 | 18/7/2027 | Từ 9/9/2027 | 18-19/9/2027 |

### Kế hoạch thu học phí

Mỗi học kỳ, học phí thu theo 2 đợt:

| Học kỳ | Đợt 1 | Đợt 2 |
|---|---|---|
| 2026.1 | 21/9 - 4/10/2026 | 16/11 - 29/11/2026 |
| 2026.2 | 22/2 - 7/3/2027 | 10/5 - 23/5/2027 |
| 2026.3 | 12/7 - 18/7/2027 (một đợt) | |

### Các ngày nghỉ lễ

- 1/1/2027: Tết Dương lịch.
- 1/2 - 14/2/2027: Tết Nguyên đán.
- 26/4: Giỗ tổ Hùng Vương.
- 30/4 - 1/5: Giải phóng miền Nam và Quốc tế lao động.
- 2/9: Quốc khánh.
- 24/11: Ngày Văn hóa Việt Nam.

Ghi chú khác trong bảng: học viên cao học làm thủ tục gia hạn trước khi hết thời gian học tập chuẩn; nghiên cứu sinh nộp báo cáo định kỳ 6 tháng tại Ban Đào tạo. Trang thông tin: https://ctt.hust.edu.vn, http://sdh.hust.edu.vn, https://qldt.hust.edu.vn.
"""


DOCUMENTS = [
    dict(
        pdf_name="QCDT_2025_5445_QD-DHBK.pdf",
        output_name="quy_che_dao_tao_2025_verified.md",
        title="Quy chế đào tạo Đại học Bách khoa Hà Nội năm 2025",
        source_url=f"{CTT_FILES}/DTDH_QDQC/Hoctap/QCDT_2025_5445_QD-DHBK.pdf",
        document_type="academic_regulation",
        effective_period="Từ năm học 2025-2026",
        pages=range(1, 35),
        note=(
            "Bản trích xuất nguyên văn theo trang từ Quyết định 5445/QĐ-ĐHBK "
            "ngày 28/05/2025. Khi có khác biệt hiển thị, PDF gốc là căn cứ ưu tiên."
        ),
    ),
    dict(
        pdf_name="So tay sinh vien_2026.pdf",
        output_name="so_tay_sinh_vien_2026_verified.md",
        title="Sổ tay sinh viên HUST 2026 - Học bổng và hỗ trợ sinh viên",
        source_url="https://www.hust.edu.vn/",
        document_type="student_handbook",
        effective_period="Năm 2026",
        pages=range(14, 19),
        note=(
            "Trích các trang PDF 14-18 về học bổng khuyến khích học tập và các chương trình "
            "hỗ trợ. Tài liệu gốc được lưu trong data/raw; PDF gốc là căn cứ ưu tiên."
        ),
        curated_summary="""
### Học bổng khuyến khích học tập: các loại và mức học bổng

Theo trang PDF 16 (trang in 30) về Học bổng khuyến khích học tập:

- Loại A (xuất sắc): GPA từ 3,6 và điểm rèn luyện học kỳ từ 90; mức học bổng bằng 1,5 lần mức loại C.
- Loại B (giỏi): GPA từ 3,2 và điểm rèn luyện học kỳ từ 80; mức học bổng bằng 1,2 lần mức loại C.
- Loại C (khá): GPA từ 2,5 và điểm rèn luyện học kỳ từ 65; mức học bổng bằng tổng học phí của các học phần có tính điểm GPA của học kỳ chính liền trước.

### Các trường hợp không được xét học bổng khuyến khích học tập

Không xét cấp trong các trường hợp được liệt kê trên cùng trang: bị kỷ luật từ khiển trách; không đạt ngưỡng đăng ký tín chỉ; học quá thời gian chuẩn; hoặc thuộc chương trình đối tác nước ngoài cấp một văn bằng duy nhất. Dòng ngưỡng 15 tín chỉ trong bản gốc in "ít nhất hơn 15", có dấu hiệu lỗi biên tập; hệ thống không tự sửa nghĩa và khuyến nghị xác nhận với Ban Công tác sinh viên.

### Học bổng Trần Đại Nghĩa: mức học bổng và nguyên tắc xét

Theo trang PDF 17 (trang in 32):

- Học bổng Trần Đại Nghĩa có 2 mức tương ứng với 50% và 100% học phí sinh viên phải đóng trong học kỳ xét, cấp học bổng.
- Học bổng được xét, cấp theo học kỳ, mỗi học kỳ xét 01 lần vào đầu học kỳ.
- Không xét, cấp cho sinh viên không đăng ký học tập tại thời điểm xét; sinh viên đang trong thời gian bị kỷ luật từ mức cảnh cáo trở lên; sinh viên đã được nhận học bổng KKHT hoặc học bổng tài trợ trong học kỳ xét; sinh viên diện chế độ chính sách được miễn, giảm học phí theo quy định của Nhà nước.
""",
    ),
    dict(
        pdf_name="QD_HOC_PHI_2025-2026.pdf",
        output_name="hoc_phi_2025_2026_verified.md",
        title="Quyết định mức học phí HUST năm học 2025-2026",
        source_url=f"{CTT_FILES}/DTDH_QDQC/Hocphi/2025-2026/QD%20HOC%20PHI%20-%202025-2026-final.pdf",
        document_type="tuition_decision",
        effective_period="Năm học 2025-2026",
        pages=range(1, 8),
        note=(
            "Bản trích xuất theo trang từ Quyết định 10232/QĐ-ĐHBK ngày 12/09/2025. "
            "Không dùng mức học phí này cho năm học khác nếu chưa có văn bản xác nhận."
        ),
    ),
    dict(
        pdf_name="QD_HOC_PHI_2026-2027_12006.pdf",
        output_name="hoc_phi_2026_2027_verified.md",
        title="Quyết định mức học phí HUST năm học 2026-2027",
        source_url=f"{CTT_FILES}/DTDH_QDQC/Hocphi/2026-2027/12006_Q%C4%90-%C4%90HBK.pdf",
        document_type="tuition_decision",
        effective_period="Năm học 2026-2027",
        pages=range(1, 8),
        page_fixes={
            3: ((
                r"(?<=1\) Các chương trình đào tạo chuẩn\n).*?tế \(IPE\)\(2\)",
                "\nMức học phí (nghìn đồng/TCHP) theo chương trình:\n"
                "- KT Cơ điện tử, KT điện tử-viễn thông, KT điều khiển-tự động hóa, Khoa học máy tính, "
                "Kỹ thuật máy tính: 700\n"
                "- Toán tin, Hệ thống thông tin quản lý, Kỹ thuật y sinh, KT cơ khí, KT cơ khí động lực, "
                "KT thực phẩm, KT sinh học, KT ôtô, KT điện, Tài chính – ngân hàng, Quản lý công nghiệp, "
                "Quản lý năng lượng, Quản trị kinh doanh, Kế toán, Ngôn ngữ Anh, Tiếng Trung KH&CN, "
                "Tiếng Hàn KH&CN: 680\n"
                "- KT hóa học, Hóa học, KT in, KT vật liệu, KT vật liệu Polyme và Compozit, KT vi điện tử "
                "và CN Nano, KT hàng không, Vật lý kỹ thuật, KT hạt nhân, KT nhiệt, Vật lý y khoa, Công "
                "nghệ dệt - may, Kỹ thuật dệt, KT môi trường, Quản lý tài nguyên và môi trường, Công nghệ "
                "giáo dục, Quản lý giáo dục, Tâm lý học CN&TC và các chương trình đào tạo chuẩn khác: 620\n"
                "\n2) Các chương trình đào tạo đặc biệt và chương trình ELITECH\n"
                "\nMức học phí (nghìn đồng/TCHP). Các học phần LLCT, GDTC, GDQP-AN(1), Tiếng Anh cơ bản, "
                "cơ sở của các chương trình dưới đây: 750. Các học phần khác:\n"
                "- Công nghệ thông tin: Việt-Nhật: 950\n"
                "- Chương trình tiên tiến Khoa học dữ liệu và Trí tuệ nhân tạo, Logistics và Quản lý "
                "chuỗi cung ứng: 1020\n"
                "- Chương trình tiên tiến Kỹ thuật điều khiển và tự động hoá, Global ICT: 900\n"
                "- Chương trình tiên tiến KT Cơ điện tử: 850\n"
                "- Các chương trình PFIEV và chương trình tiếng Anh chuyên nghiệp quốc tế (IPE)(2): 750",
            ),),
            4: (
                (
                    r"Chương trình\s+Các học phần LLCT.*?\(Các học phần \(1\) định mức 750\)",
                    "2) Các chương trình đào tạo đặc biệt và chương trình ELITECH (tiếp theo, nghìn đồng/TCHP):\n"
                    "- Các chương trình Đào tạo tài năng: 700 cho cả học phần LLCT, GDTC, GDQP-AN, "
                    "Tiếng Anh cơ bản, cơ sở và các học phần khác\n"
                    "- Chương trình tiên tiến Kế toán, Khoa học tính toán cho các hệ thống thông minh: 680 "
                    "cho cả học phần LLCT, GDTC, GDQP-AN, Tiếng Anh cơ bản, cơ sở và các học phần khác\n"
                    "- Công nghệ thông tin Việt-Pháp và các chương trình tiên tiến còn lại: 800 (các học "
                    "phần LLCT, GDTC, GDQP-AN(1) định mức 750)",
                ),
                (
                    r"(?<=3\) Các chương trình đào tạo hợp tác quốc tế\n).*?EM-VUW, EM-NU \(IEM\)[^\n]*",
                    "\nMức học phí (nghìn đồng/TCHP). Các học phần LLCT, GDTC, GDQP-AN*: 750. "
                    "Các học phần khác (trừ ngoại ngữ):\n"
                    "- ME-GU, ME-NUT, IT-LTU, IT-VUW: 1000\n"
                    "- ME-LUH, ET-LUH, IT-GINP: 950\n"
                    "- EM-VUW, EM-NU (IEM): 1020",
                ),
            ),
        },
        note=(
            "Bản trích xuất theo trang từ Quyết định 12006/QĐ-ĐHBK ngày 05/10/2026 phê duyệt "
            "mức học phí đại học chính quy, kỹ sư chuyên sâu, đào tạo thường xuyên và sau đại học "
            "năm học 2026-2027; có hiệu lực kể từ ngày ký. Đây là mức học phí áp dụng cho năm học "
            "2026-2027; mức năm 2025-2026 nằm ở Quyết định 10232/QĐ-ĐHBK."
        ),
    ),
    dict(
        pdf_name="QD_NGOAI_NGU_K71_10828.pdf",
        output_name="quy_dinh_ngoai_ngu_k71_verified.md",
        title="Quy định ngoại ngữ đối với sinh viên đại học chính quy từ K71",
        source_url=f"{CTT_FILES}/DTDH_QDQC/Hoctap/00_%20Quy%20%C4%91%E1%BB%8Bnh%20ngo%E1%BA%A1i%20ng%E1%BB%AF%20K71_final_%C4%91%C3%A3%20k%C3%BD.pdf",
        document_type="language_regulation",
        effective_period="Từ học kỳ 1 năm học 2026-2027, áp dụng cho K71 trở về sau",
        pages=range(1, 24),
        note=(
            "Bản trích xuất theo trang từ Quyết định 10828/QĐ-ĐHBK ngày 07/09/2026 về phân loại "
            "trình độ đầu vào, chương trình ngoại ngữ cơ bản và chuẩn ngoại ngữ yêu cầu. Áp dụng "
            "từ học kỳ 1 năm học 2026-2027 cho sinh viên K71 trở về sau; Quyết định 10728/QĐ-ĐHBK "
            "hết hiệu lực đối với K71 trở về sau. Bảng quy đổi chứng chỉ áp dụng cho mọi khóa với "
            "chứng chỉ cấp kể từ ngày quy định có hiệu lực; với K70 trở về trước, nếu mức quy đổi "
            "của cùng một chứng chỉ khác quy định cũ thì áp dụng mức cao hơn trong hai quy định. "
            "Các nội dung khác cho K70 tra Quyết định 10728/QĐ-ĐHBK."
        ),
    ),
    dict(
        pdf_name="QD_NGOAI_NGU_K70_10728.pdf",
        output_name="quy_dinh_ngoai_ngu_k70_verified.md",
        title="Quy định ngoại ngữ đối với sinh viên đại học chính quy từ K70",
        source_url=f"{CTT_FILES}/DTDH_QDQC/Hoctap/06_%20Quy%20%C4%91%E1%BB%8Bnh%20ngo%E1%BA%A1i%20ng%E1%BB%AF%20t%E1%BB%AB%20K70_ch%C3%ADnh%20quy_final.pdf",
        document_type="language_regulation",
        effective_period="Từ học kỳ 1 năm học 2025-2026, áp dụng cho K70",
        pages=range(1, 21),
        note=(
            "Bản trích xuất theo trang từ Quyết định 10728/QĐ-ĐHBK ngày 26/09/2025 về phân loại "
            "trình độ đầu vào, chương trình ngoại ngữ cơ bản và chuẩn ngoại ngữ yêu cầu. Áp dụng "
            "từ học kỳ 1 năm học 2025-2026; K69 trở về trước giữ quy định cũ trừ phần quy đổi "
            "tương đương. Từ K71, quy định này được thay bằng Quyết định 10828/QĐ-ĐHBK."
        ),
    ),
    dict(
        pdf_name="QD_REN_LUYEN_10911.pdf",
        output_name="quy_dinh_ren_luyen_2026_verified.md",
        title="Quy định đánh giá kết quả rèn luyện của sinh viên HUST năm 2026",
        source_url=CTSV_DRIVE.format("1WerKESynsFT2xEDXaMv4XvXI1EdylzAi"),
        document_type="conduct_regulation",
        effective_period="Từ ngày 08/09/2026",
        pages=range(1, 11),
        page_fixes={3: ((
            r"(?<=xếp loại như sau:\n).*?Dưới 50 điểm[^\n]*",
            "\n- Từ 90 đến 100 điểm: Xuất sắc\n- Từ 80 đến 89 điểm: Tốt\n- Từ 70 đến 79 điểm: Khá\n"
            "- Từ 50 đến 69 điểm: Trung bình\n- Dưới 50 điểm: Yếu",
        ),)},
        note=(
            "Bản trích xuất theo trang từ Quyết định 10911/QĐ-ĐHBK ngày 08/09/2026 ban hành Quy "
            "định đánh giá kết quả rèn luyện, gồm khung đánh giá điểm rèn luyện. Có hiệu lực kể "
            "từ ngày ký và thay thế các quy định về đánh giá rèn luyện trước đó. Nguồn: tệp do "
            "Ban Công tác sinh viên công bố."
        ),
    ),
    dict(
        pdf_name="QC_CONG_TAC_SV_2026_10370.pdf",
        output_name="quy_che_cong_tac_sinh_vien_2026_verified.md",
        title="Quy chế công tác sinh viên HUST năm 2026",
        source_url=CTSV_DRIVE.format("1wtSTDkVI5m_zaWTIWnv32FF521859gZu"),
        document_type="student_affairs_regulation",
        effective_period="Từ ngày 23/08/2026",
        pages=range(1, 25),
        note=(
            "Bản trích xuất theo trang từ Quyết định 10370/QĐ-ĐHBK ngày 23/08/2026 ban hành Quy "
            "chế công tác sinh viên (quyền và nghĩa vụ, khen thưởng, kỷ luật, hỗ trợ sinh viên). "
            "Thay thế Quyết định 2727/QĐ-ĐHBK ngày 13/03/2025. Nguồn: tệp do Ban Công tác sinh "
            "viên công bố."
        ),
    ),
    dict(
        pdf_name="QD_MIEN_GIAM_HP_10969.pdf",
        output_name="quy_dinh_mien_giam_hoc_phi_verified.md",
        title="Quy định miễn, giảm học phí và hỗ trợ chi phí học tập cho sinh viên HUST",
        source_url=CTSV_DRIVE.format("1NZx3Vbr632AyoRY-989ZKaFzabWprBrd"),
        document_type="tuition_support_regulation",
        effective_period="Từ năm học 2025-2026",
        pages=range(1, 9),
        note=(
            "Bản trích xuất các trang PDF 1-8 từ Quyết định 10969/QĐ-ĐHBK ngày 05/10/2025 ban "
            "hành Quy định miễn, giảm học phí, hỗ trợ chi phí học tập, hỗ trợ học tập. Áp dụng từ "
            "năm học 2025-2026; Quyết định 5776/QĐ-ĐHBK ngày 18/07/2023 hết hiệu lực. Các phụ lục "
            "mẫu đơn (trang PDF 10-19) không đưa vào; xem PDF gốc khi cần mẫu đơn."
        ),
    ),
    dict(
        pdf_name="QD_HB_TRAN_DAI_NGHIA_11865.pdf",
        output_name="quy_dinh_hoc_bong_tran_dai_nghia_verified.md",
        title="Quy định Học bổng Trần Đại Nghĩa, hỗ trợ khó khăn đột xuất và hỗ trợ lãi suất vay vốn",
        source_url=CTSV_DRIVE.format("1-8jXP7H6J4Rgya4MDknTEynVIr1Oar-A"),
        document_type="scholarship_regulation",
        effective_period="Từ học kỳ 1 năm học 2026-2027",
        pages=range(1, 9),
        note=(
            "Bản trích xuất các trang PDF 1-8 từ Quyết định 11865/QĐ-ĐHBK ngày 02/10/2026 về quản "
            "lý và xét, cấp Học bổng Trần Đại Nghĩa, hỗ trợ khó khăn rủi ro đột xuất và hỗ trợ lãi "
            "suất vay vốn ngân hàng; áp dụng cả cho học viên cao học và nghiên cứu sinh. Áp dụng từ "
            "học kỳ 1 năm học 2026-2027, thay thế Quyết định 10662/QĐ-ĐHBK ngày 30/08/2026. Các "
            "phụ lục mẫu đơn (trang PDF 9-16) không đưa vào."
        ),
    ),
    dict(
        pdf_name="QD_HB_TRAO_DOI_12044.pdf",
        output_name="quy_dinh_hoc_bong_trao_doi_verified.md",
        title="Quy định xét, cấp học bổng trao đổi nước ngoài cho sinh viên HUST",
        source_url=CTSV_DRIVE.format("1M8djpmN-J87lzfN-fzqJHU3MNBes2PRw"),
        document_type="scholarship_regulation",
        effective_period="Từ ngày 06/11/2025",
        pages=range(1, 8),
        note=(
            "Bản trích xuất các trang PDF 1-7 từ Quyết định 12044/QĐ-ĐHBK ngày 06/11/2025 ban "
            "hành Quy định xét, cấp học bổng trao đổi nước ngoài; thay thế Quyết định "
            "1995/QĐ-ĐHBK ngày 07/03/2024. Các phụ lục mẫu đơn, mẫu báo cáo (trang PDF 8-10) "
            "không đưa vào."
        ),
    ),
    dict(
        pdf_name="KH_NAM_HOC_2026-2027.pdf",
        output_name="ke_hoach_nam_hoc_2026_2027_verified.md",
        title="Khung kế hoạch năm học 2026-2027 của HUST",
        source_url=f"{CTT_FILES}/DTDH_Kehoach/2026-2027/01_1_%20K%E1%BA%BF%20ho%E1%BA%A1ch%20n%C4%83m%20h%E1%BB%8Dc%202026-2027_18062026_Ph%E1%BB%A5%20l%E1%BB%A5c.pdf",
        document_type="academic_calendar",
        effective_period="Năm học 2026-2027",
        pages=range(0),
        note=(
            "Bảng gốc là lưới tuần nhiều cột theo khóa, không trích được nguyên văn có nghĩa nên "
            "các mốc dưới đây được chép tay và đối chiếu với PDF gốc. Các mốc ghi \"dự kiến\" có "
            "thể được Ban Đào tạo điều chỉnh; PDF gốc và thông báo trên ctt.hust.edu.vn là căn cứ "
            "ưu tiên."
        ),
        curated_summary=ACADEMIC_CALENDAR_2026_2027,
        curated_page=1,
    ),
]


def main(only: set[str] | None = None) -> None:
    """Build every document, or only the output names given on the command line."""
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    selected = [spec for spec in DOCUMENTS if not only or spec["output_name"] in only]
    unknown = (only or set()) - {spec["output_name"] for spec in DOCUMENTS}
    if unknown:
        raise SystemExit(f"Unknown output names: {', '.join(sorted(unknown))}")
    for spec in selected:
        build_document(**spec)


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
