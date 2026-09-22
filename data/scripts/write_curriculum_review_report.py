#!/usr/bin/env python3
"""Render the review-only curriculum candidate queue as Markdown."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = DATA_DIR / "raw" / "hust_curriculum_candidates.json"
DEFAULT_OUTPUT = DATA_DIR / "reports" / "curriculum_candidates_review.md"
DEFAULT_CURRICULA = DATA_DIR / "processed" / "curricula"


def _value(value):
    return "—" if value in (None, "") else str(value)


def render(payload: dict, curricula_dir: Path = DEFAULT_CURRICULA) -> str:
    records = payload.get("records", [])
    approved = [
        record for record in records
        if (record.get("activation") or {}).get("status") == "approved"
    ]
    loaded_keys = []
    if curricula_dir.exists():
        for path in sorted(curricula_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                program = data.get("program", {})
                if program.get("program_code") and program.get("curriculum_version"):
                    loaded_keys.append(
                        f"{program['program_code']}-{program['curriculum_version']}"
                    )
            except (OSError, json.JSONDecodeError):
                continue
    lines = [
        "# Hàng đợi kiểm duyệt CTĐT",
        "",
        "> Báo cáo sinh tự động từ candidate công khai. Candidate chỉ được bật sau khi có bản ghi phê duyệt và dataset chuẩn hóa tương ứng.",
        "",
        f"- Sinh lúc (UTC): `{datetime.now(timezone.utc).isoformat()}`",
        f"- Tổng candidate: **{len(records)}**",
        f"- Candidate được nạp Rule Engine: **{payload.get('rule_engine_loaded', 0)}**",
        f"- Candidate đã phê duyệt: **{len(approved)}**",
        f"- Dataset CTĐT đang chạy: {', '.join(f'`{key}`' for key in loaded_keys) or '—'}",
        "",
        "| Candidate | Parser | Phiên bản | HP | Nhóm | Mô-đun | Tổng TC | Trạng thái | Vấn đề cần rà |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for record in records:
        quality = record.get("quality", {})
        reasons = ", ".join(f"`{reason}`" for reason in quality.get("review_reasons", [])) or "—"
        lines.append(
            "| {candidate} | {parser} | {version} | {courses} | {groups} | {modules} | {total} | {status} | {reasons} |".format(
                candidate=record.get("candidate_id", record.get("admission_code", "?")),
                parser=record.get("parser", "?"),
                version=_value(record.get("curriculum_version")),
                courses=_value(quality.get("course_count")),
                groups=_value(quality.get("group_count")),
                modules=_value(quality.get("module_count")),
                total=_value(quality.get("page_total_credits")),
                status=(record.get("activation") or {}).get("status", "needs_review"),
                reasons=reasons,
            )
        )
    lines.extend(["", "## Chi tiết tự động", ""])
    for record in records:
        quality = record.get("quality", {})
        lines.append(f"### `{record.get('candidate_id', record.get('admission_code', '?'))}`")
        lines.append("")
        lines.append(f"- Nguồn: {_value(record.get('source_url'))}")
        lines.append(f"- Tệp: `{_value(record.get('file'))}`")
        lines.append(f"- Mã môn không có trong CTT: {_value(', '.join(quality.get('course_codes_missing_from_ctt', [])))}")
        lines.append(f"- Nhóm thiếu ngưỡng tín chỉ bắt buộc: {_value(', '.join(quality.get('required_credit_thresholds_missing', [])))}")
        lines.append(f"- Chuỗi điều kiện CTT có nội dung: {_value(quality.get('ctt_conditions_nonempty'))}; các dòng rỗng được hiểu là không có học phần trước.")
        lines.append(f"- Công thức một mô-đun suy ra: {_value(quality.get('derived_one_module_total'))}; tổng trang công bố: {_value(quality.get('page_total_credits'))}")
        status = (record.get("activation") or {}).get("status", "needs_review")
        if status == "approved":
            activation = record.get("activation") or {}
            lines.append(
                f"- Phê duyệt: {activation.get('approved_by', '—')} — {activation.get('approved_at', '—')}"
            )
        else:
            lines.append(f"- Lý do giữ lại: {', '.join(quality.get('review_reasons', [])) or '—'}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(payload), encoding="utf-8")
    print(f"Đã ghi báo cáo kiểm duyệt {len(payload.get('records', []))} candidate vào {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
