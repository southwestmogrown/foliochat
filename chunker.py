"""
Chunker — splits portfolio data into semantic units for embedding.

The key insight: naive character-count chunking destroys context.
A README section about architecture should stay together.
A project's tech stack is one unit of meaning.

Chunk types:
  - identity       : Who is this developer (one per portfolio)
  - project_overview : Elevator pitch per repo
  - project_detail   : Per README section
  - project_tech     : Stack/languages per repo
  - project_story    : The "why" — intro + commit narrative
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Chunk:
    id: str
    type: str                    # identity | project_overview | project_detail | project_tech | project_story
    content: str
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        self.content = self.content.strip()


class Chunker:
    def chunk(self, portfolio_data: dict) -> list[Chunk]:
        chunks = []

        # One identity chunk for the whole portfolio
        chunks.append(self._identity_chunk(portfolio_data))

        for repo in portfolio_data["repos"]:
            chunks.append(self._overview_chunk(repo, portfolio_data["username"]))
            chunks.append(self._tech_chunk(repo, portfolio_data["username"]))
            chunks.append(self._story_chunk(repo, portfolio_data["username"]))
            chunks.extend(self._detail_chunks(repo, portfolio_data["username"]))

        # Filter empty chunks
        return [c for c in chunks if len(c.content) > 20]

    # ── Chunk builders ────────────────────────────────────────────────────────

    def _identity_chunk(self, portfolio_data: dict) -> Chunk:
        """
        Who is this developer — synthesized from profile + all repos.
        The chatbot's foundational context.
        """
        profile = portfolio_data["profile"]
        repos = portfolio_data["repos"]

        all_topics = set()
        all_languages = set()
        for repo in repos:
            all_topics.update(repo.get("topics", []))
            if repo.get("language"):
                all_languages.add(repo["language"])

        parts = [
            f"Developer: {profile['name']} (@{profile['login']})",
        ]
        if profile["bio"]:
            parts.append(f"Bio: {profile['bio']}")
        if profile["location"]:
            parts.append(f"Location: {profile['location']}")
        if profile["company"]:
            parts.append(f"Company: {profile['company']}")
        if all_languages:
            parts.append(f"Languages used: {', '.join(sorted(all_languages))}")
        if all_topics:
            parts.append(f"Topics / interests: {', '.join(sorted(all_topics))}")

        parts.append(f"Public repositories: {len(repos)}")

        repo_names = [r["name"] for r in repos]
        parts.append(f"Projects: {', '.join(repo_names)}")

        if profile["profile_readme"]:
            # Include first 500 chars of profile README — captures their own voice
            readme_intro = profile["profile_readme"][:500].strip()
            parts.append(f"\nProfile README:\n{readme_intro}")

        return Chunk(
            id="identity",
            type="identity",
            content="\n".join(parts),
            metadata={
                "username": portfolio_data["username"],
                "repo_count": len(repos),
            }
        )

    def _overview_chunk(self, repo: dict, username: str) -> Chunk:
        """
        Elevator pitch for a single repo.
        Answers: "Tell me about X project."
        """
        parts = [f"Project: {repo['name']}"]

        if repo["description"]:
            parts.append(f"Description: {repo['description']}")
        if repo["topics"]:
            parts.append(f"Topics: {', '.join(repo['topics'])}")
        if repo["language"]:
            parts.append(f"Primary language: {repo['language']}")
        if repo["homepage"]:
            parts.append(f"Live at: {repo['homepage']}")

        parts.append(f"Repository: {repo['url']}")

        return Chunk(
            id=f"{repo['name']}_overview",
            type="project_overview",
            content="\n".join(parts),
            metadata={
                "username": username,
                "repo": repo["name"],
                "url": repo["url"],
            }
        )

    def _tech_chunk(self, repo: dict, username: str) -> Chunk:
        """
        Pure tech signal per repo.
        Answers: "Do you have experience with PostgreSQL?"
        """
        parts = [f"Tech stack for {repo['name']}:"]

        if repo["language"]:
            parts.append(f"Primary language: {repo['language']}")

        if repo["languages"]:
            lang_list = sorted(repo["languages"].keys())
            parts.append(f"All languages: {', '.join(lang_list)}")

        if repo["topics"]:
            parts.append(f"Topics/tags: {', '.join(repo['topics'])}")

        # Extract tech stack table from README if present
        tech_section = self._extract_readme_section(
            repo["readme"],
            ["tech stack", "stack", "technologies", "built with", "dependencies"]
        )
        if tech_section:
            parts.append(f"\nFrom README:\n{tech_section[:600]}")

        return Chunk(
            id=f"{repo['name']}_tech",
            type="project_tech",
            content="\n".join(parts),
            metadata={
                "username": username,
                "repo": repo["name"],
                "languages": list(repo["languages"].keys()),
                "topics": repo["topics"],
            }
        )

    def _story_chunk(self, repo: dict, username: str) -> Chunk:
        """
        The "why" behind a project.
        Built from README intro + recent commit narrative.
        Answers: "Why did you build X?"
        """
        parts = [f"Story behind {repo['name']}:"]

        # First meaningful paragraph from README
        if repo["readme"]:
            intro = self._extract_readme_intro(repo["readme"])
            if intro:
                parts.append(f"From README:\n{intro}")

        # Commit history as narrative
        if repo["recent_commits"]:
            commits = repo["recent_commits"][:8]
            parts.append("\nRecent development activity:\n" + "\n".join(f"- {c}" for c in commits))

        if repo["structure"]:
            parts.append("\nProject structure:\n" + "\n".join(repo["structure"][:15]))

        return Chunk(
            id=f"{repo['name']}_story",
            type="project_story",
            content="\n".join(parts),
            metadata={
                "username": username,
                "repo": repo["name"],
            }
        )

    def _detail_chunks(self, repo: dict, username: str) -> list[Chunk]:
        """
        One chunk per README section.
        Preserves section context — architecture stays with architecture.
        """
        if not repo["readme"]:
            return []

        sections = self._split_readme_sections(repo["readme"])
        chunks = []

        for i, (heading, content) in enumerate(sections):
            if len(content.strip()) < 30:
                continue

            chunk_content = f"{repo['name']} — {heading}\n\n{content[:1000]}" if heading else content[:1000]

            chunks.append(Chunk(
                id=f"{repo['name']}_detail_{i}",
                type="project_detail",
                content=chunk_content,
                metadata={
                    "username": username,
                    "repo": repo["name"],
                    "section": heading or "intro",
                }
            ))

        return chunks

    # ── README parsing helpers ────────────────────────────────────────────────

    def _split_readme_sections(self, readme: str) -> list[tuple[str, str]]:
        """Split README by markdown headings into (heading, content) pairs."""
        sections = []
        current_heading = ""
        current_lines = []

        for line in readme.split("\n"):
            heading_match = re.match(r"^#{1,3}\s+(.+)", line)
            if heading_match:
                if current_lines:
                    sections.append((current_heading, "\n".join(current_lines).strip()))
                current_heading = heading_match.group(1).strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_heading, "\n".join(current_lines).strip()))

        return sections

    def _extract_readme_intro(self, readme: str, max_chars: int = 400) -> str:
        """
        Extract the first meaningful paragraph from a README.
        Skips badges, empty lines, and HTML.
        """
        lines = readme.split("\n")
        intro_lines = []
        found_content = False

        for line in lines:
            stripped = line.strip()

            # Skip badges, HTML, empty lines at the start
            if not found_content:
                if (not stripped or
                    stripped.startswith("![") or
                    stripped.startswith("<") or
                    stripped.startswith("#")):
                    continue
                found_content = True

            if found_content:
                if not stripped and intro_lines:
                    break  # End of first paragraph
                if stripped:
                    intro_lines.append(stripped)

        result = " ".join(intro_lines)
        return result[:max_chars] if len(result) > max_chars else result

    def _extract_readme_section(self, readme: str, section_names: list[str]) -> Optional[str]:
        """Find a README section by heading name (case-insensitive)."""
        if not readme:
            return None

        sections = self._split_readme_sections(readme)
        for heading, content in sections:
            if any(name in heading.lower() for name in section_names):
                return content

        return None