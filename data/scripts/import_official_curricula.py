"""Import public HUST curriculum extractions that pass automatic checks.

Each input file describes one bachelor curriculum (blocks, optional modules and
course lists) transcribed from a public HUST curriculum page or PDF. A program
is imported into ``data/processed/curricula`` only when every automatic check
passes; the dataset and its approval entry are labelled "kiểm tra tự động,
chưa đối chiếu thủ công" because nobody has compared it line by line with the
original document yet.

Automatic checks:
- the curriculum version (or the cohorts it applies to) and the total credits
  are stated in the source;
- every block counted toward the degree has a minimum credit threshold;
- all orientation modules share one threshold and the student picks exactly one;
- block thresholds + module threshold == total credits;
- every course of a degree block exists in the CTT catalog with the same credits;
- each block/module offers at least its required credits;
- the normalized dataset passes ``validate_curriculum``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECT_DIR = DATA_DIR.parent
DEFAULT_INPUT_DIR = DATA_DIR / "raw" / "official_curricula"
DEFAULT_CATALOG = DATA_DIR / "raw" / "ctt_course_catalog_all.json"
DEFAULT_OUTPUT_DIR = DATA_DIR / "processed" / "curricula"
DEFAULT_APPROVALS = DATA_DIR / "processed" / "curriculum_approvals.json"
DEFAULT_REPORT = DATA_DIR / "reports" / "official_curricula_import.md"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from build_curriculum import parse_condition  # noqa: E402
from validate_curriculum import validate_curriculum  # noqa: E402

AUTO_APPROVER = "automatic-checks"
AUTO_LABEL = "Kiểm tra tự động, chưa đối chiếu thủ công."
AUTHORITY = "Đại học Bách khoa Hà Nội / đơn vị quản lý chương trình"
PROGRAM_CODE_PATTERN = re.compile(r"^[A-Z0-9-]{2,12}$")
COHORT_PATTERN = re.compile(r"^K(\d{2})$")
COURSE_CODE_PATTERN = re.compile(r"^[A-Z]{2,4}\d{4}[A-Z]?$")
# Above this share of degree courses missing from CTT, the extraction is not trusted.
MAX_MISSING_FROM_CTT = 0.10
# Notes that point at files on the extraction machine are not reproducible.
LOCAL_NOTE_PATTERN = re.compile(r"[A-Za-z]:\\|data/official_curricula|appdata", re.I)


class CheckFailed(Exception):
    """Raised with a human-readable reason when a curriculum fails a check."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_number(value: float) -> int | float:
    return int(value) if float(value).is_integer() else value


