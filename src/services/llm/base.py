from __future__ import annotations

from abc import ABC, abstractmethod

from shared.contracts.tool_response import LLMResponse


class BaseLLMProvider(ABC):

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        max_tokens: int = 1000,
    ) -> LLMResponse:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Health check. Returns False if unavailable — never raises."""
        pass