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


# ---------------------------------------------------------------------------
# OpenAIEmbedder
# ---------------------------------------------------------------------------


def _make_openai_response(vectors: list[list[float]]):
    """Build a minimal fake openai.types.CreateEmbeddingResponse structure."""
    item_list = []
    for vec in vectors:
        item = MagicMock()
        item.embedding = vec
        item_list.append(item)
    response = MagicMock()
    response.data = item_list
    return response


def _make_openai_embedder(api_key: str = "sk-test"):
    """Instantiate OpenAIEmbedder with a mocked OpenAI client — no network required."""
    from cli.embedder.embedder import OpenAIEmbedder

    embedder = OpenAIEmbedder.__new__(OpenAIEmbedder)
    embedder._client = MagicMock()
    # Store the key so dimension property and other tests can use it
    embedder._api_key = api_key
    return embedder


class TestOpenAIEmbedderDimension:
    """OpenAIEmbedder must return 1536-dimensional vectors."""

    def test_dimension_property(self):
        embedder = _make_openai_embedder()
        assert embedder.dimension == 1536

    def test_embed_returns_correct_dimension(self):
        embedder = _make_openai_embedder()
        fake_vec = [0.1] * 1536
        embedder._client.embeddings.create.return_value = _make_openai_response(
            [fake_vec]
        )
        result = embedder.embed(["hello world"])
        assert len(result) == 1
        assert len(result[0]) == 1536

    def test_embed_query_returns_correct_dimension(self):
        embedder = _make_openai_embedder()
        fake_vec = [0.2] * 1536
        embedder._client.embeddings.create.return_value = _make_openai_response(
            [fake_vec]
        )
        result = embedder.embed_query("hello")
        assert isinstance(result, list)
        assert len(result) == 1536

    def test_embed_multiple_texts(self):
        embedder = _make_openai_embedder()
        fake_vecs = [[float(i)] * 1536 for i in range(3)]
        embedder._client.embeddings.create.return_value = _make_openai_response(
            fake_vecs
        )
        result = embedder.embed(["a", "b", "c"])
        assert len(result) == 3
        assert all(len(vec) == 1536 for vec in result)

    def test_embed_calls_api_with_correct_model(self):
        embedder = _make_openai_embedder()
        fake_vec = [0.0] * 1536
        embedder._client.embeddings.create.return_value = _make_openai_response(
            [fake_vec]
        )
        embedder.embed(["test"])
        embedder._client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input=["test"],
        )


class TestOpenAIEmbedderInit:
    """OpenAIEmbedder init must validate API key and handle missing openai package."""

    def test_raises_value_error_when_api_key_missing(self):
        from cli.embedder.embedder import OpenAIEmbedder

        with patch.dict("os.environ", {}, clear=True):
            # Ensure OPENAI_API_KEY is absent
            import os

            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                OpenAIEmbedder()

    def test_raises_import_error_when_openai_missing(self):
        from cli.embedder.embedder import OpenAIEmbedder

        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(ImportError, match="openai"):
                OpenAIEmbedder(api_key="sk-test")

    def test_accepts_explicit_api_key(self):
        from cli.embedder.embedder import OpenAIEmbedder

        mock_openai_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.OpenAI = mock_openai_cls
        with patch.dict("sys.modules", {"openai": mock_module}):
            OpenAIEmbedder(api_key="sk-explicit")
        mock_openai_cls.assert_called_once_with(api_key="sk-explicit")

    def test_reads_api_key_from_env(self):
        from cli.embedder.embedder import OpenAIEmbedder

        mock_openai_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.OpenAI = mock_openai_cls
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-from-env"}):
            with patch.dict("sys.modules", {"openai": mock_module}):
                OpenAIEmbedder()
        mock_openai_cls.assert_called_once_with(api_key="sk-from-env")


# ---------------------------------------------------------------------------
# VoyageEmbedder
# ---------------------------------------------------------------------------


def _make_voyage_embedder():
    """Instantiate VoyageEmbedder with a mocked voyageai client — no network required."""
    from cli.embedder.embedder import VoyageEmbedder

    embedder = VoyageEmbedder.__new__(VoyageEmbedder)
    embedder._client = MagicMock()
    return embedder


def _make_voyage_response(vectors: list[list[float]]):
    response = MagicMock()
    response.embeddings = vectors
    return response


