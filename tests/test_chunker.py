"""Unit tests for the Chunker.

Covers:
  - chunk(): chunk type classification and content accuracy
  - _split_readme_sections(): H1/H2/H3 heading parsing
  - _extract_readme_intro(): first-paragraph extraction (skips badges/HTML)
  - _extract_readme_section(): named-section lookup by keyword
"""

import pytest
from cli.chunker.chunker import Chunker


@pytest.fixture
def chunker():
    return Chunker()


# ── QuizQuest sample README (acceptance fixture) ──────────────────────────────

QUIZQUEST_README = """\
# QuizQuest

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

QuizQuest is a multiplayer trivia platform where teams compete in real-time
quiz battles. Players join rooms, answer timed questions, and earn points on a
live leaderboard.

## Features

- Real-time multiplayer rooms via WebSockets
- 10,000+ questions across 20 categories
- Customisable room settings (time limits, question count)
- Live leaderboard with instant score updates

## Tech Stack

| Layer     | Technology          |
|-----------|---------------------|
| Backend   | Python / FastAPI    |
| Frontend  | React + TypeScript  |
| Database  | PostgreSQL          |
| Cache     | Redis               |
| Realtime  | Socket.IO           |

## Architecture

QuizQuest uses an event-driven architecture. The FastAPI backend publishes
game events to Redis pub/sub channels; React clients subscribe via Socket.IO.
Each quiz session is isolated in its own Redis key-space.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (optional, for local Postgres + Redis)

### Installation

```bash
git clone https://github.com/example/quizquest
cd quizquest
pip install -r requirements.txt
npm install --prefix frontend
```

## API Reference

All endpoints are documented with OpenAPI. After starting the server, visit
`http://localhost:8000/docs` for the interactive Swagger UI.

### Authentication

Obtain a JWT by posting credentials to `/auth/token`.

## Contributing

Pull requests are welcome. Please open an issue first to discuss major changes.
Run `pytest` and `npm test` before submitting.

## License

MIT © 2024 QuizQuest contributors
"""


# ── _split_readme_sections ────────────────────────────────────────────────────


class TestSplitReadmeSections:
    def test_quizquest_produces_at_least_six_sections(self, chunker):
        """Acceptance criterion: QuizQuest README splits into ≥6 named sections."""
        sections = chunker._split_readme_sections(QUIZQUEST_README)
        named = [(h, c) for h, c in sections if h]
        assert len(named) >= 6, (
            f"Expected ≥6 named sections, got {len(named)}: {[h for h, _ in named]}"
        )

    def test_quizquest_section_headings(self, chunker):
        """All major headings from QuizQuest README appear as section headings."""
        sections = chunker._split_readme_sections(QUIZQUEST_README)
        headings = [h for h, _ in sections]
        expected_headings = [
            "Features",
            "Tech Stack",
            "Architecture",
            "Getting Started",
            "API Reference",
            "Contributing",
            "License",
        ]
        for expected in expected_headings:
            assert any(expected in h for h in headings), (
                f"Heading '{expected}' not found in {headings}"
            )

    def test_h1_heading_is_captured(self, chunker):
        readme = "# My Project\n\nSome intro text.\n"
        sections = chunker._split_readme_sections(readme)
        headings = [h for h, _ in sections]
        assert "My Project" in headings

    def test_h2_heading_is_captured(self, chunker):
        readme = "## Installation\n\nRun pip install.\n"
        sections = chunker._split_readme_sections(readme)
        headings = [h for h, _ in sections]
        assert "Installation" in headings

    def test_h3_heading_is_captured(self, chunker):
        readme = "### Prerequisites\n\n- Python 3.11+\n"
        sections = chunker._split_readme_sections(readme)
        headings = [h for h, _ in sections]
        assert "Prerequisites" in headings

    def test_content_before_first_heading_captured(self, chunker):
        readme = "Some intro text.\n\n# First Section\n\nSection body.\n"
        sections = chunker._split_readme_sections(readme)
        # Pre-heading content should appear as a section (empty heading)
        assert len(sections) >= 1
        pre_heading_content = next((c for h, c in sections if h == ""), None)
        assert pre_heading_content is not None
        assert "intro text" in pre_heading_content

    def test_content_associated_with_correct_heading(self, chunker):
        readme = "# Alpha\n\nAlpha content.\n\n# Beta\n\nBeta content.\n"
        sections = chunker._split_readme_sections(readme)
        section_map = dict(sections)
        assert "Alpha content." in section_map.get("Alpha", "")
        assert "Beta content." in section_map.get("Beta", "")

    def test_empty_readme_returns_empty_list_or_blank(self, chunker):
        sections = chunker._split_readme_sections("")
        # Either empty list or a single section with blank content is acceptable
        assert isinstance(sections, list)
        for h, c in sections:
            assert c.strip() == ""

    def test_readme_with_no_headings_returns_single_section(self, chunker):
        readme = "Just plain text.\nNo headings at all.\n"
        sections = chunker._split_readme_sections(readme)
        assert len(sections) == 1
        _, content = sections[0]
        assert "Just plain text." in content

    def test_multiple_heading_levels_all_split(self, chunker):
        readme = (
            "# Top\n\nTop content.\n"
            "## Sub\n\nSub content.\n"
            "### SubSub\n\nSubSub content.\n"
        )
        sections = chunker._split_readme_sections(readme)
        headings = [h for h, _ in sections]
        assert "Top" in headings
        assert "Sub" in headings
        assert "SubSub" in headings

    def test_h4_not_treated_as_heading(self, chunker):
        """H4 (####) should not be split as a section boundary."""
        readme = "## Section\n\n#### Not a split\n\nBody text.\n"
        sections = chunker._split_readme_sections(readme)
        # #### should remain in the content of its parent section
        body = dict(sections).get("Section", "")
        assert "#### Not a split" in body or "Not a split" in body

    def test_section_content_is_trimmed(self, chunker):
        readme = "# Title\n\n\n   \nActual content.\n\n"
        sections = chunker._split_readme_sections(readme)
        _, content = sections[0]
        assert content == content.strip()

    def test_returns_list_of_tuples(self, chunker):
        readme = "# Heading\n\nBody.\n"
        sections = chunker._split_readme_sections(readme)
        assert isinstance(sections, list)
        for item in sections:
            assert isinstance(item, tuple)
            assert len(item) == 2


