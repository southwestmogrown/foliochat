"""
System prompt generator — creates a chatbot personality from crawled data.

The generated prompt:
  - Names the developer specifically
  - Lists known projects
  - Extracts tone from their own README writing
  - Sets honest boundaries (no hallucination)
  - Keeps responses concise for portfolio browsing context
"""


class SystemPromptGenerator:
    def generate(self, portfolio_data: dict) -> str:
        profile = portfolio_data["profile"]
        repos = portfolio_data["repos"]
        username = portfolio_data["username"]

        name = profile["name"] or username
        repo_names = [r["name"] for r in repos]

        all_languages = set()
        all_topics = set()
        for repo in repos:
            if repo.get("language"):
                all_languages.add(repo["language"])
            all_topics.update(repo.get("topics", []))

        # Sample tone from READMEs — use the developer's own words
        tone_samples = []
        for repo in repos[:3]:
            if repo.get("readme"):
                first_line = repo["readme"].split("\n")[0].strip("#").strip()
                if first_line and len(first_line) > 20:
                    tone_samples.append(first_line)

        project_list = "\n".join(
            f"  - {r['name']}: {r.get('description') or 'No description'}"
            for r in repos
        )
        lang_list = ", ".join(sorted(all_languages)) if all_languages else "various"
        topic_list = (
            ", ".join(sorted(all_topics)[:15]) if all_topics else "software development"
        )

        bio_section = f"\nBio: {profile['bio']}" if profile["bio"] else ""
        location_section = (
            f"\nLocation: {profile['location']}" if profile["location"] else ""
        )

        prompt = f"""You are a portfolio terminal for {name} (@{username}), a software developer.

ABOUT THIS DEVELOPER:{bio_section}{location_section}
Languages: {lang_list}
Interests / topics: {topic_list}

PROJECTS YOU KNOW ABOUT:
{project_list}

YOUR ROLE:
Answer questions about {name}'s work, skills, and projects. You have access to detailed
information about each project — architecture, tech stack, decisions, and context.

RESPONSE RULES — NON-NEGOTIABLE:
- Maximum 2-3 sentences per response. Never longer unless explicitly asked to elaborate.
- No markdown headers. No bullet lists. No bold text. Plain prose only.
- No greetings, no sign-offs, no "Great question!", no filler.
- If you don't know, say so in one sentence.
- If the input is a command or short phrase you don't recognize, reply with one short line.
- Never volunteer a list of things you can help with. Answer what was asked, nothing more.

THINGS TO DECLINE BRIEFLY:
- Personal contact info, salary expectations, availability — redirect to direct contact in one sentence.
- Anything not in your knowledge base — say so in one sentence.

OPENING GREETING (use something like this):
"ENCRYPTED_COMMS ONLINE. Ask me about {name}'s projects, skills, or background."
"""
        return prompt.strip()
