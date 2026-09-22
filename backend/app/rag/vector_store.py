import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

from app.core.config import VECTOR_DB_DIR
from app.rag.document_loader import document_loader, DocumentChunk

class VectorStoreManager:
    def __init__(self, persist_dir: Path = VECTOR_DB_DIR):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = "hust_documents"
        self.client: Optional[chromadb.PersistentClient] = None
        self.collection = None
        self._init_client()

    def _init_client(self):
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Kho tri thức quy chế đào tạo và sổ tay sinh viên HUST"}
            )
            print(f"[VectorStoreManager] Đã kết nối ChromaDB tại {self.persist_dir}. Tổng chunks hiện có: {self.collection.count()}")
        except Exception as e:
            print(f"[VectorStoreManager] Lỗi khởi tạo ChromaDB: {e}")

    def sync_documents(self, force: bool = False) -> Dict[str, Any]:
        """
        Đồng bộ tài liệu từ data/documents vào ChromaDB Vector Store.
        Tự động nạp các chunks mới hoặc cập nhật khi có thay đổi.
        """
        if not self.collection:
            self._init_client()

        current_count = self.collection.count() if self.collection else 0

        chunks = document_loader.load_all_chunks()
        if not chunks:
            return {"status": "empty", "message": "Không tìm thấy tài liệu nào trong data/documents/", "count": 0}

        if force and self.client:
            try:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "Kho tri thức đề cương môn học và quy chế đào tạo tín chỉ HUST"}
                )
                print("[VectorStoreManager] Đã làm mới collection cho kho tri thức môn học.")
            except Exception as e:
                print(f"[VectorStoreManager] Lỗi reset collection: {e}")
        elif current_count > 0:
            print(f"[VectorStoreManager] Collection đã có {current_count} chunks. Tiến hành cập nhật/upsert...")

        documents = []
        metadatas = []
        ids = []

        for c in chunks:
            meta = c.metadata
            chunk_id = f"{meta['source']}_chunk_{meta['chunk_index']}"
            documents.append(c.text)
            # ChromaDB metadata chỉ chấp nhận str, int, float, bool
            clean_meta = {
                "source": str(meta.get("source", "")),
                "file_name": str(meta.get("file_name", "")),
                "title": str(meta.get("title", "")),
                "chunk_index": int(meta.get("chunk_index", 0)),
                "total_chunks": int(meta.get("total_chunks", 1)),
                "file_type": str(meta.get("file_type", "md")),
                "file_hash": str(meta.get("file_hash", ""))
            }
            metadatas.append(clean_meta)
            ids.append(chunk_id)

        # Batch upsert vào ChromaDB (mỗi batch tối đa 200 chunks)
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            end = i + batch_size
            self.collection.upsert(
                ids=ids[i:end],
                documents=documents[i:end],
                metadatas=metadatas[i:end]
            )

        new_total = self.collection.count()
        print(f"[VectorStoreManager] Đồng bộ thành công {len(ids)} chunks vào ChromaDB. Tổng hiện có: {new_total}")

        return {
            "status": "success",
            "synced_chunks": len(ids),
            "total_chunks": new_total,
            "sources": list(set([m["source"] for m in metadatas]))
        }

    def similarity_search(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """
        Tìm kiếm lai (Hybrid Retrieval): Kết hợp Semantic Search (Vector) 
        và Exact Code / Article Token Matching để đảm bảo chính xác 100% khi tra cứu
        mã học phần (ET4340, ET3290...), điều khoản quy chế (Điều 3, Điều 9...), hoặc thuật ngữ.
        """
        try:
            if not self.collection or self.collection.count() == 0:
                self.sync_documents()
        except Exception:
            self._init_client()
            if not self.collection or self.collection.count() == 0:
                self.sync_documents()

        if not self.collection:
            return []

        import re
        query_upper = query.upper()
        # 1. Trích xuất mã học phần (vd: ET4340, ET 4230 -> ET4230)
        norm_query = re.sub(r'\b([A-Z]{2,3})\s+(\d{4}[A-Z]?)\b', r'\1\2', query_upper)
        course_codes = re.findall(r'\b([A-Z]{2,3}\d{4}[A-Z]?)\b', norm_query)

        # 2. Trích xuất điều khoản (vd: Điều 3, Điều 9)
        article_matches = re.findall(r'\b(ĐIỀU\s+\d+)\b', norm_query)

        # 3. Vector Semantic Search
        actual_k = min(k * 2, self.collection.count())
        semantic_chunks = []
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=actual_k
            )
            if results and "documents" in results and results["documents"]:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
                dists = results["distances"][0] if "distances" in results and results["distances"] else [1.0] * len(docs)
                for doc, meta, dist in zip(docs, metas, dists):
                    semantic_chunks.append({
                        "text": doc,
                        "metadata": meta,
                        "distance": dist
                    })
        except Exception as e:
            print(f"[VectorStoreManager] Lỗi query vector: {e}")

        # 4. Exact Token Matching từ bộ sưu tập
        exact_chunks = []
        target_tokens = set(course_codes + article_matches)
        if target_tokens:
            try:
                all_data = self.collection.get(include=["documents", "metadatas"])
                if all_data and "documents" in all_data:
                    for doc, meta in zip(all_data["documents"], all_data["metadatas"]):
                        doc_upper = doc.upper()
                        for tok in target_tokens:
                            if tok in doc_upper:
                                # Ưu tiên cao hơn nếu token nằm ở tiêu đề/dòng đầu
                                first_lines = "\n".join(doc.splitlines()[:3]).upper()
                                is_in_title = tok in first_lines
                                dist = 0.02 if is_in_title else 0.08
                                exact_chunks.append({
                                    "text": doc,
                                    "metadata": meta,
                                    "distance": dist
                                })
                                break
            except Exception as e:
                print(f"[VectorStoreManager] Lỗi scan exact token: {e}")

        # 5. Hợp nhất, khử trùng lặp và sắp xếp theo khoảng cách (distance) tăng dần
        seen_texts = set()
        merged = []

        # Đưa exact matches trước (được gán distance nhỏ)
        exact_chunks.sort(key=lambda x: x["distance"])
        for item in exact_chunks:
            normalized_text = item["text"].strip()
            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                merged.append(item)

        # Đưa semantic chunks tiếp theo
        for item in semantic_chunks:
            normalized_text = item["text"].strip()
            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                merged.append(item)

        return merged[:k]

    def get_stats(self) -> Dict[str, Any]:
        """Lấy thống kê trạng thái hiện tại của Vector Store"""
        try:
            if not self.collection:
                self._init_client()
            count = self.collection.count() if self.collection else 0
        except Exception:
            self._init_client()
            count = self.collection.count() if self.collection else 0

        sources = []
        if self.collection and count > 0:
            try:
                sample = self.collection.get(limit=100)
                if sample and "metadatas" in sample:
                    sources = list(set([m.get("source", "") for m in sample["metadatas"] if m]))
            except Exception:
                pass

        return {
            "collection_name": self.collection_name,
            "total_chunks": count,
            "indexed_sources": sorted(sources),
            "persist_dir": str(self.persist_dir)
        }

vector_store = VectorStoreManager()