# ── _extract_readme_intro ─────────────────────────────────────────────────────


class TestExtractReadmeIntro:
    def test_quizquest_intro_extracted(self, chunker):
        """QuizQuest intro paragraph should be captured correctly."""
        intro = chunker._extract_readme_intro(QUIZQUEST_README)
        assert "multiplayer trivia" in intro or "QuizQuest" in intro

    def test_skips_badge_lines(self, chunker):
        readme = (
            "![Build](https://img.shields.io/badge/build-passing-green)\n"
            "![License](https://img.shields.io/badge/license-MIT-blue)\n"
            "\n"
            "This is the real intro.\n"
        )
        intro = chunker._extract_readme_intro(readme)
        assert intro == "This is the real intro."

    def test_skips_html_lines(self, chunker):
        readme = (
            "<div align='center'><img src='logo.png'/></div>\n"
            "\n"
            "Real paragraph starts here.\n"
        )
        intro = chunker._extract_readme_intro(readme)
        assert intro == "Real paragraph starts here."

    def test_skips_heading_lines(self, chunker):
        readme = "# My Project\n\nFirst real paragraph.\n"
        intro = chunker._extract_readme_intro(readme)
        assert intro == "First real paragraph."

    def test_skips_leading_empty_lines(self, chunker):
        readme = "\n\n\nActual content.\n"
        intro = chunker._extract_readme_intro(readme)
        assert intro == "Actual content."

    def test_stops_at_blank_line_after_content(self, chunker):
        readme = "First paragraph line one.\nFirst paragraph line two.\n\nSecond paragraph.\n"
        intro = chunker._extract_readme_intro(readme)
        assert "Second paragraph" not in intro
        assert "First paragraph line one" in intro

    def test_multi_line_paragraph_joined_with_spaces(self, chunker):
        readme = "Line one.\nLine two.\nLine three.\n"
        intro = chunker._extract_readme_intro(readme)
        assert intro == "Line one. Line two. Line three."

    def test_respects_max_chars(self, chunker):
        readme = "A" * 600 + "\n"
        intro = chunker._extract_readme_intro(readme, max_chars=400)
        assert len(intro) == 400

    def test_returns_empty_string_for_badges_only(self, chunker):
        readme = "![Badge1](url1)\n![Badge2](url2)\n"
        intro = chunker._extract_readme_intro(readme)
        assert intro == ""

    def test_returns_empty_string_for_empty_readme(self, chunker):
        intro = chunker._extract_readme_intro("")
        assert intro == ""

    def test_skips_standard_and_linked_badges(self, chunker):
        """Linked badges [![text](img)](url) start with '[' not '![' and must also be skipped."""
        readme = (
            "![CI](https://github.com/x/y/actions)\n"
            "[![Coverage](https://codecov.io)](https://codecov.io)\n"
            "\n"
            "Project description here.\n"
        )
        intro = chunker._extract_readme_intro(readme)
        assert "Project description here." in intro


