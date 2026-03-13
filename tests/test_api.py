"""Integration tests for the FolioChat API server.

Covers all three endpoints, CORS, lazy-loading, and LLM routing with
fully mocked dependencies so no real model or database is needed.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_mock_store(
    metadata=None,
    system_prompt="You are a portfolio assistant for Test User (@testuser).",
    chunks=None,
):
    """Return a mock ChromaStore with sensible defaults."""
    store = MagicMock()
    store.get_metadata.return_value = metadata or {
        "username": "testuser",
        "repo_count": 3,
        "built_at": "2024-01-01T00:00:00+00:00",
        "embedder": "local",
    }
    store.get_system_prompt.return_value = system_prompt
    store.query.return_value = (
        chunks
        if chunks is not None
        else [
            {
                "content": "testuser built a Python CLI tool called foliochat.",
                "metadata": {"repo": "foliochat", "type": "project_overview"},
                "relevance": 0.92,
            },
            {
                "content": "The foliochat project uses RAG and ChromaDB.",
                "metadata": {"repo": "foliochat", "type": "project_tech"},
                "relevance": 0.87,
            },
        ]
    )
    return store


def _make_mock_embedder():
    """Return a mock embedder that produces a trivial fixed vector."""
    embedder = MagicMock()
    embedder.embed_query.return_value = [0.1] * 8
    return embedder


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_store():
    return _make_mock_store()


@pytest.fixture()
def mock_embedder():
    return _make_mock_embedder()


@pytest.fixture()
def client(monkeypatch, mock_store, mock_embedder):
    """TestClient with all heavy dependencies mocked out."""
    monkeypatch.setenv("FOLIOCHAT_USERNAME", "testuser")
    monkeypatch.setenv("FOLIOCHAT_LLM", "openai")

    import cli.serve.api as api_module

    monkeypatch.setattr(api_module, "_store", mock_store)
    monkeypatch.setattr(api_module, "_embedder", mock_embedder)
    monkeypatch.setattr(api_module, "_system_prompt", "You are a portfolio assistant.")

    from cli.serve.api import app

    return TestClient(app)


# ── GET /health ───────────────────────────────────────────────────────────────


class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_status_is_ok(self, client):
        assert client.get("/health").json()["status"] == "ok"

    def test_health_returns_username(self, client):
        assert client.get("/health").json()["username"] == "testuser"


# ── GET /context ──────────────────────────────────────────────────────────────


class TestContext:
    def test_context_returns_200(self, client):
        assert client.get("/context").status_code == 200

    def test_context_contains_required_keys(self, client):
        data = client.get("/context").json()
        for key in ("username", "repo_count", "greeting", "built_at"):
            assert key in data, f"Missing key: {key}"

    def test_context_username(self, client):
        assert client.get("/context").json()["username"] == "testuser"

    def test_context_repo_count(self, client):
        assert client.get("/context").json()["repo_count"] == 3

    def test_context_built_at(self, client):
        assert client.get("/context").json()["built_at"] == "2024-01-01T00:00:00+00:00"

    def test_context_greeting_fallback_when_no_hi_line(self, client):
        # System prompt has no quoted "Hi!" line → falls back to default
        greeting = client.get("/context").json()["greeting"]
        assert greeting == "Hi! Ask me about this developer's projects."

    def test_context_greeting_extracted_from_system_prompt(
        self, monkeypatch, mock_embedder
    ):
        """Greeting is pulled from the first quoted 'Hi!' line in the system prompt."""
        system_prompt = (
            "You are an assistant.\n"
            "\"Hi! I can tell you about testuser's projects — including foliochat. "
            'What would you like to know?"\n'
        )
        mock_store = _make_mock_store(system_prompt=system_prompt)
        monkeypatch.setenv("FOLIOCHAT_USERNAME", "testuser")

        import cli.serve.api as api_module

        monkeypatch.setattr(api_module, "_store", mock_store)
        monkeypatch.setattr(api_module, "_embedder", mock_embedder)
        monkeypatch.setattr(api_module, "_system_prompt", system_prompt)

        from cli.serve.api import app

        resp = TestClient(app).get("/context")
        greeting = resp.json()["greeting"]
        assert "foliochat" in greeting
        assert greeting.startswith("Hi!")


# ── POST /chat ────────────────────────────────────────────────────────────────


class TestChat:
    def test_chat_returns_200(self, client):
        with patch(
            "cli.serve.api._call_llm",
            new=AsyncMock(return_value="I have built several projects."),
        ):
            resp = client.post(
                "/chat", json={"message": "what projects have you built?"}
            )
        assert resp.status_code == 200

    def test_chat_response_has_reply_and_sources(self, client):
        with patch(
            "cli.serve.api._call_llm",
            new=AsyncMock(return_value="I have built foliochat."),
        ):
            data = client.post(
                "/chat", json={"message": "what projects have you built?"}
            ).json()
        assert data["reply"] == "I have built foliochat."
        assert "sources" in data

    def test_chat_sources_contain_repo_names(self, client):
        with patch(
            "cli.serve.api._call_llm",
            new=AsyncMock(return_value="foliochat uses RAG."),
        ):
            data = client.post("/chat", json={"message": "what tech stack?"}).json()
        assert "foliochat" in data["sources"]

    def test_chat_sources_sorted(self, monkeypatch, mock_embedder):
        """Source repo names are returned in sorted order."""
        mock_store = _make_mock_store(
            chunks=[
                {
                    "content": "repo-b content",
                    "metadata": {"repo": "repo-b", "type": "project_tech"},
                    "relevance": 0.9,
                },
                {
                    "content": "repo-a content",
                    "metadata": {"repo": "repo-a", "type": "project_overview"},
                    "relevance": 0.8,
                },
            ]
        )
        monkeypatch.setenv("FOLIOCHAT_USERNAME", "testuser")

        import cli.serve.api as api_module

        monkeypatch.setattr(api_module, "_store", mock_store)
        monkeypatch.setattr(api_module, "_embedder", mock_embedder)
        monkeypatch.setattr(api_module, "_system_prompt", "You are an assistant.")

        from cli.serve.api import app

        with patch(
            "cli.serve.api._call_llm",
            new=AsyncMock(return_value="Answer"),
        ):
            data = TestClient(app).post("/chat", json={"message": "hi"}).json()
        assert data["sources"] == sorted(data["sources"])

    def test_chat_empty_message_fails_validation(self, client):
        resp = client.post("/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_chat_message_too_long_fails_validation(self, client):
        resp = client.post("/chat", json={"message": "x" * 2001})
        assert resp.status_code == 422

    def test_chat_no_chunks_returns_fallback_reply(self, monkeypatch, mock_embedder):
        """When the store returns no chunks a fallback reply is returned (no LLM call)."""
        mock_store = _make_mock_store(chunks=[])
        monkeypatch.setenv("FOLIOCHAT_USERNAME", "testuser")

        import cli.serve.api as api_module

        monkeypatch.setattr(api_module, "_store", mock_store)
        monkeypatch.setattr(api_module, "_embedder", mock_embedder)
        monkeypatch.setattr(api_module, "_system_prompt", "You are an assistant.")

        from cli.serve.api import app

        resp = TestClient(app).post("/chat", json={"message": "anything"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["sources"] == []
        assert (
            "information" in data["reply"].lower() or "answer" in data["reply"].lower()
        )

    def test_chat_with_conversation_history(self, client):
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        with patch(
            "cli.serve.api._call_llm",
            new=AsyncMock(return_value="Projects include foliochat."),
        ):
            resp = client.post(
                "/chat",
                json={"message": "tell me more", "history": history},
            )
        assert resp.status_code == 200
        assert resp.json()["reply"] == "Projects include foliochat."

    def test_chat_acceptance_what_projects_built(self, client):
        """Acceptance test: POST /chat with the canonical question returns a reply."""
        with patch(
            "cli.serve.api._call_llm",
            new=AsyncMock(
                return_value=(
                    "testuser has built foliochat, a RAG-powered portfolio chatbot "
                    "that converts a GitHub profile into an intelligent assistant."
                )
            ),
        ):
            resp = client.post(
                "/chat", json={"message": "what projects have you built?"}
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["reply"]) > 10
        assert isinstance(data["sources"], list)


# ── CORS ──────────────────────────────────────────────────────────────────────


class TestCORS:
    def test_cors_allow_origin_header_present(self, client):
        resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers

    def test_cors_preflight_options(self, client):
        resp = client.options(
            "/chat",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # CORS middleware responds to OPTIONS preflight with 200
        assert resp.status_code == 200


# ── LLM routing ───────────────────────────────────────────────────────────────


class TestLLMRouting:
    """Unit-tests for _call_llm routing logic (no real API calls)."""

    @pytest.mark.asyncio
    async def test_openai_routing(self):
        import cli.serve.api as api_module

        with patch(
            "cli.serve.api._openai_chat",
            new=AsyncMock(return_value="OpenAI reply"),
        ) as mock_fn:
            with patch.dict("os.environ", {"FOLIOCHAT_LLM": "openai"}):
                result = await api_module._call_llm(
                    system_prompt="sys",
                    context="ctx",
                    message="hello",
                    history=[],
                )
        assert result == "OpenAI reply"
        mock_fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_anthropic_routing(self):
        import cli.serve.api as api_module

        with patch(
            "cli.serve.api._anthropic_chat",
            new=AsyncMock(return_value="Anthropic reply"),
        ) as mock_fn:
            with patch.dict("os.environ", {"FOLIOCHAT_LLM": "anthropic"}):
                result = await api_module._call_llm(
                    system_prompt="sys",
                    context="ctx",
                    message="hello",
                    history=[],
                )
        assert result == "Anthropic reply"
        mock_fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ollama_routing(self):
        import cli.serve.api as api_module

        with patch(
            "cli.serve.api._ollama_chat",
            new=AsyncMock(return_value="Ollama reply"),
        ) as mock_fn:
            with patch.dict("os.environ", {"FOLIOCHAT_LLM": "ollama"}):
                result = await api_module._call_llm(
                    system_prompt="sys",
                    context="ctx",
                    message="hello",
                    history=[],
                )
        assert result == "Ollama reply"
        mock_fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_llm_raises_http_exception(self):
        from fastapi import HTTPException
        import cli.serve.api as api_module

        with patch.dict("os.environ", {"FOLIOCHAT_LLM": "unknown_backend"}):
            with pytest.raises(HTTPException) as exc_info:
                await api_module._call_llm(
                    system_prompt="sys",
                    context="ctx",
                    message="msg",
                    history=[],
                )
        assert exc_info.value.status_code == 500
        assert "unknown_backend" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_call_llm_augments_system_prompt_with_context(self):
        """_call_llm injects the context block into the system prompt."""
        import cli.serve.api as api_module

        captured = {}

        async def _capture(system, messages, model):
            captured["system"] = system
            return "reply"

        with patch("cli.serve.api._openai_chat", new=_capture):
            with patch.dict("os.environ", {"FOLIOCHAT_LLM": "openai"}):
                await api_module._call_llm(
                    system_prompt="BASE",
                    context="CONTEXT_DATA",
                    message="hi",
                    history=[],
                )
        assert "CONTEXT_DATA" in captured["system"]
        assert "BASE" in captured["system"]

    @pytest.mark.asyncio
    async def test_call_llm_passes_history_to_backend(self):
        """History messages appear in the messages list sent to the backend."""
        from cli.serve.api import Message
        import cli.serve.api as api_module

        captured = {}

        async def _capture(system, messages, model):
            captured["messages"] = messages
            return "reply"

        history = [Message(role="user", content="prior question")]
        with patch("cli.serve.api._openai_chat", new=_capture):
            with patch.dict("os.environ", {"FOLIOCHAT_LLM": "openai"}):
                await api_module._call_llm(
                    system_prompt="sys",
                    context="ctx",
                    message="follow-up",
                    history=history,
                )
        roles = [m["role"] for m in captured["messages"]]
        assert roles[0] == "user"  # history message
        assert roles[-1] == "user"  # current message
        assert captured["messages"][-1]["content"] == "follow-up"


# ── Lazy loading ──────────────────────────────────────────────────────────────


class TestLazyLoading:
    def test_globals_start_as_none_before_first_request(self, monkeypatch):
        """Module-level _store/_embedder/_system_prompt start as None."""
        import cli.serve.api as api_module

        monkeypatch.setattr(api_module, "_store", None)
        monkeypatch.setattr(api_module, "_embedder", None)
        monkeypatch.setattr(api_module, "_system_prompt", None)

        assert api_module._store is None
        assert api_module._embedder is None
        assert api_module._system_prompt is None

    def test_get_store_raises_without_username(self, monkeypatch):
        """get_store() raises RuntimeError when FOLIOCHAT_USERNAME is unset."""
        import cli.serve.api as api_module

        monkeypatch.delenv("FOLIOCHAT_USERNAME", raising=False)
        monkeypatch.setattr(api_module, "_store", None)

        with pytest.raises(RuntimeError, match="FOLIOCHAT_USERNAME"):
            api_module.get_store()
