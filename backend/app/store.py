import json
import threading
import uuid
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

from .config import Settings
from .pdf_utils import split_text


class NotesStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(settings.data_dir / 'chroma'))
        self.collection = self.client.get_or_create_collection('lecture_notes', metadata={'hnsw:space': 'cosine'})
        self.index_file = settings.data_dir / 'documents.json'
        self._model: SentenceTransformer | None = None
        self._lock = threading.RLock()

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._model = SentenceTransformer(self.settings.embedding_model)
        return self._model

    def _read_index(self) -> dict[str, dict[str, Any]]:
        return json.loads(self.index_file.read_text(encoding='utf-8')) if self.index_file.exists() else {}

    def _write_index(self, index: dict) -> None:
        tmp = self.index_file.with_suffix('.tmp')
        tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.index_file)

    def list_documents(self) -> list[dict]:
        with self._lock:
            return list(self._read_index().values())

    def add_document(self, filename: str, pages: list[str]) -> dict:
        records = [(page_no, chunk) for page_no, text in enumerate(pages, 1)
                   for chunk in split_text(text, self.settings.chunk_size, self.settings.chunk_overlap)]
        if not records:
            raise ValueError('No extractable text found. Scanned PDFs require OCR.')
        document_id = str(uuid.uuid4())
        ids = [f'{document_id}:{i}' for i in range(len(records))]
        vectors = self.model.encode([c for _, c in records], normalize_embeddings=True).tolist()
        metadata = [{'document_id': document_id, 'filename': filename, 'page': p} for p, _ in records]
        with self._lock:
            # Chroma may reject large inserts; add in conservative batches.
            try:
                for start in range(0, len(records), 100):
                    end = start + 100
                    self.collection.add(ids=ids[start:end], embeddings=vectors[start:end],
                                        documents=[c for _, c in records[start:end]],
                                        metadatas=metadata[start:end])
                doc = {'id': document_id, 'filename': filename, 'pages': len(pages), 'chunks': len(records)}
                index = self._read_index()
                index[document_id] = doc
                self._write_index(index)
            except Exception:
                self.collection.delete(where={'document_id': document_id})
                raise
        return doc

    def delete_document(self, document_id: str) -> bool:
        with self._lock:
            index = self._read_index()
            if document_id not in index:
                return False
            self.collection.delete(where={'document_id': document_id})
            del index[document_id]
            self._write_index(index)
        return True

    def search(self, query: str, document_ids: list[str] | None, limit: int) -> list[dict]:
        index = self._read_index()
        selected = set(document_ids) if document_ids is not None else set(index)
        selected &= set(index)
        if not selected:
            return []
        where = {'document_id': {'$in': sorted(selected)}} if len(selected) > 1 else {'document_id': next(iter(selected))}
        embedding = self.model.encode([query], normalize_embeddings=True).tolist()[0]
        result = self.collection.query(query_embeddings=[embedding], n_results=min(limit, max(1, self.collection.count())),
                                       where=where, include=['documents', 'metadatas', 'distances'])
        return [{**meta, 'excerpt': content, 'distance': float(distance)}
                for content, meta, distance in zip(result['documents'][0], result['metadatas'][0], result['distances'][0])]

    def quiz_context(self, document_ids: list[str] | None, max_chunks: int = 16) -> list[dict]:
        index = self._read_index()
        selected = set(document_ids) if document_ids is not None else set(index)
        selected &= set(index)
        if not selected:
            return []
        where = {'document_id': {'$in': sorted(selected)}} if len(selected) > 1 else {'document_id': next(iter(selected))}
        result = self.collection.get(where=where, include=['documents', 'metadatas'])
        rows = [{**meta, 'excerpt': content} for meta, content in zip(result['metadatas'], result['documents'])]
        # Deterministic spread rather than retrieving only the first few pages.
        if len(rows) > max_chunks:
            step = len(rows) / max_chunks
            rows = [rows[int(i * step)] for i in range(max_chunks)]
        return rows
