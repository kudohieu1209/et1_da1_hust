#!/usr/bin/env python3
"""Extract conservative course-list candidates from downloaded HUST PDFs.

PDF layout varies by faculty.  The parser only reads the section headed
``Danh mục học phần``/``Course list`` and rows containing a HUST-like course
code plus a credit-load expression.  It does not infer prerequisites,
compulsory status, or a graduation formula.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent
PROJECT_DIR = DATA_DIR.parent
DEFAULT_INPUT = DATA_DIR / "raw" / "hust_program_curriculum_downloads.json"
DEFAULT_OUTPUT = DATA_DIR / "raw" / "hust_curriculum_pdf_extractions.json"
COURSE_CODE_RE = re.compile(r"[A-Z]{2,5}\d{4}[A-Z]?", re.I)
CREDIT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*\([^)]{1,40}\)")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compact(value: float | None) -> int | float | None:
    if value is None:
        return None
    return int(value) if value.is_integer() else value


def _clean(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_DIR.resolve()).as_posix()
    except ValueError:
        return path.name


def pdf_text(path: Path) -> str:
    executable = shutil.which("pdftotext")
    if executable:
        process = subprocess.run(
            [executable, "-layout", str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if process.stdout.strip():
            return process.stdout
    try:
        from pypdf import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    except Exception as exc:
        raise RuntimeError(f"Không đọc được PDF {path}: {exc}") from exc


def _curriculum_section(text: str) -> str:
    starts = [
        match.start()
        for match in re.finditer(r"Danh mục học phần|Course list|Khung chương trình", text, re.I)
    ]
    if not starts:
        return text if re.search(r"MÃ SỐ|Course ID|MÃ HP", text, re.I) else ""
    sections: list[str] = []
    for start in starts:
        endings = [
            match.start()
            for match in re.finditer(
                r"Mô tả tóm tắt học phần|Course Outlines", text[start + 20 :], re.I
            )
        ]
        end = start + 20 + min(endings) if endings else len(text)
        sections.append(text[start:end])
    # A table of contents and a footer may repeat the heading.  Score each
    # candidate by actual course-code/credit rows, not by position alone.
    return max(
        sections,
        key=lambda section: (
            len(COURSE_CODE_RE.findall(section))
            + 3 * len(CREDIT_RE.findall(section)),
            len(section),
        ),
    )


def _group_name(line: str) -> str | None:
    value = _clean(line).strip("|-")
    if not value or COURSE_CODE_RE.search(value):
        return None
    lowered = value.casefold()
    prefixes = (
        "lý luận chính trị",
        "khối kiến thức",
        "cơ sở và cốt lõi",
        "kiến thức bổ trợ",
        "kiến thức chuyên ngành",
        "thực tập",
        "đồ án",
        "tự chọn theo",
        "mô đun",
        "module",
        "giáo dục thể chất",
        "giáo dục quốc phòng",
        "tiếng anh",
        "tiếng pháp",
        "ngoại ngữ",
    )
    if any(lowered.startswith(prefix) for prefix in prefixes):
        # Remove a trailing page/credit-only fragment, while retaining the
        # official group title for human review.
        return re.sub(r"\s+\(?\d+(?:[.,]\d+)?\s*(?:TC|tín chỉ).*", "", value, flags=re.I).strip()
    return None


def parse_course_list(section: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    lines = section.splitlines()
    courses_by_code: dict[str, dict[str, Any]] = {}
    groups: list[dict[str, Any]] = []
    groups_by_name: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    current_group: dict[str, Any] | None = None

    def ensure_group(name: str) -> dict[str, Any]:
        nonlocal groups
        key = name.casefold()
        existing = groups_by_name.get(key)
        if existing:
            return existing
        group = {
            "id": f"group_pdf_{len(groups) + 1}",
            "source_group_code": f"PDF{len(groups) + 1}",
            "name": name,
            "kind": (
                "module"
                if key.startswith(("mô đun", "module"))
                else "unclassified_pdf_group"
            ),
            "course_count_reported": 0,
            "catalog_credits": 0,
            "required_credits": None,
            "published_catalog_credits": None,
            "course_codes": [],
            "counts_toward_degree_credits": not any(
                token in key for token in ("tiếng anh", "ngoại ngữ", "thể chất", "quốc phòng")
            ),
        }
        groups.append(group)
        groups_by_name[key] = group
        return group

    index = 0
    while index < len(lines):
        line = lines[index]
        heading = _group_name(line)
        if heading:
            current_group = ensure_group(heading)

        code_match = COURSE_CODE_RE.search(line.upper())
        if not code_match:
            index += 1
            continue
        code = code_match.group(0).upper()
        # The table of contents also contains course codes, but lacks a
        # credit-load expression.  Accumulate only a few continuation lines;
        # seeing another code first means this was a TOC row.
        fragments = [line[code_match.end() :]]
        credit_match = CREDIT_RE.search(" ".join(fragments))
        previous_name = ""
        previous_credit = None
        lookahead = index + 1
        while credit_match is None and lookahead < min(index + 5, len(lines)):
            if COURSE_CODE_RE.search(lines[lookahead].upper()):
                break
            fragments.append(lines[lookahead])
            credit_match = CREDIT_RE.search(" ".join(fragments))
            lookahead += 1
        if credit_match is None:
            # Some PDF text layers put the credit expression on the line
            # immediately before the course code (e.g. a long course name),
            # or split ``3(0-0-6-12)`` into a trailing ``3`` and ``12)``.
            for previous_index in range(max(0, index - 2), index):
                previous = lines[previous_index]
                previous_match = CREDIT_RE.search(previous)
                if previous_match:
                    previous_name = previous[: previous_match.start()]
                    previous_credit = float(previous_match.group(1).replace(",", "."))
                    credit_match = previous_match
                    break
            if credit_match is None:
                tail = re.search(r"\b(\d+(?:[.,]\d+)?)\s*$", line)
                if tail and index + 1 < len(lines) and re.search(r"\d+\s*\)$", lines[index + 1]):
                    previous_credit = float(tail.group(1).replace(",", "."))
                    previous_name = line[code_match.end() : tail.start()]
                    lookahead = index + 2
                else:
                    index += 1
                    continue
        combined = _clean(" ".join(fragments))
        name = _clean(previous_name or combined[: credit_match.start()])
        name = re.sub(r"^\(?\d+\)?\s+", "", name)
        if not name or name.casefold() in {"tên học phần", "course name"}:
            index = max(index + 1, lookahead)
            continue
        credits = previous_credit if previous_credit is not None else float(credit_match.group(1).replace(",", "."))
        group = current_group or ensure_group("Chưa phân loại từ PDF")
        course = courses_by_code.get(code)
        if course is None:
            course = {
                "code": code,
                "name": name,
                "credits": _compact(credits),
                "suggested_semester": None,
                "group_ids": [],
            }
            courses_by_code[code] = course
        elif course.get("credits") != _compact(credits):
            warnings.append(f"{code}: tín chỉ lặp lại không nhất quán")
        if group["id"] not in course["group_ids"]:
            course["group_ids"].append(group["id"])
            group["course_codes"].append(code)
            group["course_count_reported"] += 1
            group["catalog_credits"] = _compact(float(group["catalog_credits"]) + credits)
        index = max(index + 1, lookahead)

    return groups, list(courses_by_code.values()), warnings


def extract_pdf(path: Path, admission_code: str, name: str, source_url: str | None) -> dict[str, Any]:
    text = pdf_text(path)
    section = _curriculum_section(text)
    groups, courses, warnings = parse_course_list(section)
    version_match = re.search(r"(?:CHƯƠNG TRÌNH|PROGRAM).*?\b(20\d{2})\b", text[:5000], re.I | re.S)
    version = version_match.group(1) if version_match and int(version_match.group(1)) <= 2035 else None
    total_matches = re.findall(r"Tổng cộng.*?(\d+(?:[.,]\d+)?)\s*(?:tín chỉ|credits)", text, re.I | re.S)
    total = max((float(value.replace(",", ".")) for value in total_matches), default=None)
    if not section:
        warnings.append("Không tìm thấy phần Danh mục học phần trong PDF")
    if not courses:
        warnings.append("Không trích xuất được dòng mã môn + tín chỉ")
    return {
        "admission_code": admission_code,
        "name": name,
        "parser": "hust-pdf-course-list.v1",
        "status": "extracted_pdf" if courses else "metadata_only",
        "curriculum_version": version,
        "total_credits_published": _compact(total),
        "groups": groups,
        "courses": courses,
        "warnings": warnings,
        "file": _project_relative(path),
        "source_url": source_url,
        "source_sha256": _sha256(path),
    }


def extract_manifest(input_path: Path) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for item in payload.get("records", []):
        code = str(item.get("admission_code", "")).upper()
        for attachment in item.get("attachments", []):
            if not str(attachment.get("status", "")).startswith("downloaded"):
                continue
            path = Path(attachment.get("file", ""))
            if not path.is_absolute() and not path.exists():
                for base in (PROJECT_DIR, PROJECT_DIR.parent):
                    candidate_path = base / path
                    if candidate_path.exists():
                        path = candidate_path
                        break
            if path.suffix.casefold() != ".pdf" or not path.exists():
                continue
            records.append(
                extract_pdf(path, code, item.get("name", ""), attachment.get("final_url") or attachment.get("url"))
            )
    return {
        "schema_version": "hust-curriculum-pdf-extraction.v1",
        "source_manifest": _project_relative(input_path),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "extracted": sum(item["status"] == "extracted_pdf" for item in records),
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = extract_manifest(args.input)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Đã trích xuất {result['extracted']}/{result['count']} PDF vào {args.output}")
        for record in result["records"]:
            print(
                f"[PDF] {record['admission_code']}-{record.get('curriculum_version') or '?'}: "
                f"{len(record['courses'])} HP, {record.get('total_credits_published') or '?'} TC"
            )
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
