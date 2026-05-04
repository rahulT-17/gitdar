"""
`gitdar init` — first time setup.

Flow for v1 (LM Studio only):
  1. Welcome message
  2. Ask which provider → only LM Studio for now
  3. Check if LM Studio server is running
  4. Check if a model is loaded
  5. Ask for GitHub token → validate it
  6. Save everything to ~/.gitdar-agent/config.toml
  7. Success message
"""
from __future__ import annotations

import sys

import httpx
import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

from src.config import loader
from src.services.llm.providers.lmstudio import LMStudioProvider

console = Console()


def run() -> None:
    """First-time setup — connect GitHub and configure your LLM provider."""

    # ------------------------------------------------------------------ #
    # Step 1 — Welcome                                                     #
    # ------------------------------------------------------------------ #
    console.print()
    console.print(Panel(
        "[bold]Welcome to gitdar setup[/bold]\n"
        "This will connect your GitHub account and configure your AI provider.\n"
        "Should take less than a minute.",
        border_style="dim",
    ))
    console.print()

    # ------------------------------------------------------------------ #
    # Step 2 — Choose provider                                             #
    # ------------------------------------------------------------------ #
    console.print("[bold]Choose your LLM provider:[/bold]")
    console.print("  [cyan]1.[/cyan] LM Studio  (local — nothing leaves your machine)")
    console.print()

    choice = Prompt.ask("Enter choice", choices=["1"], default="1")

    # v1: only LM Studio. More providers added in v2.
    provider_name = "lmstudio"
    console.print()

    # ------------------------------------------------------------------ #
    # Step 3 — Check if LM Studio server is running                        #
    # ------------------------------------------------------------------ #
    console.print("[dim]Checking if LM Studio is running...[/dim]")

    provider = LMStudioProvider()

    try:
        response = httpx.get("http://localhost:1234/v1/models", timeout=2.0)
        server_running = response.status_code == 200
    except Exception:
        server_running = False

    if not server_running:
        console.print()
        console.print("[red]✗ Could not connect to LM Studio.[/red]")
        console.print()
        console.print("  Make sure LM Studio is open and the local server is running.")
        console.print("  In LM Studio: go to the [bold]Local Server[/bold] tab and click [bold]Start Server[/bold].")
        console.print()
        console.print("[dim]Run [bold]gitdar init[/bold] again once the server is started.[/dim]")
        raise typer.Exit(code=1)

    console.print("[green]✓ LM Studio server is running[/green]")

    # ------------------------------------------------------------------ #
    # Step 4 — Check if a model is loaded                                  #
    # ------------------------------------------------------------------ #
    console.print("[dim]Checking if a model is loaded...[/dim]")

    loaded_model = provider.get_loaded_model()

    if not loaded_model:
        console.print()
        console.print("[red]✗ No model loaded in LM Studio.[/red]")
        console.print()
        console.print("  Open LM Studio, go to the [bold]Chat[/bold] tab,")
        console.print("  and load a model before running setup.")
        console.print()
        console.print("[dim]Run [bold]gitdar init[/bold] again once a model is loaded.[/dim]")
        raise typer.Exit(code=1)

    console.print(f"[green]✓ Model loaded:[/green] {loaded_model}")
    console.print()

    # ------------------------------------------------------------------ #
    # Step 5 — GitHub token                                                #
    # ------------------------------------------------------------------ #
    console.print("[bold]GitHub personal access token[/bold]")
    console.print("[dim]Needs scopes: repo, read:user[/dim]")
    console.print("[dim]Create one at: https://github.com/settings/tokens[/dim]")
    console.print()

    github_token = Prompt.ask("GitHub token", password=True)

    console.print("[dim]Validating token...[/dim]")

    github_user = _validate_github_token(github_token)

    if not github_user:
        console.print()
        console.print("[red]✗ Could not validate GitHub token.[/red]")
        console.print("  Check the token is correct and has [bold]repo[/bold] and [bold]read:user[/bold] scopes.")
        raise typer.Exit(code=1)

    console.print(f"[green]✓ Connected as[/green] [bold]{github_user}[/bold]")
    console.print()

    # ------------------------------------------------------------------ #
    # Step 6 — Save config                                                 #
    # ------------------------------------------------------------------ #
    config = {
        "github": {
            "token": github_token,
            "user": github_user,
        },
        "llm": {
            "provider": provider_name,
            "model": loaded_model,
        },
    }

    config_path = loader.get_config_path()
    try:
        loader.save(config)
    except Exception as exc:
        console.print()
        console.print("[red]✗ Failed to save gitdar config.[/red]")
        console.print(f"  Path: [bold]{config_path}[/bold]")
        console.print(f"  Error: {exc}")
        raise typer.Exit(code=1)

    # ------------------------------------------------------------------ #
    # Step 7 — Done                                                        #
    # ------------------------------------------------------------------ #
    console.print(Panel(
        f"[bold green]Setup complete![/bold green]\n\n"
        f"  GitHub user : [bold]{github_user}[/bold]\n"
        f"  Provider    : [bold]LM Studio[/bold]\n"
        f"  Model       : [bold]{loaded_model}[/bold]\n\n"
        f"Config saved to: [bold]{config_path}[/bold]\n\n"
        f"Run [bold cyan]gitdar standup[/bold cyan] to generate your first standup.",
        border_style="green",
    ))
    console.print()


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _validate_github_token(token: str) -> str | None:
    """
    Calls GET /user with the token.
    Returns the GitHub username if valid, None if not.
    Never raises — any failure returns None.
    """
    try:
        response = httpx.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=5.0,
        )
        if response.status_code == 200:
            return response.json().get("login")
        return None
    except Exception:
        return None