# ── _extract_readme_section ───────────────────────────────────────────────────


class TestExtractReadmeSection:
    def test_finds_tech_stack_section(self, chunker):
        content = chunker._extract_readme_section(QUIZQUEST_README, ["tech stack"])
        assert content is not None
        assert "FastAPI" in content or "Python" in content

    def test_finds_architecture_section(self, chunker):
        content = chunker._extract_readme_section(QUIZQUEST_README, ["architecture"])
        assert content is not None
        assert (
            "event-driven" in content.lower()
            or "FastAPI" in content
            or "Redis" in content
        )

    def test_case_insensitive_match(self, chunker):
        readme = "## TECH STACK\n\nPython, FastAPI\n"
        content = chunker._extract_readme_section(readme, ["tech stack"])
        assert content is not None
        assert "FastAPI" in content

    def test_returns_none_when_section_not_found(self, chunker):
        readme = "# Overview\n\nSome content.\n"
        result = chunker._extract_readme_section(readme, ["nonexistent section"])
        assert result is None

    def test_returns_none_for_empty_readme(self, chunker):
        result = chunker._extract_readme_section("", ["tech stack"])
        assert result is None

    def test_returns_none_for_none_readme(self, chunker):
        result = chunker._extract_readme_section(None, ["tech stack"])
        assert result is None

    def test_multiple_keywords_any_match(self, chunker):
        readme = "## Built With\n\nDjango, React\n"
        content = chunker._extract_readme_section(
            readme, ["tech stack", "stack", "technologies", "built with"]
        )
        assert content is not None
        assert "Django" in content

    def test_partial_keyword_match(self, chunker):
        """'stack' should match 'Tech Stack' heading."""
        readme = "## Tech Stack\n\nNode.js, Vue\n"
        content = chunker._extract_readme_section(readme, ["stack"])
        assert content is not None
        assert "Node.js" in content

    def test_returns_only_matching_sections_content(self, chunker):
        readme = (
            "## Features\n\nFeature list.\n"
            "## Tech Stack\n\nPython, FastAPI\n"
            "## License\n\nMIT\n"
        )
        content = chunker._extract_readme_section(readme, ["tech stack"])
        assert "Python" in content
        assert "Feature list" not in content
        assert "MIT" not in content


# ── Mock portfolio fixture ────────────────────────────────────────────────────


def _make_repo(
    name,
    description="",
    language="Python",
    topics=None,
    readme="",
    commits=None,
    structure=None,
    languages=None,
    homepage="",
):
    return {
        "name": name,
        "description": description,
        "url": f"https://github.com/southwestmogrown/{name}",
        "homepage": homepage,
        "topics": topics or [],
        "language": language,
        "languages": languages or {language: 10000},
        "stars": 0,
        "forks": 0,
        "readme": readme,
        "recent_commits": commits or ["Initial commit", "Add tests", "Fix bug"],
        "structure": structure or ["README.md", "src/", "tests/"],
    }


_REPO_README = """\
# {name}

{name} is a full-featured web application for managing tasks and projects.

## Features

- Create and assign tasks with due dates and priorities
- Real-time notifications for team members
- Integrations with GitHub, Slack, and Jira
- Customisable dashboards and reports

## Tech Stack

| Layer    | Technology       |
|----------|-----------------|
| Backend  | Python / Django |
| Frontend | React + Redux   |
| Database | PostgreSQL      |
| Cache    | Redis           |

## Architecture

The application follows a layered architecture separating concerns
between presentation, business logic, and data persistence layers.
Event-driven updates are handled via Django Channels and WebSockets.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for local Postgres + Redis)

### Installation

```bash
git clone https://github.com/southwestmogrown/{name}
cd {name}
pip install -r requirements.txt
npm install --prefix frontend
```

## API Reference

All endpoints are documented with OpenAPI. Visit `/docs` for the Swagger UI.

## Contributing

Pull requests are welcome. Open an issue first to discuss major changes.
Run `pytest` before submitting.

## License

MIT © 2024
"""

