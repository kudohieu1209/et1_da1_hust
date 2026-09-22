#!/usr/bin/env python3
"""Build review-only curriculum candidates from public HUST programme pages.

The extractor intentionally stops before touching ``processed/curricula``.  This
script joins its course rows with the global CTT course catalogue and produces a
provenance-rich review file.  A candidate is never marked as Rule Engine-ready
automatically: missing thresholds, incomplete source pages, credit conflicts,
or absent CTT conditions remain visible for a human review step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECT_DIR = DATA_DIR.parent
DEFAULT_EXTRACTION = DATA_DIR / "raw" / "hust_curriculum_extractions.json"
DEFAULT_PDF_EXTRACTION = DATA_DIR / "raw" / "hust_curriculum_pdf_extractions.json"
DEFAULT_CATALOG = DATA_DIR / "raw" / "ctt_course_catalog_all.json"
DEFAULT_OUTPUT = DATA_DIR / "raw" / "hust_curriculum_candidates.json"
DEFAULT_APPROVALS = DATA_DIR / "processed" / "curriculum_approvals.json"

# Keep the condition parser in one place so candidates and the verified ET1
# dataset interpret slash=OR and comma=AND identically.
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from build_curriculum import parse_condition  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_DIR.resolve()).as_posix()
    except ValueError:
        return path.name


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compact(value: float | None) -> int | float | None:
    if value is None:
        return None
    return int(value) if value.is_integer() else value


def _load_catalog(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("courses", payload) if isinstance(payload, dict) else payload
    return {
        str(row.get("code", "")).strip().upper(): row
        for row in rows
        if row.get("code")
    }


def _load_approvals(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not Path(path).exists():
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        str(item.get("candidate_id", "")).upper(): item
        for item in payload.get("approvals", [])
        if item.get("candidate_id")
    }


def _source(path: Path, *, source_id: str, kind: str, authority: str) -> dict[str, Any]:
    stat = path.stat()
    return {
        "id": source_id,
        "kind": kind,
        "file": _project_relative(path),
        "sha256": _sha256(path),
        "file_modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "authority": authority,
        "contains_personal_data": False,
        "personal_data_included_in_output": False,
    }


def _course_candidate(course: dict[str, Any], catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    code = str(course.get("code", "")).upper()
    ctt = catalog.get(code)
    raw_condition = str((ctt or {}).get("raw_condition") or "").strip()
    result = {
        "code": code,
        "name": course.get("name", ""),
        "credits": course.get("credits"),
        "suggested_semester": course.get("suggested_semester"),
        "group_ids": list(course.get("group_ids", [])),
        "registration_condition": parse_condition(raw_condition),
        "ctt_match": ctt is not None,
    }
    if ctt is not None:
        result["ctt_name"] = ctt.get("name", "")
        result["ctt_credits"] = ctt.get("credits")
        result["ctt_department"] = ctt.get("department", "")
        result["ctt_raw_condition"] = raw_condition
    return result


def _quality(record: dict[str, Any], catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    courses = record.get("courses", [])
    groups = record.get("groups", [])
    non_credit_group_ids = {
        str(group.get("id"))
        for group in groups
        if not group.get("counts_toward_degree_credits")
    }
    missing_codes = sorted(
        code for code in (str(c.get("code", "")).upper() for c in courses) if code not in catalog
    )
    credit_mismatches = []
    for course in courses:
        code = str(course.get("code", "")).upper()
        ctt = catalog.get(code)
        extracted = _number(course.get("credits"))
        ctt_credits = _number((ctt or {}).get("credits"))
        # CTT deliberately stores language/PE/defence rows as zero-credit
        # entries, while public programme pages may display workload credits.
        # That is a convention difference, not a course-credit conflict.
        if course.get("group_ids") and set(course["group_ids"]).issubset(non_credit_group_ids):
            continue
        if ctt is not None and extracted is not None and ctt_credits is not None:
            if abs(extracted - ctt_credits) > 1e-9:
                credit_mismatches.append(
                    {"code": code, "page_credits": _compact(extracted), "ctt_credits": _compact(ctt_credits)}
                )

    summary_mismatches = []
    for group in groups:
        published = _number(group.get("published_catalog_credits"))
        extracted = _number(group.get("catalog_credits"))
        if published is not None and extracted is not None and abs(published - extracted) > 1e-9:
            summary_mismatches.append(
                {
                    "group_id": group.get("id"),
                    "name": group.get("name", ""),
                    "page_catalog_credits": _compact(published),
                    "row_sum_credits": _compact(extracted),
                }
            )

    ctt_matched = sum(
        catalog.get(str(c.get("code", "")).upper()) is not None for c in courses
    )
    condition_nonempty = sum(
        bool(str((catalog.get(str(c.get("code", "")).upper()) or {}).get("raw_condition") or "").strip())
        for c in courses
    )
    degree_groups = [g for g in groups if g.get("counts_toward_degree_credits")]
    required_missing = [g.get("id") for g in degree_groups if g.get("required_credits") is None]
    modules = [
        g
        for g in degree_groups
        if g.get("kind") == "module"
        or str(g.get("name", "")).casefold().startswith(("mô đun", "module"))
    ]
    required_known_total = sum(
        float(g["required_credits"])
        for g in degree_groups
        if g.get("required_credits") is not None
    )
    page_total = _number(record.get("total_credits_published"))
    formula_with_one_module = None
    if modules and not required_missing:
        module_thresholds = {float(g["required_credits"]) for g in modules}
        if len(module_thresholds) == 1:
            formula_with_one_module = (
                required_known_total
                - sum(float(g["required_credits"]) for g in modules)
                + next(iter(module_thresholds))
            )

    reasons = []
    # A candidate needs a deliberate human sign-off before it can become a
    # versioned dataset, even when all automated checks happen to pass.
    reasons.append("normalization_not_validated")
    if not record.get("curriculum_version"):
        reasons.append("missing_curriculum_version")
    if page_total is None:
        reasons.append("missing_total_credits")
    if missing_codes:
        reasons.append("course_codes_not_in_ctt")
    if credit_mismatches:
        reasons.append("course_credit_mismatch")
    if summary_mismatches:
        reasons.append("page_summary_differs_from_row_sum")
    if required_missing:
        reasons.append("required_credit_threshold_missing")
    if formula_with_one_module is not None and page_total is not None:
        if abs(formula_with_one_module - page_total) > 1e-9:
            reasons.append("required_credit_formula_does_not_match_page_total")

    blocking_reasons = [reason for reason in reasons if reason != "normalization_not_validated"]
    return {
        "course_count": len(courses),
        "group_count": len(groups),
        "module_count": len(modules),
        "course_codes_missing_from_ctt": missing_codes,
        "course_credit_mismatches": credit_mismatches,
        "summary_credit_mismatches": summary_mismatches,
        "ctt_course_rows_matched": ctt_matched,
        "ctt_course_rows_missing": len(courses) - ctt_matched,
        "ctt_conditions_nonempty": condition_nonempty,
        "ctt_conditions_empty_or_no_prerequisite": ctt_matched - condition_nonempty,
        "ctt_condition_snapshot_complete": not missing_codes,
        "required_credit_thresholds_missing": required_missing,
        "required_credits_sum_if_known": _compact(required_known_total),
        "derived_one_module_total": _compact(formula_with_one_module),
        "page_total_credits": _compact(page_total),
        "review_reasons": reasons,
        "automatic_checks_passed": not blocking_reasons,
        "rule_engine_eligible": False,
    }


def build_candidates(
    extraction_path: Path = DEFAULT_EXTRACTION,
    catalog_path: Path = DEFAULT_CATALOG,
    pdf_extraction_path: Path | None = DEFAULT_PDF_EXTRACTION,
    approvals_path: Path | None = DEFAULT_APPROVALS,
) -> dict[str, Any]:
    extraction = json.loads(extraction_path.read_text(encoding="utf-8"))
    catalog = _load_catalog(catalog_path)
    approvals = _load_approvals(approvals_path)
    extraction_records = list(extraction.get("records", []))
    if pdf_extraction_path and Path(pdf_extraction_path).exists():
        pdf_payload = json.loads(Path(pdf_extraction_path).read_text(encoding="utf-8"))
        extraction_records.extend(pdf_payload.get("records", []))
    records = []
    for raw in sorted(
        extraction_records,
        key=lambda item: (str(item.get("admission_code", "")), str(item.get("curriculum_version", ""))),
    ):
        if not (
            str(raw.get("status", "")).startswith("extracted")
            or raw.get("status") == "metadata_only"
        ):
            continue
        candidate = dict(raw)
        code = str(raw.get("admission_code", "")).upper()
        version = raw.get("curriculum_version")
        candidate["candidate_id"] = f"{code}-{version}" if version else code
        candidate["courses"] = [_course_candidate(course, catalog) for course in raw.get("courses", [])]
        candidate["quality"] = _quality(candidate, catalog)
        approval = approvals.get(str(candidate["candidate_id"]).upper())
        approved = bool(
            approval
            and approval.get("status") == "approved"
            and candidate["quality"]["automatic_checks_passed"]
        )
        candidate["activation"] = {
            "status": "approved" if approved else (
                "manual_approval_pending"
                if candidate["quality"]["automatic_checks_passed"]
                else "needs_review"
            ),
            "rule_engine_eligible": approved,
            "reason_codes": candidate["quality"]["review_reasons"],
        }
        if approved:
            candidate["activation"].update(
                {
                    "approved_by": approval.get("approved_by", ""),
                    "approved_at": approval.get("approved_at", ""),
                    "output_file": approval.get("output_file", ""),
                }
            )
        # The nested raw source fields are useful for traceability, but this
        # output is easier to consume when the source is explicit and stable.
        candidate["sources"] = [
            {
                "id": f"public_curriculum_{code.lower()}",
                "kind": (
                    "PUBLIC_HUST_CURRICULUM_PDF"
                    if str(raw.get("parser", "")).startswith("hust-pdf")
                    else "PUBLIC_HUST_CURRICULUM_HTML"
                ),
                "file": raw.get("file"),
                "sha256": raw.get("source_sha256"),
                "url": raw.get("source_url"),
                "authority": "Đại học Bách khoa Hà Nội / đơn vị quản lý chương trình",
                "contains_personal_data": False,
            },
            _source(
                catalog_path,
                source_id="ctt_course_catalog_all",
                kind="CTT_GLOBAL_COURSE_CATALOG_JSON",
                authority="CTT - Đại học Bách khoa Hà Nội",
            ),
        ]
        records.append(candidate)
    result = {
        "schema_version": "hust-curriculum-candidates.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "extraction_manifest": _project_relative(extraction_path),
        "catalog_source": _project_relative(catalog_path),
        "count": len(records),
        "rule_engine_loaded": sum(
            bool((record.get("activation") or {}).get("rule_engine_eligible"))
            for record in records
        ),
        "records": records,
    }
    if pdf_extraction_path and Path(pdf_extraction_path).exists():
        result["pdf_extraction_manifest"] = _project_relative(Path(pdf_extraction_path))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction", type=Path, default=DEFAULT_EXTRACTION)
    parser.add_argument("--pdf-extraction", type=Path, default=DEFAULT_PDF_EXTRACTION)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--approvals", type=Path, default=DEFAULT_APPROVALS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_candidates(args.extraction, args.catalog, args.pdf_extraction, args.approvals)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã tạo {result['count']} curriculum candidate (review-only) tại {args.output}")
    for record in result["records"]:
        quality = record["quality"]
        print(
            f"[REVIEW] {record['candidate_id']}: {quality['course_count']} HP, "
            f"{quality['module_count']} mô-đun, lý do: "
            f"{', '.join(quality['review_reasons']) or 'none'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
