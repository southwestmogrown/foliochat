"""
FolioChat API server — three endpoints, that's it.

GET  /health  → liveness check
GET  /context → portfolio summary for chat widget initialization
POST /chat    → RAG-powered chat

LLM backends: openai | anthropic | ollama
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="FolioChat API", version="0.1.0")

# CORS — allow the portfolio frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten this in production
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class Message(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []


class ChatResponse(BaseModel):
    reply: str
    sources: list[str] = []  # repo names that informed the answer


# ── Lazy-loaded dependencies ──────────────────────────────────────────────────

_store = None
_embedder = None
_system_prompt = None


def get_store():
    global _store
    if _store is None:
        from cli.store.chroma import ChromaStore
        username = os.environ.get("FOLIOCHAT_USERNAME")
        if not username:
            raise RuntimeError("FOLIOCHAT_USERNAME not set")
        _store = ChromaStore(username=username)
    return _store


def get_embedder():
    global _embedder
    if _embedder is None:
        from cli.embedder.embedder import get_embedder as _get
        # Use local embedder for queries (free, consistent with build)
        _embedder = _get("local")
    return _embedder


def get_system_prompt():
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = get_store().get_system_prompt()
    return _system_prompt


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "username": os.environ.get("FOLIOCHAT_USERNAME")}


@app.get("/context")
def context():
    """
    Called by the React component on mount.
    Returns portfolio summary and opening greeting.
    """
    store = get_store()
    meta = store.get_metadata()
    system_prompt = get_system_prompt()

    # Extract greeting from system prompt
    greeting = "Hi! Ask me about this developer's projects."
    for line in system_prompt.split("\n"):
        if line.strip().startswith('"Hi!'):
            greeting = line.strip().strip('"')
            break

    return {
        "username": meta.get("username", ""),
        "repo_count": meta.get("repo_count", 0),
        "greeting": greeting,
        "built_at": meta.get("built_at", ""),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    RAG-powered chat endpoint.

    Flow:
      1. Retrieve relevant chunks from vector DB
      2. Build context-augmented prompt
      3. Call LLM
      4. Return response + source repos
    """
    store = get_store()
    embedder = get_embedder()
    system_prompt = get_system_prompt()

    # Retrieve relevant chunks
    chunks = store.query(
        query_text=request.message,
        embedder=embedder,
        n_results=5,
    )

    if not chunks:
        return ChatResponse(
            reply="I don't have enough information to answer that. Try asking about specific projects or technologies.",
            sources=[],
        )

    # Build context block
    context_parts = []
    source_repos = set()
    for chunk in chunks:
        context_parts.append(chunk["content"])
        if "repo" in chunk["metadata"]:
            source_repos.add(chunk["metadata"]["repo"])

    context_block = "\n\n---\n\n".join(context_parts)

    # Call LLM
    reply = await _call_llm(
        system_prompt=system_prompt,
        context=context_block,
        message=request.message,
        history=request.history,
    )

    return ChatResponse(
        reply=reply,
        sources=sorted(source_repos),
    )


async def _call_llm(
    system_prompt: str,
    context: str,
    message: str,
    history: list[Message],
) -> str:
    """Route to the correct LLM backend."""
    llm = os.environ.get("FOLIOCHAT_LLM", "openai")
    model = os.environ.get("FOLIOCHAT_MODEL")

    augmented_system = f"{system_prompt}\n\nRELEVANT CONTEXT FROM PORTFOLIO:\n{context}"

    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": message})

    if llm == "openai":
        return await _openai_chat(augmented_system, messages, model or "gpt-4o-mini")
    elif llm == "anthropic":
        return await _anthropic_chat(augmented_system, messages, model or "claude-sonnet-4-20250514")
    elif llm == "ollama":
        return await _ollama_chat(augmented_system, messages, model or "llama3.1")
    else:
        raise HTTPException(status_code=500, detail=f"Unknown LLM backend: {llm}")


async def _openai_chat(system: str, messages: list, model: str) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=500,
        temperature=0.3,
    )
    return response.choices[0].message.content


async def _anthropic_chat(system: str, messages: list, model: str) -> str:
    import anthropic
    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model=model,
        system=system,
        messages=messages,
        max_tokens=500,
    )
    return response.content[0].text


async def _ollama_chat(system: str, messages: list, model: str) -> str:
    import httpx
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream": False,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=60.0,
        )
        return response.json()["message"]["content"]