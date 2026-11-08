import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compare_reports import common_results
from run_eval import check_thresholds, disable_vector_search, repository_is_dirty


class CheckThresholdsTests(unittest.TestCase):
    def test_reports_metrics_below_threshold(self):
        summary = {"overall": {"recall_at_k": 0.70, "intent_accuracy": 0.99}}
        regressions = check_thresholds(summary, {"recall_at_k": 0.796, "intent_accuracy": 0.958})
        self.assertEqual(len(regressions), 1)
        self.assertIn("Recall@k", regressions[0])

    def test_missing_metric_counts_as_regression(self):
        self.assertEqual(len(check_thresholds({"overall": {}}, {"mrr": 0.5})), 1)

    def test_equal_to_threshold_passes(self):
        self.assertEqual(check_thresholds({"overall": {"mrr": 0.626}}, {"mrr": 0.626}), [])


class RepositoryStatusTests(unittest.TestCase):
    @mock.patch("run_eval.subprocess.check_output", return_value="")
    def test_generated_reports_do_not_make_evaluation_dirty(self, check_output):
        self.assertFalse(repository_is_dirty(Path("/repo")))
        command = check_output.call_args.args[0]
        self.assertIn(":(exclude)eval/reports/*", command)

    @mock.patch("run_eval.subprocess.check_output", return_value=" M backend/app.py\n")
    def test_source_changes_are_still_dirty(self, _check_output):
        self.assertTrue(repository_is_dirty(Path("/repo")))


class AblationTests(unittest.TestCase):
    def test_disable_vector_search_makes_query_fail(self):
        store = mock.Mock()
        disable_vector_search(store)
        with self.assertRaises(RuntimeError):
            store.collection.query(query_texts=["học phí"], n_results=4)


class CompareReportsTests(unittest.TestCase):
    def test_keeps_only_questions_with_same_id_and_text(self):
        before = [{"id": "a", "question": "x"}, {"id": "b", "question": "y"}, {"id": "c", "question": "z"}]
        after = [{"id": "a", "question": "x"}, {"id": "b", "question": "y đã sửa"}, {"id": "d", "question": "w"}]
        kept_before, kept_after = common_results(before, after)
        self.assertEqual([item["id"] for item in kept_before], ["a"])
        self.assertEqual([item["id"] for item in kept_after], ["a"])


if __name__ == "__main__":
    unittest.main()
