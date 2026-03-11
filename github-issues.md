# FolioChat — GitHub Issues

Copy each issue into GitHub, or use the GitHub CLI:
  gh issue create --title "..." --body "..." --label "..."

---

## Issue 1: Project scaffold + pyproject.toml
**Label:** setup
**Body:**
Set up the base project structure for FolioChat.

Tasks:
- [ ] Initialize pyproject.toml with all dependencies
- [ ] Create cli/ package with submodule structure
- [ ] Create component/ directory with package.json
- [ ] Set up .gitignore (Python + Node)
- [ ] Set up ruff linting config
- [ ] Verify `pip install -e .` works

Acceptance: `foliochat --help` runs without errors after install.

---

## Issue 2: GitHub crawler — profile + repo metadata
**Label:** crawler
**Body:**
Implement GithubCrawler.crawl() and profile fetching.

Tasks:
- [ ] Authenticate with PyGithub (token optional)
- [ ] Fetch user profile: name, bio, location, company, avatar
- [ ] Fetch profile README (username/username repo)
- [ ] List all public non-fork repositories
- [ ] Return structured portfolio_data dict
- [ ] Handle GithubException gracefully (rate limit, not found)

Acceptance: `crawler.crawl("southwestmogrown")` returns valid dict with profile and empty repos list.

---

## Issue 3: GitHub crawler — README + commits + structure
**Label:** crawler
**Body:**
Complete per-repository data fetching.

Tasks:
- [ ] Fetch README (try README.md, readme.md, README.rst)
- [ ] Fetch last 10 commit messages (first line only)
- [ ] Fetch top-level folder structure
- [ ] Fetch language breakdown
- [ ] Skip empty repos (size == 0)
- [ ] Rich progress bar during fetch

Acceptance: Full crawl of southwestmogrown returns all 5+ repos with readme, commits, structure populated.

---

## Issue 4: Chunker — README section parser
**Label:** chunker
**Body:**
Implement _split_readme_sections() and _extract_readme_intro().

Tasks:
- [ ] Split README by H1/H2/H3 headings into (heading, content) pairs
- [ ] Extract first meaningful paragraph (skip badges, HTML, empty lines)
- [ ] Extract named sections by keyword (tech stack, architecture, etc.)
- [ ] Unit tests for each parser with real README samples

Acceptance: QuizQuest README splits into at least 6 named sections correctly.

---

## Issue 5: Chunker — semantic chunk type classification
**Label:** chunker
**Body:**
Implement all five chunk types in Chunker.chunk().

Tasks:
- [ ] identity chunk (one per portfolio)
- [ ] project_overview chunk (one per repo)
- [ ] project_tech chunk (one per repo)
- [ ] project_story chunk (one per repo)
- [ ] project_detail chunks (one per README section)
- [ ] Filter chunks under 20 chars
- [ ] Unit tests verifying chunk types and content

Acceptance: southwestmogrown portfolio produces 25+ chunks with correct type labels.

---

## Issue 6: Embedder — local sentence-transformers backend
**Label:** embedder
**Body:**
Implement LocalEmbedder using all-MiniLM-L6-v2.

Tasks:
- [ ] embed(texts) → list of float vectors
- [ ] embed_query(text) → single float vector
- [ ] Batch processing (50 at a time)
- [ ] Graceful ImportError if sentence-transformers not installed
- [ ] Unit test: embed returns correct dimension (384)

Acceptance: LocalEmbedder().embed(["hello world"]) returns a list of 384 floats.

---

## Issue 7: Embedder — OpenAI + Voyage pluggable backends
**Label:** embedder
**Body:**
Implement OpenAIEmbedder and VoyageEmbedder + get_embedder factory.

Tasks:
- [ ] OpenAIEmbedder using text-embedding-3-small (1536 dims)
- [ ] VoyageEmbedder using voyage-3 (1024 dims)
- [ ] get_embedder(backend) factory function
- [ ] Clear error if API key missing
- [ ] Unit tests mocking API calls

Acceptance: get_embedder("openai") and get_embedder("local") both return valid embedder instances.

---

## Issue 8: ChromaDB store — write, read, refresh
**Label:** store
**Body:**
Implement ChromaStore with full CRUD operations.

