# FolioChat — Architecture

This document describes the detailed system design of FolioChat: how data flows from a GitHub profile to a running chatbot.

---

## Overview

FolioChat is a **Retrieval-Augmented Generation (RAG)** pipeline split into two independent phases:

| Phase | Command | What it does |
|---|---|---|
| **Build** | `foliochat build` | Crawls GitHub → chunks → embeds → stores to disk |
| **Serve** | `foliochat serve` | Reads disk → embeds query → retrieves chunks → calls LLM |

All state is stored locally in `~/.foliochat/<username>/`. No database server required.

---

## Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                        BUILD PHASE                      │
└─────────────────────────────────────────────────────────┘

  GitHub Profile + Repos
          │
          ▼
  ┌───────────────┐
  │   Crawler     │  cli/crawler/github.py
  │               │  • PyGithub API (authenticated or anonymous)
  │               │  • Fetches: READMEs, commit messages,
  │               │    folder structure, topics, languages,
  │               │    profile bio, profile README
  └───────┬───────┘
          │ portfolio_data dict
          ▼
  ┌───────────────┐
  │   Chunker     │  cli/chunker/chunker.py
  │               │  • Splits into typed semantic units
  │               │  • Does NOT split by character count
  │               │  • Chunk types: identity, project_overview,
  │               │    project_detail, project_tech, project_story
  └───────┬───────┘
          │ list[Chunk]
          ▼
  ┌───────────────┐
  │   Embedder    │  cli/embedder/embedder.py
  │               │  • Converts each chunk's text to a float vector
  │               │  • Backends: local (all-MiniLM-L6-v2),
  │               │    openai (text-embedding-3-small),
  │               │    voyage (voyage-3)
  └───────┬───────┘
          │ list[list[float]]
          ▼
  ┌───────────────┐
  │  ChromaStore  │  cli/store/chroma.py
  │               │  • Persists vectors + metadata to disk
  │               │  • Location: ~/.foliochat/<username>/chroma/
  │               │  • Also writes: metadata.json, system_prompt.txt
  └───────────────┘


┌─────────────────────────────────────────────────────────┐
│                        SERVE PHASE                      │
└─────────────────────────────────────────────────────────┘

  React widget (browser)
          │  POST /chat { message, history }
          ▼
  ┌───────────────┐
  │  FastAPI app  │  cli/serve/api.py
  │               │
  │  1. Embed     │  Embed user message with local embedder
  │  2. Retrieve  │  Query ChromaDB — top-5 chunks (cosine similarity)
  │  3. Augment   │  Inject chunks into system prompt
  │  4. LLM call  │  OpenAI / Anthropic / Ollama
  │  5. Return    │  { reply, sources[] }
  └───────────────┘
          │
          ▼
  React widget renders reply + source repo links
```

---

## Module Reference

### `cli/crawler/github.py` — Crawler

Responsible for fetching all raw data from GitHub.

**Key outputs per repo:**

| Field | Source |
|---|---|
| `name`, `description` | GitHub repo metadata |
| `readme` | Raw README.md content |
| `language`, `languages` | GitHub Languages API |
| `topics` | GitHub Topics API |
| `recent_commits` | Last 20 commit messages |
| `structure` | Root-level file/folder tree |
| `homepage` | Repo homepage URL |

**Rate limits:** Unauthenticated requests are limited to 60/hr. Pass `--token ghp_...` to raise this to 5,000/hr.

---

### `cli/chunker/chunker.py` — Chunker

Produces semantically shaped chunks rather than fixed-size windows.

**Chunk types:**

| Type | Content | Answers |
|---|---|---|
| `identity` | Developer name, bio, all languages, all topics, profile README | "Who is this developer?" |
| `project_overview` | Repo name, description, topics, language, URL | "Tell me about project X" |
| `project_tech` | Languages, topics, README tech-stack section | "Do you know PostgreSQL?" |
| `project_story` | README intro + recent commit messages + file structure | "Why did you build X?" |
| `project_detail` | Individual README sections (one chunk per heading) | "How does X work?" |

**Design choice:** README sections stay intact (split on `##` headings, not character count). A 300-word architecture section is one chunk, not three fragments.

---

### `cli/embedder/embedder.py` — Embedder

A thin `BaseEmbedder` ABC with three concrete backends.

| Backend | Model | Dimensions | Cost |
|---|---|---|---|
| `local` | `all-MiniLM-L6-v2` (sentence-transformers) | 384 | Free |
| `openai` | `text-embedding-3-small` | 1536 | ~$0.00002 / 1K tokens |
| `voyage` | `voyage-3` | 1024 | Paid |

