#!/usr/bin/env python3
"""Discover the official curriculum source linked from every HUST program page.

The admissions catalogue contains one detail page per program.  The detail
page usually links to a faculty page or a PDF/XLSX containing the curriculum.
Those sources are heterogeneous, so this script records provenance and a
small amount of availability metadata without pretending to parse them into a
validated curriculum yet.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse


DATA_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = DATA_DIR / "raw" / "hust_undergraduate_programs.json"
DEFAULT_OUTPUT = DATA_DIR / "raw" / "hust_program_curriculum_sources.json"
DEFAULT_TIMEOUT = 30

# The admissions catalogue still contains links to faculty websites that were
# retired during their 2025/2026 migrations.  Keep explicit, reviewed
# replacements here so a fresh discovery run remains reproducible instead of
# repeatedly recording known 404/DNS failures.  Every replacement is an
# official HUST faculty page and was checked on 2026-09-16.
OFFICIAL_SOURCE_OVERRIDES = {
    "BF-E12": "https://scls.hust.edu.vn/vi/dao-tao/ky-thuat-thuc-pham-elitech/",
    "BF1": "https://scls.hust.edu.vn/vi/dao-tao/ky-thuat-sinh-hoc/",
    "BF2": "https://scls.hust.edu.vn/vi/dao-tao/ky-thuat-thuc-pham/",
    "CH1": "https://scls.hust.edu.vn/vi/dao-tao/ky-thuat-hoa-hoc/",
    "ED2": "https://fed.hust.edu.vn/vi/dao-tao/dai-hoc/chuong-trinh-dt-cong-nghe-giao-duc-178281.html",
    "EE-E18": "https://seee.hust.edu.vn/vi/dao-tao/ee-e18/",
    "EE-E8": "https://seee.hust.edu.vn/vi/dao-tao/ee-e8/",
    "EE-EP": "https://seee.hust.edu.vn/vi/dao-tao/ee-ep/",
    "EE1": "https://seee.hust.edu.vn/vi/dao-tao/ee1/",
    "EE2": "https://seee.hust.edu.vn/vi/dao-tao/ee2/",
    "ET-E5": "https://seee.hust.edu.vn/vi/dao-tao/et-e5/",
    "ET2": "https://seee.hust.edu.vn/vi/dao-tao/et2/",
    "MS-E3": "https://smse.hust.edu.vn/vi/dao-tao/dao-tao-dai-hoc/chuong-trinh-khoa-hoc-va-ky-thuat-vat-lieu-cttt-5.html",
    "MS1": "https://smse.hust.edu.vn/vi/dao-tao/dao-tao-dai-hoc/chuong-trinh-ky-thuat-vat-lieu-4.html",
    "MS5": "https://smse.hust.edu.vn/vi/dao-tao/dao-tao-dai-hoc/chuong-trinh-ky-thuat-in-6.html",
}

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/140.0 Safari/537.36"
    )
}


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<script\b.*?</script\s*>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style\s*>", " ", value, flags=re.I | re.S)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def _is_external(href: str, detail_url: str) -> bool:
    if not href or href.startswith(("#", "javascript:", "mailto:")):
        return False
    absolute = urljoin(detail_url, html.unescape(href).strip())
    detail_host = (urlparse(detail_url).hostname or "").lower()
    source_host = (urlparse(absolute).hostname or "").lower()
    return bool(source_host) and source_host != detail_host


def extract_curriculum_link(detail_html: str, detail_url: str) -> str | None:
    """Return the first external link in the detail page's curriculum tab."""

    section_match = re.search(
        r'<section\b[^>]*id=["\']tab_2["\'][^>]*>.*?</section>',
        detail_html,
        flags=re.I | re.S,
    )
    fragment = section_match.group(0) if section_match else detail_html
    candidates: list[tuple[int, str]] = []
    for anchor in re.finditer(
        r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a\s*>',
        fragment,
        flags=re.I | re.S,
    ):
        href = urljoin(detail_url, html.unescape(anchor.group(1)).strip())
        if not _is_external(href, detail_url):
            continue
        text = _clean_text(anchor.group(2)).casefold()
        # “Xem tại đây” is the canonical curriculum link on current pages;
        # prefer it over incidental links in the same section.
        priority = 0 if any(token in text for token in ("xem", "chi tiết", "curriculum")) else 1
        candidates.append((priority, href))
    return min(candidates)[1] if candidates else None


