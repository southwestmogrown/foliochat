# Contributing to FolioChat

Thanks for your interest in contributing! This guide gets you from a fresh clone to running tests in a few minutes.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Project Layout](#project-layout)
- [Running Tests](#running-tests)
- [Linting and Formatting](#linting-and-formatting)
- [Making Changes](#making-changes)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Architecture Overview](#architecture-overview)

---

## Prerequisites

- **Python 3.9+**
- **git**
- (Optional) A GitHub personal access token for higher API rate limits during development

---

## Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/southwestmogrown/foliochat.git
cd foliochat

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install in editable / development mode
pip install -e ".[dev]"
```

That installs the `foliochat` CLI, all runtime dependencies, and the dev tools (`pytest`, `ruff`).

---

## Project Layout

```
foliochat/
├── cli/
│   ├── main.py              ← Typer CLI entry-point (build / serve / info commands)
│   ├── crawler/             ← GitHub API crawler
│   ├── chunker/             ← Semantic chunker
│   ├── embedder/            ← Embedding backends (local / OpenAI / Voyage)
│   ├── store/               ← ChromaDB wrapper
│   └── serve/               ← FastAPI app + system-prompt generator
├── foliochat.tsx            ← React/TypeScript floating chat widget
├── component/               ← TypeScript package config for the widget
├── examples/
│   ├── nextjs/              ← Next.js integration example
│   └── vanilla-html/        ← CDN / static HTML integration example
├── docs/
│   └── architecture.md      ← Detailed system design
├── tests/                   ← Pytest test suite
├── pyproject.toml
└── .env.example
```

---

## Running Tests

```bash
# Run the full test suite
pytest

# Run a single test file
pytest tests/test_chunker.py

# Run a single test by name
pytest tests/test_chunker.py::test_identity_chunk

# Run with verbose output
pytest -v
```

Tests use `pytest-asyncio` for async endpoint tests and mock out network calls (GitHub API, LLM APIs) so no credentials are required to run them.

---

## Linting and Formatting

FolioChat uses [Ruff](https://docs.astral.sh/ruff/) for both linting and formatting.

```bash
# Check for lint errors
ruff check .

# Auto-fix lint errors where possible
ruff check . --fix

# Format code
ruff format .

# Check formatting without writing (CI mode)
ruff format . --check
```

Please run `ruff check .` and `ruff format .` before committing. The CI pipeline will fail on lint errors.

---

## Making Changes

### Python backend

1. The source is under `cli/`. Each subdirectory has a focused responsibility — see [Architecture](docs/architecture.md) for the full picture.
2. Add or update tests in `tests/` for any logic you change.
3. Keep functions small and focused; prefer explicit over clever.

### React widget (`foliochat.tsx`)

The component is intentionally self-contained (no external CSS, no context providers). Changes should:

- Maintain zero external dependencies (only `react` and `react-dom` as peer deps).
- Not break the existing `FolioChatProps` interface without a version bump.
- Be tested via the component tests in `tests/test_component.py`.

### CLI commands (`cli/main.py`)

- Follow the existing pattern: validate early, provide clear `rich` console feedback, exit with a non-zero code on error.
- Keep each command's implementation self-contained (imports inside the function body to avoid slow startup when `--help` is called).

---

## Submitting a Pull Request

1. **Fork** the repository and create a branch from `main`:
   ```bash
   git checkout -b feature/my-improvement
   ```

2. **Make your changes** — keep commits focused (one logical change per commit).

3. **Run the checks:**
   ```bash
   ruff check .
   ruff format .
   pytest
   ```

4. **Push** and open a Pull Request against `main`. Fill in the PR description — what changed and why.

5. A maintainer will review and merge or request changes.

---

## Architecture Overview

For a deep-dive into how the RAG pipeline works — crawler, chunker, embedder, ChromaDB, and the FastAPI serve layer — read [docs/architecture.md](docs/architecture.md).

---

## Getting Help

Open a [GitHub Issue](https://github.com/southwestmogrown/foliochat/issues) if you hit a problem or have a question. Please include:

- Your Python version (`python --version`)
- The full error output
- The command you ran
