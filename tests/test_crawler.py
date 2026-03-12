"""Tests for GithubCrawler — uses unittest.mock to avoid live API calls."""

import pytest
from unittest.mock import MagicMock, patch
from github import GithubException

from cli.crawler.github import GithubCrawler


def _make_mock_user(login="southwestmogrown"):
    """Return a minimal mock NamedUser object."""
    user = MagicMock()
    user.login = login
    user.name = "Southwest Mo Grown"
    user.bio = "Gardening and code."
    user.location = "Missouri"
    user.blog = "https://example.com"
    user.company = "ACME"
    user.public_repos = 3
    user.followers = 10
    user.avatar_url = "https://avatars.githubusercontent.com/u/1"
    # No public repos (empty list covers the acceptance criteria)
    user.get_repos.return_value = []
    return user


def test_crawl_returns_valid_dict_structure():
    """crawl() returns a dict with the required top-level keys."""
    mock_user = _make_mock_user()

    with patch("cli.crawler.github.Github") as MockGithub:
        instance = MockGithub.return_value
        instance.get_user.return_value = mock_user
        # No profile README repo
        instance.get_repo.side_effect = GithubException(404, "Not Found", None)

        crawler = GithubCrawler(token=None)
        result = crawler.crawl("southwestmogrown")

    assert isinstance(result, dict)
    assert result["username"] == "southwestmogrown"
    assert "profile" in result
    assert "repos" in result
    assert "crawled_at" in result


def test_crawl_profile_fields():
    """crawl() profile dict contains all required fields."""
    mock_user = _make_mock_user()

    with patch("cli.crawler.github.Github") as MockGithub:
        instance = MockGithub.return_value
        instance.get_user.return_value = mock_user
        instance.get_repo.side_effect = GithubException(404, "Not Found", None)

        crawler = GithubCrawler(token=None)
        result = crawler.crawl("southwestmogrown")

    profile = result["profile"]
    for field in ("name", "login", "bio", "location", "blog", "company",
                  "public_repos", "followers", "profile_readme", "avatar_url"):
        assert field in profile, f"Missing profile field: {field}"

    assert profile["login"] == "southwestmogrown"
    assert profile["name"] == "Southwest Mo Grown"
    assert profile["bio"] == "Gardening and code."
    assert profile["avatar_url"] == "https://avatars.githubusercontent.com/u/1"


def test_crawl_empty_repos_when_no_public_repos():
    """crawl() returns empty repos list when user has no public repositories."""
    mock_user = _make_mock_user()
    mock_user.get_repos.return_value = []

    with patch("cli.crawler.github.Github") as MockGithub:
        instance = MockGithub.return_value
        instance.get_user.return_value = mock_user
        instance.get_repo.side_effect = GithubException(404, "Not Found", None)

        crawler = GithubCrawler(token=None)
        result = crawler.crawl("southwestmogrown")

    assert result["repos"] == []


def test_crawl_skips_forks():
    """crawl() skips forked repositories."""
    mock_user = _make_mock_user()
    fork_repo = MagicMock()
    fork_repo.name = "forked-project"
    fork_repo.fork = True
    fork_repo.size = 100
    mock_user.get_repos.return_value = [fork_repo]

    with patch("cli.crawler.github.Github") as MockGithub:
        instance = MockGithub.return_value
        instance.get_user.return_value = mock_user
        instance.get_repo.side_effect = GithubException(404, "Not Found", None)

        crawler = GithubCrawler(token=None)
        result = crawler.crawl("southwestmogrown")

    assert result["repos"] == []


def test_crawl_skips_profile_readme_repo():
    """crawl() skips the username/username profile README repo from the repo list."""
    mock_user = _make_mock_user(login="myuser")
    profile_repo = MagicMock()
    profile_repo.name = "myuser"  # same as login — profile README repo
    profile_repo.fork = False
    profile_repo.size = 10
    mock_user.get_repos.return_value = [profile_repo]

    with patch("cli.crawler.github.Github") as MockGithub:
        instance = MockGithub.return_value
        instance.get_user.return_value = mock_user
        instance.get_repo.side_effect = GithubException(404, "Not Found", None)

        crawler = GithubCrawler(token=None)
        result = crawler.crawl("myuser")

    assert result["repos"] == []


def test_crawl_raises_on_unknown_user():
    """crawl() raises ValueError for a non-existent GitHub user."""
    with patch("cli.crawler.github.Github") as MockGithub:
        instance = MockGithub.return_value
        instance.get_user.side_effect = GithubException(404, "Not Found", None)

        crawler = GithubCrawler(token=None)
        with pytest.raises(ValueError, match="not found"):
            crawler.crawl("this-user-does-not-exist-xyz")


