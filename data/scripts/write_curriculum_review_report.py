"""Publish current curriculum coverage from the actual source and runtime files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def coverage(data_dir=DATA):
    catalog = load(data_dir / "raw/hust_undergraduate_programs.json")["programs"]
    codes = {p["admission_code"] for p in catalog}
    active = [load(p) for p in sorted((data_dir / "processed/curricula").glob("*.json"))]
    active_keys = {(d["program"]["program_code"], str(d["program"]["curriculum_version"])) for d in active}
    approvals = load(data_dir / "processed/curriculum_approvals.json")["approvals"]
    activations = {a.get("source_candidate_id") or a["candidate_id"]: a["candidate_id"].rsplit("-", 1)[-1]
                   for a in approvals if a.get("status") == "approved"}
    records = {}
    for directory in (data_dir / "raw/official_curricula", data_dir / "raw/reviewed_curricula"):
        for path in sorted(directory.glob("*.json")):
            records[path.stem] = (path, load(path))
    rows = []
    for identifier, (path, raw) in sorted(records.items()):
        code = raw["admission_code"]
        available = (code, str(activations.get(identifier) or raw.get("curriculum_version"))) in active_keys
        status = "Đã dùng để rà soát tiến độ" if available else "Đã đưa vào tra cứu"
        reasons = []
        if code not in codes:
            status = "Ngoài danh mục đại học"
            reasons.append("Chương trình sau cử nhân hoặc tuyển chọn riêng; không gán cho mã tuyển sinh đại học.")
        elif not available:
            if raw.get("curriculum_version") is None and not raw.get("applies_to_cohorts"):
                reasons.append("Nguồn chưa xác định phiên bản/khóa áp dụng.")
            if raw.get("total_credits") is None:
                reasons.append("Nguồn chưa có tổng tín chỉ tốt nghiệp đầy đủ.")
            if not reasons:
                reasons.append("Khung/nhóm tín chỉ hoặc thông tin CTT còn khác nhau; giữ số liệu nguồn để tra cứu, không tự cân bằng.")
        rows.append((identifier, path, raw, status, " ".join(reasons)))
    lines = ["# Phạm vi dữ liệu CTĐT đang có trong ứng dụng", "",
             "Sinh lại bằng `python data/scripts/write_curriculum_review_report.py`. Đây là trạng thái xử lý dữ liệu, không phải danh sách việc giao cho người dùng review.", "",
             f"- {len(catalog)} ngành đại học đều có mục tra cứu tài liệu đã thu thập qua giao diện và `/api/programs/{{code}}/curricula`.",
             f"- {len(active)} phiên bản CTĐT đã chuẩn hóa để rà soát tiến độ theo khóa.",
             "- Nguồn thiếu khung đầy đủ vẫn xem được học phần và ghi chú; không bị bỏ ngoài ứng dụng.",
             "- Môn chưa có điều kiện trong snapshot CTT không được tự kết luận đủ điều kiện đăng ký.", "",
             "| Tài liệu | Sử dụng hiện tại | Phạm vi còn thiếu trong nguồn |", "|---|---|---|"]
    for identifier, path, raw, status, reason in rows:
        link = "../" + path.relative_to(data_dir).as_posix()
        lines.append(f"| [{identifier}]({link}) | {status} | {reason or 'Theo khung chuẩn hóa và khóa áp dụng trong dữ liệu.'} |")
    lines += ["", "## Các khung đã dùng cho tiến độ", "",
              "| Mã | Phiên bản | Tổng TC | Học phần | Khóa áp dụng |", "|---|---|---:|---:|---|"]
    for d in active:
        p = d["program"]
        cohorts = ", ".join(d.get("applies_to_cohorts") or []) or f"K{int(p['curriculum_version']) - 1955}"
        lines.append(f"| {p['program_code']} | {p['curriculum_version']} | {p['total_required_credits']} | {len(d['courses'])} | {cohorts} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DATA / "reports/curriculum_candidates_review.md")
    args = parser.parse_args()
    report = coverage()
    args.output.write_text(report, encoding="utf-8", newline="\n")
    # Both old entry points now describe the same current data, not conflicting snapshots.
    (DATA / "reports/official_curricula_import.md").write_text(report, encoding="utf-8", newline="\n")
    print("Đã cập nhật phạm vi dữ liệu từ các tệp nguồn và CTĐT đang chạy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
