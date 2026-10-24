"""Generate a trusted RAG document from a normalized curriculum dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
DEFAULT_INPUT = DATA_DIR / "processed" / "curricula" / "et1_2022.json"
DEFAULT_OUTPUT = DATA_DIR / "documents" / "ctt_et1_2022_verified.md"


def render_curriculum_document(data: dict[str, Any]) -> str:
    program = data["program"]
    groups = {group["id"]: group for group in data["groups"]}
    courses = {course["code"]: course for course in data["courses"]}
    bachelor = next(path for path in data["graduation_paths"] if path["id"] == "bachelor")
    lines = [
        "---",
        "rag_status: VERIFIED",
        "document_type: curriculum",
        f"effective_period: CTĐT {program['program_code']} {program['curriculum_version']}",
        "---",
        "",
        f"# CTĐT {program['program_code']}–{program['curriculum_version']} đã chuẩn hóa",
        "",
        "> Trạng thái: VERIFIED_DATASET. Tài liệu này được sinh tự động từ các snapshot nguồn đã khai báo; "
        "không phải bản mô tả do mô hình ngôn ngữ tự soạn.",
        "",
        "## Nhận dạng chương trình",
        "",
        f"- Mã chương trình CTT: {program['program_id']}",
        f"- Mã ngành: {program['program_code']}",
        f"- Tên: {program['name']}",
        f"- Phiên bản: {program['curriculum_version']}",
        f"- Tổng tín chỉ Cử nhân: {bachelor['total_required_credits']}",
        f"- Công thức gốc: `{bachelor['raw_expression']}`",
        "- Ngoại ngữ, Giáo dục thể chất và Giáo dục quốc phòng được theo dõi "
        "ngoài tổng tín chỉ tốt nghiệp của snapshot này; không tự cộng thêm vào tổng yêu cầu.",
        "",
        "## Các thành phần tốt nghiệp",
        "",
    ]
    for component in bachelor["components"]:
        if component["type"] == "GROUP_CREDITS":
            group = groups[component["group_id"]]
            lines.append(
                f"- {group['name']}: yêu cầu {component['required_credits']} TC "
                f"(danh mục {group['catalog_credits']} TC)."
            )
            continue

        lines.append(
            f"- Chọn 1 trong {len(component['options'])} mô-đun, "
            f"mỗi mô-đun yêu cầu tối thiểu {component['required_credits']} TC:"
        )
        for index, option in enumerate(component["options"], 1):
            group = groups[option["group_id"]]
            course_text = ", ".join(
                f"{code} ({courses[code]['name']}, {courses[code]['credits']} TC)"
                for code in group["course_codes"]
            )
            lines.append(
                f"  - Mô-đun {index}: danh mục {group['catalog_credits']} TC; {course_text}."
            )

    lines.extend(["", "## Nguồn và truy vết", ""])
    for source in data["sources"]:
        lines.append(
            f"- {source['authority']} — `{source['file']}` — SHA-256 `{source['sha256']}`."
        )
    lines.extend([
        "",
        "Dữ liệu danh tính và bảng điểm sinh viên trong HTML nguồn không được sao chép vào tài liệu này.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_curriculum_document(data), encoding="utf-8")
    print(f"[OK] Đã sinh tài liệu RAG đã kiểm chứng: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
