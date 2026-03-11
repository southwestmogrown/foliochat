"""
FolioChat CLI — Turn your GitHub profile into an intelligent portfolio chatbot.

Usage:
    foliochat build --username southwestmogrown
    foliochat serve --username southwestmogrown
    foliochat build --username southwestmogrown --refresh
"""

import typer
from rich.console import Console
from rich.panel import Panel
from typing import Optional

app = typer.Typer(
    name="foliochat",
    help="Turn your GitHub profile into an intelligent portfolio chatbot.",
    add_completion=False,
)
console = Console()


@app.command()
def build(
    username: str = typer.Option(..., "--username", "-u", help="GitHub username to crawl"),
    embedder: str = typer.Option("local", "--embedder", "-e", help="Embedding backend: local | openai | voyage"),
    refresh: bool = typer.Option(False, "--refresh", help="Re-crawl and rebuild existing database"),
    token: Optional[str] = typer.Option(None, "--token", "-t", help="GitHub personal access token (increases rate limit)"),
    include_private: bool = typer.Option(False, "--include-private", help="Include private repos (requires token)"),
):
    """
    Crawl a GitHub profile and build a local vector database.

    Examples:
        foliochat build --username southwestmogrown
        foliochat build --username southwestmogrown --embedder openai
        foliochat build --username southwestmogrown --refresh
    """
    from cli.crawler.github import GithubCrawler
    from cli.chunker.chunker import Chunker
    from cli.embedder.embedder import get_embedder
    from cli.store.chroma import ChromaStore
    from cli.serve.prompt import SystemPromptGenerator
    import json
    from pathlib import Path

    console.print(Panel(
        f"[bold orange1]FolioChat[/bold orange1] — Building portfolio database for [cyan]{username}[/cyan]",
        border_style="orange1"
    ))

    # 1. Crawl
    console.print("\n[bold]Step 1/4:[/bold] Crawling GitHub profile...")
    crawler = GithubCrawler(token=token)
    portfolio_data = crawler.crawl(username, include_private=include_private)
    console.print(f"  [green]✓[/green] Found {len(portfolio_data['repos'])} repositories")

    # 2. Chunk
    console.print("\n[bold]Step 2/4:[/bold] Chunking content...")
    chunker = Chunker()
    chunks = chunker.chunk(portfolio_data)
    console.print(f"  [green]✓[/green] Created {len(chunks)} semantic chunks")

    # 3. Embed + Store
    console.print(f"\n[bold]Step 3/4:[/bold] Embedding with [cyan]{embedder}[/cyan] backend...")
    embedder_instance = get_embedder(embedder)
    store = ChromaStore(username=username)

    if refresh:
        store.clear()
        console.print("  [yellow]↺[/yellow] Cleared existing database")

    store.add_chunks(chunks, embedder_instance)
    console.print(f"  [green]✓[/green] Stored {len(chunks)} chunks in vector database")

    # 4. Generate system prompt
    console.print("\n[bold]Step 4/4:[/bold] Generating system prompt...")
    generator = SystemPromptGenerator()
    system_prompt = generator.generate(portfolio_data)
    store.save_system_prompt(system_prompt)
    console.print("  [green]✓[/green] System prompt saved")

    # Save metadata
    meta_path = store.metadata_path()
    meta_path.write_text(json.dumps({
        "username": username,
        "embedder": embedder,
        "repo_count": len(portfolio_data["repos"]),
        "chunk_count": len(chunks),
        "built_at": portfolio_data["crawled_at"],
    }, indent=2))

    console.print(Panel(
        f"[green]✓ Done![/green] Database built for [cyan]{username}[/cyan]\n\n"
        f"Run [bold]foliochat serve --username {username}[/bold] to start the chat server.",
        border_style="green"
    ))


@app.command()
def serve(
    username: str = typer.Option(..., "--username", "-u", help="GitHub username to serve"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to run the server on"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    llm: str = typer.Option("openai", "--llm", help="LLM provider: openai | anthropic | ollama"),
    model: Optional[str] = typer.Option(None, "--model", help="Model name override"),
):
    """
    Start the FolioChat API server.

    Examples:
        foliochat serve --username southwestmogrown
        foliochat serve --username southwestmogrown --port 8080 --llm anthropic
        foliochat serve --username southwestmogrown --llm ollama --model llama3.1
    """
    from cli.store.chroma import ChromaStore
    import uvicorn

    store = ChromaStore(username=username)
    if not store.exists():
        console.print(f"[red]✗[/red] No database found for [cyan]{username}[/cyan].")
        console.print(f"  Run [bold]foliochat build --username {username}[/bold] first.")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold orange1]FolioChat[/bold orange1] serving [cyan]{username}[/cyan]\n\n"
        f"API:       [link]http://{host}:{port}[/link]\n"
        f"LLM:       {llm}\n"
        f"Chat:      POST http://{host}:{port}/chat\n"
        f"Context:   GET  http://{host}:{port}/context",
        border_style="orange1"
    ))

    import os
    os.environ["FOLIOCHAT_USERNAME"] = username
    os.environ["FOLIOCHAT_LLM"] = llm
    if model:
        os.environ["FOLIOCHAT_MODEL"] = model

    uvicorn.run(
        "cli.serve.api:app",
        host=host,
        port=port,
        reload=False,
    )


@app.command()
def info(
    username: str = typer.Option(..., "--username", "-u", help="GitHub username"),
):
    """Show info about a built database."""
    from cli.store.chroma import ChromaStore
    import json

    store = ChromaStore(username=username)
    if not store.exists():
        console.print(f"[red]✗[/red] No database found for [cyan]{username}[/cyan].")
        raise typer.Exit(1)

    meta = json.loads(store.metadata_path().read_text())
    console.print(Panel(
        "\n".join([f"[cyan]{k}:[/cyan] {v}" for k, v in meta.items()]),
        title=f"FolioChat — {username}",
        border_style="orange1"
    ))


if __name__ == "__main__":
    app()