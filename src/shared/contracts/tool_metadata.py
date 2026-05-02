from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ToolMetadata:
    """
    Every tool declares its own identity here.
    The runtime reads this — no hardcoded tool mappings anywhere else.

    Fields:
        tool_name:             unique snake_case identifier
        domain:                which domain owns this tool ("engineering")
        task_type:             "read" | "write" | "search"
        description:           one-line description for the planner prompt
        requires_confirmation: if True, executor asks user before running
        preferred_provider:    hint to LLM registry ("groq" for speed-critical)
        context_budget:        estimated token cost for this tool's prompt
    """
    tool_name: str
    domain: str
    task_type: str
    description: str
    requires_confirmation: bool = False
    preferred_provider: Optional[str] = None
    context_budget: int = 2000
