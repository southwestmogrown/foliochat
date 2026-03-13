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