class TestVoyageEmbedderDimension:
    """VoyageEmbedder must return 1024-dimensional vectors."""

    def test_dimension_property(self):
        embedder = _make_voyage_embedder()
        assert embedder.dimension == 1024

    def test_embed_returns_correct_dimension(self):
        embedder = _make_voyage_embedder()
        fake_vecs = [[0.1] * 1024]
        embedder._client.embed.return_value = _make_voyage_response(fake_vecs)
        result = embedder.embed(["hello world"])
        assert len(result) == 1
        assert len(result[0]) == 1024

    def test_embed_query_returns_correct_dimension(self):
        embedder = _make_voyage_embedder()
        fake_vecs = [[0.2] * 1024]
        embedder._client.embed.return_value = _make_voyage_response(fake_vecs)
        result = embedder.embed_query("hello")
        assert isinstance(result, list)
        assert len(result) == 1024

    def test_embed_query_uses_input_type_query(self):
        embedder = _make_voyage_embedder()
        fake_vecs = [[0.0] * 1024]
        embedder._client.embed.return_value = _make_voyage_response(fake_vecs)
        embedder.embed_query("test")
        embedder._client.embed.assert_called_once_with(
            ["test"], model="voyage-3", input_type="query"
        )

    def test_embed_multiple_texts(self):
        embedder = _make_voyage_embedder()
        fake_vecs = [[float(i)] * 1024 for i in range(4)]
        embedder._client.embed.return_value = _make_voyage_response(fake_vecs)
        result = embedder.embed(["a", "b", "c", "d"])
        assert len(result) == 4
        assert all(len(vec) == 1024 for vec in result)


class TestVoyageEmbedderInit:
    """VoyageEmbedder init must validate API key and handle missing voyageai package."""

    def test_raises_value_error_when_api_key_missing(self):
        from cli.embedder.embedder import VoyageEmbedder

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="VOYAGE_API_KEY"):
                VoyageEmbedder()

    def test_raises_import_error_when_voyageai_missing(self):
        from cli.embedder.embedder import VoyageEmbedder

        with patch.dict("sys.modules", {"voyageai": None}):
            with pytest.raises(ImportError, match="voyageai"):
                VoyageEmbedder(api_key="vk-test")

    def test_accepts_explicit_api_key(self):
        from cli.embedder.embedder import VoyageEmbedder

        mock_client_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.Client = mock_client_cls
        with patch.dict("sys.modules", {"voyageai": mock_module}):
            VoyageEmbedder(api_key="vk-explicit")
        mock_client_cls.assert_called_once_with(api_key="vk-explicit")

    def test_reads_api_key_from_env(self):
        from cli.embedder.embedder import VoyageEmbedder

        mock_client_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.Client = mock_client_cls
        with patch.dict("os.environ", {"VOYAGE_API_KEY": "vk-from-env"}):
            with patch.dict("sys.modules", {"voyageai": mock_module}):
                VoyageEmbedder()
        mock_client_cls.assert_called_once_with(api_key="vk-from-env")


# ---------------------------------------------------------------------------
# get_embedder factory
# ---------------------------------------------------------------------------


class TestGetEmbedder:
    """get_embedder factory must return the correct embedder instance."""

    def test_get_embedder_local_returns_local_embedder(self):
        from cli.embedder.embedder import LocalEmbedder, get_embedder

        embedder = LocalEmbedder.__new__(LocalEmbedder)
        embedder._model = _make_fake_model(384)

        with patch("cli.embedder.embedder.LocalEmbedder", return_value=embedder):
            result = get_embedder("local")
        assert result is embedder

    def test_get_embedder_openai_returns_openai_embedder(self):
        from cli.embedder.embedder import get_embedder

        mock_instance = _make_openai_embedder()
        with patch("cli.embedder.embedder.OpenAIEmbedder", return_value=mock_instance):
            result = get_embedder("openai")
        assert result is mock_instance

    def test_get_embedder_voyage_returns_voyage_embedder(self):
        from cli.embedder.embedder import get_embedder

        mock_instance = _make_voyage_embedder()
        with patch("cli.embedder.embedder.VoyageEmbedder", return_value=mock_instance):
            result = get_embedder("voyage")
        assert result is mock_instance

    def test_get_embedder_unknown_raises_value_error(self):
        from cli.embedder.embedder import get_embedder

        with pytest.raises(ValueError, match="unknown_backend"):
            get_embedder("unknown_backend")

    def test_get_embedder_error_lists_valid_backends(self):
        from cli.embedder.embedder import get_embedder

        with pytest.raises(ValueError, match="local"):
            get_embedder("bad")
        with pytest.raises(ValueError, match="openai"):
            get_embedder("bad")
        with pytest.raises(ValueError, match="voyage"):
            get_embedder("bad")
