"""gitdar prs — shows open PRs ranked by urgency."""
from __future__ import annotations
import asyncio
import typer
from rich.console import Console
from src.cli.output.formatter import print_prs
from src.runtime.orchestrator import Orchestrator

console = Console()

def run() -> None:
    """Show your open PRs ranked by urgency and risk."""
    from src.config import loader
    if not loader.get_github_token():
        console.print("[red]✗ Not set up yet. Run [bold]gitdar init[/bold] first.[/red]")
        raise typer.Exit(code=1)

    from src.services.llm.providers.lmstudio import LMStudioProvider
    if not LMStudioProvider().is_available():
        console.print("[red]✗ LM Studio is not running. Start it and load a model first.[/red]")
        raise typer.Exit(code=1)

    console.print("[dim]Fetching your open PRs...[/dim]")

    try:
        result = asyncio.run(Orchestrator().get_ranked_prs())
    except RuntimeError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        raise typer.Exit(code=1)

    if not result:
        console.print("[red]✗ Could not fetch PRs. Check your GitHub token.[/red]")
        raise typer.Exit(code=1)

    print_prs(result)