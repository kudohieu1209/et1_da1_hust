"""So sánh hai báo cáo đánh giá trên phần câu hỏi chung.

Chỉ giữ các câu có cùng ``id`` và cùng nội dung câu hỏi ở cả hai báo cáo, để
so sánh trước/sau trên đúng một tập câu hỏi.

    python eval/compare_reports.py eval/reports/baseline.json eval/reports/final.json
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from metrics import summarize  # noqa: E402

METRICS = [
    ("intent_accuracy", "Phân loại ý định"),
    ("entity_accuracy", "Trích xuất mã học phần"),
    ("recall_at_k", "Recall@4 (có bằng chứng trong top-4)"),
    ("mrr", "MRR@4"),
    ("answer_accuracy", "Câu trả lời chứa ý chính"),
]


def common_results(before: List[Dict[str, Any]], after: List[Dict[str, Any]]
                   ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    after_by_id = {item["id"]: item for item in after}
    kept_before, kept_after = [], []
    for item in before:
        match = after_by_id.get(item["id"])
        if match is not None and match["question"] == item["question"]:
            kept_before.append(item)
            kept_after.append(match)
    return kept_before, kept_after


def _fmt(value: Optional[float]) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args(argv)

    before = json.loads(args.before.read_text(encoding="utf-8"))
    after = json.loads(args.after.read_text(encoding="utf-8"))
    k = after.get("k", 4)
    kept_before, kept_after = common_results(before["results"], after["results"])
    summary_before = summarize(kept_before, k)["overall"]
    summary_after = summarize(kept_after, k)["overall"]

    print(f"Số câu chung (cùng id và nội dung): {len(kept_before)} / {len(before['results'])}")
    print(f"| Chỉ số | {args.before.stem} | {args.after.stem} |")
    print("|---|---:|---:|")
    for key, label in METRICS:
        print(f"| {label} | {_fmt(summary_before[key])} | {_fmt(summary_after[key])} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
