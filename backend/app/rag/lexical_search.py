"""Small-corpus BM25 retrieval, including Vietnamese phrase tokens."""
import math
import re
import unicodedata
from collections import Counter

STOP_WORDS = set("của và là có được không cho em mình tôi bạn thì nào gì bao nhiêu trong theo với cần muốn hỏi về tại các những một".split())


def tokenize(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"\bkt\b", "kỹ thuật", text)
    words = re.findall(r"[^\W_]+", text, flags=re.UNICODE)
    tokens = [word for word in words if word not in STOP_WORDS]
    # Removing linking words also makes "học phí được tính" match "học phí tính".
    phrase_tokens = [f"{left} {right}" for left, right in zip(tokens, tokens[1:])]
    tokens.extend(phrase_tokens)
    return tokens


def bm25_scores(query: str, documents: list[str]) -> list[float]:
    bags = [Counter(tokenize(document)) for document in documents]
    lengths = [sum(bag.values()) for bag in bags]
    average = sum(lengths) / max(1, len(lengths)) or 1
    frequency = Counter(token for bag in bags for token in bag)
    terms = set(tokenize(query))
    scores = []
    for bag, length in zip(bags, lengths):
        score = 0.0
        for term in terms:
            count = bag[term]
            if count:
                idf = math.log(1 + (len(bags) - frequency[term] + 0.5) / (frequency[term] + 0.5))
                score += idf * count * 2.5 / (count + 1.5 * (0.25 + 0.75 * length / average))
        scores.append(score)
    return scores