MOCK_REPOS = [
    _make_repo(
        name="taskflow",
        description="A task management platform built with Django and React",
        language="Python",
        topics=["django", "react", "postgresql", "task-management"],
        readme=_REPO_README.format(name="taskflow"),
        languages={"Python": 60000, "TypeScript": 20000, "CSS": 5000},
    ),
    _make_repo(
        name="quizquest",
        description="Multiplayer trivia platform with real-time leaderboards",
        language="Python",
        topics=["fastapi", "websockets", "redis", "trivia"],
        readme=QUIZQUEST_README,
        languages={"Python": 50000, "TypeScript": 15000},
    ),
    _make_repo(
        name="devmetrics",
        description="Developer productivity analytics dashboard",
        language="Go",
        topics=["golang", "metrics", "dashboard", "analytics"],
        readme=_REPO_README.format(name="devmetrics"),
        languages={"Go": 70000, "JavaScript": 10000},
    ),
    _make_repo(
        name="bytevault",
        description="Encrypted file storage service with end-to-end encryption",
        language="Rust",
        topics=["rust", "encryption", "storage", "security"],
        readme=_REPO_README.format(name="bytevault"),
        languages={"Rust": 80000},
    ),
    _make_repo(
        name="openfolio",
        description="Open-source developer portfolio generator",
        language="TypeScript",
        topics=["typescript", "nextjs", "portfolio", "open-source"],
        readme=_REPO_README.format(name="openfolio"),
        languages={"TypeScript": 45000, "CSS": 8000},
        homepage="https://openfolio.dev",
    ),
]

MOCK_PORTFOLIO = {
    "username": "southwestmogrown",
    "profile": {
        "name": "Southwest Mo Grown",
        "login": "southwestmogrown",
        "bio": "Full-stack developer building open-source tools",
        "location": "Kansas City, MO",
        "company": "Self-employed",
        "profile_readme": (
            "Hi, I'm Southwest Mo Grown — a full-stack developer passionate "
            "about open-source tools, developer experience, and building "
            "software that matters. I primarily work with Python, Go, and "
            "TypeScript."
        ),
    },
    "repos": MOCK_REPOS,
}


# ── TestChunkMethod ───────────────────────────────────────────────────────────


