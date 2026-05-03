"""gitdar standup — generates your daily standup."""
from __future__ import annotations
import asyncio
import typer
from rich.console import Console
from src.cli.output.formatter import print_standup
from src.runtime.orchestrator import Orchestrator

console = Console()

def run(
    copy: bool = typer.Option(False, "--copy", "-c", help="Copy to clipboard."),
) -> None:
    """Generate your standup from yesterday's GitHub activity."""
    from src.config import loader
    if not loader.get_github_token():
        console.print("[red]✗ Not set up yet. Run [bold]gitdar init[/bold] first.[/red]")
        raise typer.Exit(code=1)

    from src.services.llm.providers.lmstudio import LMStudioProvider
    if not LMStudioProvider().is_available():
        console.print("[red]✗ LM Studio is not running. Start it and load a model first.[/red]")
        raise typer.Exit(code=1)

    console.print("[dim]Fetching your GitHub activity...[/dim]")

    try:
        result = asyncio.run(Orchestrator().generate_standup())
        
    except RuntimeError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        raise typer.Exit(code=1)

    if not result:
        console.print("[red]✗ Could not generate standup. Check your GitHub token.[/red]")
        raise typer.Exit(code=1)

    print_standup(result)

    if copy:
        try:
            import pyperclip
            pyperclip.copy(result.standup_text)
            console.print("[green]✓ Copied to clipboard[/green]")
        except Exception:
            console.print("[dim]Could not copy to clipboard[/dim]")