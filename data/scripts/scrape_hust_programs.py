#!/usr/bin/env python3
"""Create a versioned catalog of HUST undergraduate programs.

This is intentionally separate from curriculum data.  The admissions page
contains the official program/admission codes and basic metadata, while the
course list and CTĐT files contain the subjects and registration rules.  A
program is therefore marked as ``curriculum_supported`` by the API only when
we have a matching, validated curriculum dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin


PROGRAMS_URL = "https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc"
DATA_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = DATA_DIR / "raw" / "hust_undergraduate_programs.json"
ITEM_RE = re.compile(r'<div class="accordion-item"[^>]*data-slug="([^"]+)"[^>]*>', re.I)


def clean_text(fragment: str | None) -> str:
    if not fragment:
        return ""
    fragment = re.sub(r"<script\b.*?</script\s*>", " ", fragment, flags=re.I | re.S)
    fragment = re.sub(r"<style\b.*?</style\s*>", " ", fragment, flags=re.I | re.S)
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_int(value: str | None) -> int | None:
    value = clean_text(value).replace(".", "").replace(",", "")
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def parse_programs(html_text: str, base_url: str = PROGRAMS_URL) -> list[dict]:
    starts = list(ITEM_RE.finditer(html_text))
    if not starts:
        raise ValueError("Không tìm thấy accordion chương trình trên trang HUST.")

    programs: list[dict] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(html_text)
        body = html_text[start.end() : end]

        header_match = re.search(r"<h3[^>]*>.*?<a[^>]*>(.*?)</a\s*>", body, re.I | re.S)
        header = clean_text(header_match.group(1)) if header_match else ""
        parsed_header = re.match(r"(?P<order>\d+)\s*-\s*\(\s*(?P<code>[^)]*?)\s*\)\s*(?P<name>.*)", header)
        if not parsed_header:
            raise ValueError(f"Không phân tích được tiêu đề chương trình thứ {index + 1}: {header!r}")

        detail_match = re.search(r'<a[^>]*class="[^"]*read-more[^"]*"[^>]*href="([^"]+)"', body, re.I)
        language_match = re.search(r"Ngôn ngữ đào tạo:\s*<strong>(.*?)</strong>", body, re.I | re.S)
        admission_code_match = re.search(r"Mã xét tuyển:\s*<strong>(.*?)</strong>", body, re.I | re.S)
        quota_match = re.search(r"Chỉ tiêu tuyển sinh:\s*<strong>(.*?)</strong>", body, re.I | re.S)
        faculty_match = re.search(r"fa-map-marker-alt[^>]*></i>\s*(.*?)</p>", body, re.I | re.S)
        year_match = re.search(r'<option[^>]*value="(20\d{2})"[^>]*selected', body, re.I)

        combinations: list[dict[str, str]] = []
        seen_combinations: set[str] = set()
        for combo in re.finditer(
            r'<a[^>]*class="[^"]*ds-tooltip[^"]*"[^>]*>\s*([A-Za-z0-9]+)\s*<span>(.*?)</span>',
            body,
            re.I | re.S,
        ):
            code = combo.group(1).upper()
            if code in seen_combinations:
                continue
            seen_combinations.add(code)
            description = clean_text(combo.group(2))
            description = re.sub(rf"^{re.escape(code)}\s*:\s*", "", description, flags=re.I)
            combinations.append({"code": code, "description": description})

        admission_code = clean_text(admission_code_match.group(1) if admission_code_match else "")
        programs.append(
            {
                "source_order": int(parsed_header.group("order")),
                "slug": start.group(1),
                "admission_code": admission_code or clean_text(parsed_header.group("code")),
                "name": clean_text(parsed_header.group("name")),
                "language": clean_text(language_match.group(1) if language_match else ""),
                "faculty": clean_text(faculty_match.group(1) if faculty_match else ""),
                "admissions_year": int(year_match.group(1)) if year_match else None,
                "admission_quota": parse_int(quota_match.group(1) if quota_match else ""),
                "admission_combinations": combinations,
                "detail_url": urljoin(base_url, detail_match.group(1)) if detail_match else None,
            }
        )
    return programs


def fetch(url: str, insecure: bool = False) -> str:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Thiếu requests; hãy chạy trong venv backend hoặc cài requests.") from exc

    response = requests.get(url, timeout=60, verify=not insecure)
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response.text


def write_catalog(path: Path, html_text: str, url: str) -> None:
    programs = parse_programs(html_text, url)
    payload = {
        "schema_version": "hust-undergraduate-programs.v1",
        "source": {
            "url": url,
            "page_title": clean_text(re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S).group(1))
            if re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
            else "",
            "accessed_at": datetime.now(timezone.utc).isoformat(),
            "html_sha256": hashlib.sha256(html_text.encode("utf-8")).hexdigest(),
        },
        "count": len(programs),
        "programs": programs,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã ghi {len(programs)} chương trình vào {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Lấy danh mục ngành/chương trình đại học HUST.")
    parser.add_argument("--url", default=PROGRAMS_URL)
    parser.add_argument("--input-html", type=Path, help="Dùng HTML đã lưu, không gọi mạng.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--insecure", action="store_true", help="Tắt kiểm tra TLS khi môi trường thiếu CA (chỉ dùng khi cần).")
    args = parser.parse_args()
    try:
        html_text = args.input_html.read_text(encoding="utf-8", errors="replace") if args.input_html else fetch(args.url, args.insecure)
        write_catalog(args.output, html_text, args.url)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
