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
