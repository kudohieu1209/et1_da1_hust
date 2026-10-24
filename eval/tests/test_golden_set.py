import sys
import unittest
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_DIR))
sys.path.insert(0, str(EVAL_DIR.parent / "backend"))

from app.rag.document_loader import DocumentLoader
from golden_set import KNOWN_INTENTS, load_golden_set
from metrics import normalize_text

DOCUMENTS_DIR = EVAL_DIR.parent / "data" / "documents"


class GoldenSetIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = load_golden_set(EVAL_DIR / "golden_questions.jsonl") + load_golden_set(EVAL_DIR / "validation_questions.jsonl")

    def test_ids_are_unique(self):
        ids = [item["id"] for item in self.items]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_item_has_a_known_intent(self):
        for item in self.items:
            with self.subTest(item=item["id"]):
                self.assertIn(item["expected_intent"], KNOWN_INTENTS)

    def test_evidence_quotes_exist_verbatim_in_verified_documents(self):
        for item in self.items:
            for evidence in item.get("evidence", []):
                with self.subTest(item=item["id"], quote=evidence["contains"]):
                    path = DOCUMENTS_DIR / evidence["file"]
                    text = path.read_text(encoding="utf-8")
                    self.assertIn(path, DocumentLoader(DOCUMENTS_DIR).get_document_files())
                    self.assertIn(normalize_text(evidence["contains"]), normalize_text(text))

    def test_rag_questions_have_retrieval_evidence(self):
        for item in self.items:
            if item["expected_intent"] == "RAG_HUST_KNOWLEDGE":
                with self.subTest(item=item["id"]):
                    self.assertTrue(item.get("evidence"))


class GoldenSetLoaderTests(unittest.TestCase):
    def test_rejects_item_without_question(self):
        bad = EVAL_DIR / "tests" / "_bad_golden.jsonl"
        bad.write_text('{"id": "x", "category": "c", "expected_intent": "DEGREE_AUDIT"}\n', encoding="utf-8")
        try:
            with self.assertRaisesRegex(ValueError, "question"):
                load_golden_set(bad)
        finally:
            bad.unlink()


if __name__ == "__main__":
    unittest.main()
