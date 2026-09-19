from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    An in-memory vector store for text chunks.

    The embedding_fn parameter allows dependency injection,
    including mock embeddings for automated tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name

        # Bài lab chỉ sử dụng kho lưu trữ in-memory.
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

    def _make_record(
        self,
        doc: Document,
    ) -> dict[str, Any]:
        """
        Convert a Document into a normalized in-memory record.

        A copy of metadata is stored so later changes made by
        the caller do not modify the record inside the store.
        """
        metadata = dict(doc.metadata)

        # Các chunk "file#0", "file#1",... cùng thuộc file "file".
        metadata.setdefault(
            "doc_id",
            doc.id.split("#", 1)[0],
        )

        record = {
            "id": doc.id,
            "content": doc.content,
            "metadata": metadata,
            "embedding": self._embedding_fn(doc.content),
            "index": self._next_index,
        }

        self._next_index += 1
        return record

    def _search_records(
        self,
        query: str,
        records: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        Run similarity search over the supplied candidate records.
        """
        if not records or top_k <= 0:
            return []

        query_embedding = self._embedding_fn(query)
        results: list[dict[str, Any]] = []

        for record in records:
            score = _dot(
                query_embedding,
                record["embedding"],
            )

            results.append(
                {
                    "id": record["id"],
                    "content": record["content"],
                    "metadata": dict(record["metadata"]),
                    "score": score,
                }
            )

        results.sort(
            key=lambda result: result["score"],
            reverse=True,
        )

        return results[:top_k]

    def add_documents(
        self,
        docs: list[Document],
    ) -> None:
        """
        Embed each document's content and add it to the store.

        One Document corresponds to one stored record. This method
        does not perform chunking automatically.
        """
        for doc in docs:
            record = self._make_record(doc)
            self._store.append(record)

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find the top_k stored records most similar to the query.

        Because embeddings are normalized, dot product is equivalent
        to cosine similarity.
        """
        return self._search_records(
            query,
            self._store,
            top_k,
        )

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._store)

    def search_with_filter(
        self,
        query: str,
        top_k: int = 3,
        metadata_filter: dict = None,
    ) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        Candidate records are filtered before similarity search so
        irrelevant records cannot occupy positions in top_k.
        """
        if not metadata_filter:
            candidates = self._store
        else:
            candidates = [
                record
                for record in self._store
                if all(
                    record["metadata"].get(key) == value
                    for key, value in metadata_filter.items()
                )
            ]

        return self._search_records(
            query,
            candidates,
            top_k,
        )

    def delete_document(
        self,
        doc_id: str,
    ) -> bool:
        """
        Remove all chunks belonging to one original document.

        Returns True if at least one chunk was removed.
        Otherwise, returns False.
        """
        size_before = len(self._store)

        self._store = [
            record
            for record in self._store
            if record["metadata"].get("doc_id") != doc_id
        ]

        return len(self._store) < size_before