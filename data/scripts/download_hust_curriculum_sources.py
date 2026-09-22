#!/usr/bin/env python3
"""Download public curriculum-source snapshots discovered for HUST programs.

This step deliberately stores raw responses only.  It does not parse or mark
any program as supported; parsing and validation happen in a later pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse


DATA_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = DATA_DIR / "raw" / "hust_program_curriculum_sources.json"
DEFAULT_OUTPUT = DATA_DIR / "raw" / "hust_program_curriculum_downloads.json"
DEFAULT_DIR = DATA_DIR / "raw" / "program_sources"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/140.0 Safari/537.36"
    )
}


def _kind_and_extension(url: str, content_type: str) -> tuple[str, str]:
    path = urlparse(url).path.casefold()
    mime = content_type.casefold()
    if path.endswith(".pdf") or "application/pdf" in mime:
        return "pdf", "pdf"
    if path.endswith((".xls", ".xlsx")) or "spreadsheet" in mime or "excel" in mime:
        return "spreadsheet", "xlsx" if path.endswith(".xlsx") else "xls"
    if "text/html" in mime or path.endswith((".htm", ".html", "/")):
        return "html", "html"
    return "unknown", "bin"


def _safe_code(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip().upper())
    return value or "UNKNOWN"


def _write_if_changed(target: Path, content: bytes, digest: str, *, refresh: bool) -> None:
    """Keep the manifest hash and on-disk snapshot in sync."""
    if refresh or not target.exists():
        target.write_bytes(content)
        return
    current = hashlib.sha256(target.read_bytes()).hexdigest()
    if current != digest:
        target.write_bytes(content)


def _attachment_links(document: str, base_url: str) -> list[str]:
    """Return likely curriculum attachments linked by an HTML source page."""
    candidates: list[tuple[int, str]] = []
    for href in re.findall(r'''(?:href|src)\s*=\s*["']([^"']+)["']''', document, flags=re.I):
        absolute = urljoin(base_url, href.strip())
        path = urlparse(absolute).path.casefold()
        if not path.endswith((".pdf", ".xls", ".xlsx", ".doc", ".docx", ".csv")):
            continue
        text = absolute.casefold()
        priority = 0 if any(token in text for token in ("ctdt", "chuong-trinh", "curriculum", "program", "dao-tao")) else 1
        candidates.append((priority, absolute))
    unique: list[str] = []
    for _priority, url in sorted(candidates):
        if url not in unique:
            unique.append(url)
    return unique


def download(
    input_path: Path,
    output_path: Path,
    output_dir: Path,
    *,
    insecure: bool,
    timeout: int,
    refresh: bool,
    follow_attachments: bool = False,
    selected_codes: set[str] | None = None,
) -> dict:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Thiếu requests; hãy chạy trong venv backend hoặc cài requests.") from exc

    if insecure:
        try:
            import urllib3

            urllib3.disable_warnings()
        except ImportError:
            pass

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    all_records = payload.get("records", [])
    records = (
        [
            item
            for item in all_records
            if str(item.get("admission_code", "")).upper() in selected_codes
        ]
        if selected_codes
        else all_records
    )
    previous_by_code: dict[str, dict] = {}
    if output_path.exists():
        try:
            previous_payload = json.loads(output_path.read_text(encoding="utf-8"))
            previous_by_code = {
                str(item.get("admission_code", "")).upper(): item
                for item in previous_payload.get("records", [])
            }
        except (OSError, ValueError):
            previous_by_code = {}
    output_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    results: list[dict] = []

    for index, item in enumerate(records, 1):
        code = str(item.get("admission_code", "")).upper()
        source_url = str(item.get("curriculum_source_url") or "")
        result = {
            "admission_code": code,
            "name": item.get("name", ""),
            "source_url": source_url,
            "status": "not_available",
            "file": None,
            "sha256": None,
            "bytes": None,
            "content_type": None,
            "final_url": None,
            "fetched_at": None,
            "error": None,
            "attachments": [],
        }
        if not source_url:
            results.append(result)
            print(f"[{index}/{len(records)}] {code}: không có URL nguồn")
            continue

        try:
            response = session.get(
                source_url,
                timeout=timeout,
                verify=not insecure,
                allow_redirects=True,
                headers=REQUEST_HEADERS,
            )
            result["content_type"] = response.headers.get("content-type", "")
            result["final_url"] = response.url
            kind, extension = _kind_and_extension(response.url, result["content_type"])
            if response.status_code >= 400:
                result["status"] = "http_error"
                result["error"] = f"HTTP {response.status_code}"
            elif not response.content:
                result["status"] = "empty"
                result["error"] = "Phản hồi rỗng"
            else:
                digest = hashlib.sha256(response.content).hexdigest()
                target = output_dir / f"{_safe_code(code)}.{extension}"
                _write_if_changed(target, response.content, digest, refresh=refresh)
                result.update(
                    {
                        "status": "downloaded" if kind != "unknown" else "downloaded_unknown",
                        "file": str(target),
                        "sha256": digest,
                        "bytes": len(response.content),
                    }
                )
                if follow_attachments and kind == "html":
                    for attachment_index, attachment_url in enumerate(
                        _attachment_links(response.text, response.url)[:5], 1
                    ):
                        attachment = {
                            "url": attachment_url,
                            "status": "not_available",
                            "file": None,
                            "sha256": None,
                            "bytes": None,
                            "content_type": None,
                            "final_url": None,
                            "error": None,
                        }
                        try:
                            attachment_response = session.get(
                                attachment_url,
                                timeout=timeout,
                                verify=not insecure,
                                allow_redirects=True,
                                headers=REQUEST_HEADERS,
                            )
                            attachment["content_type"] = attachment_response.headers.get("content-type", "")
                            attachment["final_url"] = attachment_response.url
                            attachment_kind, attachment_extension = _kind_and_extension(
                                attachment_response.url, attachment["content_type"]
                            )
                            if attachment_response.status_code >= 400:
                                attachment["status"] = "http_error"
                                attachment["error"] = f"HTTP {attachment_response.status_code}"
                            elif not attachment_response.content:
                                attachment["status"] = "empty"
                                attachment["error"] = "Phản hồi rỗng"
                            else:
                                attachment_target = output_dir / (
                                    f"{_safe_code(code)}__attachment_{attachment_index}.{attachment_extension}"
                                )
                                attachment_digest = hashlib.sha256(attachment_response.content).hexdigest()
                                _write_if_changed(
                                    attachment_target,
                                    attachment_response.content,
                                    attachment_digest,
                                    refresh=refresh,
                                )
                                attachment.update(
                                    {
                                        "status": "downloaded" if attachment_kind != "unknown" else "downloaded_unknown",
                                        "file": str(attachment_target),
                                        "sha256": attachment_digest,
                                        "bytes": len(attachment_response.content),
                                    }
                                )
                        except Exception as exc:  # keep the primary snapshot usable
                            attachment["status"] = "network_error"
                            attachment["error"] = f"{type(exc).__name__}: {exc}"
                        result["attachments"].append(attachment)
            result["fetched_at"] = datetime.now(timezone.utc).isoformat()
            print(f"[{index}/{len(records)}] {code}: {result['status']} ({result['content_type'] or 'unknown'})")
        except Exception as exc:  # keep processing the remaining programs
            result["status"] = "network_error"
            result["error"] = f"{type(exc).__name__}: {exc}"
            result["fetched_at"] = datetime.now(timezone.utc).isoformat()
            print(f"[{index}/{len(records)}] {code}: {result['status']}")
        previous = previous_by_code.get(code)
        if (
            not result["status"].startswith("downloaded")
            and previous
            and str(previous.get("status", "")).startswith("downloaded")
            and previous.get("source_url") == source_url
        ):
            preserved = dict(previous)
            preserved["last_refresh_attempted_at"] = result.get("fetched_at")
            preserved["last_refresh_error"] = result.get("error") or result.get("status")
            result = preserved
            print(f"[{index}/{len(records)}] {code}: giá»¯ snapshot cÅ© sau lá»—i lÃ m má»›i")
        results.append(result)

    if selected_codes:
        updated_by_code = {item["admission_code"]: item for item in results}
        results = [
            updated_by_code.get(code) or previous_by_code.get(code) or {
                "admission_code": code,
                "name": item.get("name", ""),
                "source_url": item.get("curriculum_source_url"),
                "status": "not_refreshed",
                "file": None,
                "sha256": None,
                "bytes": None,
                "content_type": None,
                "final_url": None,
                "fetched_at": None,
                "error": None,
                "attachments": [],
            }
            for item in all_records
            for code in [str(item.get("admission_code", "")).upper()]
        ]

    downloaded = sum(item["status"].startswith("downloaded") for item in results)
    attachments_downloaded = sum(
        attachment.get("status", "").startswith("downloaded")
        for item in results
        for attachment in item.get("attachments", [])
    )
    return {
        "schema_version": "hust-curriculum-downloads.v1",
        "source_manifest": str(input_path),
        "download_dir": str(output_dir),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "downloaded": downloaded,
        "attachments_downloaded": attachments_downloaded,
        "records": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Lưu snapshot nguồn CTĐT công khai của các ngành HUST.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--insecure", action="store_true", help="Tắt kiểm tra TLS khi môi trường thiếu CA.")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--refresh", action="store_true", help="Ghi lại tệp đã tồn tại.")
    parser.add_argument(
        "--follow-attachments",
        action="store_true",
        help="Tìm và tải tối đa 5 liên kết PDF/XLSX/DOCX trong mỗi trang HTML.",
    )
    parser.add_argument(
        "--codes",
        help="Chá»‰ lÃ m má»›i danh sÃ¡ch mÃ£ tuyá»ƒn sinh phÃ¢n tÃ¡ch bá»Ÿi dáº¥u pháº©y; giá»¯ nguyÃªn báº£n ghi khÃ¡c.",
    )
    args = parser.parse_args()
    try:
        result = download(
            args.input,
            args.output,
            args.output_dir,
            insecure=args.insecure,
            timeout=args.timeout,
            refresh=args.refresh,
            follow_attachments=args.follow_attachments,
            selected_codes={code.strip().upper() for code in args.codes.split(",") if code.strip()}
            if args.codes
            else None,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"Đã lưu {result['downloaded']}/{result['count']} snapshot và "
            f"{result['attachments_downloaded']} tệp đính kèm vào {args.output_dir}"
        )
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
