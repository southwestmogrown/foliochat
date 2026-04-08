"""
ChromaDB store — local vector database management.

Data lives in ~/.foliochat/[username]/
  chroma/           → ChromaDB collection
  metadata.json     → crawl info
  system_prompt.txt → auto-generated chatbot personality
"""

import json
import os
from pathlib import Path
from typing import Optional


FOLIOCHAT_DIR = Path(os.environ.get("FOLIOCHAT_DIR", Path.home() / ".foliochat"))
COLLECTION_NAME = "portfolio"


class ChromaStore:
    def __init__(self, username: str):
        self.username = username
        self.base_path = FOLIOCHAT_DIR / username
        self.chroma_path = self.base_path / "chroma"

        self.base_path.mkdir(parents=True, exist_ok=True)
        self.chroma_path.mkdir(parents=True, exist_ok=True)

        self._client = None
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(self.chroma_path))
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_chunks(self, chunks, embedder) -> None:
        """Embed and store all chunks."""
        collection = self._get_collection()

        texts = [c.content for c in chunks]
        ids = [c.id for c in chunks]
        metadatas = [c.metadata for c in chunks]

        # Embed in batches of 50 to avoid memory issues
        batch_size = 50
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            all_embeddings.extend(embedder.embed(batch))

        collection.add(
            ids=ids,
            embeddings=all_embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    def query(
        self,
        query_text: str,
        embedder,
        n_results: int = 5,
        chunk_types: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Retrieve relevant chunks for a query.

        chunk_types: optionally filter by chunk type
                     e.g. ["project_tech"] for stack questions
        """
        collection = self._get_collection()
        query_embedding = embedder.embed_query(query_text)

        where = {"type": {"$in": chunk_types}} if chunk_types else None

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "content": doc,
                "metadata": meta,
                "relevance": round(1 - dist, 3),  # cosine distance → similarity
            })

        return chunks

    def get_system_prompt(self) -> str:
        path = self.base_path / "system_prompt.txt"
        if path.exists():
            return path.read_text()
        return ""

    def save_system_prompt(self, prompt: str) -> None:
        (self.base_path / "system_prompt.txt").write_text(prompt)

    def metadata_path(self) -> Path:
        return self.base_path / "metadata.json"

    def get_metadata(self) -> dict:
        path = self.metadata_path()
        if path.exists():
            return json.loads(path.read_text())
        return {}

    def exists(self) -> bool:
        """Check whether a database has been built for this username."""
        return self.chroma_path.exists() and any(self.chroma_path.iterdir())

    def clear(self) -> None:
        """Delete all stored vectors for this username."""
        import shutil
        if self.chroma_path.exists():
            shutil.rmtree(self.chroma_path)
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._collection = None

    def count(self) -> int:
        """Number of chunks stored."""
        return self._get_collection().count()