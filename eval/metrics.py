"""Hàm chấm điểm thuần cho bộ đánh giá chatbot (không phụ thuộc backend).

Tách khỏi ``run_eval.py`` để kiểm thử được mà không cần ChromaDB hay Gemini.
"""
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional


def normalize_text(text: str) -> str:
    """Đưa về NFC, chữ thường, gộp khoảng trắng.

    Văn bản trích từ PDF bị ngắt dòng giữa câu ("từ đầu khóa\\n lớn hơn 24"),
    nên so khớp cụm bằng chứng phải bỏ qua khác biệt khoảng trắng.
    """
    composed = unicodedata.normalize("NFC", text or "").lower()
    return re.sub(r"\s+", " ", composed.replace("**", "")).strip()


def _chunk_matches(chunk: Dict[str, Any], evidence: Dict[str, str]) -> bool:
    metadata = chunk.get("metadata") or {}
    if metadata.get("file_name") != evidence["file"]:
        return False
    return normalize_text(evidence["contains"]) in normalize_text(chunk.get("text", ""))


def first_relevant_rank(
    chunks: List[Dict[str, Any]], evidence: List[Dict[str, str]]
) -> Optional[int]:
    """Thứ hạng (bắt đầu từ 1) của chunk đầu tiên khớp bất kỳ bằng chứng nào."""
    for rank, chunk in enumerate(chunks, 1):
        if any(_chunk_matches(chunk, item) for item in evidence):
            return rank
    return None


def recall_at_k(ranks: List[Optional[int]], k: int) -> Optional[float]:
    if not ranks:
        return None
    return sum(1 for rank in ranks if rank is not None and rank <= k) / len(ranks)


def mean_reciprocal_rank(ranks: List[Optional[int]]) -> Optional[float]:
    if not ranks:
        return None
    return sum(1 / rank for rank in ranks if rank) / len(ranks)


def contains_all(reply: str, key_points: Iterable[str]) -> bool:
    normalized_reply = normalize_text(reply)
    return all(normalize_text(point) in normalized_reply for point in key_points)


def _ratio(values: List[Optional[bool]]) -> Optional[float]:
    scored = [value for value in values if value is not None]
    if not scored:
        return None
    return sum(1 for value in scored if value) / len(scored)


def _score_group(results: List[Dict[str, Any]], k: int) -> Dict[str, Any]:
    ranks = [item["rank"] for item in results if item.get("retrieval_scored", True)]
    return {
        "count": len(results),
        "intent_accuracy": _ratio([item.get("intent_ok") for item in results]),
        "entity_accuracy": _ratio([item.get("codes_ok") for item in results]),
        "recall_at_k": recall_at_k(ranks, k),
        "mrr": mean_reciprocal_rank(ranks),
        "answer_accuracy": _ratio([item.get("answer_ok") for item in results]),
    }


def summarize(results: List[Dict[str, Any]], k: int) -> Dict[str, Any]:
    """Tổng hợp chỉ số toàn bộ và theo từng nhóm câu hỏi.

    Câu hỏi không có bằng chứng truy xuất (``retrieval_scored=False``) không
    được tính vào Recall/MRR; trường ``None`` nghĩa là không áp dụng.
    """
    categories: Dict[str, List[Dict[str, Any]]] = {}
    for item in results:
        categories.setdefault(item["category"], []).append(item)
    return {
        "overall": _score_group(results, k),
        "by_category": {
            name: _score_group(items, k) for name, items in sorted(categories.items())
        },
    }
