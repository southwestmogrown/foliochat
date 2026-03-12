"""Unit tests for the LocalEmbedder (sentence-transformers backend)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest


def _make_fake_model(dimension: int = 384):
    """Return a mock SentenceTransformer that produces random vectors of *dimension* dims."""

    def fake_encode(texts, convert_to_numpy=True, **kwargs):
        return np.random.rand(len(texts), dimension).astype(np.float32)

    model = MagicMock()
    model.encode.side_effect = fake_encode
    return model


def _make_local_embedder(dimension: int = 384):
    """Instantiate LocalEmbedder with a mocked model — no network required."""
    from cli.embedder.embedder import LocalEmbedder

    embedder = LocalEmbedder.__new__(LocalEmbedder)
    embedder._model = _make_fake_model(dimension)
    return embedder


class TestLocalEmbedderDimension:
    """LocalEmbedder must return 384-dimensional vectors."""

    def test_embed_returns_correct_dimension(self):
        embedder = _make_local_embedder()
        result = embedder.embed(["hello world"])
        assert isinstance(result, list)
        assert len(result) == 1
        assert len(result[0]) == 384

    def test_embed_query_returns_correct_dimension(self):
        embedder = _make_local_embedder()
        result = embedder.embed_query("hello world")
        assert isinstance(result, list)
        assert len(result) == 384

    def test_embed_returns_list_of_floats(self):
        embedder = _make_local_embedder()
        result = embedder.embed(["hello world"])
        assert all(isinstance(v, float) for v in result[0])

    def test_embed_multiple_texts(self):
        embedder = _make_local_embedder()
        texts = ["hello world", "foo bar", "baz qux"]
        result = embedder.embed(texts)
        assert len(result) == 3
        assert all(len(vec) == 384 for vec in result)

    def test_dimension_property(self):
        embedder = _make_local_embedder()
        assert embedder.dimension == 384


class TestLocalEmbedderBatchProcessing:
    """LocalEmbedder must process texts in batches of 50."""

    def test_batch_size_constant(self):
        from cli.embedder.embedder import LocalEmbedder

        assert LocalEmbedder.BATCH_SIZE == 50

    def test_batch_processing_large_input(self):
        embedder = _make_local_embedder()
        texts = [f"text number {i}" for i in range(120)]
        result = embedder.embed(texts)
        assert len(result) == 120
        assert all(len(vec) == 384 for vec in result)

    def test_encode_called_in_batches(self):
        embedder = _make_local_embedder()
        texts = [f"text {i}" for i in range(110)]

        encode_call_sizes = []
        original_side_effect = embedder._model.encode.side_effect

        def tracking_encode(batch, **kwargs):
            encode_call_sizes.append(len(batch))
            return original_side_effect(batch, **kwargs)

        embedder._model.encode.side_effect = tracking_encode
        embedder.embed(texts)

        assert encode_call_sizes == [50, 50, 10]

    def test_exactly_50_texts_is_one_batch(self):
        embedder = _make_local_embedder()
        texts = [f"text {i}" for i in range(50)]

        call_sizes = []
        original = embedder._model.encode.side_effect

        def tracking_encode(batch, **kwargs):
            call_sizes.append(len(batch))
            return original(batch, **kwargs)

        embedder._model.encode.side_effect = tracking_encode
        result = embedder.embed(texts)

        assert call_sizes == [50]
        assert len(result) == 50


class TestLocalEmbedderImportError:
    """LocalEmbedder must raise ImportError gracefully when sentence-transformers is missing."""

    def test_raises_import_error_when_sentence_transformers_missing(self):
        from cli.embedder.embedder import LocalEmbedder

        with patch.dict("sys.modules", {"sentence_transformers": None}):
            with pytest.raises(ImportError, match="sentence-transformers"):
                LocalEmbedder()
