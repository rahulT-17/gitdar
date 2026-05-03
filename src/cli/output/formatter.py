"""
Terminal formatter — owns all visual output for gitdar.

One job: take data, make it look good in the terminal.
No logic. No LLM calls. Just formatting.
"""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.runtime.orchestrator import PRsResult, StandupResult

console = Console()


def print_standup(result: StandupResult) -> None:
    """Prints the standup output in the gitdar style."""
    github_ms = result.latency_ms.get("github_fetch", 0)
    llm_ms    = result.latency_ms.get("llm_call", 0)
    total_s   = round((github_ms + llm_ms) / 1000, 1)

    console.print()
    console.print(Panel(
        result.standup_text,
        title="[bold]your standup[/bold]",
        border_style="dim",
        padding=(1, 2),
    ))
    console.print(
        f"[dim]Generated in {total_s}s "
        f"(github: {int(github_ms)}ms, "
        f"llm: {int(llm_ms)}ms)[/dim]"
    )
    console.print()


def print_prs(result: PRsResult) -> None:
    """Prints ranked PRs with LLM reasoning."""
    console.print()

    if not result.prs:
        console.print(Panel(
            "[green]No open PRs — you're clear![/green]",
            border_style="dim",
        ))
        return

    # urgency indicators based on PR state
    lines = []
    for pr in result.prs:
        if pr.has_conflicts or pr.age_hours > 72:
            indicator = "[red]🔴[/red]"
        elif pr.needs_review or pr.review_requests:
            indicator = "[yellow]🟡[/yellow]"
        else:
            indicator = "[green]🟢[/green]"

        lines.append(
            f"{indicator} PR #{pr.number} — {pr.title} "
            f"[dim]({pr.repository.full_name})[/dim]"
        )

    pr_list = "\n".join(lines)

    console.print(Panel(
        pr_list,
        title="[bold]open PRs[/bold]",
        border_style="dim",
        padding=(1, 2),
    ))

    # LLM reasoning below the list
    console.print()
    console.print("[dim]── reasoning ──[/dim]")
    console.print(result.reasoning)
    console.print()

    github_ms = result.latency_ms.get("github_fetch", 0)
    llm_ms    = result.latency_ms.get("llm_call", 0)
    total_s   = round((github_ms + llm_ms) / 1000, 1)
    console.print(f"[dim]Generated in {total_s}s[/dim]")
    console.print()