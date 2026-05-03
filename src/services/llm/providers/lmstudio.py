"""
LM Studio provider.

LM Studio exposes an OpenAI-compatible API on localhost:1234.
You need LM Studio running with a model loaded before this provider works.

How is_available() works:
  LM Studio has a /v1/models endpoint that lists loaded models.
  We hit that with a 2s timeout. If it responds and returns at least
  one model, the provider is available. If LM Studio isn't running,
  the connection is refused immediately — no hanging.

How complete() works:
  Uses openai.AsyncOpenAI pointed at localhost:1234/v1.
  The api_key value ("lmstudio") is required by the openai client
  but ignored by LM Studio — it accepts anything.
  We stamp latency ourselves using time.perf_counter().
"""
from __future__ import annotations

import time
from typing import Optional

import httpx
from openai import AsyncOpenAI

from src.services.llm.base import BaseLLMProvider
from src.shared.contracts.tool_response import LLMResponse
from src.config.defaults import PROVIDER_CONFIGS


class LMStudioProvider(BaseLLMProvider):

    BASE_URL   = PROVIDER_CONFIGS["lmstudio"]["base_url"]   # http://localhost:1234/v1
    MODEL      = PROVIDER_CONFIGS["lmstudio"]["default_model"]
    API_KEY    = PROVIDER_CONFIGS["lmstudio"]["api_key"]    # "lmstudio" — ignored by server
    HEALTH_URL = "http://localhost:1234/api/v0/models"          # returns {"data": [...models...]}

    def __init__(self, model: Optional[str] = None) -> None:
        self.model = model or self.MODEL
        self._client = AsyncOpenAI(
            base_url=self.BASE_URL,
            api_key=self.API_KEY,
        )

    # ------------------------------------------------------------------ #
    # Health check                                                         #
    # ------------------------------------------------------------------ #

    def is_available(self) -> bool:
        """
        Returns True only if:
          1. LM Studio is running (HTTP connection succeeds)
          2. At least one model is loaded (data list is non-empty)

        Never raises — any failure returns False.
        Timeout is 2s so a slow network doesn't block the CLI startup.
        """
        try:
            response = httpx.get(self.HEALTH_URL, timeout=2.0)
            if response.status_code != 200:
                return False
            body = response.json()
            models = body.get("data", [])

            loaded_models = [m for m in models if m.get("state") == "loaded"]
            return len(loaded_models) > 0
        except Exception:
            return False

    def get_loaded_model(self) -> Optional[str]:
        """
        Returns the name of the first loaded model, or None if unavailable.
        Useful so the caller doesn't need to hardcode a model name —
        LM Studio loads whatever model the user has selected in the UI.
        """
        try:
            response = httpx.get(self.HEALTH_URL, timeout=2.0)
            if response.status_code != 200:
                return None
            body = response.json()
            models = body.get("data", [])
            if not models:
                return None
            
            for model in models:
                if model.get("state") == "loaded":
                    return model.get("id")
            return None
        
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # Completion                                                           #
    # ------------------------------------------------------------------ #

    async def complete(
        self,
        messages: list[dict],
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """
        Send messages to LM Studio and return a structured LLMResponse.

        We use the first loaded model if self.model is still the default
        placeholder ("local-model"). This means the user never has to
        configure a model name — LM Studio manages that through its UI.
        """
        model = self._resolve_model()

        start = time.perf_counter()

        completion = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        content    = completion.choices[0].message.content or ""
        tokens     = completion.usage.total_tokens if completion.usage else 0

        return LLMResponse(
            content=content,
            provider="lmstudio",
            model=model,
            latency_ms=round(elapsed_ms, 1),
            tokens_used=tokens,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _resolve_model(self) -> str:
        """
        If the configured model is the generic placeholder, ask LM Studio
        which model is actually loaded and use that instead.
        Falls back to the placeholder if the server is unreachable
        (complete() will then fail with a clear API error).
        """
        if self.model and self.model != "local-model":
            return self.model     # user explicitly set a model — use it

        loaded = self.get_loaded_model()
        if loaded:
            return loaded       
        raise RuntimeError("It seems like LM Studio isn't running or doesn't have any loaded models.")
    