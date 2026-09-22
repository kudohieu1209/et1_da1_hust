"""Compare the authoritative CTT-derived ET1 dataset with draft project facts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECT_DIR = DATA_DIR.parent
DEFAULT_CURRICULUM = DATA_DIR / "processed" / "curricula" / "et1_2022.json"
DEFAULT_REPORT = DATA_DIR / "reports" / "et1_2022_conflicts.md"


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_DIR.resolve()).as_posix()


def _find_markdown_course_credits(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    facts: list[dict[str, Any]] = []

    # List entries such as: `ET3260` - Course name (3.0 TC)
    for match in re.finditer(
        r"`(?P<code>[A-Z]{2,4}\d{4}[A-Z]?)`[^\n]*?"
        r"(?P<credits>\d+(?:\.\d+)?)\s*TC",
        text,
    ):
        facts.append(
            {
                "code": match.group("code"),
                "credits": float(match.group("credits")),
                "line": _line_number(text, match.start()),
                "file": _relative(path),
            }
        )

    # Detail sections such as: ### ET2040 ... followed by **Số tín chỉ:** 2.0 TC
    for match in re.finditer(
        r"(?ms)^###\s+(?P<code>[A-Z]{2,4}\d{4}[A-Z]?)\b.*?"
        r"^\s*-\s*\*\*Số tín chỉ:\*\*\s*(?P<credits>\d+(?:\.\d+)?)\s*TC",
        text,
    ):
        facts.append(
            {
                "code": match.group("code"),
                "credits": float(match.group("credits")),
                "line": _line_number(text, match.start()),
                "file": _relative(path),
            }
        )
    return facts


def build_report(curriculum: dict[str, Any]) -> str:
    courses = {item["code"]: item for item in curriculum["courses"]}
    program = curriculum["program"]
    bachelor = next(path for path in curriculum["graduation_paths"] if path["id"] == "bachelor")
    module_choice = next(
        item for item in bachelor["components"] if item["type"] == "ONE_OF_GROUPS"
    )

    conflicts: list[dict[str, Any]] = []
    notes: list[str] = []
    documents = [
        DATA_DIR / "documents" / "chuong_trinh_dao_tao_et1.md",
        DATA_DIR / "documents" / "de_cuong_chi_tiet_mon_hoc_et1.md",
    ]

    for path in documents:
        if not path.exists():
            continue
        for fact in _find_markdown_course_credits(path):
            authoritative = courses.get(fact["code"])
            if authoritative and float(authoritative["credits"]) != fact["credits"]:
                conflicts.append(
                    {
                        "fact": f"Tín chỉ {fact['code']}",
                        "draft": f"{fact['credits']:g}",
                        "ctt": f"{authoritative['credits']:g}",
                        "location": f"{fact['file']}:{fact['line']}",
                    }
                )

    program_doc = DATA_DIR / "documents" / "chuong_trinh_dao_tao_et1.md"
    if program_doc.exists():
        text = program_doc.read_text(encoding="utf-8")
        total_match = re.search(r"Tổng khối lượng tích lũy:\s*\*\*(\d+) tín chỉ", text)
        if total_match and int(total_match.group(1)) != program["total_required_credits"]:
            conflicts.append(
                {
                    "fact": "Tổng tín chỉ tốt nghiệp",
                    "draft": total_match.group(1),
                    "ctt": str(program["total_required_credits"]),
                    "location": f"{_relative(program_doc)}:{_line_number(text, total_match.start())}",
                }
            )

        described_modules = len(re.findall(r"(?m)^###\s+3\.\d+\.\s+Mô-đun", text))
        ctt_modules = len(module_choice["options"])
        if described_modules and described_modules != ctt_modules:
            first_module = re.search(r"(?m)^###\s+3\.\d+\.\s+Mô-đun", text)
            conflicts.append(
                {
                    "fact": "Số mô-đun",
                    "draft": str(described_modules),
                    "ctt": str(ctt_modules),
                    "location": f"{_relative(program_doc)}:{_line_number(text, first_module.start())}",
                }
            )

    rules_file = PROJECT_DIR / "backend" / "app" / "core" / "hust_rules.py"
    if rules_file.exists():
        rules_text = rules_file.read_text(encoding="utf-8")
        hardcoded = re.search(r'"total_credits_min":\s*(\d+)', rules_text)
        if hardcoded:
            status = "khớp" if int(hardcoded.group(1)) == program["total_required_credits"] else "không khớp"
            notes.append(
                f"`{_relative(rules_file)}:{_line_number(rules_text, hardcoded.start())}` "
                f"đang hard-code {hardcoded.group(1)} TC ({status} ET1 2022), nhưng chưa gắn "
                "với program/version."
            )

    unresolved = sorted(
        {
            warning
            for warning in curriculum.get("build_warnings", [])
            if "nằm ngoài catalog" in warning
        }
    )
    # build_warnings contains parser warnings; validator-only unresolved warnings are recomputed here.
    for course in curriculum["courses"]:
        for alternative in course["registration_condition"]["any_of"]:
            for requirement in alternative["all_of"]:
                if requirement["course_code"] not in courses:
                    unresolved.append(
                        f"{course['code']} -> {requirement['course_code']} ({requirement['relation']})"
                    )
    unresolved = sorted(set(unresolved))

    lines = [
        "# Báo cáo kiểm kê dữ liệu ET1 2022",
        "",
        "> Nguồn chuẩn cho báo cáo này là bản xuất CTT của Chương trình 1654. "
        "Dữ liệu sinh viên không được sao chép sang dataset chuẩn hóa.",
        "",
        "## Kết luận đã xác minh",
        "",
        f"- Chương trình: `{program['program_code']}` / `{program['program_id']}` / phiên bản `{program['curriculum_version']}`.",
        f"- Tổng tín chỉ tốt nghiệp hệ cử nhân: **{program['total_required_credits']} TC**.",
        f"- Mô-đun: chọn một trong **{len(module_choice['options'])}** mô-đun, tối thiểu **{module_choice['required_credits']} TC**.",
        "- Tiếng Anh, GDTC và GDQP là các nhóm 0 TC; không cộng vào tổng 126 TC.",
        "",
        "## Mâu thuẫn với tài liệu nháp",
        "",
        "| Dữ kiện | Bản nháp | CTT ET1 2022 | Vị trí |",
        "|---|---:|---:|---|",
    ]
    if conflicts:
        for item in sorted(conflicts, key=lambda value: (value["location"], value["fact"])):
            lines.append(
                f"| {item['fact']} | {item['draft']} | {item['ctt']} | `{item['location']}` |"
            )
    else:
        lines.append("| Không phát hiện | – | – | – |")

    lines.extend(["", "## Nợ kỹ thuật", ""])
    lines.extend(f"- {note}" for note in notes)
    lines.append(
        "- Tài liệu Markdown nháp không có metadata program/version; không nên "
        "index vào RAG như nguồn chính thức."
    )
    lines.extend(["", "## Mã điều kiện nằm ngoài catalog ET1 2022", ""])
    lines.append(
        "Các mã sau có trong chuỗi điều kiện CTT nhưng không nằm trong 117 học phần "
        "của bản CTĐT này. Cần đối chiếu bảng mã tương đương/phiên bản, không được tự động xóa."
    )
    lines.append("")
    lines.extend(f"- `{item}`" for item in unresolved)
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curriculum", type=Path, default=DEFAULT_CURRICULUM)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    curriculum = json.loads(args.curriculum.read_text(encoding="utf-8"))
    report = build_report(curriculum)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"[OK] Đã ghi {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
