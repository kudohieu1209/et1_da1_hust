"""Validate a normalized curriculum dataset without third-party dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECT_DIR = DATA_DIR.parent
DEFAULT_INPUT = DATA_DIR / "processed" / "curricula" / "et1_2022.json"

VALID_RELATIONS = {"PREREQUISITE", "PRIOR", "COREQUISITE"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_curriculum(
    data: dict[str, Any], project_dir: Path | None = None
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = list(data.get("build_warnings", []))
    project_dir = Path(project_dir or PROJECT_DIR)

    if data.get("schema_version") != "1.0.0":
        errors.append("schema_version phải là 1.0.0")

    program = data.get("program", {})
    for key in ("program_id", "program_code", "curriculum_version", "total_required_credits"):
        if program.get(key) in (None, ""):
            errors.append(f"Thiếu program.{key}")

    groups = data.get("groups", [])
    group_by_id = {group.get("id"): group for group in groups}
    if len(group_by_id) != len(groups):
        errors.append("ID nhóm học phần bị trùng")

    courses = data.get("courses", [])
    course_by_code = {course.get("code"): course for course in courses}
    if len(course_by_code) != len(courses):
        errors.append("Mã học phần bị trùng trong catalog")

    for group in groups:
        group_id = group.get("id", "<unknown>")
        codes = group.get("course_codes", [])
        if len(codes) != len(set(codes)):
            errors.append(f"{group_id}: danh sách học phần bị trùng")
        missing = sorted(set(codes) - set(course_by_code))
        if missing:
            errors.append(f"{group_id}: học phần không có trong catalog: {missing}")
        if group.get("course_count_reported") != len(codes):
            errors.append(
                f"{group_id}: CTT báo {group.get('course_count_reported')} học phần "
                f"nhưng parser thu được {len(codes)}"
            )
        catalog_sum = sum(float(course_by_code[code]["credits"]) for code in codes)
        if abs(catalog_sum - float(group.get("catalog_credits", 0))) > 1e-9:
            errors.append(
                f"{group_id}: tổng tín chỉ học phần {catalog_sum:g} không khớp "
                f"Tổng TC trên CTT {group.get('catalog_credits')}"
            )

    for course in courses:
        code = course.get("code", "<unknown>")
        for group_id in course.get("group_ids", []):
            if group_id not in group_by_id:
                errors.append(f"{code}: tham chiếu nhóm không tồn tại {group_id}")
        condition = course.get("registration_condition", {})
        for alternative in condition.get("any_of", []):
            if not alternative.get("all_of"):
                errors.append(f"{code}: nhánh điều kiện AND rỗng")
            for requirement in alternative.get("all_of", []):
                relation = requirement.get("relation")
                if relation not in VALID_RELATIONS:
                    errors.append(f"{code}: loại quan hệ không hợp lệ {relation!r}")
                required_code = requirement.get("course_code")
                if required_code not in course_by_code:
                    warnings.append(
                        f"{code}: học phần điều kiện {required_code} nằm ngoài catalog "
                        f"của chương trình này"
                    )

    paths = data.get("graduation_paths", [])
    if not paths:
        errors.append("Không có graduation_paths")
    for path in paths:
        computed_total = 0.0
        for component in path.get("components", []):
            required = float(component.get("required_credits", 0))
            computed_total += required
            if component.get("type") == "GROUP_CREDITS":
                group_id = component.get("group_id")
                group = group_by_id.get(group_id)
                if not group:
                    errors.append(f"{path.get('id')}: thiếu nhóm {group_id}")
                elif float(group.get("catalog_credits", 0)) < required:
                    errors.append(
                        f"{path.get('id')}: {group_id} chỉ có {group.get('catalog_credits')} TC, "
                        f"thấp hơn mức yêu cầu {required:g}"
                    )
            elif component.get("type") == "ONE_OF_GROUPS":
                options = component.get("options", [])
                if not options:
                    errors.append(f"{path.get('id')}: ONE_OF_GROUPS không có lựa chọn")
                for option in options:
                    group = group_by_id.get(option.get("group_id"))
                    if not group:
                        errors.append(
                            f"{path.get('id')}: thiếu nhóm mô-đun {option.get('group_id')}"
                        )
                    elif float(group.get("catalog_credits", 0)) < required:
                        errors.append(
                            f"{path.get('id')}: mô-đun {group['id']} không đủ {required:g} TC"
                        )
            else:
                errors.append(
                    f"{path.get('id')}: component type không hợp lệ {component.get('type')!r}"
                )
        declared_total = float(path.get("total_required_credits", 0))
        if abs(computed_total - declared_total) > 1e-9:
            errors.append(
                f"{path.get('id')}: tổng tính lại {computed_total:g} != "
                f"tổng khai báo {declared_total:g}"
            )

    bachelor = next((path for path in paths if path.get("id") == "bachelor"), None)
    if bachelor and float(program.get("total_required_credits", 0)) != float(
        bachelor.get("total_required_credits", 0)
    ):
        errors.append("Tổng tín chỉ program không khớp graduation path bachelor")

    for source in data.get("sources", []):
        source_file = source.get("file")
        expected_hash = source.get("sha256")
        if not source_file or not expected_hash:
            errors.append(f"Nguồn {source.get('id', '<unknown>')} thiếu file hoặc sha256")
            continue
        path = project_dir / source_file
        if not path.exists():
            warnings.append(f"Không thể kiểm tra hash vì thiếu file nguồn: {source_file}")
        elif _sha256(path) != expected_hash:
            errors.append(f"File nguồn đã thay đổi so với hash: {source_file}")

    return errors, sorted(set(warnings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    errors, warnings = validate_curriculum(data)
    for warning in warnings:
        print(f"[WARN] {warning}")
    for error in errors:
        print(f"[ERROR] {error}")
    if errors:
        print(f"[FAIL] {len(errors)} lỗi, {len(warnings)} cảnh báo")
        return 1
    print(
        f"[OK] {data['program']['program_code']} "
        f"{data['program']['curriculum_version']}: "
        f"{data['program']['total_required_credits']} TC; "
        f"{len(data['groups'])} nhóm; {len(data['courses'])} học phần; "
        f"{len(warnings)} cảnh báo"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