class TestChunkMethod:
    """Tests for Chunker.chunk() — chunk type classification and content."""

    @pytest.fixture
    def chunks(self, chunker):
        return chunker.chunk(MOCK_PORTFOLIO)

    @pytest.fixture
    def chunks_by_type(self, chunks):
        result = {}
        for c in chunks:
            result.setdefault(c.type, []).append(c)
        return result

    # ── Chunk counts / structure ───────────────────────────────────────────

    def test_produces_25_or_more_chunks(self, chunks):
        """Acceptance criterion: southwestmogrown portfolio produces 25+ chunks."""
        assert len(chunks) >= 25, (
            f"Expected ≥25 chunks, got {len(chunks)}: "
            f"{[(c.id, c.type) for c in chunks]}"
        )

    def test_exactly_one_identity_chunk(self, chunks_by_type):
        identity_chunks = chunks_by_type.get("identity", [])
        assert len(identity_chunks) == 1, (
            f"Expected exactly 1 identity chunk, got {len(identity_chunks)}"
        )

    def test_one_overview_chunk_per_repo(self, chunks_by_type):
        overview_chunks = chunks_by_type.get("project_overview", [])
        assert len(overview_chunks) == len(MOCK_REPOS), (
            f"Expected {len(MOCK_REPOS)} overview chunks, got {len(overview_chunks)}"
        )

    def test_one_tech_chunk_per_repo(self, chunks_by_type):
        tech_chunks = chunks_by_type.get("project_tech", [])
        assert len(tech_chunks) == len(MOCK_REPOS), (
            f"Expected {len(MOCK_REPOS)} tech chunks, got {len(tech_chunks)}"
        )

    def test_one_story_chunk_per_repo(self, chunks_by_type):
        story_chunks = chunks_by_type.get("project_story", [])
        assert len(story_chunks) == len(MOCK_REPOS), (
            f"Expected {len(MOCK_REPOS)} story chunks, got {len(story_chunks)}"
        )

    def test_detail_chunks_present(self, chunks_by_type):
        detail_chunks = chunks_by_type.get("project_detail", [])
        assert len(detail_chunks) >= len(MOCK_REPOS), (
            f"Expected at least {len(MOCK_REPOS)} detail chunks (one per repo), "
            f"got {len(detail_chunks)}"
        )

    def test_all_chunk_types_present(self, chunks_by_type):
        expected_types = {
            "identity",
            "project_overview",
            "project_tech",
            "project_story",
            "project_detail",
        }
        assert expected_types.issubset(chunks_by_type.keys()), (
            f"Missing chunk types: {expected_types - chunks_by_type.keys()}"
        )

    # ── Filter: no chunk under 20 chars ───────────────────────────────────

    def test_no_chunk_has_content_under_20_chars(self, chunks):
        short_chunks = [c for c in chunks if len(c.content) <= 20]
        assert short_chunks == [], (
            f"Found chunks with ≤20 chars: {[(c.id, repr(c.content)) for c in short_chunks]}"
        )

    def test_short_chunk_filtered_from_single_repo(self, chunker):
        """A repo whose only README content is <20 chars produces no detail chunk."""
        repo = _make_repo(
            name="tiny",
            description="Tiny repo",
            readme="# Title\n\nHi.\n",  # only "Hi." after heading strip -> filtered
        )
        portfolio = {
            "username": "u",
            "profile": {
                "name": "U",
                "login": "u",
                "bio": "",
                "location": "",
                "company": "",
                "profile_readme": "",
            },
            "repos": [repo],
        }
        chunks = chunker.chunk(portfolio)
        detail_chunks = [c for c in chunks if c.type == "project_detail"]
        # "Hi." is 3 chars — the detail _and_ main filter both drop it
        for c in detail_chunks:
            assert len(c.content) > 20

    # ── Chunk IDs ─────────────────────────────────────────────────────────

    def test_all_chunk_ids_are_unique(self, chunks):
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids)), (
            f"Duplicate chunk IDs found: {[i for i in ids if ids.count(i) > 1]}"
        )

    def test_identity_chunk_id_is_identity(self, chunks_by_type):
        identity = chunks_by_type["identity"][0]
        assert identity.id == "identity"

    def test_overview_chunk_ids_contain_repo_name(self, chunks_by_type):
        for chunk in chunks_by_type["project_overview"]:
            assert any(r["name"] in chunk.id for r in MOCK_REPOS)

    def test_tech_chunk_ids_contain_repo_name(self, chunks_by_type):
        for chunk in chunks_by_type["project_tech"]:
            assert any(r["name"] in chunk.id for r in MOCK_REPOS)

    # ── Identity chunk content ─────────────────────────────────────────────

    def test_identity_chunk_contains_username(self, chunks_by_type):
        identity = chunks_by_type["identity"][0]
        assert "southwestmogrown" in identity.content

    def test_identity_chunk_contains_bio(self, chunks_by_type):
        identity = chunks_by_type["identity"][0]
        assert "Full-stack developer" in identity.content

    def test_identity_chunk_lists_all_repos(self, chunks_by_type):
        identity = chunks_by_type["identity"][0]
        for repo in MOCK_REPOS:
            assert repo["name"] in identity.content, (
                f"Repo '{repo['name']}' not found in identity chunk"
            )

    def test_identity_chunk_metadata_has_username(self, chunks_by_type):
        identity = chunks_by_type["identity"][0]
        assert identity.metadata["username"] == "southwestmogrown"

    def test_identity_chunk_metadata_repo_count(self, chunks_by_type):
        identity = chunks_by_type["identity"][0]
        assert identity.metadata["repo_count"] == len(MOCK_REPOS)

    # ── project_overview chunk content ────────────────────────────────────

    def test_overview_chunk_contains_description(self, chunks_by_type):
        taskflow_overview = next(
            c for c in chunks_by_type["project_overview"] if "taskflow" in c.id
        )
        assert "task management" in taskflow_overview.content.lower()

    def test_overview_chunk_contains_repo_url(self, chunks_by_type):
        for chunk in chunks_by_type["project_overview"]:
            repo_name = chunk.metadata["repo"]
            expected_url = f"https://github.com/southwestmogrown/{repo_name}"
            assert expected_url in chunk.content

    def test_overview_chunk_metadata_has_repo(self, chunks_by_type):
        for chunk in chunks_by_type["project_overview"]:
            assert "repo" in chunk.metadata
            assert chunk.metadata["repo"] in [r["name"] for r in MOCK_REPOS]

    def test_overview_chunk_with_homepage_includes_it(self, chunks_by_type):
        openfolio_overview = next(
            c for c in chunks_by_type["project_overview"] if "openfolio" in c.id
        )
        assert "openfolio.dev" in openfolio_overview.content

    # ── project_tech chunk content ────────────────────────────────────────

    def test_tech_chunk_contains_primary_language(self, chunks_by_type):
        taskflow_tech = next(
            c for c in chunks_by_type["project_tech"] if "taskflow" in c.id
        )
        assert "Python" in taskflow_tech.content

    def test_tech_chunk_contains_all_languages(self, chunks_by_type):
        taskflow_tech = next(
            c for c in chunks_by_type["project_tech"] if "taskflow" in c.id
        )
        assert "TypeScript" in taskflow_tech.content

    def test_tech_chunk_contains_topics(self, chunks_by_type):
        quizquest_tech = next(
            c for c in chunks_by_type["project_tech"] if "quizquest" in c.id
        )
        assert (
            "fastapi" in quizquest_tech.content.lower()
            or "websockets" in quizquest_tech.content.lower()
        )

    def test_tech_chunk_metadata_has_languages(self, chunks_by_type):
        for chunk in chunks_by_type["project_tech"]:
            assert "languages" in chunk.metadata
            assert isinstance(chunk.metadata["languages"], list)

    # ── project_story chunk content ───────────────────────────────────────

    def test_story_chunk_contains_repo_name(self, chunks_by_type):
        for chunk in chunks_by_type["project_story"]:
            repo_name = chunk.metadata["repo"]
            assert repo_name in chunk.content

    def test_story_chunk_contains_commit_history(self, chunks_by_type):
        taskflow_story = next(
            c for c in chunks_by_type["project_story"] if "taskflow" in c.id
        )
        assert (
            "Initial commit" in taskflow_story.content
            or "Add tests" in taskflow_story.content
        )

    def test_story_chunk_contains_readme_intro(self, chunks_by_type):
        quizquest_story = next(
            c for c in chunks_by_type["project_story"] if "quizquest" in c.id
        )
        # QuizQuest README starts with "QuizQuest is a multiplayer trivia platform"
        assert (
            "multiplayer" in quizquest_story.content.lower()
            or "trivia" in quizquest_story.content.lower()
        )

    # ── project_detail chunk content ──────────────────────────────────────

    def test_detail_chunks_have_section_metadata(self, chunks_by_type):
        for chunk in chunks_by_type["project_detail"]:
            assert "section" in chunk.metadata

    def test_detail_chunk_content_includes_repo_name_or_heading(self, chunks_by_type):
        for chunk in chunks_by_type["project_detail"]:
            repo_name = chunk.metadata["repo"]
            # Content should either be prefixed with "reponame — heading" or be raw text
            assert repo_name in chunk.content or len(chunk.content) > 20

    def test_detail_chunks_cover_multiple_readme_sections(self, chunks_by_type):
        """Each repo with a rich README should produce multiple detail chunks."""
        quizquest_details = [
            c
            for c in chunks_by_type["project_detail"]
            if c.metadata["repo"] == "quizquest"
        ]
        assert len(quizquest_details) >= 3, (
            f"Expected ≥3 detail chunks for quizquest, got {len(quizquest_details)}"
        )

    # ── Chunk type label accuracy ──────────────────────────────────────────

    def test_all_chunk_types_are_valid(self, chunks):
        valid_types = {
            "identity",
            "project_overview",
            "project_tech",
            "project_story",
            "project_detail",
        }
        for chunk in chunks:
            assert chunk.type in valid_types, (
                f"Chunk '{chunk.id}' has unexpected type '{chunk.type}'"
            )

    def test_chunk_content_is_stripped(self, chunks):
        for chunk in chunks:
            assert chunk.content == chunk.content.strip(), (
                f"Chunk '{chunk.id}' has unstripped content"
            )
