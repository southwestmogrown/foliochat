"""
Embedder — pluggable embedding backends.

Backends:
  local   → sentence-transformers (free, no API key, good quality)
  openai  → text-embedding-3-small (cheap, great quality)
  voyage  → voyage-3 (best quality, Claude-native)

Local is the default — zero cost, works offline, no signup required.
Switch to openai or voyage for production deployments.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseEmbedder(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts, return list of float vectors."""
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension for this embedder."""
        ...


class LocalEmbedder(BaseEmbedder):
    """
    sentence-transformers/all-MiniLM-L6-v2
    - Free, runs locally, no API key
    - 384 dimensions
    - Good retrieval quality for portfolio content
    """

    MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.MODEL_NAME)
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        return 384


class OpenAIEmbedder(BaseEmbedder):
    """
    text-embedding-3-small
    - ~$0.00002 per 1K tokens (essentially free for portfolio use)
    - 1536 dimensions
    - Excellent retrieval quality
    Requires: OPENAI_API_KEY environment variable
    """

    MODEL_NAME = "text-embedding-3-small"

    def __init__(self, api_key: Optional[str] = None):
        try:
            from openai import OpenAI
            import os
            self._client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        except ImportError:
            raise ImportError("openai not installed. Run: pip install openai")

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=self.MODEL_NAME,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        return 1536


class VoyageEmbedder(BaseEmbedder):
    """
    voyage-3
    - Best retrieval quality, Claude-native
    - 1024 dimensions
    Requires: VOYAGE_API_KEY environment variable
    """

    MODEL_NAME = "voyage-3"

    def __init__(self, api_key: Optional[str] = None):
        try:
            import voyageai
            import os
            self._client = voyageai.Client(
                api_key=api_key or os.environ.get("VOYAGE_API_KEY")
            )
        except ImportError:
            raise ImportError("voyageai not installed. Run: pip install voyageai")

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = self._client.embed(texts, model=self.MODEL_NAME)
        return result.embeddings

    def embed_query(self, text: str) -> list[float]:
        result = self._client.embed([text], model=self.MODEL_NAME, input_type="query")
        return result.embeddings[0]

    @property
    def dimension(self) -> int:
        return 1024


def get_embedder(backend: str) -> BaseEmbedder:
    """Factory — return the right embedder for a given backend string."""
    backends = {
        "local": LocalEmbedder,
        "openai": OpenAIEmbedder,
        "voyage": VoyageEmbedder,
    }
    if backend not in backends:
        raise ValueError(
            f"Unknown embedder '{backend}'. Choose from: {', '.join(backends.keys())}"
        )
    return backends[backend]()