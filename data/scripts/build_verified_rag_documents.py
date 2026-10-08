#!/usr/bin/env python3
"""Build the trusted Markdown corpus from official HUST PDF sources.

The generated files keep page boundaries so the RAG layer can cite the
official document and page instead of relying on hand-written summaries.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_DIR / "data" / "raw"
DOCUMENTS_DIR = PROJECT_DIR / "data" / "documents"


def extract_page(pdf_path: Path, page_number: int) -> str:
    result = subprocess.run(
        [
            "pdftotext",
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
        text=True,
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
    if curated_summary:
        front_matter.extend(["## Thông tin tra cứu chính", "", curated_summary.strip(), ""])
    sections = []
    for page_number in pages:
        page_text = extract_page(pdf_path, page_number)
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


def main() -> None:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    build_document(
        pdf_name="QCDT_2025_5445_QD-DHBK.pdf",
        output_name="quy_che_dao_tao_2025_verified.md",
        title="Quy chế đào tạo Đại học Bách khoa Hà Nội năm 2025",
        source_url="https://ctt.hust.edu.vn/Upload/Nguy%E1%BB%85n%20Qu%E1%BB%91c%20%C4%90%E1%BA%A1t/files/DTDH_QDQC/Hoctap/QCDT_2025_5445_QD-DHBK.pdf",
        document_type="academic_regulation",
        effective_period="Từ năm học 2025-2026",
        pages=range(1, 35),
        note=(
            "Bản trích xuất nguyên văn theo trang từ Quyết định 5445/QĐ-ĐHBK "
            "ngày 28/05/2025. Khi có khác biệt hiển thị, PDF gốc là căn cứ ưu tiên."
        ),
    )
    build_document(
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
Theo trang PDF 16 (trang in 30) về Học bổng khuyến khích học tập:

### Học bổng loại xuất sắc (Loại A)

- GPA từ 3,6 và điểm rèn luyện học kỳ từ 90; mức học bổng bằng 1,5 lần mức loại C.
- Loại B (giỏi): GPA từ 3,2 và điểm rèn luyện học kỳ từ 80; mức học bổng bằng 1,2 lần mức loại C.
- Loại C (khá): GPA từ 2,5 và điểm rèn luyện học kỳ từ 65; mức học bổng bằng tổng học phí của các học phần có tính điểm GPA của học kỳ chính liền trước.

Không xét cấp trong các trường hợp được liệt kê trên cùng trang: bị kỷ luật từ khiển trách; không đạt ngưỡng đăng ký tín chỉ; học quá thời gian chuẩn; hoặc thuộc chương trình đối tác nước ngoài cấp một văn bằng duy nhất. Dòng ngưỡng 15 tín chỉ trong bản gốc in "ít nhất hơn 15", có dấu hiệu lỗi biên tập; hệ thống không tự sửa nghĩa và khuyến nghị xác nhận với Ban Công tác sinh viên.
""",
    )
    build_document(
        pdf_name="QD_HOC_PHI_2025-2026.pdf",
        output_name="hoc_phi_2025_2026_verified.md",
        title="Quyết định mức học phí HUST năm học 2025-2026",
        source_url="https://ctt.hust.edu.vn/Upload/Nguy%E1%BB%85n%20Qu%E1%BB%91c%20%C4%90%E1%BA%A1t/files/DTDH_QDQC/Hocphi/2025-2026/QD%20HOC%20PHI%20-%202025-2026-final.pdf",
        document_type="tuition_decision",
        effective_period="Năm học 2025-2026",
        pages=range(1, 8),
        note=(
            "Bản trích xuất theo trang từ Quyết định 10232/QĐ-ĐHBK ngày 12/09/2025. "
            "Không dùng mức học phí này cho năm học khác nếu chưa có văn bản xác nhận."
        ),
    )


if __name__ == "__main__":
    main()
