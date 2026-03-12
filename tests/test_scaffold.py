"""Smoke tests for the project scaffold — verifies imports and CLI entry point."""

import subprocess
import sys


def test_cli_help():
    """foliochat --help should exit 0 and mention the three commands."""
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "build" in result.stdout
    assert "serve" in result.stdout
    assert "info" in result.stdout


def test_cli_package_importable():
    """All submodules in the cli/ package must be importable without errors."""
    import cli.main  # noqa: F401
    import cli.chunker.chunker  # noqa: F401
    import cli.embedder.embedder  # noqa: F401
    import cli.store.chroma  # noqa: F401
    import cli.serve.prompt  # noqa: F401


def test_chunker_basic():
    """Chunker produces non-empty output for minimal portfolio data."""
    from cli.chunker.chunker import Chunker

    portfolio = {
        "username": "testuser",
        "profile": {
            "name": "Test User",
            "login": "testuser",
            "bio": "A developer",
            "location": "",
            "company": "",
            "blog": "",
            "public_repos": 1,
            "followers": 0,
            "profile_readme": "",
            "avatar_url": "",
        },
        "repos": [
            {
                "name": "test-repo",
                "full_name": "testuser/test-repo",
                "description": "A test repository",
                "url": "https://github.com/testuser/test-repo",
                "homepage": "",
                "topics": ["python"],
                "language": "Python",
                "languages": {"Python": 1000},
                "stars": 1,
                "forks": 0,
                "is_private": False,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "readme": "# test-repo\n\nA simple test repository for testing.",
                "recent_commits": ["Initial commit"],
                "structure": ["README.md"],
            }
        ],
        "crawled_at": "2024-01-01T00:00:00+00:00",
    }

    chunker = Chunker()
    chunks = chunker.chunk(portfolio)
    assert len(chunks) > 0
    assert any(c.type == "identity" for c in chunks)
    assert any(c.type == "project_overview" for c in chunks)
