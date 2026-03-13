# 💬 FolioChat

> *Your GitHub profile, as a chatbot. One command.*

FolioChat crawls your GitHub profile, builds a local vector database from your projects, and gives you an embeddable chat widget that lets portfolio visitors ask questions about your work.

```bash
pip install foliochat
foliochat build --username southwestmogrown
foliochat serve --username southwestmogrown
```

That's it. Drop the React component into your portfolio. Done.

---

## What Visitors Can Ask

- *"What projects have you built?"*
- *"Do you have experience with PostgreSQL?"*
- *"How does QuizQuest work?"*
- *"What's your tech stack?"*
- *"Why did you build the stem splitter?"*

The chatbot answers from your actual README content, project descriptions, and commit history — not hallucinations.

---

## How It Works

```
GitHub Profile + Repos
        ↓
Crawler (GitHub API)
reads READMEs, commit messages,
folder structure, topics, languages
        ↓
Smart Chunker
splits content into semantic units
by type — not by character count
        ↓
Embedder (local or API-based)
converts chunks to vector embeddings
        ↓
ChromaDB (local, ~/.foliochat/)
stores and indexes all vectors
        ↓
FastAPI server
retrieves relevant chunks per question,
sends to your LLM of choice
        ↓
React component
floating chat widget on your portfolio
```

---

## Installation

### Python CLI

```bash
pip install foliochat
```

### React Component

```bash
npm install foliochat
```

---

## CLI Usage

### Build the database

```bash
# Default — free local embeddings, no API key required
foliochat build --username yourusername

# Better retrieval quality with OpenAI embeddings
foliochat build --username yourusername --embedder openai

# Authenticated — higher GitHub rate limit (5000 req/hr vs 60)
foliochat build --username yourusername --token ghp_yourtoken

# Rebuild after pushing new projects
foliochat build --username yourusername --refresh
```

### Start the server

```bash
# Default — OpenAI GPT-4o-mini
foliochat serve --username yourusername

# Use Claude
foliochat serve --username yourusername --llm anthropic

# Use a local Ollama model (completely free)
foliochat serve --username yourusername --llm ollama --model llama3.1

# Custom port
foliochat serve --username yourusername --port 8080
```

### Check your database

```bash
foliochat info --username yourusername
```

---

## React Component

```tsx
import { FolioChat } from "foliochat";

export default function Portfolio() {
  return (
    <>
      <YourPortfolioContent />
      <FolioChat
        endpoint="http://localhost:8000"
        theme="dark"
        position="bottom-right"
        accentColor="#f97316"
      />
    </>
  );
}
```

### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `endpoint` | string | required | URL of running foliochat server |
| `theme` | `dark` \| `light` \| `auto` | `dark` | Color theme |
| `position` | `bottom-right` \| `bottom-left` | `bottom-right` | Widget position |
| `accentColor` | string | `#f97316` | Button + highlight color |
| `greeting` | string | auto-generated | Override opening message |

---

## LLM Setup

FolioChat works with any LLM. Set your API key as an environment variable before running `foliochat serve`.

**OpenAI (default)**
```bash
export OPENAI_API_KEY=sk-...
foliochat serve --username yourusername --llm openai
```

**Anthropic**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
foliochat serve --username yourusername --llm anthropic
```

**Ollama (free, local)**
```bash
ollama pull llama3.1
foliochat serve --username yourusername --llm ollama
```

---

## Embedding Backends

| Backend | Quality | Cost | Requires |
|---|---|---|---|
| `local` (default) | Good | Free | Nothing |
| `openai` | Great | ~$0.00002/build | OPENAI_API_KEY |
| `voyage` | Best | Paid | VOYAGE_API_KEY |

Local embeddings use `sentence-transformers/all-MiniLM-L6-v2` and run entirely on your machine.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `"Could not connect to FolioChat server"` in the widget | Ensure `foliochat serve` is running and the `endpoint` prop is correct |
| CORS errors in the browser console | Set `CORS_ORIGINS=https://yourdomain.com` on the server before serving |
| Stale project data in the chatbot | Run `foliochat build --username <you> --refresh` |
| Rate-limit errors during build | Pass `--token ghp_...` to use an authenticated GitHub token (5,000 req/hr) |
| `FOLIOCHAT_USERNAME not set` server error | Always start the server with `foliochat serve --username <you>`, not `uvicorn` directly |
| Embedder mismatch between build and serve | Rebuild with the same `--embedder` flag you intend to use; the choice is recorded in `metadata.json` |

---

## Architecture Notes

**Why smart chunking?** Naive character-count splitting destroys context. A README section about architecture should stay together. A project's tech stack is one unit of meaning. FolioChat chunks by semantic type — overview, tech, story, detail — so retrieval matches the shape of the question being asked.

**Why local storage?** Your portfolio data stays on your machine. Nothing is sent to a third party except the LLM API call at query time (and you can avoid that too with Ollama).

**Why ChromaDB?** Zero config, no server to run, persists to disk. Everything lives in `~/.foliochat/[username]/`.

For a detailed walk-through of every module, data model, and design decision, see [docs/architecture.md](docs/architecture.md).

---

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for local setup, testing, and code-style instructions.

Built by [@southwestmogrown](https://github.com/southwestmogrown).

---

## License

MIT
