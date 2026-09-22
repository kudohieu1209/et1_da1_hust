"""Build a versioned, provenance-aware curriculum dataset from a CTT HTML export.

The generated dataset deliberately excludes the student's identity and transcript.  A
student CTT export is used only as a snapshot of the curriculum structure visible to
that cohort.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECT_DIR = DATA_DIR.parent

DEFAULT_HTML = DATA_DIR / "raw" / "et1_curiculum.html"
DEFAULT_CONDITIONS = DATA_DIR / "raw" / "ctt_et_conditions.json"
DEFAULT_OUTPUT = DATA_DIR / "processed" / "curricula" / "et1_2022.json"

ABBREVIATION_TO_GROUP = {
    "ĐAKLTN": "7",
    "LLCT": "210",
    "TKHCB": "250",
    "CSCLN": "300",
    "KTBT": "320",
    "TT": "360",
    "MOD1": "400",
    "MOD2": "401",
    "MOD3": "402",
    "MOD4": "403",
    "MOD5": "404",
    "MOD6": "405",
    "DANC": "700",
}

RELATION_MAP = {
    "PREREQUISITE": "PREREQUISITE",
    "PRIOR": "PRIOR",
    "COREQUISITE": "COREQUISITE",
}


def _clean_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", "", value))
    return " ".join(value.replace("\xa0", " ").split())


def _number(value: str) -> float:
    value = value.strip()
    return float(value) if value else 0.0


def _compact_number(value: float) -> int | float:
    return int(value) if value.is_integer() else value


def _project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_DIR.resolve()).as_posix()
    except ValueError:
        return path.name


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_condition(raw_condition: str) -> dict[str, Any]:
    """Parse the CTT syntax: slash=OR, comma=AND, !=passed, ==corequisite."""
    raw_condition = html.unescape(raw_condition or "").replace("\xa0", " ").strip()
    if not raw_condition:
        return {"raw": "", "any_of": []}

    alternatives: list[dict[str, Any]] = []
    for raw_branch in raw_condition.split("/"):
        branch = raw_branch.strip()
        if not branch:
            continue

        group_relation: str | None = None
        if branch.endswith("!") and "(" in branch:
            group_relation = "PREREQUISITE"
            branch = branch[:-1]
        elif branch.endswith("=") and "(" in branch:
            group_relation = "COREQUISITE"
            branch = branch[:-1]

        requirements = []
        for raw_item in branch.replace("(", "").replace(")", "").split(","):
            item = raw_item.strip()
            if not item:
                continue
            relation = group_relation or "PRIOR"
            if item.endswith("!"):
                relation, item = "PREREQUISITE", item[:-1]
            elif item.endswith("="):
                relation, item = "COREQUISITE", item[:-1]
            requirements.append(
                {"course_code": item.strip(), "relation": RELATION_MAP[relation]}
            )
        if requirements:
            alternatives.append({"all_of": requirements})

    return {"raw": raw_condition, "any_of": alternatives}


def _parse_program(html_text: str, program_code: str) -> dict[str, Any]:
    clean = html.unescape(html_text).replace("\xa0", " ")
    match = re.search(
        r"Chương trình\s+(?P<id>\d+)\s*-\s*(?P<name>.*?)\s+"
        r"(?P<version>20\d{2})\s+cho sinh viên\s+\d+",
        clean,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise ValueError("Không tìm thấy tiêu đề chương trình trong HTML CTT")
    return {
        "program_id": match.group("id"),
        "program_code": program_code.upper(),
        "name": " ".join(match.group("name").split()),
        "curriculum_version": match.group("version"),
        "degree_level": "BACHELOR",
    }


def _parse_graduation_paths(html_text: str) -> list[dict[str, Any]]:
    label = re.search(
        r'id="[^"]*RequireGraduatePanel_lbCondiGraduate"[^>]*>(.*?)</span>',
        html_text,
        re.DOTALL,
    )
    if not label:
        raise ValueError("Không tìm thấy công thức điều kiện tốt nghiệp")

    content = html.unescape(label.group(1))
    entries = re.findall(r"<strong>(.*?)</strong>\s*:\s*(.*?)(?:<br\s*/?>|$)", content, re.DOTALL)
    paths = []
    for index, (raw_name, raw_expression) in enumerate(entries):
        name = _clean_text(raw_name)
        expression = _clean_text(raw_expression).removesuffix("<0.").strip()

        module_options = [
            {"group_id": f"group_{ABBREVIATION_TO_GROUP[key]}", "required_credits": int(value)}
            for key, value in re.findall(r"(MOD[1-6]):\s*(\d+(?:\.\d+)?)", expression)
        ]
        without_modules = re.sub(r"\([^)]*MOD1[^)]*\)", "", expression)
        scalar_parts = re.findall(
            r"(LLCT|TKHCB|CSCLN|KTBT|TT|ĐAKLTN|DANC):\s*(\d+(?:\.\d+)?)",
            without_modules,
        )

        components: list[dict[str, Any]] = [
            {
                "type": "GROUP_CREDITS",
                "group_id": f"group_{ABBREVIATION_TO_GROUP[key]}",
                "required_credits": _compact_number(float(value)),
            }
            for key, value in scalar_parts
        ]
        if module_options:
            required_values = {option["required_credits"] for option in module_options}
            if len(required_values) != 1:
                raise ValueError(f"Các mô-đun có ngưỡng khác nhau trong công thức: {expression}")
            components.insert(
                4,
                {
                    "type": "ONE_OF_GROUPS",
                    "required_credits": next(iter(required_values)),
                    "options": module_options,
                },
            )

        total = sum(float(item["required_credits"]) for item in components)
        path_id = "bachelor" if "CN -THS" not in name else "integrated_bachelor_master"
        paths.append(
            {
                "id": path_id,
                "name": name,
                "raw_expression": expression,
                "components": components,
                "total_required_credits": _compact_number(total),
                "source_order": index,
            }
        )
    return paths


def _parse_groups_and_courses(html_text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    rows = re.findall(r"<tr\b([^>]*)>(.*?)</tr>", html_text, re.DOTALL | re.IGNORECASE)
    groups: dict[str, dict[str, Any]] = {}
    catalog: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    pending_group_code: str | None = None
    current_group_code: str | None = None

    for row_attributes, row in rows:
        row_text = _clean_text(row)
        group_code_match = re.search(
            r"Mã loại HP:\s*(\d+)\s*\(Count=(\d+),\s*Tổng TC:\s*([\d.]*)",
            row_text,
        )
        if group_code_match:
            pending_group_code = group_code_match.group(1)
            groups[pending_group_code] = {
                "id": f"group_{pending_group_code}",
                "source_group_code": pending_group_code,
                "name": "",
                "course_count_reported": int(group_code_match.group(2)),
                "catalog_credits": _compact_number(_number(group_code_match.group(3))),
                "course_codes": [],
            }
            continue

        group_name_match = re.search(
            r"Loại HP:\s*(.*?)\s*\(Count=(\d+),\s*Tổng TC:\s*([\d.]*)",
            row_text,
        )
        if group_name_match and pending_group_code:
            group = groups[pending_group_code]
            group["name"] = group_name_match.group(1).strip()
            current_group_code = pending_group_code
            pending_group_code = None
            continue

        if "dxgvDataRow" not in row_attributes or not current_group_code:
            continue

        tds = re.findall(r"<td([^>]*)>(.*?)</td>", row, re.DOTALL | re.IGNORECASE)
        if len(tds) < 13:
            continue
        cells = [_clean_text(cell_html) for _, cell_html in tds]
        code = cells[2].upper()
        if not re.fullmatch(r"[A-Z]{2,4}\d{4}[A-Z]?", code):
            continue

        credits = _number(cells[6])
        semester = int(cells[4]) if cells[4].isdigit() else None
        checkbox_html = tds[5][1]
        is_compulsory = "dxWeb_edtCheckBoxChecked" in checkbox_html
        group_id = f"group_{current_group_code}"
        group = groups[current_group_code]
        if code not in group["course_codes"]:
            group["course_codes"].append(code)

        candidate = {
            "code": code,
            "name": cells[3],
            "credits": _compact_number(credits),
            "suggested_semester": semester,
            "is_compulsory": is_compulsory,
            "category": cells[9],
            "department": cells[12],
            "group_ids": [group_id],
        }
        if code not in catalog:
            catalog[code] = candidate
        else:
            existing = catalog[code]
            if group_id not in existing["group_ids"]:
                existing["group_ids"].append(group_id)
            for field in ("name", "credits"):
                if existing[field] != candidate[field]:
                    warnings.append(
                        f"{code}: {field} không nhất quán giữa các nhóm "
                        f"({existing[field]!r} != {candidate[field]!r})"
                    )

    return list(groups.values()), list(catalog.values()), warnings


def build_curriculum(
    html_path: Path = DEFAULT_HTML,
    conditions_path: Path = DEFAULT_CONDITIONS,
    program_code: str = "ET1",
) -> dict[str, Any]:
    html_path = Path(html_path)
    conditions_path = Path(conditions_path)
    html_text = html_path.read_text(encoding="utf-8", errors="ignore")

    program = _parse_program(html_text, program_code)
    groups, courses, parse_warnings = _parse_groups_and_courses(html_text)
    paths = _parse_graduation_paths(html_text)
    bachelor_path = next(path for path in paths if path["id"] == "bachelor")
    program["total_required_credits"] = bachelor_path["total_required_credits"]

    conditions = json.loads(conditions_path.read_text(encoding="utf-8"))
    condition_map = {item["code"].upper(): item.get("condition", "") for item in conditions}
    for course in courses:
        course["registration_condition"] = parse_condition(condition_map.get(course["code"], ""))

    used_group_ids = {
        component.get("group_id")
        for path in paths
        for component in path["components"]
        if component["type"] == "GROUP_CREDITS"
    }
    used_group_ids.update(
        option["group_id"]
        for path in paths
        for component in path["components"]
        if component["type"] == "ONE_OF_GROUPS"
        for option in component["options"]
    )
    for group in groups:
        group["counts_toward_degree_credits"] = group["id"] in used_group_ids

    stat = html_path.stat()
    source = {
        "id": "ctt_et1_2022_snapshot",
        "kind": "CTT_CURRICULUM_HTML_EXPORT",
        "file": _project_relative(html_path),
        "sha256": _sha256(html_path),
        "file_modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "authority": "CTT - Đại học Bách khoa Hà Nội",
        "contains_personal_data": True,
        "personal_data_included_in_output": False,
    }
    condition_source = {
        "id": "ctt_course_conditions_snapshot",
        "kind": "CTT_COURSE_CONDITIONS_JSON_EXPORT",
        "file": _project_relative(conditions_path),
        "sha256": _sha256(conditions_path),
        "file_modified_at": datetime.fromtimestamp(
            conditions_path.stat().st_mtime, timezone.utc
        ).isoformat(),
        "authority": "CTT - Đại học Bách khoa Hà Nội",
        "contains_personal_data": False,
        "personal_data_included_in_output": False,
    }

    return {
        "schema_version": "1.0.0",
        "program": program,
        "sources": [source, condition_source],
        "graduation_paths": paths,
        "groups": groups,
        "courses": courses,
        "non_credit_group_ids": [
            group["id"]
            for group in groups
            if float(group["catalog_credits"]) == 0
            and not group["counts_toward_degree_credits"]
        ],
        "build_warnings": parse_warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--conditions", type=Path, default=DEFAULT_CONDITIONS)
    parser.add_argument("--program-code", default="ET1")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    data = build_curriculum(args.html, args.conditions, args.program_code)

    # Import here so this module remains usable independently in tests.
    from validate_curriculum import validate_curriculum

    errors, warnings = validate_curriculum(data, project_dir=PROJECT_DIR)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"[OK] {data['program']['program_code']} {data['program']['curriculum_version']}: "
        f"{data['program']['total_required_credits']} TC, "
        f"{len(data['groups'])} nhóm, {len(data['courses'])} học phần"
    )
    print(f"[OK] Đã ghi {args.output}")
    for warning in warnings:
        print(f"[WARN] {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
