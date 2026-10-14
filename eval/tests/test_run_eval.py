import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_eval import check_thresholds


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


if __name__ == "__main__":
    unittest.main()