Tasks:
- [ ] PersistentClient at ~/.foliochat/[username]/chroma/
- [ ] add_chunks(chunks, embedder) — batch embed and store
- [ ] query(query_text, embedder, n_results) — similarity search
- [ ] query with optional chunk_type filter
- [ ] save_system_prompt / get_system_prompt
- [ ] metadata_path, get_metadata, exists, clear, count
- [ ] Unit tests with temp directory

Acceptance: Store 10 chunks, query returns top 3 by relevance with correct metadata.

---

## Issue 9: System prompt generator
**Label:** serve
**Body:**
Implement SystemPromptGenerator.generate() from portfolio data.

Tasks:
- [ ] Developer name, bio, location
- [ ] Full project list with descriptions
- [ ] Languages and topics aggregate
- [ ] Tone sampling from README intros
- [ ] Response guidelines (concise, honest, no hallucination)
- [ ] Opening greeting with real project names
- [ ] Unit test: prompt contains username and all repo names

Acceptance: Generated prompt for southwestmogrown mentions QuizQuest, Guitar Hub, Terminal Chess.

---

## Issue 10: FastAPI server — all three endpoints
**Label:** serve
**Body:**
Implement the complete API server.

Tasks:
- [ ] GET /health → liveness check
- [ ] GET /context → portfolio summary + greeting
- [ ] POST /chat → RAG pipeline
- [ ] CORS middleware configured
- [ ] Lazy-loaded store + embedder (no startup cost)
- [ ] _call_llm routing: openai | anthropic | ollama
- [ ] Integration test: full chat round trip with mocked LLM

Acceptance: POST /chat {"message": "what projects have you built?"} returns coherent response.

---

## Issue 11: React component — FolioChat.tsx base
**Label:** component
**Body:**
Implement core chat widget functionality.

Tasks:
- [ ] Floating button (bottom-right or bottom-left)
- [ ] Chat window open/close
- [ ] Message list with user/assistant bubbles
- [ ] Input field + send button
- [ ] Enter key to send
- [ ] Loading indicator (···)
- [ ] Fetch /context on mount, display greeting

Acceptance: Component renders, opens, and displays greeting message.

---

## Issue 12: React component — theme + props + polish
**Label:** component
**Body:**
Complete component props and visual polish.

Tasks:
- [ ] dark / light / auto theme
- [ ] accentColor prop
- [ ] position prop (bottom-right / bottom-left)
- [ ] greeting prop override
- [ ] Source repos shown below assistant messages
- [ ] Error state when server unreachable
- [ ] Scroll to bottom on new messages
- [ ] Keyboard accessibility

Acceptance: Component matches design spec, works in dark and light theme.

---

## Issue 13: CLI entrypoint — build + serve + info commands
**Label:** cli
**Body:**
Wire up the Typer CLI with all three commands.

Tasks:
- [ ] foliochat build (crawler → chunker → embedder → store → prompt)
- [ ] foliochat serve (validate DB exists, start uvicorn)
- [ ] foliochat info (show stored metadata)
- [ ] Rich progress output at each step
- [ ] Clear error if DB missing on serve
- [ ] --refresh flag clears and rebuilds

Acceptance: Full pipeline runs end to end: foliochat build --username southwestmogrown succeeds.

---

## Issue 14: Next.js + vanilla HTML examples
**Label:** docs
**Body:**
Add integration examples.

Tasks:
- [ ] examples/nextjs/ — layout.tsx integration
- [ ] examples/vanilla-html/ — script tag integration (CDN)
- [ ] .env.example with FOLIOCHAT_URL
- [ ] README in each example directory

Acceptance: Someone following the Next.js example can add FolioChat to their portfolio in under 5 minutes.

---

## Issue 15: README + docs
**Label:** docs
**Body:**
Write the main README and supporting docs.

Tasks:
- [ ] Project overview + one-liner
- [ ] Architecture diagram
- [ ] Installation steps
- [ ] foliochat build / serve / info usage
- [ ] React component integration guide
- [ ] LLM provider setup (OpenAI, Anthropic, Ollama)
- [ ] docs/architecture.md — detailed system design
- [ ] CONTRIBUTING.md

Acceptance: A developer can clone, build, and see the chatbot running by following the README alone.