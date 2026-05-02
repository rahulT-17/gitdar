from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ToolStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"   # ran but result is incomplete
    SKIPPED = "skipped"   # executor decided not to run


@dataclass
class LLMResponse:
    """Attached to a ToolResponse when the tool made an LLM call."""
    content: str
    provider: str
    model: str
    latency_ms: float
    tokens_used: int


@dataclass
class ToolResponse:
    """
    The single execution contract returned by every tool in the system.

    Rules:
    - Tools ALWAYS return a ToolResponse — they never raise to the caller.
    - Catch exceptions inside the tool, return status=FAILURE with error set.
    - latency_ms is stamped by the executor, not the tool itself.
    """
    tool_name: str
    status: ToolStatus
    data: Any = None
    message: str = ""
    error: Optional[str] = None
    latency_ms: Optional[float] = None
    llm_response: Optional[LLMResponse] = None   # set when tool used an LLM
    timestamp: float = field(default_factory=time.time)

    def succeeded(self) -> bool:
        return self.status == ToolStatus.SUCCESS

    def failed(self) -> bool:
        return self.status == ToolStatus.FAILURE

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "data": self.data,
            "message": self.message,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }
