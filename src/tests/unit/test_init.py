"""
Tests for `gitdar init` command - LM Studio flow.

Since init.py talks to two external services (LM Studio and GitHub),
we mock both. We never make real HTTP calls in unit tests.

Run with:
    pytest tests/unit/test_init.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


# ------------------------------------------------------------------ #
# Helpers — reusable fake responses                                    #
# ------------------------------------------------------------------ #

def _lmstudio_running_response(model_id: str = "phi-3-mini") -> MagicMock:
    """Fake LM Studio /v1/models response with one model loaded."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"data": [{"id": model_id}]}
    return mock


def _lmstudio_no_model_response() -> MagicMock:
    """Fake LM Studio response when server is on but no model loaded."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"data": []}
    return mock


def _github_valid_response(username: str = "rahulgitdar") -> MagicMock:
    """Fake GitHub /user response for a valid token."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"login": username}
    return mock


def _github_invalid_response() -> MagicMock:
    """Fake GitHub /user response for a bad token."""
    mock = MagicMock()
    mock.status_code = 401
    return mock


# ------------------------------------------------------------------ #
# Step 3 tests - is LM Studio server running?                          #
# ------------------------------------------------------------------ #

class TestLMStudioServerCheck:

    def test_exits_with_helpful_message_when_server_is_off(self):
        import httpx as httpx_module

        with patch("httpx.get", side_effect=httpx_module.ConnectError("refused")):
            result = runner.invoke(app, ["init"], input="1\n")

        assert result.exit_code == 1
        assert "Could not connect to LM Studio" in result.output
        assert "Start Server" in result.output

    def test_exits_when_server_times_out(self):
        import httpx as httpx_module

        with patch("httpx.get", side_effect=httpx_module.TimeoutException("timeout")):
            result = runner.invoke(app, ["init"], input="1\n")

        assert result.exit_code == 1
        assert "Could not connect to LM Studio" in result.output


# ------------------------------------------------------------------ #
# Step 4 tests - is a model loaded?                                    #
# ------------------------------------------------------------------ #

class TestModelLoadedCheck:

    def test_exits_with_helpful_message_when_no_model_loaded(self):
        with patch("httpx.get", return_value=_lmstudio_no_model_response()):
            result = runner.invoke(app, ["init"], input="1\n")

        assert result.exit_code == 1
        assert "No model loaded" in result.output

    def test_shows_model_name_when_loaded(self):
        with patch("httpx.get", return_value=_lmstudio_running_response("phi-3-mini")):
            with patch("cli.commands.init._validate_github_token", return_value=None):
                result = runner.invoke(app, ["init"], input="1\nghp_faketoken\n")

        assert "phi-3-mini" in result.output


# ------------------------------------------------------------------ #
# Step 5 tests - GitHub token validation                               #
# ------------------------------------------------------------------ #

class TestGitHubTokenValidation:

    def test_exits_when_github_token_is_invalid(self):
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [
                _lmstudio_running_response(),
                _lmstudio_running_response(),
                _github_invalid_response(),
            ]
            result = runner.invoke(app, ["init"], input="1\nghp_badtoken\n")

        assert result.exit_code == 1
        assert "Could not validate GitHub token" in result.output

    def test_shows_username_when_token_is_valid(self):
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [
                _lmstudio_running_response(),
                _lmstudio_running_response(),
                _github_valid_response("rahulgitdar"),
            ]
            with patch("cli.commands.init.loader.save"):
                result = runner.invoke(app, ["init"], input="1\nghp_validtoken\n")

        assert "rahulgitdar" in result.output


# ------------------------------------------------------------------ #
# Full happy path                                                      #
# ------------------------------------------------------------------ #

class TestFullHappyPath:

    def test_complete_setup_succeeds(self):
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [
                _lmstudio_running_response("phi-3-mini"),
                _lmstudio_running_response("phi-3-mini"),
                _github_valid_response("rahulgitdar"),
            ]
            with patch("cli.commands.init.loader.save") as mock_save:
                result = runner.invoke(app, ["init"], input="1\nghp_validtoken\n")

        assert result.exit_code == 0
        assert "Setup complete" in result.output
        assert "rahulgitdar" in result.output
        assert "LM Studio" in result.output
        assert "phi-3-mini" in result.output

        saved_config = mock_save.call_args[0][0]
        assert saved_config["llm"]["provider"] == "lmstudio"
        assert saved_config["llm"]["model"] == "phi-3-mini"
        assert saved_config["github"]["user"] == "rahulgitdar"