def test_crawl_with_profile_readme():
    """crawl() includes profile README content when the profile repo exists."""
    mock_user = _make_mock_user()
    readme_content = b"# Hello World\nThis is my profile."

    mock_readme_file = MagicMock()
    mock_readme_file.decoded_content = readme_content

    mock_readme_repo = MagicMock()
    mock_readme_repo.get_contents.return_value = mock_readme_file

    with patch("cli.crawler.github.Github") as MockGithub:
        instance = MockGithub.return_value
        instance.get_user.return_value = mock_user
        instance.get_repo.return_value = mock_readme_repo

        crawler = GithubCrawler(token=None)
        result = crawler.crawl("southwestmogrown")

    assert "Hello World" in result["profile"]["profile_readme"]


def test_crawl_with_token():
    """GithubCrawler accepts a personal access token."""
    mock_user = _make_mock_user()

    with patch("cli.crawler.github.Github") as MockGithub:
        instance = MockGithub.return_value
        instance.get_user.return_value = mock_user
        instance.get_repo.side_effect = GithubException(404, "Not Found", None)

        crawler = GithubCrawler(token="ghp_test_token")
        result = crawler.crawl("southwestmogrown")

    MockGithub.assert_called_once_with("ghp_test_token")
    assert result["username"] == "southwestmogrown"


# ---------------------------------------------------------------------------
# Per-repo data-fetching tests
# ---------------------------------------------------------------------------


def _make_mock_repo(name="my-project", size=500):
    """Return a minimal mock repo with sensible defaults."""
    repo = MagicMock()
    repo.name = name
    repo.full_name = f"southwestmogrown/{name}"
    repo.fork = False
    repo.size = size
    repo.description = "A test project"
    repo.html_url = f"https://github.com/southwestmogrown/{name}"
    repo.homepage = ""
    repo.language = "Python"
    repo.stargazers_count = 3
    repo.forks_count = 1
    repo.private = False
    repo.created_at = MagicMock()
    repo.created_at.isoformat.return_value = "2024-01-01T00:00:00"
    repo.updated_at = MagicMock()
    repo.updated_at.isoformat.return_value = "2024-06-01T00:00:00"
    repo.get_topics.return_value = ["python", "cli"]
    repo.get_languages.return_value = {"Python": 8000, "Shell": 200}
    # No commits, no readme, no structure by default — overridden per test
    repo.get_commits.return_value = []
    repo.get_contents.side_effect = GithubException(404, "Not Found", None)
    return repo


def test_process_repo_skips_empty_repos():
    """_process_repo() returns None for repos with size == 0."""
    crawler = GithubCrawler.__new__(GithubCrawler)
    empty_repo = _make_mock_repo(size=0)
    assert crawler._process_repo(empty_repo) is None


def test_process_repo_returns_required_fields():
    """_process_repo() returns a dict with all required keys."""
    crawler = GithubCrawler.__new__(GithubCrawler)
    repo = _make_mock_repo()

    result = crawler._process_repo(repo)

    assert result is not None
    for key in (
        "name", "full_name", "description", "url", "homepage",
        "topics", "language", "languages", "stars", "forks",
        "is_private", "created_at", "updated_at",
        "readme", "recent_commits", "structure",
    ):
        assert key in result, f"Missing key: {key}"


def test_get_readme_returns_content_for_readme_md():
    """_get_readme() returns content when README.md exists."""
    crawler = GithubCrawler.__new__(GithubCrawler)
    repo = _make_mock_repo()

    readme_file = MagicMock()
    readme_file.decoded_content = b"# My Project\nGreat stuff."
    repo.get_contents.side_effect = None
    repo.get_contents.return_value = readme_file

    content = crawler._get_readme(repo)

    assert "My Project" in content


def test_get_readme_falls_back_to_lowercase():
    """_get_readme() falls back to readme.md when README.md raises 404."""
    crawler = GithubCrawler.__new__(GithubCrawler)
    repo = _make_mock_repo()

    readme_file = MagicMock()
    readme_file.decoded_content = b"# Lower readme"

    def get_contents_side_effect(filename):
        if filename == "README.md":
            raise GithubException(404, "Not Found", None)
        return readme_file

    repo.get_contents.side_effect = get_contents_side_effect

    content = crawler._get_readme(repo)

    assert "Lower readme" in content


def test_get_readme_falls_back_to_rst():
    """_get_readme() falls back to README.rst when .md variants raise 404."""
    crawler = GithubCrawler.__new__(GithubCrawler)
    repo = _make_mock_repo()

    readme_file = MagicMock()
    readme_file.decoded_content = b"RST readme content"

    def get_contents_side_effect(filename):
        if filename in ("README.md", "readme.md"):
            raise GithubException(404, "Not Found", None)
        return readme_file

    repo.get_contents.side_effect = get_contents_side_effect

    content = crawler._get_readme(repo)

    assert "RST readme content" in content


def test_get_readme_returns_empty_when_no_readme_exists():
    """_get_readme() returns empty string when no README variant is found."""
    crawler = GithubCrawler.__new__(GithubCrawler)
    repo = _make_mock_repo()
    repo.get_contents.side_effect = GithubException(404, "Not Found", None)

    content = crawler._get_readme(repo)

    assert content == ""


