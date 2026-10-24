"""Bounded conversation state, reconstructed from the current conversation only.

Course focus comes from user questions, never course codes mentioned in answers
(which may just be prerequisites). No student profile or grades are inferred.
"""
import re

REFERENCE = re.compile(r"(?:môn|học phần)\s+(?:đó|này|ấy|vừa (?:hỏi|nói|nhắc))|\bnó\b", re.I)
PLURAL = re.compile(r"(?:cả|hai|các|những)\s+(?:hai\s+)?(?:môn|học phần)", re.I)


def previous_focus(history, detect_courses, is_repeat):
    for item in reversed((history or [])[-12:]):
        if item.get("role") == "assistant":
            context = (item.get("data_context") or {}).get("conversation_context")
            if isinstance(context, dict):
                return context
        if item.get("role") == "user":
            query = item.get("content", "")
            if is_repeat(query):
                continue
            if detect_courses(query) or any(word in query.lower() for word in ("tín chỉ", "học phí", "quy chế")):
                return {"course_codes": detect_courses(query), "topic_query": query[:1200]}
    return {}


def resolve_followup(message, focus, detect_courses):
    """Return a resolved query, or a clarification when a reference is ambiguous."""
    if detect_courses(message):
        return message, None
    if re.fullmatch(r"(?:vậy\s+)?(?:nếu\s+)?(?:trượt|rớt|tạch)(?:\s+thì)?\s+(?:sao|thế nào)[?!.\s]*", message, re.I):
        message = re.sub(r"(trượt|rớt|tạch)", r"\1 môn đó", message, count=1, flags=re.I)
    if REFERENCE.search(message):
        codes = focus.get("course_codes") or []
        if not codes:
            return message, "Bạn đang nói tới môn nào? Bạn gửi tên hoặc mã học phần giúp mình nhé."
        if len(codes) > 1 and not PLURAL.search(message):
            return message, f"Bạn muốn hỏi môn nào trong {', '.join(codes)}? Bạn gửi mã môn để mình kiểm tra đúng nhé."
        return REFERENCE.sub(" / ".join(codes), message), None
    if re.search(r"^(?:vậy\s+)?(?:còn\s+)?(?:học\s+)?kỳ\s+(?:hè|chính)\b", message, re.I):
        previous = focus.get("topic_query", "")
        if "tín chỉ" in previous.lower() and not detect_courses(previous):
            # Remove the old term so retrieval does not favor the previous answer.
            base = re.sub(r"(?:học\s+)?kỳ\s+(?:hè|chính)", "học kỳ", previous, flags=re.I)
            return f"{base[:800]}\nCâu hỏi tiếp theo: {message}", None
    return message, None