def _source_kind(url: str, content_type: str = "") -> str:
    path = urlparse(url).path.casefold()
    content_type = content_type.casefold()
    if path.endswith(".pdf") or "application/pdf" in content_type:
        return "pdf"
    if path.endswith((".xls", ".xlsx")) or "spreadsheet" in content_type or "excel" in content_type:
        return "spreadsheet"
    if "text/html" in content_type or path.endswith((".htm", ".html", "/")):
        return "html"
    return "unknown"


def _course_code_count(text: str) -> int:
    codes = re.findall(r"\b[A-Z]{2,4}\d{4}[A-Z]?\b", text.upper())
    return len(set(codes))


def _inspect_source(response) -> dict:
    content_type = response.headers.get("content-type", "")
    result = {
        "http_status": response.status_code,
        "final_url": response.url,
        "content_type": content_type,
        "source_kind": _source_kind(response.url, content_type),
    }
    if "text/html" in content_type:
        body = response.text
        result.update(
            {
                "html_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                "table_count": len(re.findall(r"<table\b", body, flags=re.I)),
                "course_code_count": _course_code_count(body),
            }
        )
    else:
        result.update({"html_sha256": None, "table_count": None, "course_code_count": None})
    return result


def fetch(url: str, *, verify: bool, timeout: int):
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Thiếu requests; hãy chạy trong venv backend hoặc cài requests.") from exc
    return requests.get(
        url,
        timeout=timeout,
        verify=verify,
        allow_redirects=True,
        headers=REQUEST_HEADERS,
    )


def discover(input_path: Path, *, insecure: bool, timeout: int) -> dict:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Thiếu requests; hãy chạy trong venv backend hoặc cài requests.") from exc

    if insecure:
        # The HUST sites are sometimes served through a local/proxy CA.  Keep
        # the opt-in flag usable without flooding the progress output.
        try:
            import urllib3

            urllib3.disable_warnings()
        except ImportError:
            pass

    catalogue = json.loads(input_path.read_text(encoding="utf-8"))
    programs = catalogue.get("programs", [])
    records: list[dict] = []
    session = requests.Session()
    for index, program in enumerate(programs, 1):
        code = str(program.get("admission_code", "")).upper()
        detail_url = str(program.get("detail_url") or "")
        record = {
            "admission_code": code,
            "name": program.get("name", ""),
            "detail_url": detail_url,
            "curriculum_source_url": None,
            "detail_http_status": None,
            "error": None,
        }
        try:
            detail_response = session.get(
                detail_url,
                timeout=timeout,
                verify=not insecure,
                headers=REQUEST_HEADERS,
            )
            record["detail_http_status"] = detail_response.status_code
            detail_response.raise_for_status()
            catalogue_source_url = extract_curriculum_link(detail_response.text, detail_url)
            source_url = OFFICIAL_SOURCE_OVERRIDES.get(code, catalogue_source_url)
            record["curriculum_source_url"] = source_url
            record["catalogue_source_url"] = catalogue_source_url
            record["source_overridden"] = source_url != catalogue_source_url
            if source_url:
                source_response = session.get(
                    source_url,
                    timeout=timeout,
                    verify=not insecure,
                    headers=REQUEST_HEADERS,
                )
                record["source"] = _inspect_source(source_response)
                if source_response.status_code >= 400:
                    record["error"] = (
                        f"HTTPError: {source_response.status_code} "
                        f"for url: {source_response.url}"
                    )
            else:
                record["source"] = None
        except Exception as exc:  # keep the remaining programs discoverable
            record["error"] = f"{type(exc).__name__}: {exc}"
        records.append(record)
        print(f"[{index}/{len(programs)}] {code}: {record['curriculum_source_url'] or 'không tìm thấy liên kết'}")

    linked = sum(bool(item.get("curriculum_source_url")) for item in records)
    available = sum(
        bool(item.get("source"))
        and int(item["source"].get("http_status", 500)) < 400
        for item in records
    )
    return {
        "schema_version": "hust-curriculum-sources.v1",
        "source_catalog": str(input_path),
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "with_source_link": linked,
        "source_fetch_ok": available,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Tìm nguồn CTĐT chính thức cho danh mục ngành HUST.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--insecure", action="store_true", help="Tắt kiểm tra TLS khi môi trường thiếu CA.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()
    try:
        payload = discover(args.input, insecure=args.insecure, timeout=args.timeout)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Đã ghi {payload['with_source_link']}/{payload['count']} nguồn CTĐT vào {args.output}")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
