"""Manifest cache contracts; no model downloads or real embedding calls."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.rag.document_loader import DocumentChunk
from app.rag.vector_store import embedding_identity, VectorStoreManager


class VectorManifestTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.manager = object.__new__(VectorStoreManager)
        self.manager.persist_dir = Path(directory.name)
        self.manager.collection_name = "test_documents"
        self.manager.client = mock.Mock()
        self.collection = self.manager.collection = mock.Mock()
        self.manager.client.get_or_create_collection.return_value = self.collection
        self.rows = {}
        self.collection.count.side_effect = lambda: len(self.rows)
        self.collection.get.side_effect = lambda **kwargs: {"ids": list(self.rows)}
        self.embed = mock.Mock()

        def upsert(ids, documents, metadatas):
            self.embed(documents)
            self.rows.update(zip(ids, zip(documents, metadatas)))

        self.collection.upsert.side_effect = upsert
        self.collection.delete.side_effect = lambda ids: [self.rows.pop(key) for key in ids]
        self.manager.client.delete_collection.side_effect = lambda name: self.rows.clear()
        self.chunks = [DocumentChunk("Approved text", {"file_name": "approved.md", "chunk_index": 0,
                                                      "source": "Approved source"})]
        loader = mock.patch("app.rag.vector_store.document_loader.load_all_chunks", side_effect=lambda: self.chunks)
        loader.start()
        self.addCleanup(loader.stop)

    def sync(self, force=False):
        return self.manager.sync_documents(force=force)

    def test_second_sync_and_reopened_manager_skip_upsert_and_embedding(self):
        self.assertEqual(self.sync()["status"], "success")
        self.collection.upsert.reset_mock()
        self.embed.reset_mock()
        # Cached checks must not even construct the real embedding function.
        with mock.patch("chromadb.utils.embedding_functions.ONNXMiniLM_L6_V2.__init__", side_effect=AssertionError("model loaded")):
            reopened = copy.copy(self.manager)
            self.assertEqual(reopened.sync_documents()["status"], "skipped")
        self.collection.upsert.assert_not_called()
        self.embed.assert_not_called()
        self.assertEqual(json.loads(self.manager._manifest_path.read_text())["chunk_count"], 1)

    def test_text_metadata_id_and_model_changes_trigger_sync(self):
        for change in ("text", "metadata", "id", "model"):
            with self.subTest(change=change):
                self.sync()
                self.collection.upsert.reset_mock()
                self.embed.reset_mock()
                if change == "text":
                    self.chunks[0].text += " updated"
                elif change == "metadata":
                    self.chunks[0].metadata["source"] = "Changed source"
                elif change == "id":
                    self.chunks[0].metadata["chunk_index"] += 1
                identity = embedding_identity()
                if change == "model":
                    identity = {**identity, "revision": "new-model"}
                with mock.patch("app.rag.vector_store.embedding_identity", return_value=identity):
                    self.assertEqual(self.sync()["status"], "success")
                self.collection.upsert.assert_called_once()
                self.embed.assert_called_once()

    def test_force_always_rebuilds_matching_index(self):
        self.sync()
        self.collection.upsert.reset_mock()
        self.embed.reset_mock()
        self.assertEqual(self.sync(force=True)["status"], "success")
        self.manager.client.delete_collection.assert_called_once_with("test_documents")
        self.collection.upsert.assert_called_once()
        self.embed.assert_called_once()

    def test_missing_corrupt_or_wrong_count_manifest_does_not_skip(self):
        for kind in ("missing", "corrupt", "count"):
            with self.subTest(kind=kind):
                self.sync()
                if kind == "missing":
                    self.manager._manifest_path.unlink()
                elif kind == "corrupt":
                    self.manager._manifest_path.write_text("{broken")
                else:
                    self.rows["stale"] = ("stale", {})
                self.assertEqual(self.sync()["status"], "success")
                self.assertEqual(len(self.rows), 1)

    def test_failed_sync_invalidates_manifest_before_partial_write(self):
        self.sync()
        self.chunks[0].text = "Changed text"
        self.collection.upsert.side_effect = RuntimeError("embedding failed")
        with self.assertRaisesRegex(RuntimeError, "embedding failed"):
            self.sync()
        self.assertFalse(self.manager._manifest_path.exists())

    def test_revoking_all_sources_clears_index_and_manifest(self):
        self.sync()
        self.chunks = []
        self.assertEqual(self.sync()["status"], "empty")
        self.assertEqual(self.rows, {})
        self.assertFalse(self.manager._manifest_path.exists())

    def test_canonical_order_and_normalized_metadata_do_not_invalidate_cache(self):
        self.chunks.append(DocumentChunk("Second", {"chunk_index": 0, "file_name": "second.md"}))
        self.sync()
        self.chunks.reverse()
        self.chunks[0].metadata = dict(reversed(list(self.chunks[0].metadata.items())))
        self.chunks[0].metadata["page"] = "0"
        self.assertEqual(self.sync()["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
