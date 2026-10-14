"""Chạy bộ đánh giá định lượng cho chatbot HUST Course Advisor.

Mặc định tắt LLM để kết quả tất định, không tốn quota Gemini: chỉ số đo
router ý định, trích xuất mã môn, truy xuất RAG và câu trả lời trích dẫn.

    python project/eval/run_eval.py --label baseline
    python project/eval/run_eval.py --check      # thoát mã 1 nếu thụt lùi
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

EVAL_DIR = Path(__file__).resolve().parent
BACKEND_DIR = EVAL_DIR.parent / "backend"
DEFAULT_GOLDEN = EVAL_DIR / "golden_questions.jsonl"
DEFAULT_THRESHOLDS = EVAL_DIR / "thresholds.json"
DEFAULT_REPORT_DIR = EVAL_DIR / "reports"
DEFAULT_K = 4  # Bằng k mà ChatbotService truyền cho RAGEngine.

sys.path.insert(0, str(EVAL_DIR))

from golden_set import load_golden_set  # noqa: E402
from metrics import contains_all, first_relevant_rank, summarize  # noqa: E402

METRIC_LABELS = {
    "intent_accuracy": "Phân loại ý định",
    "entity_accuracy": "Trích xuất mã môn",
    "recall_at_k": "Recall@k truy xuất",
    "mrr": "MRR@k truy xuất",
    "answer_accuracy": "Câu trả lời chứa ý chính",
}


def _load_backend(use_llm: bool):
    # Hồ sơ demo đọc từ kho cục bộ để kết quả tất định, không phụ thuộc Atlas.
    os.environ["MONGODB_URI"] = ""
    if not use_llm:
        # load_dotenv không ghi đè biến đã tồn tại, nên chuỗi rỗng ở đây
        # buộc GeminiService chạy chế độ trích dẫn cục bộ.
        os.environ["GEMINI_API_KEY"] = ""
        os.environ["OPENAI_API_KEY"] = ""
    sys.path.insert(0, str(BACKEND_DIR))
    from app.rag.vector_store import vector_store
    from app.services.chatbot_service import chatbot_service

    return chatbot_service, vector_store


def evaluate_item(item: Dict[str, Any], chatbot, vector_store, k: int) -> Dict[str, Any]:
    question = item["question"]
    started = time.perf_counter()
    response = chatbot.process_message(question)
    latency_ms = (time.perf_counter() - started) * 1000

    evidence = item.get("evidence") or []
    rank: Optional[int] = None
    if evidence:
        rank = first_relevant_rank(vector_store.similarity_search(question, k=k), evidence)

    expected_codes = item.get("expected_codes")
    detected_codes = chatbot._detect_courses(question) if expected_codes else []
    key_points = item.get("answer_contains") or []

    return {
        "id": item["id"],
        "category": item["category"],
        "question": question,
        "expected_intent": item["expected_intent"],
        "actual_intent": response.get("intent"),
        "intent_ok": response.get("intent") == item["expected_intent"],
        "codes_ok": set(detected_codes) == set(expected_codes) if expected_codes else None,
        "detected_codes": detected_codes,
        "retrieval_scored": bool(evidence),
        "rank": rank,
        "answer_ok": contains_all(response.get("reply", ""), key_points) if key_points else None,
        "missing_points": [
            point for point in key_points if not contains_all(response.get("reply", ""), [point])
        ],
        "latency_ms": round(latency_ms, 1),
        "model_used": response.get("model_used"),
    }


def _fmt(value: Optional[float]) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def render_markdown(label: str, summary: Dict[str, Any], results: List[Dict[str, Any]], k: int) -> str:
    latencies = sorted(item["latency_ms"] for item in results)
    p50 = latencies[len(latencies) // 2] if latencies else 0
    lines = [
        f"# Kết quả đánh giá: {label}",
        "",
        f"- Thời điểm: {datetime.now().isoformat(timespec='seconds')}",
        f"- Số câu hỏi: {len(results)}; k = {k}; độ trễ trung vị: {p50:.0f} ms",
        "",
        "| Nhóm | Số câu | " + " | ".join(METRIC_LABELS.values()) + " |",
        "|---|---:|" + "---:|" * len(METRIC_LABELS),
    ]
    rows = [("**Tổng**", summary["overall"])] + list(summary["by_category"].items())
    for name, scores in rows:
        cells = " | ".join(_fmt(scores[key]) for key in METRIC_LABELS)
        lines.append(f"| {name} | {scores['count']} | {cells} |")

    failures = [
        item for item in results
        if item["intent_ok"] is False
        or item["codes_ok"] is False
        or item["answer_ok"] is False
        or (item["retrieval_scored"] and not item["rank"])
    ]
    lines += ["", f"## Câu hỏi chưa đạt ({len(failures)})", ""]
    for item in failures:
        problems = []
        if not item["intent_ok"]:
            problems.append(f"ý định `{item['actual_intent']}` ≠ `{item['expected_intent']}`")
        if item["codes_ok"] is False:
            problems.append(f"mã môn {item['detected_codes']}")
        if item["retrieval_scored"] and not item["rank"]:
            problems.append(f"không truy xuất được bằng chứng trong top-{k}")
        if item["answer_ok"] is False:
            problems.append(f"thiếu ý {item['missing_points']}")
        lines.append(f"- `{item['id']}` {item['question']} — {'; '.join(problems)}")
    return "\n".join(lines) + "\n"


def check_thresholds(summary: Dict[str, Any], thresholds: Dict[str, float]) -> List[str]:
    regressions = []
    for metric, minimum in thresholds.items():
        actual = summary["overall"].get(metric)
        if actual is None or actual + 1e-9 < minimum:
            regressions.append(f"{METRIC_LABELS.get(metric, metric)}: {_fmt(actual)} < {_fmt(minimum)}")
    return regressions


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--label", default="latest", help="Tên báo cáo trong eval/reports/")
    parser.add_argument("--use-llm", action="store_true", help="Gọi Gemini thật (tốn quota, không tất định)")
    parser.add_argument("--check", action="store_true", help="So với thresholds.json, thoát mã 1 nếu thụt lùi")
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    args = parser.parse_args(argv)

    items = load_golden_set(args.golden)
    chatbot, vector_store = _load_backend(args.use_llm)
    results = [evaluate_item(item, chatbot, vector_store, args.k) for item in items]
    summary = summarize(results, k=args.k)

    DEFAULT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (DEFAULT_REPORT_DIR / f"{args.label}.json").write_text(
        json.dumps({"k": args.k, "summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report = render_markdown(args.label, summary, results, args.k)
    (DEFAULT_REPORT_DIR / f"{args.label}.md").write_text(report, encoding="utf-8")
    print(report)

    if args.check:
        thresholds = json.loads(args.thresholds.read_text(encoding="utf-8"))
        regressions = check_thresholds(summary, thresholds)
        if regressions:
            print("THỤT LÙI so với ngưỡng:\n- " + "\n- ".join(regressions), file=sys.stderr)
            return 1
        print("Đạt mọi ngưỡng trong", args.thresholds.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
