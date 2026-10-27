import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

from app.core.config import VECTOR_DB_DIR
from app.rag.document_loader import document_loader, DocumentChunk
from app.rag.lexical_search import bm25_scores

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
            if self.collection:
                existing_ids = self.collection.get().get("ids", [])
                if existing_ids:
                    self.collection.delete(ids=existing_ids)
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
            chunk_id = f"{meta['file_name']}_chunk_{meta['chunk_index']}"
            documents.append(c.text)
            # ChromaDB metadata chỉ chấp nhận str, int, float, bool
            clean_meta = {
                "source": str(meta.get("source", "")),
                "file_name": str(meta.get("file_name", "")),
                "title": str(meta.get("title", "")),
                "chunk_index": int(meta.get("chunk_index", 0)),
                "total_chunks": int(meta.get("total_chunks", 1)),
                "file_type": str(meta.get("file_type", "md")),
                "file_hash": str(meta.get("file_hash", "")),
                "document_type": str(meta.get("document_type", "general")),
                "effective_period": str(meta.get("effective_period", "")),
                "source_url": str(meta.get("source_url", "")),
                "page": int(meta.get("page", 0)),
                "article": str(meta.get("article", "")),
                "section": str(meta.get("section", "")),
                "clause": str(meta.get("clause", "")),
                "education_level": str(meta.get("education_level", "general")),
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

        # Giữ collection là bản phản chiếu chính xác của thư mục documents:
        # xóa chunk cũ khi file bị xóa hoặc số chunk giảm sau khi biên tập.
        existing = self.collection.get()
        stale_ids = sorted(set(existing.get("ids", [])) - set(ids))
        if stale_ids:
            self.collection.delete(ids=stale_ids)
            print(f"[VectorStoreManager] Đã xóa {len(stale_ids)} chunks cũ không còn trong nguồn.")

        new_total = self.collection.count()
        print(f"[VectorStoreManager] Đồng bộ thành công {len(ids)} chunks vào ChromaDB. Tổng hiện có: {new_total}")

        return {
            "status": "success",
            "synced_chunks": len(ids),
            "total_chunks": new_total,
            "sources": list(set([m["source"] for m in metadatas]))
        }

    def similarity_search(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """Combine BM25 scores and vector ranks within the requested academic scope."""
        if k <= 0:
            return []
        if not self.collection or self.collection.count() == 0:
            self.sync_documents()
        if not self.collection:
            return []

        search_query = query.replace("cảnh cáo học tập", "cảnh báo học tập")
        # The active supported curricula are bachelor's programmes. Explicit
        # graduate-level questions and article numbers override that default.
        requested_level = next((level for term, level in (
            ("thạc sĩ", "master"), ("tiến sĩ", "doctorate"), ("nghiên cứu sinh", "doctorate"),
            ("kỹ sư", "engineer"),
        ) if term in query.lower()), "undergraduate")
        search_query = re.sub("cử nhân", "đại học", search_query, flags=re.I)
        if "học bổng" in search_query.lower():
            search_query = re.sub(r"loại A\b", "loại xuất sắc", search_query, flags=re.I)
            search_query = re.sub(r"loại B\b", "loại giỏi", search_query, flags=re.I)
            search_query = re.sub(r"loại C\b", "loại khá", search_query, flags=re.I)
        corpus = self.collection.get(include=["documents", "metadatas"])
        rows = [
            {"id": identifier, "text": document, "metadata": metadata or {}}
            for identifier, document, metadata in zip(corpus["ids"], corpus["documents"], corpus["metadatas"])
        ]
        if not rows:
            return []
        lexical = bm25_scores(search_query, [
            f"{row['metadata'].get('title', '')}\n{row['text']}" for row in rows
        ])
        lexical_order = sorted(range(len(rows)), key=lambda index: lexical[index], reverse=True)
        lexical_ranks = {rows[index]["id"]: rank for rank, index in enumerate(lexical_order, 1) if lexical[index] > 0}
        semantic_ranks = {}
        try:
            semantic = self.collection.query(query_texts=[search_query], n_results=min(k * 4, len(rows)))
            semantic_ranks = {identifier: rank for rank, identifier in enumerate(semantic["ids"][0], 1)}
        except Exception as exc:
            print(f"[VectorStoreManager] Vector search unavailable; using BM25: {type(exc).__name__}")

        years = set(re.findall(r"\b20\d{2}\b", query))
        codes = set(re.findall(r"\b[A-Z]{2,3}\d{4}[A-Z]?\b", query.upper()))
        articles = set(re.findall(r"điều\s+(\d+)\b", query.lower()))
        is_curriculum = bool(re.search(r"\bET\d\b|mô[ -]đun|mô đun|ctđt", query, re.I))
        preferred_type = "tuition_decision" if "học phí" in query.lower() else (
            "student_handbook" if "học bổng" in query.lower() else "academic_regulation"
        )
        if preferred_type in {"tuition_decision", "student_handbook"}:
            # A programme code identifies the student, not the document type.
            is_curriculum = False
        max_lexical = max(lexical) or 1
        ranked = []
        for index, row in enumerate(rows):
            identifier = row["id"]
            if identifier not in lexical_ranks:
                continue
            metadata = row["metadata"]
            article_number = re.search(r"Điều\s+(\d+)\b", metadata.get("article", ""))
            explicit_article = bool(articles and article_number and article_number.group(1) in articles)
            scope = metadata.get("education_level", "general")
            if scope not in {"general", requested_level} and not explicit_article:
                continue
            if is_curriculum and metadata.get("document_type") != "curriculum":
                continue
            score = lexical[index] / max_lexical
            if identifier in semantic_ranks:
                score += 0.10 / semantic_ranks[identifier]
            if metadata.get("document_type") == preferred_type:
                score *= 1.25
            if metadata.get("document_type") == "curriculum" and years:
                if not any(year in metadata.get("effective_period", "") for year in years):
                    continue
            if codes and all(code in row["text"].upper() for code in codes):
                score += 0.02
            if explicit_article:
                score += 0.02
            row["distance"] = 1 / (1 + lexical[index])
            row["retrieval_score"] = score
            ranked.append(row)
        ranked.sort(key=lambda row: row["retrieval_score"], reverse=True)
        # Return whole numbered clauses when a point matches. Conditions such
        # as graduation or dismissal must retain their AND/OR lead-in and peers.
        def clause_key(row):
            meta = row["metadata"]
            if not meta.get("clause"):
                return (row["id"],)
            return (meta.get("file_name"), meta.get("article"), meta["clause"],
                    0 if meta.get("article") else meta.get("page", 0))

        groups = {}
        for row in rows:
            groups.setdefault(clause_key(row), []).append(row)
        selected = []
        seen = set()
        for row in ranked:
            key = clause_key(row)
            if key in seen:
                continue
            siblings = sorted(groups[key], key=lambda item: item["metadata"].get("chunk_index", 0))
            meta = row["metadata"]
            if meta.get("clause") and len(siblings) > 1:
                header = "\n".join(dict.fromkeys(meta.get(field, "") for field in ("article", "section", "clause") if meta.get(field)))
                bodies = []
                for sibling in siblings:
                    sibling_meta = sibling["metadata"]
                    prefix = "\n".join(dict.fromkeys(sibling_meta.get(field, "") for field in ("article", "section", "clause") if sibling_meta.get(field)))
                    body = sibling["text"].removeprefix(prefix).strip()
                    if body and body != meta["clause"] and body not in bodies:
                        bodies.append(body)
                expanded = "\n\n".join([header, *bodies])
                if len(expanded) <= 4000:
                    pages = [item["metadata"].get("page", 0) for item in siblings]
                    row = {**row, "text": expanded, "metadata": {
                        **meta, "page": min(pages), "page_end": max(pages),
                    }}
                else:
                    key = (row["id"],)
            seen.add(key)
            selected.append(row)
            if len(selected) == k:
                break
        return selected

    def get_stats(self) -> Dict[str, Any]:
        """Lấy thống kê trạng thái hiện tại của Vector Store.

        Chỉ mục hỏng không được làm hỏng cả /api/rag/status: trả ``error`` để
        giao diện vẫn hiển thị được trạng thái mô hình. Không trả đường dẫn
        thư mục vì endpoint này công khai.
        """
        try:
            if not self.collection:
                self._init_client()
            count = self.collection.count() if self.collection else 0
        except Exception:
            self._init_client()
            try:
                count = self.collection.count() if self.collection else 0
            except Exception as exc:
                print(f"[VectorStoreManager] Không đọc được chỉ mục: {exc}")
                return {
                    "collection_name": self.collection_name,
                    "total_chunks": 0,
                    "indexed_sources": [],
                    "error": "index_unavailable",
                }

        sources = []
        if self.collection and count > 0:
            try:
                sample = self.collection.get(include=["metadatas"])
                if sample and "metadatas" in sample:
                    sources = list(set([m.get("source", "") for m in sample["metadatas"] if m]))
            except Exception:
                pass

        return {
            "collection_name": self.collection_name,
            "total_chunks": count,
            "indexed_sources": sorted(sources),
        }

vector_store = VectorStoreManager()
