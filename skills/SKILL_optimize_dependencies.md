---
name: python-env-optimizer
description: >
  Audit and optimize Python project environments before installation — catching
  bloated dependencies, venv misconfiguration, and deployment/local mismatches
  BEFORE they waste time or bandwidth. Use this skill whenever the user is about
  to run pip install, set up a new Python project, configure a venv, troubleshoot
  a ModuleNotFoundError, or deploy a Python app to a cloud platform (Railway,
  Render, Fly, Heroku, etc.). Also triggers when the user mentions sentence-transformers,
  torch, transformers, CUDA, or any ML/AI library in a non-ML project context —
  these carry massive transitive dependencies that are almost never needed in
  full. Always run this audit silently before suggesting any pip install command.
---

# Python Environment Optimizer

Prevent wasted bandwidth, bloated installs, broken venvs, and deployment failures
by auditing the environment BEFORE running pip install or deploying.

## Rule 1: Always audit before installing

Before suggesting ANY pip install command, answer these four questions:

1. **Is the venv healthy?** (see Venv Health Check below)
2. **Are there ML/GPU libraries in the dependency tree?** (see Bloat Detection below)
3. **Does the install target match the runtime?** (local GPU vs cloud CPU)
4. **Is this a fresh install or a repair?** (different strategies apply)

Never skip this audit. A 10-minute wasted install has a real cost.

---

## Venv Health Check

Run this before any pip install:

```bash
which python
which pip
```

**Healthy state:** Both point to the same venv:
```
/path/to/project/.venv/bin/python
/path/to/project/.venv/bin/pip
```

**Broken state — pip points elsewhere:**
```
/path/to/project/.venv/bin/python   ← venv python
/home/user/.pyenv/shims/pip         ← pyenv pip (WRONG)
```

**Fix for broken pip:**
```bash
# Always use the venv's pip directly
.venv/bin/pip install -e ".[dev]"

# Or recreate the venv cleanly
deactivate
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip   # ALWAYS upgrade pip first
pip install -e ".[dev]"
```

**Why upgrade pip first:** pip <21 does not support pyproject.toml editable installs.
Running `pip install -e .` on old pip produces: "setup.py not found" errors even when
pyproject.toml is present and correct.

---

## Bloat Detection

These packages carry massive transitive dependency chains. Flag them immediately
when found in any project that doesn't explicitly need GPU/ML inference:

| Package | Why it's heavy | Typical download size |
|---|---|---|
| `torch` / `pytorch` | Pulls CUDA libs on GPU systems | 2-4 GB with CUDA |
| `sentence-transformers` | Depends on torch | Inherits torch bloat |
| `transformers` | Hugging Face, depends on torch | 500 MB+ |
| `tensorflow` | Full ML framework | 500 MB+ |
| `onnxruntime-gpu` | GPU inference runtime | 300 MB+ |

**When you see these in requirements or pyproject.toml, ask:**
> "This project depends on [package] which will download [size] of ML/CUDA libraries.
> Is this running locally with a GPU, or will it also deploy to a cloud environment?
> If deploying to cloud, we should split the dependencies."

---

## Dependency Splitting Pattern

When a project uses heavy ML libs locally but deploys to CPU-only cloud:

### In pyproject.toml
```toml
[project]
dependencies = [
    "fastapi>=0.104.0",
    "chromadb>=0.4.0",
    "PyGithub>=2.1.0",
    # ... lightweight deps only
]

[project.optional-dependencies]
local = [
    "sentence-transformers>=2.2.0",  # pulls torch + CUDA locally
]
cloud = [
    "openai>=1.0.0",                 # lightweight cloud embedder
]
dev = [
    "pytest>=7.4.0",
    "ruff>=0.1.0",
]
```

### Install commands
```bash
# Local development (with GPU)
pip install -e ".[local,dev]"

# Cloud deployment (Railway, Render, Fly)
pip install -e ".[cloud]"
```

### railway.toml
```toml
[build]
buildCommand = "pip install --upgrade pip && pip install -e '.[cloud]'"

[deploy]
startCommand = "python -m your.module serve --embedder openai --port $PORT"
```

---

## Railway-Specific Rules

Railway deployments fail silently on dependency issues. Always check:

1. **No GPU deps in the build** — Railway has no GPU. `sentence-transformers`,
   `torch`, and CUDA packages will install but be useless, wasting 5-10 min build time.

2. **PORT must be dynamic** — Railway injects `$PORT`. Never hardcode a port number.
   Start command must use `--port $PORT` or `os.environ.get("PORT", 8000)`.

3. **CLI entry points may not be on PATH** — After `pip install -e .`, the installed
   CLI script may not be available as a bare command in Railway's shell. Use
   `python -m module.path` instead of the CLI name in build/start commands.

4. **Verify the module path before pushing** — Run `python -m your.module --help`
   locally first. If it fails locally it will fail on Railway.

5. **Check pyproject.toml console_scripts** to find the correct module path:
   ```bash
   grep -A5 "console_scripts\|scripts" pyproject.toml
   ```
   If it shows `foliochat = "cli.main:app"`, the module path is `python -m cli.main`.

---

## ModuleNotFoundError Diagnosis

When `import X` fails despite `pip show X` saying it's installed:

```bash
# Step 1: Find where pip installed it
pip show X | grep Location

# Step 2: Find where Python looks
python -c "import sys; print('\n'.join(sys.path))"

# Step 3: Check if they match
which python
which pip
```

If pip's Location and Python's sys.path don't overlap — the package is installed
in the wrong place. Fix the venv (see Venv Health Check above), don't just reinstall.

---

## Pre-Install Checklist

Before running any pip install, confirm:

- [ ] `which python` and `which pip` both point to the same venv
- [ ] pip version is >= 21 (run `pip --version`, upgrade if not)
- [ ] No torch/sentence-transformers/transformers in deps unless GPU is available
  AND this is not a cloud deployment target
- [ ] If deploying to cloud: dependency groups are split (local vs cloud)
- [ ] pyproject.toml editable install is supported by current pip version
- [ ] Railway start command uses `$PORT` not a hardcoded port
- [ ] Railway build command uses `python -m module.path` not bare CLI name

---

## Quick Reference — Common Errors and Fixes

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError` after successful install | pip and python point to different envs | Rebuild venv, use `.venv/bin/pip` |
| `setup.py not found` with pyproject.toml present | pip version < 21 | `pip install --upgrade pip` first |
| `foliochat: not found` on Railway | CLI entry point not on PATH | Use `python -m cli.main` |
| `Got unexpected extra argument` | Wrong flag name or value | Run `python -m module --help` locally first |
| CUDA packages downloading unexpectedly | `sentence-transformers` dep on torch | Split deps, use cloud embedder on Railway |
| `AttributeError: 'dict' has no attribute 'get_X'` | PyGithub method called on plain dict | Use dict access `obj["key"]` not `obj.get_X()` |
| ChromaDB `metadata list value non-empty` | Empty list `[]` passed as metadata value | Serialize to string: `",".join(val) if val else ""` |
