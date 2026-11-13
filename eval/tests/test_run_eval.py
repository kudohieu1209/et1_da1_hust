import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compare_reports import common_results
from run_eval import check_thresholds, repository_is_dirty


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


class BM25EvaluationTests(unittest.TestCase):
    def test_env_off_and_legacy_flag_use_bm25_without_vector_imports(self):
        import os
        import subprocess
        import tempfile
        script = r"""
import importlib.abc
import json
import os
from pathlib import Path
import sys
import run_eval

class BlockVectorImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname.split(".")[0] in {"chromadb", "onnxruntime"}:
            raise AssertionError("Unexpected vector dependency: " + fullname)
sys.meta_path.insert(0, BlockVectorImports())
directory = Path(os.environ["EVAL_TEST_DIR"])
item = next(item for item in run_eval.load_golden_set(run_eval.DEFAULT_GOLDEN) if item.get("evidence"))
golden = directory / "golden.jsonl"
golden.write_text(json.dumps(item, ensure_ascii=False) + "\n", encoding="utf-8")
run_eval.DEFAULT_REPORT_DIR = directory
args = ["--golden", str(golden), "--label", "bm25_test"] + sys.argv[1:]
assert run_eval.main(args) == 0
report = json.loads((directory / "bm25_test.json").read_text())
assert report["metadata"]["retrieval"] == "bm25_only"
assert report["summary"]["overall"]["recall_at_k"] == 1
assert "chromadb" not in sys.modules
assert "onnxruntime" not in sys.modules
assert not Path(os.environ["VECTOR_DB_DIR"]).exists()
"""
        for flag in (False, True):
            with self.subTest(legacy_flag=flag), tempfile.TemporaryDirectory() as directory:
                environment = {**os.environ, "PYTHON_DOTENV_DISABLED": "1", "EVAL_TEST_DIR": directory,
                               "VECTOR_DB_DIR": str(Path(directory) / "absent"),
                               "RAG_VECTOR_SEARCH": "on" if flag else "off",
                               "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
                result = subprocess.run([sys.executable, "-c", script] + (["--no-vector"] if flag else []),
                                        env=environment, capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class CompareReportsTests(unittest.TestCase):
    def test_keeps_only_questions_with_same_id_and_text(self):
        before = [{"id": "a", "question": "x"}, {"id": "b", "question": "y"}, {"id": "c", "question": "z"}]
        after = [{"id": "a", "question": "x"}, {"id": "b", "question": "y đã sửa"}, {"id": "d", "question": "w"}]
        kept_before, kept_after = common_results(before, after)
        self.assertEqual([item["id"] for item in kept_before], ["a"])
        self.assertEqual([item["id"] for item in kept_after], ["a"])


if __name__ == "__main__":
    unittest.main()
