"""
Tests for LMStudioProvider.

Since LM Studio isn't running in CI, we mock the HTTP calls and the
openai client. This is how you test providers that depend on external
services — you never call the real server in unit tests.

Run these with:
    pytest tests/unit/test_lmstudio_provider.py -v
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.llm.providers.lmstudio import LMStudioProvider
from shared.contracts.tool_response import LLMResponse


# ------------------------------------------------------------------ #
# is_available() tests                                                 #
# ------------------------------------------------------------------ #

class TestIsAvailable:

    def test_returns_true_when_lmstudio_running_with_model_loaded(self):
        """Happy path: server up, one model loaded."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "mistral-7b-instruct", "object": "model"}]
        }

        with patch("httpx.get", return_value=mock_response):
            provider = LMStudioProvider()
            assert provider.is_available() is True

    def test_returns_false_when_lmstudio_running_but_no_model_loaded(self):
        """Server is up but no model selected in LM Studio UI."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        with patch("httpx.get", return_value=mock_response):
            provider = LMStudioProvider()
            assert provider.is_available() is False

    def test_returns_false_when_lmstudio_not_running(self):
        """Connection refused — LM Studio is closed."""
        import httpx as httpx_module

        with patch("httpx.get", side_effect=httpx_module.ConnectError("refused")):
            provider = LMStudioProvider()
            assert provider.is_available() is False

    def test_returns_false_on_timeout(self):
        """Slow response — 2s timeout fires."""
        import httpx as httpx_module

        with patch("httpx.get", side_effect=httpx_module.TimeoutException("timeout")):
            provider = LMStudioProvider()
            assert provider.is_available() is False

    def test_returns_false_on_non_200_status(self):
        """Server returns error status."""
        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch("httpx.get", return_value=mock_response):
            provider = LMStudioProvider()
            assert provider.is_available() is False


# ------------------------------------------------------------------ #
# get_loaded_model() tests                                             #
# ------------------------------------------------------------------ #

class TestGetLoadedModel:

    def test_returns_model_id_when_model_is_loaded(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "llama-3-8b-instruct"}]
        }

        with patch("httpx.get", return_value=mock_response):
            provider = LMStudioProvider()
            assert provider.get_loaded_model() == "llama-3-8b-instruct"

    def test_returns_none_when_no_model_loaded(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        with patch("httpx.get", return_value=mock_response):
            provider = LMStudioProvider()
            assert provider.get_loaded_model() is None

    def test_returns_none_when_server_unavailable(self):
        import httpx as httpx_module

        with patch("httpx.get", side_effect=httpx_module.ConnectError("refused")):
            provider = LMStudioProvider()
            assert provider.get_loaded_model() is None


# ------------------------------------------------------------------ #
# complete() tests                                                     #
# ------------------------------------------------------------------ #

class TestComplete:

    @pytest.fixture
    def mock_completion(self):
        """Fake openai ChatCompletion response object."""
        choice = MagicMock()
        choice.message.content = "Here is your standup summary."

        usage = MagicMock()
        usage.total_tokens = 142

        completion = MagicMock()
        completion.choices = [choice]
        completion.usage = usage
        return completion

    @pytest.mark.asyncio
    async def test_returns_llm_response_on_success(self, mock_completion):
        provider = LMStudioProvider(model="mistral-7b")

        # Mock the openai async client
        with patch.object(
            provider._client.chat.completions,
            "create",
            new=AsyncMock(return_value=mock_completion),
        ):
            result = await provider.complete(
                messages=[{"role": "user", "content": "Summarise my PRs"}]
            )

        assert isinstance(result, LLMResponse)
        assert result.content == "Here is your standup summary."
        assert result.provider == "lmstudio"
        assert result.model == "mistral-7b"
        assert result.tokens_used == 142
        assert result.latency_ms >= 0    # mock returns instantly so 0.0 is valid; real calls will be >0

    @pytest.mark.asyncio
    async def test_uses_loaded_model_when_model_is_placeholder(self, mock_completion):
        """
        When model is still 'local-model' (the default placeholder),
        complete() should ask LM Studio which model is loaded and use that.
        """
        provider = LMStudioProvider()   # model defaults to "local-model"
        assert provider.model == "local-model"

        mock_models_response = MagicMock()
        mock_models_response.status_code = 200
        mock_models_response.json.return_value = {
            "data": [{"id": "phi-3-mini"}]
        }

        with patch("httpx.get", return_value=mock_models_response):
            with patch.object(
                provider._client.chat.completions,
                "create",
                new=AsyncMock(return_value=mock_completion),
            ) as mock_create:
                await provider.complete(
                    messages=[{"role": "user", "content": "hello"}]
                )
                # confirm it used the resolved model name, not "local-model"
                call_kwargs = mock_create.call_args.kwargs
                assert call_kwargs["model"] == "phi-3-mini"

    @pytest.mark.asyncio
    async def test_uses_explicit_model_without_calling_health_endpoint(self, mock_completion):
        """If model is explicitly set, skip the /v1/models lookup."""
        provider = LMStudioProvider(model="llama-3-8b")

        with patch("httpx.get") as mock_http:
            with patch.object(
                provider._client.chat.completions,
                "create",
                new=AsyncMock(return_value=mock_completion),
            ):
                await provider.complete(
                    messages=[{"role": "user", "content": "hello"}]
                )

            # httpx.get should NOT have been called — no model resolution needed
            mock_http.assert_not_called()