import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from metrics import (
    contains_all,
    first_relevant_rank,
    mean_reciprocal_rank,
    normalize_text,
    recall_at_k,
    summarize,
)


def _chunk(file_name, text):
    return {"metadata": {"file_name": file_name}, "text": text}


class NormalizeTextTests(unittest.TestCase):
    def test_collapses_line_breaks_inside_pdf_extracts(self):
        self.assertEqual(
            normalize_text("số TC nợ đọng từ đầu khóa\n    lớn hơn 24"),
            "số tc nợ đọng từ đầu khóa lớn hơn 24",
        )

    def test_composes_nfd_vietnamese_input(self):
        decomposed = "học bổng"
        self.assertEqual(normalize_text(decomposed), "học bổng")


class RelevantRankTests(unittest.TestCase):
    def setUp(self):
        self.evidence = [{"file": "quy_che.md", "contains": "tối đa 24 TC"}]

    def test_returns_one_based_rank_of_first_matching_chunk(self):
        chunks = [
            _chunk("so_tay.md", "tối đa 24 TC"),
            _chunk("quy_che.md", "nội dung khác"),
            _chunk("quy_che.md", "được đăng ký tối đa\n24 TC trong học kỳ"),
        ]
        self.assertEqual(first_relevant_rank(chunks, self.evidence), 3)

    def test_returns_none_when_evidence_missing(self):
        chunks = [_chunk("quy_che.md", "tối đa 14 TC")]
        self.assertIsNone(first_relevant_rank(chunks, self.evidence))

    def test_any_listed_evidence_counts_as_relevant(self):
        evidence = self.evidence + [{"file": "so_tay.md", "contains": "loại A"}]
        chunks = [_chunk("so_tay.md", "Học bổng loại A")]
        self.assertEqual(first_relevant_rank(chunks, evidence), 1)


class RankingMetricTests(unittest.TestCase):
    def test_recall_counts_ranks_within_cutoff(self):
        self.assertAlmostEqual(recall_at_k([1, 4, 5, None], k=4), 0.5)

    def test_mrr_treats_missing_as_zero(self):
        self.assertAlmostEqual(mean_reciprocal_rank([1, 2, None, 4]), (1 + 0.5 + 0 + 0.25) / 4)

    def test_empty_inputs_return_none_instead_of_dividing_by_zero(self):
        self.assertIsNone(recall_at_k([], k=4))
        self.assertIsNone(mean_reciprocal_rank([]))


class ContainsAllTests(unittest.TestCase):
    def test_requires_every_key_point(self):
        reply = "Sinh viên được đăng ký tối đa **24** TC,\ntối thiểu 12 TC."
        self.assertTrue(contains_all(reply, ["24", "tối thiểu 12 tc"]))
        self.assertFalse(contains_all(reply, ["24", "8 TC"]))

    def test_no_key_points_is_vacuously_true(self):
        self.assertTrue(contains_all("bất kỳ", []))


class SummarizeTests(unittest.TestCase):
    def test_groups_scores_by_category_and_skips_unscored_items(self):
        results = [
            {"category": "regulation", "intent_ok": True, "rank": 1, "answer_ok": True, "codes_ok": None},
            {"category": "regulation", "intent_ok": False, "rank": None, "answer_ok": False, "codes_ok": None},
            {"category": "course_check", "intent_ok": True, "rank": None, "answer_ok": None, "codes_ok": True,
             "retrieval_scored": False},
        ]
        summary = summarize(results, k=4)

        self.assertEqual(summary["overall"]["count"], 3)
        self.assertAlmostEqual(summary["overall"]["intent_accuracy"], 2 / 3)
        self.assertAlmostEqual(summary["overall"]["recall_at_k"], 0.5)
        self.assertAlmostEqual(summary["overall"]["answer_accuracy"], 0.5)
        self.assertAlmostEqual(summary["overall"]["entity_accuracy"], 1.0)
        self.assertIsNone(summary["by_category"]["course_check"]["recall_at_k"])


if __name__ == "__main__":
    unittest.main()
