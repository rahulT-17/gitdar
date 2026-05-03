"""
Engineering domain tools.

Thin adapters — their only job is:
  1. Call the repository
  2. Wrap the result in a ToolResponse
  3. Return it to the executor

No business logic. No formatting. No LLM calls.
Never raise to the caller — return ToolStatus.FAILURE instead.
"""
from __future__ import annotations

from src.config import loader
from src.domains.engineering.infra.repository import GitHubRepository
from src.shared.contracts.tool_metadata import ToolMetadata
from src.shared.contracts.tool_response import ToolResponse, ToolStatus


# ------------------------------------------------------------------ #
# Tool metadata — runtime reads these, no hardcoded lists anywhere    #
# ------------------------------------------------------------------ #

GET_OPEN_PRS_METADATA = ToolMetadata(
    tool_name="get_open_prs",
    domain="engineering",
    task_type="read",
    description="Fetch all open pull requests for the authenticated GitHub user.",
)

GET_RECENT_ACTIVITY_METADATA = ToolMetadata(
    tool_name="get_recent_activity",
    domain="engineering",
    task_type="read",
    description="Fetch PRs merged or closed in the last 24 hours for standup generation.",
)


# ------------------------------------------------------------------ #
# Tools                                                                #
# ------------------------------------------------------------------ #

def get_open_prs() -> ToolResponse:
    """Fetches all open PRs. Used by gitdar prs."""
    try:
        token = loader.get_github_token()
        if not token:
            return ToolResponse(
                tool_name="get_open_prs",
                status=ToolStatus.FAILURE,
                error="No GitHub token found. Run gitdar init first.",
            )

        repo = GitHubRepository(token=token)
        prs  = repo.get_open_pull_requests()

        return ToolResponse(
            tool_name="get_open_prs",
            status=ToolStatus.SUCCESS,
            data=prs,
            message=f"Fetched {len(prs)} open PRs.",
        )

    except Exception as e:
        return ToolResponse(
            tool_name="get_open_prs",
            status=ToolStatus.FAILURE,
            error=str(e),
        )


def get_recent_activity(since_hours: int = 24) -> ToolResponse:
    """Fetches recently merged/closed PRs. Used by gitdar standup."""
    try:
        token = loader.get_github_token()
        if not token:
            return ToolResponse(
                tool_name="get_recent_activity",
                status=ToolStatus.FAILURE,
                error="No GitHub token found. Run gitdar init first.",
            )

        repo = GitHubRepository(token=token)
        prs  = repo.get_recent_activity(since_hours=since_hours)

        return ToolResponse(
            tool_name="get_recent_activity",
            status=ToolStatus.SUCCESS,
            data=prs,
            message=f"Fetched {len(prs)} recently active PRs.",
        )

    except Exception as e:
        return ToolResponse(
            tool_name="get_recent_activity",
            status=ToolStatus.FAILURE,
            error=str(e),
        )