The embedder used during `build` is recorded in `metadata.json`, and the same backend must be used at query time to ensure vector-space alignment. In practice, `api.py` currently hardcodes the query-time embedder to `local` (zero cost). This works because ChromaDB simply stores and returns whatever float vectors it receives — as long as both build-time and query-time vectors share the same model, similarity scores are meaningful.

---

### `cli/store/chroma.py` — ChromaStore

Wraps ChromaDB with portfolio-specific helpers.

**Disk layout:**

```
~/.foliochat/
└── <username>/
    ├── chroma/          ← ChromaDB persisted collection
    ├── metadata.json    ← build metadata (embedder, repo count, timestamp)
    └── system_prompt.txt ← LLM personality prompt
```

**Key methods:**

| Method | Description |
|---|---|
| `exists()` | True if a built database is present |
| `query(query_text, embedder, n_results)` | Embed + nearest-neighbour search |
| `get_metadata()` | Read `metadata.json` |
| `get_system_prompt()` | Read `system_prompt.txt` |
| `clear()` | Wipe collection before a `--refresh` rebuild |

---

### `cli/serve/api.py` — FastAPI Server

Three endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | `GET` | Liveness probe |
| `/context` | `GET` | Portfolio summary for widget initialisation |
| `/chat` | `POST` | RAG-powered chat |

**`/chat` flow:**

1. Embed user message (local embedder — free)
2. Query ChromaDB for top-5 chunks by cosine similarity
3. Concatenate chunks into a `RELEVANT CONTEXT` block
4. Prepend system prompt with context block
5. Call LLM (OpenAI / Anthropic / Ollama) with full message history
6. Return `{ reply, sources }` — `sources` is the sorted list of repo names

**LLM routing:** Controlled by `FOLIOCHAT_LLM` and `FOLIOCHAT_MODEL` environment variables (set automatically by `foliochat serve`).

**CORS:** Defaults to `*` for local dev. Set `CORS_ORIGINS=https://yourdomain.com` in production.

---

### `cli/serve/prompt.py` — System Prompt Generator

Generates a first-person chatbot personality at build time from the crawled portfolio data. Saved to `system_prompt.txt` and loaded once at serve time.

---

### `foliochat.tsx` — React Widget

Self-contained TypeScript/React component. No build step in this repo — consumers bundle it with their own toolchain.

**Key behaviours:**

- Fetches `/context` on mount to get the greeting and repo count
- Sends user message to `/chat` and renders the full response on completion (token-by-token streaming is not yet implemented)
- Supports `theme: "auto"` — listens to `prefers-color-scheme` media query
- Closes on `Escape` key
- Source repos render as clickable GitHub links

---

## Design Decisions

### Why semantic chunking over token-count splitting?

Character-count or token-count splitting breaks context at arbitrary boundaries. A README section about deployment should stay together — splitting it at 500 characters produces fragments that each miss the point. FolioChat splits on markdown headings and semantic roles (tech stack, story, overview) so each retrieved chunk answers a recognisable question shape.

### Why local storage only?

Portfolio data stays on the developer's machine. Nothing is uploaded to a third party except the LLM API call at query time — and even that can be avoided with Ollama.

### Why ChromaDB?

Zero-config, no server to run, persists vectors to disk as a flat directory. The entire vector store is a folder you can copy, back up, or delete.

### Why lazy-load dependencies in `api.py`?

The ChromaDB collection, embedder model, and system prompt are loaded once on the first request, not at import time. This keeps the server startup fast and lets the module be imported in tests without triggering heavy model downloads.

---

## Sequence Diagram — Chat Request

```
Browser          FastAPI          ChromaDB         LLM API
   │                │                 │                │
   │  POST /chat    │                 │                │
   │───────────────>│                 │                │
   │                │ embed(message)  │                │
   │                │──────────────── (local model)    │
   │                │                 │                │
   │                │ query(vector,5) │                │
   │                │────────────────>│                │
   │                │  top-5 chunks   │                │
   │                │<────────────────│                │
   │                │                 │                │
   │                │ chat(system+ctx+history+message) │
   │                │─────────────────────────────────>│
   │                │                 │     reply      │
   │                │<─────────────────────────────────│
   │  { reply,      │                 │                │
   │    sources }   │                 │                │
   │<───────────────│                 │                │
```
