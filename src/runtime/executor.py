"""
Executor — runs tools and stamps latency on every call.

Single responsibility:
  - Take a tool function
  - Run it
  - Stamp how long it took onto the ToolResponse
  - Return it to the orchestrator

Does not decide WHAT to run — that's the planner.
Does not coordinate flow — that's the orchestrator.
Just runs one tool at a time and measures it.
"""
from __future__ import annotations

import time
from typing import Callable

from src.shared.contracts.tool_response import ToolResponse, ToolStatus


class Executor:

    def run(self, tool_fn: Callable, **kwargs) -> ToolResponse:
        """
        Runs a single tool, stamps latency, returns ToolResponse.

        If the tool raises despite our contract, we catch it here.
        This is the last safety net before the orchestrator.
        """
        start = time.perf_counter()

        try:
            response: ToolResponse = tool_fn(**kwargs)
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return ToolResponse(
                tool_name=getattr(tool_fn, "__name__", "unknown"),
                status=ToolStatus.FAILURE,
                error=f"Tool raised unexpectedly: {e}",
                latency_ms=round(elapsed_ms, 1),
            )

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.latency_ms = round(elapsed_ms, 1)
        return response