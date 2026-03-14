"""
GitHub crawler — fetches profile and repository data.

Pulls three content sources per repo:
  1. Metadata (name, description, topics, language, stars)
  2. README content
  3. Recent commit messages (last 10)
  4. Top-level folder structure

Rate limits:
  - Unauthenticated: 60 requests/hour
  - Authenticated:   5000 requests/hour

Always recommend a token for real usage.
"""

from datetime import datetime, timezone
import os
from typing import Optional
from github import Github, GithubException
from rich.console import Console
from rich.progress import track

console = Console()

# Repos to always skip
SKIP_REPOS = {
    # GitHub profile README repo (same name as username)
    # handled separately below
}

# File extensions worth noting in structure
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs",
    ".java", ".rb", ".php", ".cs", ".cpp", ".c"
}


class GithubCrawler:
    def __init__(self, token: Optional[str] = None):
        token = token or os.environ.get("GITHUB_TOKEN")
        self.gh = Github(token) if token else Github()

    def crawl(self, username: str, include_private: bool = False) -> dict:
        """
        Crawl a GitHub profile and return structured portfolio data.
        """
        try:
            user = self.gh.get_user(username)
        except GithubException as e:
            raise ValueError(f"GitHub user '{username}' not found: {e}")

        profile = self._get_profile(user)
        repos = self._get_repos(user, include_private=include_private)

        return {
            "username": username,
            "profile": profile,
            "repos": repos,
            "crawled_at": datetime.now(timezone.utc).isoformat(),
        }

    def _get_profile(self, user) -> dict:
        """Extract profile-level data."""
        # Try to get profile README
        profile_readme = ""
        try:
            readme_repo = self.gh.get_repo(f"{user.login}/{user.login}")
            readme_file = readme_repo.get_contents("README.md")
            profile_readme = readme_file.decoded_content.decode("utf-8")
        except GithubException:
            pass  # No profile README — that's fine

        return {
            "name": user.name or user.login,
            "login": user.login,
            "bio": user.bio or "",
            "location": user.location or "",
            "blog": user.blog or "",
            "company": user.company or "",
            "public_repos": user.public_repos,
            "followers": user.followers,
            "profile_readme": profile_readme,
            "avatar_url": user.avatar_url,
        }

    def _get_repos(self, user, include_private: bool = False) -> list[dict]:
        """Fetch and process all repos."""
        repos = []
        visibility = "all" if include_private else "public"

        all_repos = list(user.get_repos(type=visibility, sort="updated"))

        # Skip the profile README repo
        all_repos = [r for r in all_repos if r.name != user.login]

        # Skip forks by default — they don't represent original work
        original_repos = [r for r in all_repos if not r.fork]

        for repo in track(original_repos, description="  Fetching repos..."):
            try:
                repo_data = self._process_repo(repo)
                if repo_data:
                    repos.append(repo_data)
            except GithubException as e:
                console.print(f"  [yellow]⚠[/yellow] Skipping {repo.name}: {e}")
                continue

        return repos

    def _process_repo(self, repo) -> Optional[dict]:
        """Process a single repository into structured data."""
        # Skip empty repos
        if repo.size == 0:
            return None

        readme = self._get_readme(repo)
        commits = self._get_recent_commits(repo)
        structure = self._get_structure(repo)
        languages = self._get_languages(repo)

        return {
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description or "",
            "url": repo.html_url,
            "homepage": repo.homepage or "",
            "topics": repo.get_topics(),
            "language": repo.language or "",
            "languages": languages,
            "stars": repo.stargazers_count,
            "forks": repo.forks_count,
            "is_private": repo.private,
            "created_at": repo.created_at.isoformat(),
            "updated_at": repo.updated_at.isoformat(),
            "readme": readme,
            "recent_commits": commits,
            "structure": structure,
        }

    def _get_readme(self, repo) -> str:
        """Fetch README content."""
        for filename in ["README.md", "readme.md", "README.rst", "README.txt", "README"]:
            try:
                content = repo.get_contents(filename)
                return content.decoded_content.decode("utf-8")
            except GithubException:
                continue
        return ""

    def _get_recent_commits(self, repo, limit: int = 10) -> list[str]:
        """Get recent commit messages — reveal how the developer works."""
        try:
            commits = repo.get_commits()[:limit]
            return [c.commit.message.split("\n")[0] for c in commits]
        except GithubException:
            return []

    def _get_structure(self, repo) -> list[str]:
        """
        Get top-level folder/file structure.
        Reveals architectural intent without the noise of full code.
        """
        try:
            contents = repo.get_contents("")
            structure = []
            for item in contents:
                if item.type == "dir":
                    structure.append(f"{item.name}/")
                else:
                    structure.append(item.name)
            return sorted(structure)
        except GithubException:
            return []

    def _get_languages(self, repo) -> dict[str, int]:
        """Get language breakdown (bytes per language)."""
        try:
            return dict(repo.get_languages())
        except GithubException:
            return {}