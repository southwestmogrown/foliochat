# FolioChat DEVLOG

---

## 2026-03-13 — Local Pipeline Validated

### Goal
Get the full build pipeline running locally for the first time. Crawler through API.

### What Happened

**Bug 1: GitHub 403**
Crawler was hitting the GitHub API unauthenticated. Fixed by passing a personal access token via `--token` flag. Long-term fix: store token in `.env` and confirm crawler reads from environment.

**Bug 2: ChromaDB rejecting empty list metadata**
ChromaDB validates metadata strictly — empty lists are not allowed. The chunker was passing `repo["topics"]` directly into metadata, which came through as `[]` for repos with no GitHub topics set. Fixed by serializing to a comma-separated string with an empty string fallback:
```python
"topics": ",".join(repo["topics"]) if repo["topics"] else "",
```
Same pattern applied to `languages`. Note: when reading topics/languages back out in the serve phase, split on `","`.

**Bug 3: `get_topics()` AttributeError**
During debugging, a `repo.get_topics()` call was introduced — a PyGithub method that doesn't exist on a plain dict. The crawler returns dicts, not PyGithub objects. Reverted to `repo["topics"]` with the empty guard from Bug 2.

### Results
```
Step 1/4: Crawling GitHub profile...   51 repos found
Step 2/4: Chunking content...          440 semantic chunks created
Step 3/4: Embedding with local...      440/440 stored in 3 seconds
Step 4/4: Generating system prompt...  saved
```

### API Validated
Served with Ollama (`llama3.1:latest`) locally.

`POST /chat` — returns coherent answers about actual GitHub projects with source attribution.
`GET /context` — returns username, repo count, generated greeting, and build timestamp.

### Next Session
- Wire up React widget against local API
- Deploy backend to Railway or Render
- Get a public URL pointing at the live API

---

## 2026-03-13 — Railway Deployment (same session, continued)

### Goal
Get FolioChat API live on Railway at a public URL.

### What Happened

**Bug 1: Typer 0.24.x breaking change**
Railway was installing `typer==0.24.1` while local had `0.23.2`. In 0.24.x, the first
positional argument to `typer.Option()` is no longer treated as the default value — it's
treated as an option name. Fixed by using explicit `default=` keyword on all Option calls:
```python
# Before (breaks on 0.24.x)
embedder: str = typer.Option("local", "--embedder", "-e", help="...")
# After
embedder: str = typer.Option(default="local", help="...")
```
Pinned typer to `>=0.9.0,<0.24.0` in pyproject.toml.

**Bug 2: Railway using `sh` not `bash`**
Railway's build environment runs commands with `sh` by default. `${{VARIABLE}}` syntax
causes "bad substitution" in sh. Fixed by wrapping commands in `bash -c '...'`.

**Bug 3: Dependencies not available at runtime**
Build phase dependencies weren't persisting to the runtime container. Nixpacks phase
separation didn't work as expected. Fixed by moving everything (install + build + serve)
into a single start command so all steps run in the same environment:
```toml
[deploy]
startCommand = "pip install -e '.' || true && python -m cli.main build ... && python -m cli.main serve ..."
```

**Bug 4: `$GITHUB_TOKEN` not expanding in railway.toml**
Shell variable expansion of `$GITHUB_TOKEN` was unreliable in Railway's toml parsing,
causing `--token` to receive no value. Fix: removed `--token` from the CLI entirely and
added `os.environ.get("GITHUB_TOKEN")` fallback in `GithubCrawler.__init__()`.
`GITHUB_TOKEN` is set as a Railway environment variable and read automatically at runtime.

**Bug 5: venv/pip mismatch (local)**
Local venv had `python` pointing to `.venv` but `pip` pointing to pyenv shims. Every
`pip install` was going to pyenv global site-packages. Fixed by rebuilding venv cleanly
and always using `.venv/bin/pip`.

**Bug 6: OPENAI_API_KEY typo**
Railway variable was set as `OPEN_API_KEY` instead of `OPENAI_API_KEY`. Renamed in
Railway dashboard.

### Status at end of session
- Railway deploying, crawler running, GitHub token env var fix in progress
- Claude Code examining crawler code to confirm token is being read from environment

### Next Session
- Confirm Railway deployment is fully live
- Hit `/health` and `/chat` on the public URL
- Wire up React widget against live Railway API
- Begin Issue 2: bundle widget for portfolio consumption

## 2026-03-13 — GitHub token not loaded on Railway; crawl hangs

**Goal:** Fix Railway deployment hanging during the build/crawl phase due to GitHub API rate limiting.

**Problem:** `foliochat build` was running unauthenticated against the GitHub API (60 req/hr limit) on Railway, causing PyGithub's retry/backoff logic to stall the process indefinitely. The token was present in the local `.env` file but was never making it into `os.environ` for two reasons:
1. `load_dotenv()` was never called anywhere in the codebase, so `.env` vars were invisible to `os.environ` even locally.
2. Railway does not load `.env` files at all — it only exposes vars set in its Variables dashboard. The `.env` file is local-only and not deployed.

**What broke:** Crawl phase hung silently with no error. No indication that the token was missing — the code just fell back to unauthenticated GitHub requests and waited on rate limit resets.

**Fix (`cli/main.py`):**
- Added `from dotenv import load_dotenv` and called `load_dotenv()` at module load time. This loads `.env` locally and is a no-op on Railway (where Railway injects vars directly into the environment).
- Added an explicit check for `GITHUB_TOKEN` before constructing `GithubCrawler`. If no token is found (via `--token` flag or `GITHUB_TOKEN` env var), the command exits immediately with a clear error message instead of hanging.

**Railway action required:** Set `GITHUB_TOKEN` in the Railway service's Variables dashboard. The `.env` file is never deployed.

---

## 2026-03-14 — Railway token issue confirmed resolved; code cleanup

### Root cause confirmed
The hang was entirely a Railway-side configuration gap: `GITHUB_TOKEN` had not been set in the Railway service's Variables dashboard. Once the variable was added there, the existing `os.environ.get("GITHUB_TOKEN")` fallback in `cli/main.py` picked it up correctly. No further code changes to the token-reading path were needed.

### Cleanup performed

**`railway.toml` — added `--host 0.0.0.0` to the serve command**
Railway routes external traffic to the container's port; the server must bind to all interfaces, not just `127.0.0.1`. Without this, the API would start but be unreachable from outside the container.
```toml
# Before
python -m cli.main serve ... --port $PORT
# After
python -m cli.main serve ... --host 0.0.0.0 --port $PORT
```

**`tests/test_chunker.py` — corrected language metadata type assertion**
`test_tech_chunk_metadata_has_languages` was asserting `isinstance(languages, list)`. The chunker correctly serialises `languages` to a comma-separated string for ChromaDB compatibility (ChromaDB rejects list values in metadata — documented in CLAUDE.md). Updated the assertion to `isinstance(languages, str)`.

**`docs/DEVLOG.md` — removed duplicate top-level header**
A stray `# FolioChat Devlog` header had been inserted mid-file, duplicating the `# FolioChat DEVLOG` at line 1. Removed the duplicate.

### Next session
- Hit `/health` and `/chat` on the Railway public URL
- Wire up the React widget against the live Railway API
- Begin Issue 2: bundle widget for portfolio consumption

