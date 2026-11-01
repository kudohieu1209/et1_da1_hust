"""Summarize the normalized ET1 curriculum and dependencies outside its catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECT_DIR = DATA_DIR.parent
DEFAULT_CURRICULUM = DATA_DIR / "processed" / "curricula" / "et1_2022.json"
DEFAULT_REPORT = DATA_DIR / "reports" / "et1_2022_conflicts.md"


def build_report(curriculum: dict[str, Any]) -> str:
    courses = {item["code"]: item for item in curriculum["courses"]}
    program = curriculum["program"]
    bachelor = next(path for path in curriculum["graduation_paths"] if path["id"] == "bachelor")
    module_choice = next(
        item for item in bachelor["components"] if item["type"] == "ONE_OF_GROUPS"
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
        "# Kiểm tra dữ liệu ET1 2022",
        "",
        "## Dữ liệu chuẩn hóa",
        "",
        f"- Chương trình: `{program['program_code']}` / `{program['program_id']}` / phiên bản `{program['curriculum_version']}`.",
        f"- Tổng tín chỉ tốt nghiệp hệ cử nhân: **{program['total_required_credits']} TC**.",
        f"- Mô-đun: chọn một trong **{len(module_choice['options'])}** mô-đun, tối thiểu **{module_choice['required_credits']} TC**.",
        "- Tiếng Anh, GDTC và GDQP là các nhóm 0 TC; không cộng vào tổng 126 TC.",
    ]
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
    args.output.write_text(report, encoding="utf-8", newline="\n")
    print(f"[OK] Đã ghi {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
