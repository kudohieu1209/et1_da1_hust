#!/usr/bin/env python3
"""Promote one reviewed public curriculum candidate to a versioned dataset.

The candidate builder is intentionally review-only.  This script is the
explicit, reproducible approval step: it accepts a candidate only when all
automated checks pass, copies only fields allowed by the normalized curriculum
schema, and records the source hashes in the resulting dataset.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
DEFAULT_CANDIDATES = DATA_DIR / "raw" / "hust_curriculum_candidates.json"
DEFAULT_OUTPUT = DATA_DIR / "processed" / "curricula" / "et1_2023.json"
DEFAULT_APPROVALS = DATA_DIR / "processed" / "curriculum_approvals.json"
PROJECT_DIR = DATA_DIR.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from validate_curriculum import validate_curriculum  # noqa: E402


PROGRAM_IDS = {"ET1": "1654"}


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _compact(value: float) -> int | float:
    return int(value) if value.is_integer() else value


def _source(source: dict[str, Any]) -> dict[str, Any]:
    """Keep only the source fields accepted by curriculum.schema.json."""

    return {
        "id": str(source.get("id", "")),
        "kind": str(source.get("kind", "")),
        "file": str(source.get("file", "")),
        "sha256": str(source.get("sha256", "")),
        "authority": str(source.get("authority", "")),
        "contains_personal_data": bool(source.get("contains_personal_data", False)),
        "personal_data_included_in_output": bool(
            source.get("personal_data_included_in_output", False)
        ),
        **(
            {"file_modified_at": str(source["file_modified_at"])}
            if source.get("file_modified_at")
            else {}
        ),
    }


def _approval_map(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(item.get("candidate_id", "")).upper(): item
        for item in payload.get("approvals", [])
        if item.get("candidate_id")
    }


def _mandatory_group_ids(groups: list[dict[str, Any]]) -> set[str]:
    """Infer globally compulsory blocks from the published minimums.

    Module groups are alternatives, so their rows must not become globally
    compulsory.  A block whose required minimum equals its full catalogue is
    safe to expose as compulsory.  ET3270 is the common practical component
    of the public ET1-2023 graduation block and is kept as an explicit
    compulsory course; the page does not expose a course-level OR operator for
    the ET4900/ET4920 choice.
    """

    result = set()
    for group in groups:
        if not group.get("counts_toward_degree_credits"):
            continue
        if group.get("kind") == "module":
            continue
        required = group.get("required_credits")
        catalog = group.get("catalog_credits")
        if required is not None and catalog is not None and _number(required) == _number(catalog):
            result.add(str(group["id"]))
    return result


def _normalise(candidate: dict[str, Any], *, program_id: str) -> dict[str, Any]:
    groups_raw = list(candidate.get("groups", []))
    groups = [
        {
            "id": str(group["id"]),
            "source_group_code": str(group.get("source_group_code", "")),
            "name": str(group.get("name", "")),
            "course_count_reported": int(group.get("course_count_reported") or 0),
            "catalog_credits": _compact(_number(group.get("catalog_credits"))),
            "course_codes": [str(code).upper() for code in group.get("course_codes", [])],
            "counts_toward_degree_credits": bool(
                group.get("counts_toward_degree_credits", False)
            ),
        }
        for group in groups_raw
    ]
    group_by_id = {group["id"]: group for group in groups}
    mandatory_ids = _mandatory_group_ids(groups_raw)

    courses = []
    for course in candidate.get("courses", []):
        code = str(course.get("code", "")).upper()
        group_ids = [str(group_id) for group_id in course.get("group_ids", [])]
        ctt_credits = course.get("ctt_credits")
        credits = course.get("credits")
        if credits is None:
            credits = ctt_credits if ctt_credits is not None else 0
        group_names = [group_by_id[group_id]["name"] for group_id in group_ids if group_id in group_by_id]
        category = group_names[0] if group_names else ""
        is_compulsory = bool(set(group_ids) & mandatory_ids) or code == "ET3270"
        courses.append(
            {
                "code": code,
                # Prefer the CTT catalogue name when available; the public
                # page has a few visibly truncated labels (for example ET4230).
                "name": str(course.get("ctt_name") or course.get("name") or code),
                "credits": _compact(_number(credits)),
                "suggested_semester": course.get("suggested_semester"),
                "is_compulsory": is_compulsory,
                "category": category,
                "department": str(course.get("ctt_department", "")),
                "group_ids": group_ids,
                "registration_condition": dict(
                    course.get("registration_condition") or {"raw": "", "any_of": []}
                ),
            }
        )

    modules = [
        group
        for group in groups_raw
        if group.get("kind") == "module"
    ]
    if not modules:
        raise ValueError("Candidate không có mô-đun để tạo công thức tốt nghiệp")
    thresholds = {_number(group.get("required_credits")) for group in modules}
    if len(thresholds) != 1 or next(iter(thresholds)) <= 0:
        raise ValueError("Ngưỡng tín chỉ mô-đun không nhất quán")
    module_required = next(iter(thresholds))

    components = []
    for group in groups_raw:
        if not group.get("counts_toward_degree_credits") or group.get("kind") == "module":
            continue
        required = group.get("required_credits")
        if required is None:
            raise ValueError(f"Thiếu ngưỡng tín chỉ bắt buộc cho {group.get('id')}")
        components.append(
            {
                "type": "GROUP_CREDITS",
                "group_id": str(group["id"]),
                "required_credits": _compact(_number(required)),
            }
        )
    components.append(
        {
            "type": "ONE_OF_GROUPS",
            "required_credits": _compact(module_required),
            "options": [
                {
                    "group_id": str(group["id"]),
                    "required_credits": _compact(module_required),
                }
                for group in modules
            ],
        }
    )
    total = sum(
        _number(component.get("required_credits")) for component in components
    )
    published_total = _number(candidate.get("total_credits_published"))
    if total != published_total:
        raise ValueError(f"Công thức chuẩn hóa {total:g} TC không khớp trang công bố {published_total:g} TC")

    source_items = candidate.get("sources", [])
    if not source_items:
        raise ValueError("Candidate thiếu nguồn truy vết")
    program_code = str(candidate.get("admission_code", "")).upper()
    now = datetime.now(timezone.utc).isoformat()
    expression = "+ ".join(
        f"{group_by_id[component['group_id']]['name']}: {component['required_credits']}"
        for component in components
        if component["type"] == "GROUP_CREDITS"
    )
    expression += " + (một trong " + ", ".join(
        group_by_id[option["group_id"]]["name"] + f": {option['required_credits']}"
        for option in components[-1]["options"]
    ) + ")"

    return {
        "schema_version": "1.0.0",
        "program": {
            "program_id": program_id,
            "program_code": program_code,
            "name": "Kỹ thuật Điện tử - Viễn thông",
            "curriculum_version": str(candidate.get("curriculum_version")),
            "degree_level": "BACHELOR",
            "total_required_credits": _compact(total),
        },
        "sources": [_source(item) for item in source_items],
        "graduation_paths": [
            {
                "id": "bachelor",
                "name": "Kỹ thuật Điện tử - Viễn thông 2023 (Cử nhân)",
                "raw_expression": expression,
                "components": components,
                "total_required_credits": _compact(total),
                "source_order": 0,
            }
        ],
        "groups": groups,
        "courses": courses,
        "non_credit_group_ids": [
            group["id"]
            for group in groups
            if not group["counts_toward_degree_credits"]
        ],
        "build_warnings": [
            "CTĐT ET1-2023 được chuẩn hóa từ trang chương trình công khai và snapshot điều kiện CTT; nguồn công khai không cung cấp một chuỗi công thức tốt nghiệp riêng nên công thức được suy ra từ ngưỡng từng khối.",
            "Khối Thực tập & tốt nghiệp công bố tối thiểu 8 TC cho ET3270/ET4900/ET4920; dataset giữ ngưỡng 8 TC và không tự áp đặt lựa chọn khóa học ngoài dữ liệu nguồn.",
            f"Sinh lúc UTC: {now}.",
        ],
    }


def promote(
    candidate_path: Path = DEFAULT_CANDIDATES,
    output_path: Path = DEFAULT_OUTPUT,
    approvals_path: Path = DEFAULT_APPROVALS,
    candidate_id: str = "ET1-2023",
    program_id: str = "1654",
) -> dict[str, Any]:
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    normalized_id = candidate_id.upper()
    candidate = next(
        (item for item in payload.get("records", []) if str(item.get("candidate_id", "")).upper() == normalized_id),
        None,
    )
    if candidate is None:
        raise ValueError(f"Không tìm thấy candidate {candidate_id}")
    quality = candidate.get("quality", {})
    if not quality.get("automatic_checks_passed"):
        raise ValueError(
            "Candidate chưa vượt qua kiểm tra tự động: "
            + ", ".join(quality.get("review_reasons", []))
        )
    approval = _approval_map(approvals_path).get(normalized_id)
    if not approval or approval.get("status") != "approved":
        raise ValueError(
            f"Candidate {candidate_id} chưa có phê duyệt rõ ràng trong {approvals_path}"
        )
    data = _normalise(candidate, program_id=program_id)
    errors, _warnings = validate_curriculum(data, project_dir=PROJECT_DIR)
    if errors:
        raise ValueError("Dataset sau chuẩn hóa không hợp lệ: " + "; ".join(errors))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", default="ET1-2023")
    parser.add_argument("--program-id", default=PROGRAM_IDS["ET1"])
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--approvals", type=Path, default=DEFAULT_APPROVALS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    data = promote(
        args.candidates,
        args.output,
        args.approvals,
        args.candidate,
        args.program_id,
    )
    print(
        f"[OK] Đã bật {data['program']['program_code']}-{data['program']['curriculum_version']}: "
        f"{data['program']['total_required_credits']} TC, "
        f"{len(data['courses'])} học phần, {len(data['groups'])} nhóm"
    )
    print(f"[OK] Dataset: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
