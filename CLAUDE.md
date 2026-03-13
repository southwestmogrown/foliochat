# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# CLI commands
foliochat build --username <github_user> [--embedder local|openai|voyage] [--refresh] [--token <gh_token>] [--include-private]
foliochat serve --username <github_user> [--port 8000] [--llm openai|anthropic|ollama] [--model <name>]
foliochat info --username <github_user>

# Lint / format
ruff check .
ruff format .

# Tests
pytest
pytest tests/path/to/test_file.py::test_name  # single test
```

## Architecture

FolioChat is a RAG pipeline that converts a GitHub profile into a portfolio chatbot. The data flow is:

**Build phase** (`foliochat build`):
1. `cli/crawler.py` — fetches repos, READMEs, commits, topics, languages via PyGithub
2. `chunker.py` — produces typed semantic chunks (identity, project_overview, project_detail, project_tech, project_story) — one identity chunk per portfolio, several per repo
3. `embedder.py` — pluggable backends (LocalEmbedder → all-MiniLM-L6-v2, OpenAIEmbedder → text-embedding-3-small, VoyageEmbedder → voyage-3)
4. `chroma.py` — stores vectors + metadata in `~/.foliochat/<username>/chroma/`; also writes `metadata.json` and `system_prompt.txt`
5. `prompt.py` — generates a chatbot personality from crawled profile data; saved once at build time

**Serve phase** (`foliochat serve`):
- `api.py` — FastAPI with 3 endpoints: `GET /health`, `GET /context`, `POST /chat`
- `/chat` embeds the user message, queries ChromaDB for top-5 chunks (cosine), injects them into the system prompt, then calls the configured LLM (OpenAI / Anthropic / Ollama)
- LLM backends are selected via `--llm` flag; `openai` client is used for OpenAI, `anthropic` for Claude, `httpx` for Ollama

**Frontend** (`foliochat.tsx`):
- Self-contained React/TypeScript floating widget; no build step in this repo (consumers bundle it)
- Calls `/context` on mount for greeting, streams `/chat` on submit
- Supports `theme` (dark/light/auto), `position`, `accentColor`, `greeting` props

## Key Design Decisions

- **Chunk types over token counts** — chunker creates semantically-shaped chunks (README sections stay whole) so RAG retrieval matches question patterns naturally
- **Lazy dependency loading in api.py** — store, embedder, and system prompt are loaded once on first request via module-level globals, not at import time
- **Embedder must match at query time** — the embedder used during `build` must be the same at `serve` time; `metadata.json` records which was used
- **All state lives in `~/.foliochat/<username>/`** — no database server required; ChromaDB persists to disk

## Environment Variables

| Variable | When needed |
|---|---|
| `OPENAI_API_KEY` | `--embedder openai` or `--llm openai` |
| `ANTHROPIC_API_KEY` | `--llm anthropic` |
| `VOYAGE_API_KEY` | `--embedder voyage` |
| `OLLAMA_HOST` | `--llm ollama` (default: `http://localhost:11434`) |
| `CORS_ORIGINS` | Serve phase; comma-separated (default: `*`) |

## Known Bugs Fixed

### Metadata serialization (chunker.py)
ChromaDB rejects empty lists in metadata. Any field that could be an empty list must be
serialized to a comma-separated string with an empty string fallback. This applies to
`topics` and `languages` in all chunk types:

```python
"topics": ",".join(repo["topics"]) if repo["topics"] else "",
"languages": ",".join(repo["languages"].keys()) if repo["languages"] else "",
```

When reading these fields back in the serve phase, split on `","` to reconstruct the list.
Do not revert these to list values — ChromaDB will reject them.

### repo is a dict, not a PyGithub object (chunker.py)
The crawler returns plain dicts, not PyGithub objects. Do not call PyGithub methods like
`repo.get_topics()` or `repo.get_languages()` anywhere in chunker.py. Always use dict
access: `repo["topics"]`, `repo["languages"]`, etc.

### GitHub token required for crawling
The crawler requires a GitHub personal access token to avoid 403 errors. Pass via
`--token` flag or set `GITHUB_TOKEN` in `.env`. Required scopes: `public_repo`, `read:user`.

---

## Working Conventions

### DEVLOG
Append an entry to `DEVLOG.md` at the end of every working session. Each entry should
include the date, the goal, what was attempted, what broke, how it was fixed, and what
the next session should tackle. Keep it factual and brief — it doubles as article material.
