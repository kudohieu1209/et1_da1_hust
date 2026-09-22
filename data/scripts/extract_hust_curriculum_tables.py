#!/usr/bin/env python3
"""Extract course tables from the public HUST curriculum snapshots.

The current HUST faculty pages use a small, regular ``hp-table`` HTML format,
while other faculties publish Word/Excel exports or free-form pages.  This
script only extracts the regular table layout and writes a raw candidate file;
it intentionally does not create a ``processed/curricula`` dataset.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = DATA_DIR / "raw" / "hust_program_curriculum_downloads.json"
DEFAULT_OUTPUT = DATA_DIR / "raw" / "hust_curriculum_extractions.json"
PROJECT_DIR = DATA_DIR.parent

COURSE_CODE_RE = re.compile(r"[A-Z]{2,5}\d{4}[A-Z]?\Z", re.I)


def _project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_DIR.resolve()).as_posix()
    except ValueError:
        return path.name


def clean_text(fragment: str | None) -> str:
    if not fragment:
        return ""
    fragment = re.sub(r"<script\b.*?</script\s*>", " ", fragment, flags=re.I | re.S)
    fragment = re.sub(r"<style\b.*?</style\s*>", " ", fragment, flags=re.I | re.S)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_number(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"\d+(?:[.,]\d+)?", clean_text(value))
    if not match:
        return None
    return float(match.group(0).replace(",", "."))


def compact_number(value: float | None) -> int | float | None:
    if value is None:
        return None
    return int(value) if float(value).is_integer() else value


def _class_has(attrs: str, name: str) -> bool:
    match = re.search(r'class=["\']([^"\']*)["\']', attrs, re.I)
    return bool(match and re.search(rf"(?:^|\s){re.escape(name)}(?:\s|$)", match.group(1)))


def _course_name(name_html: str) -> str:
    without_english = re.sub(
        r'<span\b[^>]*class=["\'][^"\']*\bt-en\b[^"\']*["\'][^>]*>.*?</span\s*>',
        " ",
        name_html,
        flags=re.I | re.S,
    )
    without_tag = re.sub(
        r'<span\b[^>]*class=["\'][^"\']*\btc-tag\b[^"\']*["\'][^>]*>.*?</span\s*>',
        " ",
        without_english,
        flags=re.I | re.S,
    )
    return clean_text(without_tag)


def _course_credits(name_html: str) -> float | None:
    tag = re.search(
        r'<span\b[^>]*class=["\'][^"\']*\btc-tag\b[^"\']*["\'][^>]*>(.*?)</span\s*>',
        name_html,
        flags=re.I | re.S,
    )
    if tag:
        match = re.match(r"\s*(\d+(?:[.,]\d+)?)\s*\(", clean_text(tag.group(1)))
        if match:
            return float(match.group(1).replace(",", "."))
    # Fallback for pasted tables where the credit tag is plain text.
    match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*\(", clean_text(name_html))
    return float(match.group(1).replace(",", ".")) if match else None


def parse_table(table_html: str) -> list[dict]:
    courses: list[dict] = []
    for row_match in re.finditer(r"<tr\b.*?</tr\s*>", table_html, flags=re.I | re.S):
        row = row_match.group(0)
        cells = re.findall(r"<td\b([^>]*)>(.*?)</td\s*>", row, flags=re.I | re.S)
        if len(cells) < 2:
            continue
        code = clean_text(cells[0][1]).upper()
        if not COURSE_CODE_RE.fullmatch(code):
            continue
        name_html = cells[1][1]
        semester = None
        for semester_index, (attrs, _cell) in enumerate(cells[2:], 1):
            if _class_has(attrs, "on"):
                semester = semester_index
                break
        courses.append(
            {
                "code": code,
                "name": _course_name(name_html),
                "credits": compact_number(_course_credits(name_html)),
                "suggested_semester": semester,
            }
        )
    return courses


def parse_generic_table(table_html: str) -> list[dict]:
    """Extract rows from a conventional HTML table with a course-code column.

    This is deliberately conservative: callers only accept a table when it
    contains several course-code rows.  It captures the course list but does
    not invent semesters, groups, or graduation requirements.
    """
    courses: list[dict] = []
    for row_match in re.finditer(r"<tr\b.*?</tr\s*>", table_html, flags=re.I | re.S):
        row = row_match.group(0)
        cells = re.findall(r"<(?P<tag>td|th)\b(?P<attrs>[^>]*)>(?P<body>.*?)</(?P=tag)\s*>", row, flags=re.I | re.S)
        if len(cells) < 3:
            continue
        code_index = next(
            (
                index
                for index, (_tag, _attrs, body) in enumerate(cells)
                if COURSE_CODE_RE.fullmatch(clean_text(body).upper())
            ),
            None,
        )
        if code_index is None or code_index + 1 >= len(cells):
            continue
        code = clean_text(cells[code_index][2]).upper()
        name_html = cells[code_index + 1][2]
        credit_html = cells[code_index + 2][2] if code_index + 2 < len(cells) else ""
        credits = _course_credits(credit_html)
        if credits is None:
            credits = parse_number(credit_html)
        courses.append(
            {
                "code": code,
                "name": _course_name(name_html),
                "credits": compact_number(credits),
                "suggested_semester": None,
            }
        )
    return courses


def _summary_field(fragment: str, class_name: str) -> str:
    match = re.search(
        rf'<span\b[^>]*class=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\'][^>]*>(.*?)</span\s*>',
        fragment,
        flags=re.I | re.S,
    )
    return clean_text(match.group(1)) if match else ""


def _summary_hp_tc(value: str | None) -> tuple[int | None, float | None]:
    """Parse an Astro summary such as ``34 HP · 87 TC``.

    ``khoi-tc`` (when present) is a required-credit threshold, while
    ``khoi-n`` contains the number of rows and the total credits offered by
    the block.  Keeping both values prevents the normalizer from confusing a
    minimum with the full course catalogue.
    """
    text = clean_text(value)
    if not text:
        return None, None
    match = re.search(
        r"(\d+)\s*HP\s*[·•.]\s*(\d+(?:[.,]\d+)?)\s*TC",
        text,
        flags=re.I,
    )
    if not match:
        return None, None
    return int(match.group(1)), float(match.group(2).replace(",", "."))


def _is_non_credit(name: str) -> bool:
    normalized = name.casefold()
    return any(token in normalized for token in ("ngoại ngữ", "giáo dục thể chất", "quốc phòng"))


def _new_group(
    *,
    group_id: str,
    source_group_code: str,
    name: str,
    courses: list[dict],
    required_credits: float | None,
    published_catalog_credits: float | None,
    course_count_reported: int | None,
    kind: str,
) -> dict:
    credits = sum(float(item.get("credits") or 0) for item in courses)
    return {
        "id": group_id,
        "source_group_code": source_group_code,
        "name": name,
        "kind": kind,
        "course_count_reported": course_count_reported if course_count_reported is not None else len(courses),
        "catalog_credits": compact_number(credits),
        "required_credits": compact_number(required_credits),
        "published_catalog_credits": compact_number(published_catalog_credits),
        "course_codes": [item["code"] for item in courses],
        "counts_toward_degree_credits": not _is_non_credit(name),
    }


def _detail_blocks(document: str) -> list[tuple[str, str]]:
    blocks = []
    for match in re.finditer(
        r'<details\b[^>]*class=["\'][^"\']*\bkhoi\b[^"\']*["\'][^>]*>',
        document,
        flags=re.I,
    ):
        end = document.find("</details>", match.end())
        if end < 0:
            continue
        blocks.append((match.group(0), document[match.start() : end + len("</details>")]))
    return blocks


def _module_blocks(document: str) -> list[str]:
    starts = list(
        re.finditer(
            r'<div\b[^>]*class=["\'][^"\']*\bmgroup\b[^"\']*["\'][^>]*>',
            document,
            flags=re.I,
        )
    )
    boundaries = [
        *(
            match.start()
            for match in re.finditer(
                r'<details\b[^>]*class=["\'][^"\']*\bkhoi\b[^"\']*["\'][^>]*>',
                document,
                flags=re.I,
            )
        ),
        *(match.start() for match in starts),
        document.find("</section>") if "</section>" in document else len(document),
    ]
    blocks: list[str] = []
    for match in starts:
        end_candidates = [position for position in boundaries if position > match.start()]
        end = min(end_candidates) if end_candidates else len(document)
        blocks.append(document[match.start() : end])
    return blocks


def extract_curriculum(document: str, admission_code: str, name: str) -> dict:
    table_count = len(re.findall(r"<table\b", document, flags=re.I))
    hp_table_count = len(
        re.findall(
            r'<table\b[^>]*class=["\'][^"\']*\bhp-table\b[^"\']*["\']',
            document,
            flags=re.I,
        )
    )
    result = {
        "admission_code": admission_code,
        "name": name,
        "parser": "hust-astro-hp-table.v1",
        "status": "extracted" if hp_table_count else "layout_not_supported",
        "table_count": table_count,
        "hp_table_count": hp_table_count,
        "curriculum_version": None,
        "total_credits_published": None,
        "groups": [],
        "courses": [],
        "warnings": [],
    }
    if not hp_table_count:
        # A few units publish a Word-exported table directly in the page.  It
        # has no Astro classes or semester columns, so retain only a cautious
        # course-list candidate for later manual grouping.
        generic_courses: list[dict] = []
        generic_table_index: int | None = None
        for table_index, table_match in enumerate(
            re.finditer(r"<table\b.*?</table\s*>", document, flags=re.I | re.S), 1
        ):
            parsed = parse_generic_table(table_match.group(0))
            if len(parsed) >= 3:
                generic_courses = parsed
                generic_table_index = table_index
                break
        if not generic_courses:
            return result
        result["parser"] = "hust-generic-table.v1"
        result["status"] = "extracted_generic"
        group = _new_group(
            group_id="group_table_1",
            source_group_code=f"TABLE{generic_table_index}",
            name="Danh mục học phần (bảng HTML)",
            courses=generic_courses,
            required_credits=None,
            published_catalog_credits=sum(float(item.get("credits") or 0) for item in generic_courses),
            course_count_reported=len(generic_courses),
            kind="unclassified_table",
        )
        group["_courses"] = generic_courses
        course_by_code = {item["code"]: dict(item, group_ids=[group["id"]]) for item in generic_courses}
        result["groups"] = [{key: value for key, value in group.items() if key != "_courses"}]
        result["courses"] = list(course_by_code.values())
        result["warnings"].append("Bảng HTML không có nhóm/mô-đun hoặc công thức tốt nghiệp; cần phân loại thủ công")
        return result

    version_match = re.search(
        r'<span\b[^>]*class=["\'][^"\']*\binfo-nhan\b[^"\']*["\'][^>]*>\s*Phiên bản\s*</span>\s*'
        r'<span\b[^>]*class=["\'][^"\']*\binfo-gt\b[^"\']*["\']?[^>]*>(.*?)</span\s*>',
        document,
        flags=re.I | re.S,
    )
    if version_match:
        result["curriculum_version"] = clean_text(version_match.group(1))
    total_match = re.search(r"Tổng tín chỉ\s*(\d+(?:[.,]\d+)?)\s*TC", clean_text(document), flags=re.I)
    if total_match:
        result["total_credits_published"] = compact_number(float(total_match.group(1).replace(",", ".")))

    groups: list[dict] = []
    course_by_code: dict[str, dict] = {}

    def add_group(group: dict) -> None:
        groups.append(group)
        for item in group["_courses"]:
            code = item["code"]
            existing = course_by_code.get(code)
            if existing is None:
                existing = dict(item)
                existing["group_ids"] = []
                course_by_code[code] = existing
            if group["id"] not in existing["group_ids"]:
                existing["group_ids"].append(group["id"])
            for field in ("name", "credits"):
                # Some pages repeat an integrated-program row in a second
                # table without repeating its credit tag.  A missing value is
                # not evidence of a contradiction; keep the known value.
                if item.get(field) is not None and existing.get(field) not in (None, item.get(field)):
                    result["warnings"].append(
                        f"{code}: {field} không nhất quán giữa các nhóm "
                        f"({existing.get(field)!r} != {item.get(field)!r})"
                    )

    for index, (_opening, block) in enumerate(_detail_blocks(document), 1):
        table_match = re.search(r"<table\b.*?</table\s*>", block, flags=re.I | re.S)
        if not table_match:
            continue
        courses = parse_table(table_match.group(0))
        if not courses:
            continue
        name_value = _summary_field(block, "khoi-ten") or f"Khối {index}"
        required_credits = parse_number(_summary_field(block, "khoi-tc"))
        reported_count, published_catalog_credits = _summary_hp_tc(
            _summary_field(block, "khoi-n")
        )
        group = _new_group(
            group_id=f"group_khoi_{index}",
            source_group_code=f"KHOI{index}",
            name=name_value,
            courses=courses,
            required_credits=required_credits,
            published_catalog_credits=published_catalog_credits,
            course_count_reported=reported_count,
            kind="knowledge_block",
        )
        group["_courses"] = courses
        add_group(group)

    for module_block in _module_blocks(document):
        buttons = [
            clean_text(value)
            for value in re.findall(
                r'<button\b[^>]*class=["\'][^"\']*\bmtab\b[^"\']*["\'][^>]*>(.*?)</button\s*>',
                module_block,
                flags=re.I | re.S,
            )
        ]
        total_match = re.search(
            r'<p\b[^>]*class=["\'][^"\']*\bmtotal\b[^"\']*["\'][^>]*>.*?'
            r'<b\b[^>]*>(\d+(?:[.,]\d+)?)\s*tín chỉ',
            module_block,
            flags=re.I | re.S,
        )
        required_credits = float(total_match.group(1).replace(",", ".")) if total_match else None
        tables = [match.group(0) for match in re.finditer(r"<table\b.*?</table\s*>", module_block, flags=re.I | re.S)]
        for index, table in enumerate(tables, 1):
            courses = parse_table(table)
            if not courses:
                continue
            group_name = buttons[index - 1] if index <= len(buttons) else f"Mô đun {index}"
            group = _new_group(
                group_id=f"group_mod_{index}",
                source_group_code=f"MOD{index}",
                name=group_name,
                courses=courses,
                required_credits=required_credits,
                published_catalog_credits=required_credits,
                course_count_reported=len(courses),
                kind="module",
            )
            group["_courses"] = courses
            add_group(group)

    for group in groups:
        group.pop("_courses", None)
    result["groups"] = groups
    result["courses"] = list(course_by_code.values())
    if not result["groups"]:
        result["status"] = "no_course_rows"
    return result


def extract_manifest(input_path: Path) -> dict:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    records = []
    for item in payload.get("records", []):
        file_name = item.get("file")
        if not file_name or not str(item.get("status", "")).startswith("downloaded"):
            continue
        path = Path(file_name)
        if not path.is_absolute() and not path.exists():
            for base in (PROJECT_DIR, PROJECT_DIR.parent):
                candidate_path = base / path
                if candidate_path.exists():
                    path = candidate_path
                    break
        if not path.exists():
            continue
        document = path.read_text(encoding="utf-8", errors="replace")
        extracted = extract_curriculum(document, str(item.get("admission_code", "")).upper(), item.get("name", ""))
        extracted.update(
            {
                "file": _project_relative(path),
                "source_url": item.get("source_url"),
                "source_sha256": item.get("sha256"),
            }
        )
        records.append(extracted)
    return {
        "schema_version": "hust-curriculum-extraction.v1",
        "source_manifest": str(input_path),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "extracted": sum(str(item.get("status", "")).startswith("extracted") for item in records),
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Trích xuất bảng học phần CTĐT HUST dạng hp-table.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = extract_manifest(args.input)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Đã trích xuất {result['extracted']}/{result['count']} nguồn vào {args.output}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
