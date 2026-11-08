"""Đọc và kiểm tra cấu trúc bộ câu hỏi chuẩn (JSONL, mỗi dòng một câu)."""
import json
from pathlib import Path
from typing import Any, Dict, List

KNOWN_INTENTS = {
    "RAG_HUST_KNOWLEDGE",
    "COURSE_ELIGIBILITY_CHECK",
    "COURSE_RECOMMENDATION",
    "DEGREE_AUDIT",
    "IMPACT_SIMULATION",
    "GENERAL_GREETING",
}
REQUIRED_FIELDS = ("id", "category", "question", "expected_intent")


def load_golden_set(path: Path) -> List[Dict[str, Any]]:
    items = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            item = json.loads(line)
            missing = [field for field in REQUIRED_FIELDS if not item.get(field)]
            if missing:
                raise ValueError(f"Dòng {line_number}: thiếu trường {', '.join(missing)}")
            items.append(item)
    return items
