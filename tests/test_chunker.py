"""Unit tests for the Chunker README parsing helpers.

Covers:
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
        expected_headings = ["Features", "Tech Stack", "Architecture", "Getting Started", "API Reference", "Contributing", "License"]
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
        assert "event-driven" in content.lower() or "FastAPI" in content or "Redis" in content

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
