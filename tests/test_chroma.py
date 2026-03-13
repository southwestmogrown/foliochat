"""Unit tests for ChromaStore — local vector database management."""

import json
from unittest.mock import MagicMock

import numpy as np
import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_chunks(n: int = 10):
    """Create *n* test Chunk objects with varied types and content."""
    from cli.chunker.chunker import Chunk

    chunk_types = [
        "identity",
        "project_overview",
        "project_tech",
        "project_detail",
        "project_story",
    ]
    chunks = []
    for i in range(n):
        chunk_type = chunk_types[i % len(chunk_types)]
        chunks.append(
            Chunk(
                id=f"chunk_{i}",
                type=chunk_type,
                content=f"Chunk {i}: {chunk_type} content about repository repo_{i}.",
                metadata={
                    "username": "testuser",
                    "repo": f"repo_{i}",
                },
            )
        )
    return chunks


def _make_fake_embedder(dimension: int = 8):
    """
    Return a mock embedder that produces deterministic, unique float vectors.

    Each text gets a fixed random vector seeded by its hash so that repeated
    calls return the same embedding without hitting any real model.
    """
    _cache: dict[str, list[float]] = {}

    def _vec(text: str) -> list[float]:
        if text not in _cache:
            rng = np.random.default_rng(abs(hash(text)) % (2**32))
            _cache[text] = rng.random(dimension).tolist()
        return _cache[text]

    embedder = MagicMock()
    embedder.embed.side_effect = lambda texts: [_vec(t) for t in texts]
    embedder.embed_query.side_effect = _vec
    embedder.dimension = dimension
    return embedder


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """ChromaStore backed by *tmp_path* so tests never touch ~/.foliochat."""
    monkeypatch.setattr("cli.store.chroma.FOLIOCHAT_DIR", tmp_path)
    from cli.store.chroma import ChromaStore

    return ChromaStore(username="testuser")


@pytest.fixture()
def embedder():
    return _make_fake_embedder()


@pytest.fixture()
def populated_store(store, embedder):
    """Store pre-loaded with 10 test chunks."""
    chunks = _make_chunks(10)
    store.add_chunks(chunks, embedder)
    return store, embedder, chunks


# ── Initialisation ────────────────────────────────────────────────────────────


class TestChromaStoreInit:
    def test_directories_created_on_init(self, tmp_path, monkeypatch):
        monkeypatch.setattr("cli.store.chroma.FOLIOCHAT_DIR", tmp_path)
        from cli.store.chroma import ChromaStore

        ChromaStore(username="testuser")
        assert (tmp_path / "testuser").is_dir()
        assert (tmp_path / "testuser" / "chroma").is_dir()

    def test_base_and_chroma_paths(self, store, tmp_path):
        assert store.base_path == tmp_path / "testuser"
        assert store.chroma_path == tmp_path / "testuser" / "chroma"

    def test_collection_lazy_loaded(self, store):
        # Before any operation, internal client/collection should be None
        assert store._client is None
        assert store._collection is None


# ── add_chunks / count ────────────────────────────────────────────────────────


class TestAddChunks:
    def test_count_after_adding_ten_chunks(self, store, embedder):
        chunks = _make_chunks(10)
        store.add_chunks(chunks, embedder)
        assert store.count() == 10

    def test_embed_called_with_chunk_texts(self, store, embedder):
        chunks = _make_chunks(5)
        store.add_chunks(chunks, embedder)
        # embed() must have been called; extract all texts passed across calls
        all_embedded = [
            text for call in embedder.embed.call_args_list for text in call[0][0]
        ]
        expected_texts = [c.content for c in chunks]
        assert all_embedded == expected_texts

    def test_type_stored_in_metadata(self, populated_store):
        store, embedder, chunks = populated_store
        collection = store._get_collection()
        result = collection.get(include=["metadatas"])
        stored_types = {m["type"] for m in result["metadatas"]}
        expected_types = {c.type for c in chunks}
        assert stored_types == expected_types

    def test_batch_embed_called_in_batches_of_50(self, store):
        """add_chunks must call embed() in slices of ≤ 50 texts."""
        chunks = _make_chunks(60)
        embedder = _make_fake_embedder()
        store.add_chunks(chunks, embedder)
        batch_sizes = [len(call[0][0]) for call in embedder.embed.call_args_list]
        assert batch_sizes == [50, 10]


# ── query ─────────────────────────────────────────────────────────────────────


