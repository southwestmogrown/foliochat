"""Tests for the foliochat CLI commands: build, serve, info."""

import json
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch

from cli.main import app

runner = CliRunner()


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_portfolio():
    return {
        "username": "testuser",
        "profile": {
            "name": "Test User",
            "login": "testuser",
            "bio": "Builder of things",
            "location": "Earth",
            "company": "",
            "blog": "",
            "public_repos": 1,
            "followers": 0,
            "profile_readme": "",
            "avatar_url": "",
        },
        "repos": [
            {
                "name": "my-proj",
                "full_name": "testuser/my-proj",
                "description": "A cool project",
                "url": "https://github.com/testuser/my-proj",
                "homepage": "",
                "topics": ["python"],
                "language": "Python",
                "languages": {"Python": 5000},
                "stars": 1,
                "forks": 0,
                "is_private": False,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "readme": "# my-proj\n\nA great project for testing.",
                "recent_commits": ["Initial commit"],
                "structure": ["README.md", "main.py"],
            }
        ],
        "crawled_at": "2024-01-01T00:00:00+00:00",
    }


# ── build command ──────────────────────────────────────────────────────────────

class TestBuildCommand:
    def test_build_succeeds_end_to_end(self, tmp_path):
        """build runs the full pipeline and writes metadata + system_prompt."""
        portfolio = _make_portfolio()
        meta_file = tmp_path / "metadata.json"

        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = portfolio

        mock_embedder = MagicMock()
        # Return one vector per embed() call (batched)
        mock_embedder.embed.return_value = [[0.1] * 384] * 5

        mock_store = MagicMock()
        mock_store.exists.return_value = False
        mock_store.metadata_path.return_value = meta_file

        with (
            patch("cli.crawler.github.GithubCrawler", return_value=mock_crawler),
            patch("cli.embedder.embedder.get_embedder", return_value=mock_embedder),
            patch("cli.store.chroma.ChromaStore", return_value=mock_store),
        ):
            result = runner.invoke(app, ["build", "--username", "testuser"])

        assert result.exit_code == 0, result.output
        assert "Done" in result.output
        mock_store._store_with_embeddings.assert_called_once()
        mock_store.save_system_prompt.assert_called_once()

    def test_build_exits_with_error_when_db_exists_without_refresh(self):
        """build exits 1 and prints a helpful message if DB exists and --refresh not set."""
        mock_store = MagicMock()
        mock_store.exists.return_value = True

        with patch("cli.store.chroma.ChromaStore", return_value=mock_store):
            result = runner.invoke(app, ["build", "--username", "testuser"])

        assert result.exit_code == 1
        assert "--refresh" in result.output

    def test_build_with_refresh_clears_existing_db(self, tmp_path):
        """build --refresh clears the existing DB before rebuilding."""
        portfolio = _make_portfolio()
        meta_file = tmp_path / "metadata.json"

        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = portfolio

        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [[0.1] * 384] * 5

        mock_store = MagicMock()
        mock_store.exists.return_value = True
        mock_store.metadata_path.return_value = meta_file

        with (
            patch("cli.crawler.github.GithubCrawler", return_value=mock_crawler),
            patch("cli.embedder.embedder.get_embedder", return_value=mock_embedder),
            patch("cli.store.chroma.ChromaStore", return_value=mock_store),
        ):
            result = runner.invoke(app, ["build", "--username", "testuser", "--refresh"])

        assert result.exit_code == 0, result.output
        mock_store.clear.assert_called_once()

    def test_build_prints_step_headings(self, tmp_path):
        """build output contains the four step headings."""
        portfolio = _make_portfolio()
        meta_file = tmp_path / "metadata.json"

        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = portfolio

        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [[0.1] * 384] * 5

        mock_store = MagicMock()
        mock_store.exists.return_value = False
        mock_store.metadata_path.return_value = meta_file

        with (
            patch("cli.crawler.github.GithubCrawler", return_value=mock_crawler),
            patch("cli.embedder.embedder.get_embedder", return_value=mock_embedder),
            patch("cli.store.chroma.ChromaStore", return_value=mock_store),
        ):
            result = runner.invoke(app, ["build", "--username", "testuser"])

        assert "Step 1/4" in result.output
        assert "Step 2/4" in result.output
        assert "Step 3/4" in result.output
        assert "Step 4/4" in result.output

    def test_build_saves_metadata_json(self, tmp_path):
        """build writes a valid metadata.json with the expected keys."""
        portfolio = _make_portfolio()
        meta_file = tmp_path / "metadata.json"

        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = portfolio

        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [[0.1] * 384] * 5

        mock_store = MagicMock()
        mock_store.exists.return_value = False
        mock_store.metadata_path.return_value = meta_file

        with (
            patch("cli.crawler.github.GithubCrawler", return_value=mock_crawler),
            patch("cli.embedder.embedder.get_embedder", return_value=mock_embedder),
            patch("cli.store.chroma.ChromaStore", return_value=mock_store),
        ):
            result = runner.invoke(app, ["build", "--username", "testuser"])

        assert result.exit_code == 0, result.output
        assert meta_file.exists()
        meta = json.loads(meta_file.read_text())
        assert meta["username"] == "testuser"
        assert meta["embedder"] == "local"
        assert meta["repo_count"] == 1
        assert "chunk_count" in meta
        assert "built_at" in meta


