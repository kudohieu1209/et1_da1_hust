"""BM25-only lifecycle, trusted corpus and legacy fallback compatibility."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from app.rag.document_loader import DocumentLoader
from app.rag.vector_store import VectorStoreManager


class BM25ModeTests(unittest.TestCase):
    def test_app_startup_query_and_force_sync_never_import_vector_dependencies(self):
        script = '''
import importlib.abc
import os
from pathlib import Path
import sys

class BlockVectorImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname.split(".")[0] in {"chromadb", "onnxruntime"}:
            raise AssertionError("Unexpected vector dependency: " + fullname)
sys.meta_path.insert(0, BlockVectorImports())
import tests
from fastapi.testclient import TestClient
from app.main import app
from app.rag.rag_engine import rag_engine
from unittest import mock
with mock.patch.object(rag_engine.loader, "load_all_chunks", wraps=rag_engine.loader.load_all_chunks) as load:
    with TestClient(app) as client:
        assert load.call_count == (0 if os.environ["RAG_SYNC_ON_STARTUP"] == "never" else 1)
        assert client.get("/api/health").status_code == 200
        register = client.post("/api/auth/register", json={
            "student_id": "20239999", "password": "synthetic-test-password-2026",
            "student_name": "Sinh viên kiểm thử", "class_name": "Điện tử - K68", "program_code": "ET1"})
        assert register.status_code == 201, register.text
        response = client.post("/api/rag/query", json={"query": "Sinh viên bị cảnh báo học tập khi nào?"})
        assert response.status_code == 200, response.text
        assert response.json()["sources"], response.text
        status = client.get("/api/rag/status").json()
        assert status["mode"] == status["vector_store"]["mode"] == "bm25_only"
        assert status["vector_store"]["total_chunks"] > 0
        assert "error" not in status["vector_store"]
        assert load.call_count == 1
        rag_engine.sync_knowledge_base(force=True)
        assert load.call_count == 2
assert "chromadb" not in sys.modules
assert "onnxruntime" not in sys.modules
assert not Path(os.environ["VECTOR_DB_DIR"]).exists()
print("BM25 lifecycle OK; no chromadb/onnxruntime; no vector directory")
'''
        for startup in ("auto", "always", "never"):
            with self.subTest(startup=startup), tempfile.TemporaryDirectory() as directory:
                environment = {**os.environ, "PYTHON_DOTENV_DISABLED": "1", "RAG_VECTOR_SEARCH": "off",
                               "RAG_SYNC_ON_STARTUP": startup, "VECTOR_DB_DIR": str(Path(directory) / "absent"),
                               "COOKIE_SECURE": "false", "MONGODB_URI": "", "GEMINI_API_KEY": "",
                               "GOOGLE_API_KEY": ""}
                result = subprocess.run([sys.executable, "-c", script], env=environment,
                                        capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("RAG: chế độ chỉ BM25", result.stdout)

    def test_direct_chunks_equal_vector_failure_path_and_sync_revokes_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            approved = root / "approved.md"
            approved.write_text('---\nrag_status: VERIFIED\ndocument_type: tuition_decision\n'
                                'effective_period: 2026-2027\nsource_url: https://example.org/fees\n---\n'
                                '# Học phí\n## Trang PDF 3\nĐiều 1. Mức học phí\n'
                                '1. Học phí ET1 năm 2026-2027 là 630 nghìn đồng mỗi tín chỉ.\n', encoding="utf-8")
            (root / "draft.md").write_text('# Học phí\nHọc phí ET1 chưa được phê duyệt.', encoding="utf-8")
            loader = DocumentLoader(root)
            chunks = loader.load_all_chunks()
            self.assertTrue(chunks)
            rows = VectorStoreManager._chunk_rows(chunks)
            fallback = object.__new__(VectorStoreManager)
            fallback.vector_search = "on"
            fallback.collection = mock.Mock()
            fallback.collection.count.return_value = len(rows)
            fallback.collection.get.return_value = {
                "ids": [row["id"] for row in rows], "documents": [row["text"] for row in rows],
                "metadatas": [row["metadata"] for row in rows]}
            fallback.collection.query.side_effect = RuntimeError("vector unavailable")
            with mock.patch("app.rag.vector_store.document_loader", loader):
                direct = VectorStoreManager(root / "absent", vector_search="off")
                for question in ("Học phí ET1 năm 2026-2027 bao nhiêu?", "Điều 1 mức học phí", "học phí cử nhân"):
                    self.assertEqual(direct.similarity_search(question), fallback.similarity_search(question))
                metadata = direct.similarity_search("Học phí")[0]["metadata"]
                self.assertEqual(metadata["page"], 3)
                self.assertEqual(metadata["source_url"], "https://example.org/fees")
                self.assertNotIn("retrieval_score", direct._bm25_rows[0])
                approved.unlink()
                self.assertEqual(direct.sync_documents(force=True)["total_chunks"], 0)
                self.assertEqual(direct.similarity_search("Học phí"), [])
                self.assertNotIn("error", direct.get_stats())
                self.assertFalse((root / "absent").exists())

    def test_vector_config_default_and_validation(self):
        for value, expected in ((None, "on"), (" OFF ", "off"), ("invalid", None)):
            with self.subTest(value=value):
                environment = {**os.environ, "PYTHON_DOTENV_DISABLED": "1"}
                environment.pop("RAG_VECTOR_SEARCH", None)
                if value is not None:
                    environment["RAG_VECTOR_SEARCH"] = value
                result = subprocess.run([sys.executable, "-c",
                                         "from app.core.config import RAG_VECTOR_SEARCH; print(RAG_VECTOR_SEARCH)"],
                                        env=environment, capture_output=True, text=True)
                if expected:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.strip(), expected)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("RAG_VECTOR_SEARCH must be on or off", result.stderr)


if __name__ == "__main__":
    unittest.main()