def test_get_recent_commits_returns_first_line_only():
    """_get_recent_commits() returns only the first line of each commit message."""
    crawler = GithubCrawler.__new__(GithubCrawler)
    repo = _make_mock_repo()

    def _make_commit(msg):
        c = MagicMock()
        c.commit.message = msg
        return c

    repo.get_commits.return_value = [
        _make_commit("Add feature X\n\nDetailed explanation here."),
        _make_commit("Fix bug\n\nMore details about the bug."),
        _make_commit("Single line commit"),
    ]

    commits = crawler._get_recent_commits(repo)

    assert commits == ["Add feature X", "Fix bug", "Single line commit"]


def test_get_recent_commits_respects_limit():
    """_get_recent_commits() returns at most 10 commit messages."""
    crawler = GithubCrawler.__new__(GithubCrawler)
    repo = _make_mock_repo()

    def _make_commit(i):
        c = MagicMock()
        c.commit.message = f"Commit {i}"
        return c

    # Simulate 15 commits available; slicing [:10] should limit to 10
    repo.get_commits.return_value = [_make_commit(i) for i in range(15)]

    commits = crawler._get_recent_commits(repo)

    assert len(commits) == 10


def test_get_recent_commits_returns_empty_on_error():
    """_get_recent_commits() returns [] when GitHub raises an exception."""
    crawler = GithubCrawler.__new__(GithubCrawler)
    repo = _make_mock_repo()
    repo.get_commits.side_effect = GithubException(409, "Empty repository", None)

    commits = crawler._get_recent_commits(repo)

    assert commits == []


def test_get_structure_returns_sorted_list_with_dir_suffix():
    """_get_structure() returns sorted items with '/' suffix for directories."""
    crawler = GithubCrawler.__new__(GithubCrawler)
    repo = _make_mock_repo()

    def _make_item(name, item_type):
        item = MagicMock()
        item.name = name
        item.type = item_type
        return item

    repo.get_contents.side_effect = None
    repo.get_contents.return_value = [
        _make_item("src", "dir"),
        _make_item("README.md", "file"),
        _make_item("tests", "dir"),
        _make_item("setup.py", "file"),
    ]

    structure = crawler._get_structure(repo)

    assert "src/" in structure
    assert "tests/" in structure
    assert "README.md" in structure
    assert "setup.py" in structure
    assert structure == sorted(structure)


def test_get_structure_returns_empty_on_error():
    """_get_structure() returns [] when GitHub raises an exception."""
    crawler = GithubCrawler.__new__(GithubCrawler)
    repo = _make_mock_repo()
    repo.get_contents.side_effect = GithubException(404, "Not Found", None)

    structure = crawler._get_structure(repo)

    assert structure == []


def test_get_languages_returns_dict():
    """_get_languages() returns a dict of language -> byte counts."""
    crawler = GithubCrawler.__new__(GithubCrawler)
    repo = _make_mock_repo()
    repo.get_languages.return_value = {"Python": 9000, "JavaScript": 1500}

    languages = crawler._get_languages(repo)

    assert languages == {"Python": 9000, "JavaScript": 1500}
    assert isinstance(languages, dict)


def test_get_languages_returns_empty_on_error():
    """_get_languages() returns {} when GitHub raises an exception."""
    crawler = GithubCrawler.__new__(GithubCrawler)
    repo = _make_mock_repo()
    repo.get_languages.side_effect = GithubException(403, "Forbidden", None)

    languages = crawler._get_languages(repo)

    assert languages == {}


def test_crawl_with_full_repo_data():
    """crawl() returns repos with readme, commits, and structure populated."""
    mock_user = _make_mock_user()

    repo = _make_mock_repo()

    # README
    readme_file = MagicMock()
    readme_file.decoded_content = b"# my-project\nA great project."

    # Commits
    def _make_commit(msg):
        c = MagicMock()
        c.commit.message = msg
        return c

    repo.get_commits.return_value = [
        _make_commit("Initial commit"),
        _make_commit("Add tests\n\nCovers edge cases."),
    ]

    # Structure
    def _make_item(name, item_type):
        item = MagicMock()
        item.name = name
        item.type = item_type
        return item

    def get_contents_side_effect(path):
        if path == "":
            return [_make_item("src", "dir"), _make_item("README.md", "file")]
        # README.md fetch
        return readme_file

    repo.get_contents.side_effect = get_contents_side_effect
    mock_user.get_repos.return_value = [repo]

    with patch("cli.crawler.github.Github") as MockGithub:
        instance = MockGithub.return_value
        instance.get_user.return_value = mock_user
        instance.get_repo.side_effect = GithubException(404, "Not Found", None)

        crawler = GithubCrawler(token=None)
        result = crawler.crawl("southwestmogrown")

    assert len(result["repos"]) == 1
    repo_data = result["repos"][0]
    assert repo_data["readme"] != ""
    assert len(repo_data["recent_commits"]) == 2
    assert repo_data["recent_commits"][1] == "Add tests"
    assert "src/" in repo_data["structure"]
    assert "README.md" in repo_data["structure"]
    assert repo_data["languages"] == {"Python": 8000, "Shell": 200}