# ── serve command ──────────────────────────────────────────────────────────────

class TestServeCommand:
    def test_serve_exits_with_clear_error_when_db_missing(self):
        """serve exits 1 with a helpful message when DB hasn't been built."""
        mock_store = MagicMock()
        mock_store.exists.return_value = False

        with patch("cli.store.chroma.ChromaStore", return_value=mock_store):
            result = runner.invoke(app, ["serve", "--username", "testuser"])

        assert result.exit_code == 1
        assert "foliochat build" in result.output

    def test_serve_starts_uvicorn_when_db_exists(self):
        """serve calls uvicorn.run when the database exists."""
        mock_store = MagicMock()
        mock_store.exists.return_value = True

        with (
            patch("cli.store.chroma.ChromaStore", return_value=mock_store),
            patch("uvicorn.run") as mock_run,
        ):
            runner.invoke(app, ["serve", "--username", "testuser"])

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs[1]["port"] == 8000

    def test_serve_sets_env_vars(self):
        """serve exports FOLIOCHAT_USERNAME and FOLIOCHAT_LLM before starting."""
        import os

        captured: dict = {}

        def fake_run(*args, **kwargs):
            captured["username"] = os.environ.get("FOLIOCHAT_USERNAME")
            captured["llm"] = os.environ.get("FOLIOCHAT_LLM")

        mock_store = MagicMock()
        mock_store.exists.return_value = True

        with (
            patch("cli.store.chroma.ChromaStore", return_value=mock_store),
            patch("uvicorn.run", side_effect=fake_run),
        ):
            runner.invoke(app, ["serve", "--username", "testuser", "--llm", "anthropic"])

        assert captured["username"] == "testuser"
        assert captured["llm"] == "anthropic"

    def test_serve_respects_custom_port(self):
        """serve passes the --port option to uvicorn."""
        mock_store = MagicMock()
        mock_store.exists.return_value = True

        with (
            patch("cli.store.chroma.ChromaStore", return_value=mock_store),
            patch("uvicorn.run") as mock_run,
        ):
            runner.invoke(app, ["serve", "--username", "testuser", "--port", "9000"])

        call_kwargs = mock_run.call_args
        assert call_kwargs[1]["port"] == 9000


# ── info command ───────────────────────────────────────────────────────────────

class TestInfoCommand:
    def test_info_shows_metadata_when_db_exists(self, tmp_path):
        """info prints metadata key/value pairs when the DB has been built."""
        meta = {
            "username": "testuser",
            "embedder": "local",
            "repo_count": 3,
            "chunk_count": 25,
            "built_at": "2024-01-01T00:00:00+00:00",
        }
        meta_file = tmp_path / "metadata.json"
        meta_file.write_text(json.dumps(meta))

        mock_store = MagicMock()
        mock_store.exists.return_value = True
        mock_store.metadata_path.return_value = meta_file

        with patch("cli.store.chroma.ChromaStore", return_value=mock_store):
            result = runner.invoke(app, ["info", "--username", "testuser"])

        assert result.exit_code == 0, result.output
        assert "testuser" in result.output
        assert "local" in result.output
        assert "3" in result.output

    def test_info_exits_with_error_when_db_missing(self):
        """info exits 1 when no database has been built for the username."""
        mock_store = MagicMock()
        mock_store.exists.return_value = False

        with patch("cli.store.chroma.ChromaStore", return_value=mock_store):
            result = runner.invoke(app, ["info", "--username", "testuser"])

        assert result.exit_code == 1


# ── --help ─────────────────────────────────────────────────────────────────────

class TestHelp:
    def test_root_help_lists_all_commands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "build" in result.output
        assert "serve" in result.output
        assert "info" in result.output

    def test_build_help_mentions_refresh(self):
        result = runner.invoke(app, ["build", "--help"])
        assert "refresh" in result.output

    def test_serve_help_mentions_llm(self):
        result = runner.invoke(app, ["serve", "--help"])
        assert "llm" in result.output