class TestQuery:
    def test_query_returns_n_results(self, populated_store):
        store, embedder, _ = populated_store
        results = store.query("repo content", embedder, n_results=3)
        assert len(results) == 3

    def test_query_result_has_required_keys(self, populated_store):
        store, embedder, _ = populated_store
        results = store.query("repo content", embedder, n_results=1)
        assert set(results[0].keys()) == {"content", "metadata", "relevance"}

    def test_relevance_between_zero_and_one(self, populated_store):
        store, embedder, _ = populated_store
        results = store.query("repo content", embedder, n_results=5)
        for r in results:
            assert 0.0 <= r["relevance"] <= 1.0

    def test_metadata_contains_username(self, populated_store):
        store, embedder, _ = populated_store
        results = store.query("repo content", embedder, n_results=3)
        for r in results:
            assert r["metadata"]["username"] == "testuser"

    def test_query_returns_fewer_than_n_when_store_small(self, store, embedder):
        chunks = _make_chunks(2)
        store.add_chunks(chunks, embedder)
        results = store.query("content", embedder, n_results=5)
        assert len(results) == 2

    def test_chunk_type_filter_restricts_results(self, populated_store):
        store, embedder, _ = populated_store
        results = store.query("content", embedder, n_results=10, chunk_types=["identity"])
        for r in results:
            assert r["metadata"]["type"] == "identity"

    def test_chunk_type_filter_multiple_types(self, populated_store):
        store, embedder, _ = populated_store
        results = store.query(
            "content",
            embedder,
            n_results=10,
            chunk_types=["identity", "project_tech"],
        )
        for r in results:
            assert r["metadata"]["type"] in {"identity", "project_tech"}

    def test_no_filter_returns_all_types(self, populated_store):
        store, embedder, _ = populated_store
        results = store.query("content", embedder, n_results=10)
        types_returned = {r["metadata"]["type"] for r in results}
        assert len(types_returned) > 1

    def test_acceptance_store_ten_query_top_three(self, store, embedder):
        """Acceptance criterion: store 10 chunks, query returns top 3 with metadata."""
        chunks = _make_chunks(10)
        store.add_chunks(chunks, embedder)
        results = store.query("project overview content", embedder, n_results=3)
        assert len(results) == 3
        for r in results:
            assert "content" in r
            assert "metadata" in r
            assert "relevance" in r
            assert r["metadata"]["username"] == "testuser"


# ── system prompt ─────────────────────────────────────────────────────────────


class TestSystemPrompt:
    def test_save_and_get_system_prompt(self, store):
        store.save_system_prompt("You are a helpful portfolio assistant.")
        assert store.get_system_prompt() == "You are a helpful portfolio assistant."

    def test_get_system_prompt_returns_empty_string_when_missing(self, store):
        assert store.get_system_prompt() == ""

    def test_system_prompt_persists_to_file(self, store, tmp_path):
        store.save_system_prompt("hello")
        file_path = tmp_path / "testuser" / "system_prompt.txt"
        assert file_path.exists()
        assert file_path.read_text() == "hello"

    def test_save_overwrites_previous_prompt(self, store):
        store.save_system_prompt("first")
        store.save_system_prompt("second")
        assert store.get_system_prompt() == "second"


# ── metadata ──────────────────────────────────────────────────────────────────


class TestMetadata:
    def test_metadata_path_returns_correct_path(self, store, tmp_path):
        assert store.metadata_path() == tmp_path / "testuser" / "metadata.json"

    def test_get_metadata_returns_empty_dict_when_missing(self, store):
        assert store.get_metadata() == {}

    def test_get_metadata_returns_saved_data(self, store):
        data = {"username": "testuser", "chunk_count": 10, "embedder": "local"}
        store.metadata_path().write_text(json.dumps(data))
        assert store.get_metadata() == data


# ── exists / clear ────────────────────────────────────────────────────────────


class TestExistsAndClear:
    def test_exists_returns_false_for_empty_store(self, store):
        # chroma dir exists but is empty after init
        assert store.exists() is False

    def test_exists_returns_true_after_adding_chunks(self, populated_store):
        store, _, _ = populated_store
        assert store.exists() is True

    def test_clear_resets_count_to_zero(self, populated_store):
        store, embedder, _ = populated_store
        store.clear()
        assert store.count() == 0

    def test_clear_resets_internal_references(self, populated_store):
        store, _, _ = populated_store
        store.clear()
        # _collection is reset to None so the next access creates a fresh one.
        # _client is intentionally kept alive so it can be reused immediately
        # for subsequent add_chunks calls without reconnecting.
        assert store._collection is None

    def test_clear_allows_subsequent_add(self, populated_store):
        store, embedder, _ = populated_store
        store.clear()
        new_chunks = _make_chunks(3)
        store.add_chunks(new_chunks, embedder)
        assert store.count() == 3