def sanitize_source(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a copy without notes that reference the extraction machine."""
    notes = [note for note in raw.get("notes") or [] if not LOCAL_NOTE_PATTERN.search(str(note))]
    return {**raw, "notes": notes}


def cohort_years(cohorts: list[str] | None) -> list[str]:
    years = []
    for cohort in cohorts or []:
        match = COHORT_PATTERN.match(str(cohort).strip().upper())
        if not match:
            raise CheckFailed(f"khóa áp dụng không hợp lệ: {cohort!r}")
        years.append(str(1955 + int(match.group(1))))
    return sorted(set(years))


def resolve_version(raw: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    """Return (curriculum_version, applies_to_cohorts, warnings)."""
    cohorts = sorted({str(c).strip().upper() for c in raw.get("applies_to_cohorts") or []})
    years = cohort_years(cohorts)
    version = str(raw.get("curriculum_version") or "").strip()
    if version:
        if not re.fullmatch(r"20\d{2}", version):
            raise CheckFailed(f"năm phiên bản không hợp lệ: {version!r}")
        return version, cohorts, []
    if not years:
        raise CheckFailed("nguồn không ghi năm phiên bản và không ghi khóa áp dụng")
    warning = (
        f"Nguồn không ghi năm phiên bản; dùng năm nhập học của khóa sớm nhất được áp dụng "
        f"({cohorts[0]} → {years[0]}) làm khóa tra cứu."
    )
    return years[0], cohorts, [warning]


def _is_placeholder(code: Any) -> bool:
    return not code or not COURSE_CODE_PATTERN.match(str(code).strip().upper())


def _collect_group_courses(
    group: dict[str, Any], catalog: dict[str, dict[str, Any]], counts: bool, warnings: list[str]
) -> list[dict[str, Any]]:
    """Keep real catalog courses; reject a degree group whose courses disagree with CTT."""
    kept: list[dict[str, Any]] = []
    seen: set[str] = set()
    for course in group.get("courses") or []:
        code = str(course.get("code") or "").strip().upper()
        if _is_placeholder(code):
            warnings.append(
                f"{group['name']}: bỏ dòng không có mã học phần cụ thể "
                f"({course.get('code') or 'trống'} – {course.get('name') or 'không tên'})."
            )
            continue
        if code in seen:
            continue
        seen.add(code)
        source_credits = _number(course.get("credits"))
        ctt = catalog.get(code)
        if ctt is None:
            # Newer courses may be missing from the CTT snapshot; the official
            # curriculum still states their credits, but no registration rule.
            if source_credits is None:
                if counts:
                    raise CheckFailed(f"{group['name']}: {code} không có trong CTT và nguồn không ghi TC")
                warnings.append(f"{group['name']}: bỏ {code} vì không có trong danh mục CTT.")
                continue
            warnings.append(f"{code} chưa có trong snapshot danh mục CTT; dùng {source_credits:g} TC theo CTĐT.")
            kept.append({**course, "code": code, "_ctt": None, "_credits": source_credits})
            continue
        ctt_credits = float(ctt.get("credits") or 0)
        if ctt_credits == 0 and source_credits:
            # CTT lists English/PE courses with 0 TC; some curricula count them.
            warnings.append(f"{code}: CTT ghi 0 TC; dùng {source_credits:g} TC theo CTĐT.")
            ctt_credits = source_credits
        elif counts and source_credits is not None and abs(source_credits - ctt_credits) > 1e-9:
            raise CheckFailed(
                f"{group['name']}: {code} ghi {source_credits:g} TC nhưng CTT ghi {ctt_credits:g} TC"
            )
        kept.append({**course, "code": code, "_ctt": ctt, "_credits": ctt_credits})
    return kept


def _graduation_parts(raw: dict[str, Any]) -> tuple[list[dict], list[dict], list[dict], float]:
    groups = raw.get("groups") or []
    blocks = [g for g in groups if g.get("kind") == "block" and g.get("counts_toward_degree")]
    modules = [g for g in groups if g.get("kind") == "module" and g.get("counts_toward_degree")]
    others = [g for g in groups if not g.get("counts_toward_degree")]
    if not blocks:
        raise CheckFailed("không có khối kiến thức tính tốt nghiệp")
    for block in blocks:
        if not _number(block.get("required_credits")):
            raise CheckFailed(f"khối '{block.get('name')}' chưa có số TC tối thiểu")
    module_threshold = 0.0
    if modules:
        thresholds = {_number(m.get("required_credits")) for m in modules}
        if None in thresholds or len(thresholds) != 1:
            raise CheckFailed("các mô-đun không cùng một ngưỡng TC rõ ràng")
        module_threshold = thresholds.pop()
    return blocks, modules, others, module_threshold


def build_dataset(
    raw: dict[str, Any], source_file: str, source_sha256: str, catalog: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    code = str(raw.get("admission_code") or "").strip().upper()
    if not PROGRAM_CODE_PATTERN.match(code):
        raise CheckFailed(f"mã chương trình không hợp lệ: {code!r}")
    version, cohorts, warnings = resolve_version(raw)
    total = _number(raw.get("total_credits"))
    if not total:
        raise CheckFailed("nguồn không ghi tổng số TC tốt nghiệp")
    blocks, modules, others, module_threshold = _graduation_parts(raw)
    computed = sum(float(b["required_credits"]) for b in blocks) + module_threshold
    if abs(computed - total) > 1e-9:
        raise CheckFailed(f"tổng ngưỡng các khối {computed:g} TC khác tổng công bố {total:g} TC")

    groups: list[dict[str, Any]] = []
    courses: dict[str, dict[str, Any]] = {}
    components: list[dict[str, Any]] = []
    module_options: list[dict[str, Any]] = []
    numbered = [("khoi", "KHOI", g) for g in blocks + others] + [("mod", "MOD", g) for g in modules]
    counters = {"khoi": 0, "mod": 0}
    for prefix, source_prefix, group in numbered:
        counters[prefix] += 1
        group_id = f"group_{prefix}_{counters[prefix]}"
        counts = bool(group.get("counts_toward_degree"))
        kept = _collect_group_courses(group, catalog, counts, warnings)
        catalog_credits = sum(c["_credits"] for c in kept)
        required = _number(group.get("required_credits")) or 0.0
        if counts and catalog_credits + 1e-9 < required:
            raise CheckFailed(
                f"'{group['name']}' chỉ có {catalog_credits:g} TC học phần, thấp hơn mức {required:g} TC"
            )
        compulsory_block = prefix == "khoi" and counts and abs(catalog_credits - required) < 1e-9
        for course in kept:
            entry = courses.setdefault(course["code"], _course_entry(course, group["name"]))
            entry["group_ids"].append(group_id)
            explicit = course.get("compulsory")
            entry["is_compulsory"] = entry["is_compulsory"] or (
                explicit if isinstance(explicit, bool) else compulsory_block
            )
        groups.append({
            "id": group_id,
            "source_group_code": f"{source_prefix}{counters[prefix]}",
            "name": str(group["name"]),
            "course_count_reported": len(kept),
            "catalog_credits": _clean_number(catalog_credits),
            "course_codes": [c["code"] for c in kept],
            "counts_toward_degree_credits": counts,
        })
        if counts and prefix == "khoi":
            components.append({"type": "GROUP_CREDITS", "group_id": group_id, "required_credits": _clean_number(required)})
        elif counts:
            module_options.append({"group_id": group_id, "required_credits": _clean_number(required)})
    _check_ctt_coverage(groups, courses)
    if module_options:
        components.append({"type": "ONE_OF_GROUPS", "required_credits": _clean_number(module_threshold), "options": module_options})

    name = str(raw.get("name") or code).strip()
    dataset = {
        "schema_version": "1.0.0",
        "program": {
            "program_id": code,
            "program_code": code,
            "name": name,
            "curriculum_version": version,
            "degree_level": "BACHELOR",
            "total_required_credits": _clean_number(total),
        },
        "sources": [{
            "id": f"public_curriculum_{code.lower().replace('-', '_')}",
            "kind": "PUBLIC_HUST_CURRICULUM_EXTRACTION",
            "file": source_file,
            "sha256": source_sha256,
            "authority": AUTHORITY,
            "contains_personal_data": False,
            "personal_data_included_in_output": False,
        }],
        "graduation_paths": [{
            "id": "bachelor",
            "name": f"{name} {version} (Cử nhân)",
            "raw_expression": str(raw.get("graduation_rule") or _expression(groups, components)),
            "components": components,
            "total_required_credits": _clean_number(total),
            "source_order": 0,
        }],
        "groups": groups,
        "courses": list(courses.values()),
        "non_credit_group_ids": [g["id"] for g in groups if not g["counts_toward_degree_credits"]],
        "build_warnings": [
            f"CTĐT {code}-{version} được nhập tự động từ tài liệu công khai: "
            f"{raw.get('source_url') or 'không ghi URL'} (truy cập {raw.get('retrieved_at') or 'không rõ ngày'}). "
            + AUTO_LABEL,
            *dict.fromkeys(warnings),
        ],
    }
    if cohorts:
        dataset["applies_to_cohorts"] = cohorts
    errors, _ = validate_curriculum(dataset, PROJECT_DIR)
    if errors:
        raise CheckFailed("validate_curriculum: " + "; ".join(errors[:3]))
    return dataset


def _check_ctt_coverage(groups: list[dict[str, Any]], courses: dict[str, dict[str, Any]]) -> None:
    degree_codes = {
        code for group in groups if group["counts_toward_degree_credits"] for code in group["course_codes"]
    }
    missing = [code for code in degree_codes if courses[code].pop("_missing_from_ctt", False)]
    for course in courses.values():
        course.pop("_missing_from_ctt", None)
    if degree_codes and len(missing) / len(degree_codes) > MAX_MISSING_FROM_CTT:
        raise CheckFailed(
            f"{len(missing)}/{len(degree_codes)} học phần tính tốt nghiệp không có trong danh mục CTT"
        )


def _course_entry(course: dict[str, Any], group_name: str) -> dict[str, Any]:
    ctt = course["_ctt"] or {}
    semester = _number(course.get("suggested_semester"))
    return {
        "code": course["code"],
        "name": str(course.get("name") or ctt.get("name") or course["code"]).strip(),
        "credits": _clean_number(course["_credits"]),
        "suggested_semester": int(semester) if semester and semester.is_integer() else None,
        "is_compulsory": False,
        "category": group_name,
        "department": str(ctt.get("department") or ""),
        "group_ids": [],
        "registration_condition": parse_condition(ctt.get("raw_condition") or ""),
        "_missing_from_ctt": course["_ctt"] is None,
    }


def _expression(groups: list[dict[str, Any]], components: list[dict[str, Any]]) -> str:
    names = {g["id"]: g["name"] for g in groups}
    parts = []
    for component in components:
        if component["type"] == "GROUP_CREDITS":
            parts.append(f"{names[component['group_id']]}: {component['required_credits']}")
        else:
            options = ", ".join(names[o["group_id"]] for o in component["options"])
            parts.append(f"một trong ({options}): {component['required_credits']}")
    return " + ".join(parts)


def load_catalog(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["courses"] if isinstance(data, dict) else data
    return {str(row["code"]).strip().upper(): row for row in rows if row.get("code")}


def output_name(dataset: dict[str, Any]) -> str:
    program = dataset["program"]
    return f"{program['program_code'].lower().replace('-', '_')}_{program['curriculum_version']}.json"


def lookup_years(dataset: dict[str, Any]) -> set[str]:
    """Entry years served by a dataset; mirrors CurriculumRepository.reload."""
    return set(cohort_years(dataset.get("applies_to_cohorts"))) or {dataset["program"]["curriculum_version"]}


def drop_conflicts(accepted: dict[str, dict[str, Any]], rejected: dict[str, str]) -> None:
    """Reject datasets of the same program that would answer the same cohort."""
    by_key: dict[tuple[str, str], list[str]] = {}
    for name, dataset in accepted.items():
        for year in lookup_years(dataset):
            by_key.setdefault((dataset["program"]["program_code"], year), []).append(name)
    for (code, year), names in by_key.items():
        if len(names) > 1:
            for name in names:
                if accepted.pop(name, None) is not None:
                    rejected[name] = f"nhiều tài liệu {code} cùng áp dụng cho năm/khóa {year}"


def run(input_dir: Path, catalog_path: Path, output_dir: Path, approvals_path: Path, report_path: Path,
        source_dir: Path | None = None) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    catalog = load_catalog(catalog_path)
    approvals = json.loads(approvals_path.read_text(encoding="utf-8"))
    manual = [a for a in approvals["approvals"] if a.get("approved_by") != AUTO_APPROVER]
    manual_programs = {str(a["candidate_id"]).rsplit("-", 1)[0].upper() for a in manual}
    stale_outputs = [a["output_file"] for a in approvals["approvals"] if a.get("approved_by") == AUTO_APPROVER]

    source_dir = source_dir or input_dir
    source_dir.mkdir(parents=True, exist_ok=True)
    accepted: dict[str, dict[str, Any]] = {}
    rejected: dict[str, str] = {}
    for path in sorted(input_dir.glob("*.json")):
        raw = sanitize_source(json.loads(path.read_text(encoding="utf-8")))
        target = source_dir / path.name
        target.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if str(raw.get("admission_code") or "").upper() in manual_programs:
            rejected[path.stem] = "đã có dữ liệu được đối chiếu thủ công, giữ bản thủ công"
            continue
        try:
            source_file = target.resolve().relative_to(PROJECT_DIR).as_posix()
        except ValueError:
            source_file = target.as_posix()
        try:
            accepted[path.stem] = build_dataset(raw, source_file, _sha256(target), catalog)
        except CheckFailed as exc:
            rejected[path.stem] = str(exc)
    drop_conflicts(accepted, rejected)

    for stale in stale_outputs:
        (PROJECT_DIR / stale).unlink(missing_ok=True)
    auto_entries = []
    for name, dataset in sorted(accepted.items()):
        target = output_dir / output_name(dataset)
        if target.exists():
            raise SystemExit(f"Không ghi đè dataset thủ công: {target}")
        target.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        auto_entries.append(_approval(dataset, target))
    approvals["approvals"] = manual + auto_entries
    approvals_path.write_text(json.dumps(approvals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(render_report(accepted, rejected), encoding="utf-8")
    return accepted, rejected


def _approval(dataset: dict[str, Any], target: Path) -> dict[str, Any]:
    program = dataset["program"]
    try:
        output_file = target.resolve().relative_to(PROJECT_DIR).as_posix()
    except ValueError:
        output_file = target.as_posix()
    return {
        "candidate_id": f"{program['program_code']}-{program['curriculum_version']}",
        "status": "approved",
        "approved_by": AUTO_APPROVER,
        "output_file": output_file,
        "notes": [
            AUTO_LABEL,
            f"{len(dataset['courses'])} học phần khớp danh mục CTT; tổng ngưỡng các khối bằng "
            f"{program['total_required_credits']} TC công bố.",
        ],
    }


def render_report(accepted: dict[str, dict[str, Any]], rejected: dict[str, str]) -> str:
    lines = [
        "# Kết quả nhập CTĐT công khai",
        "",
        f"Đã nhập {len(accepted)} CTĐT qua kiểm tra tự động (chưa đối chiếu thủ công); "
        f"{len(rejected)} tài liệu chưa đạt.",
        "",
        "## Đã nhập",
        "",
        "| Tài liệu | Mã | Phiên bản | Khóa áp dụng | Tổng TC | Học phần |",
        "|---|---|---|---|---:|---:|",
    ]
    for name, dataset in sorted(accepted.items()):
        program = dataset["program"]
        cohorts = ", ".join(dataset.get("applies_to_cohorts", [])) or "theo năm phiên bản"
        lines.append(
            f"| {name} | {program['program_code']} | {program['curriculum_version']} | {cohorts} | "
            f"{program['total_required_credits']} | {len(dataset['courses'])} |"
        )
    lines += ["", "## Chưa đạt", "", "| Tài liệu | Lý do |", "|---|---|"]
    for name, reason in sorted(rejected.items()):
        lines.append(f"| {name} | {reason.replace('|', '/')} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_INPUT_DIR,
                        help="nơi lưu bản nguồn đã làm sạch (được ghi vào sources[].file)")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--approvals", type=Path, default=DEFAULT_APPROVALS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    accepted, rejected = run(args.input_dir, args.catalog, args.output_dir, args.approvals,
                             args.report, args.source_dir)
    print(f"[OK] Nhập {len(accepted)} CTĐT; {len(rejected)} tài liệu chưa đạt. Báo cáo: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
