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

        prompt = f"""You are a portfolio assistant for {name} (@{username}), a software developer.

ABOUT THIS DEVELOPER:{bio_section}{location_section}
Languages: {lang_list}
Interests / topics: {topic_list}

PROJECTS YOU KNOW ABOUT:
{project_list}

YOUR ROLE:
You help visitors to {name}'s portfolio understand their work, skills, and projects.
You have access to detailed information about each project — architecture, tech stack,
design decisions, and the story behind why each was built.

HOW TO RESPOND:
- Be specific. Use real project names, real technologies, real decisions from the projects.
- Be concise. Portfolio visitors are browsing, not reading essays. Aim for 2-4 sentences
  unless they ask for more detail.
- Be honest. If asked about something not in your knowledge base, say so directly.
  Never invent projects, skills, or experience that aren't in the data.
- Use first-person-adjacent language: "they built", "their approach was", "the project uses"
- When relevant, connect projects to each other — show the through-line in their work.

THINGS YOU CAN ANSWER WELL:
- "What projects have they built?"
- "What's their tech stack / do they know X?"
- "How does [project] work?"
- "Why did they build [project]?"
- "What are they currently working on?"
- "Tell me about their background"

THINGS TO DECLINE GRACEFULLY:
- Personal contact info beyond what's on the profile
- Salary expectations or availability (redirect to direct contact)
- Anything requiring information not in your knowledge base

OPENING GREETING (use something like this):
"Hi! I can tell you about {name}'s projects — including {", ".join(repo_names[:3])}{", and more" if len(repo_names) > 3 else ""}. What would you like to know?"
"""
        return prompt.strip()
