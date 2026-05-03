"""
Orchestrator — coordinates the full standup and prs flow.

Exactly what the user described:
  1. Check GitHub token exists
  2. Fetch GitHub data via executor + tools
  3. Call LM Studio to reason and summarise
  4. Return result to the CLI command for formatting

It does not know HOW to fetch PRs — that's tools.py
It does not know HOW to call LLM — that's the provider
It does not know HOW to format — that's formatter.py
It just coordinates who does what and in what order.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config import loader
from src.domains.application.tools import (
    get_open_prs,
    get_recent_activity,
)
from src.runtime.executor import Executor
from src.services.llm.providers.lmstudio import LMStudioProvider
from src.shared.contracts.tool_response import ToolResponse, ToolStatus


@dataclass
class StandupResult:
    """Clean result handed back to the CLI standup command."""
    raw_prs: list          # PullRequest objects from GitHub
    standup_text: str      # LLM generated standup text
    latency_ms: dict       # latency per step for observability


@dataclass
class PRsResult:
    """Clean result handed back to the CLI prs command."""
    prs: list              # PullRequest objects from GitHub
    reasoning: str         # LLM reasoning about priority
    latency_ms: dict       # latency per step for observability


class Orchestrator:

    def __init__(self) -> None:
        self.executor = Executor()
        self.provider = LMStudioProvider()

    # ---------------------------------------------------------------- #
    # gitdar standup                                                     #
    # ---------------------------------------------------------------- #

    async def generate_standup(self) -> StandupResult | None:
        """
        Full standup flow:
          1. Check token
          2. Fetch recent GitHub activity
          3. Send to LM Studio for summarisation
          4. Return StandupResult to CLI
        """
        latency = {}

        # Step 1 — check token
        token = loader.get_github_token()
        if not token:
            return None

        # Step 2 — fetch GitHub data via executor
        activity_response: ToolResponse = self.executor.run(
            get_recent_activity,
            since_hours=24,
        )
        latency["github_fetch"] = activity_response.latency_ms

        if activity_response.failed():
            return None

        prs = activity_response.data or []

        # Step 3 — build prompt and call LM Studio
        prompt = self._build_standup_prompt(prs)

        llm_response = await self.provider.complete(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        latency["llm_call"] = llm_response.latency_ms

        return StandupResult(
            raw_prs=prs,
            standup_text=llm_response.content,
            latency_ms=latency,
        )

    # ---------------------------------------------------------------- #
    # gitdar prs                                                         #
    # ---------------------------------------------------------------- #

    async def get_ranked_prs(self) -> PRsResult | None:
        """
        Full prs flow:
          1. Check token
          2. Fetch open PRs
          3. Send to LM Studio for risk reasoning
          4. Return PRsResult to CLI
        """
        latency = {}

        token = loader.get_github_token()
        if not token:
            return None

        # Fetch open PRs
        prs_response: ToolResponse = self.executor.run(get_open_prs)
        latency["github_fetch"] = prs_response.latency_ms

        if prs_response.failed():
            return None

        prs = prs_response.data or []

        # Ask LM Studio to reason about priority
        prompt = self._build_prs_prompt(prs)

        llm_response = await self.provider.complete(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
        )
        latency["llm_call"] = llm_response.latency_ms

        return PRsResult(
            prs=prs,
            reasoning=llm_response.content,
            latency_ms=latency,
        )

    # ---------------------------------------------------------------- #
    # Prompt builders                                                    #
    # ---------------------------------------------------------------- #

    def _build_standup_prompt(self, prs: list) -> str:
        if not prs:
            return (
                "I had no pull request activity on GitHub yesterday. "
                "Write a brief standup noting this."
            )

        pr_lines = []
        for pr in prs:
            status = pr.state.value
            repo   = pr.repository.full_name
            pr_lines.append(
                f"- PR #{pr.number} '{pr.title}' in {repo} — {status}"
                + (f" (merged)" if pr.merged_at else "")
            )

        pr_summary = "\n".join(pr_lines)

        return f"""You are a developer assistant. Based on this GitHub activity from the last 24 hours, write a concise daily standup.

GitHub activity:
{pr_summary}

Write the standup in this exact format:
YESTERDAY
- [what was done]

TODAY
- [what is planned based on open items]

BLOCKED
- [anything blocking, or 'Nothing blocking me']

Be concise. Use plain English. No markdown. No bullet symbols other than dashes."""

    def _build_prs_prompt(self, prs: list) -> str:
        if not prs:
            return "I have no open pull requests right now."

        pr_lines = []
        for pr in prs:
            flags = []
            if pr.has_conflicts:
                flags.append("has conflicts")
            if pr.is_draft:
                flags.append("draft")
            if pr.needs_review:
                flags.append("needs review")
            if pr.changes_requested:
                flags.append("changes requested")
            if pr.age_hours > 72:
                flags.append(f"open {int(pr.age_hours)}hrs")
            if pr.review_requests:
                reviewers = ", ".join(r.login for r in pr.review_requests)
                flags.append(f"waiting on {reviewers}")

            flag_str = f" [{', '.join(flags)}]" if flags else ""
            pr_lines.append(
                f"- PR #{pr.number} '{pr.title}' "
                f"in {pr.repository.full_name}{flag_str}"
            )

        pr_summary = "\n".join(pr_lines)

        return f"""You are a developer assistant. Rank these open pull requests by urgency.

Open PRs:
{pr_summary}

For each PR explain in one line why it needs attention and what to do.
Order from most urgent to least urgent.
Be direct. No markdown headers."""