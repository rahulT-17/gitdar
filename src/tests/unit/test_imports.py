"""
Smoke test — confirms the package installs and critical imports work.
Run after any structural change: pytest tests/unit/test_imports.py
"""
from shared.contracts.tool_response import ToolResponse, ToolStatus, LLMResponse
from shared.contracts.tool_metadata import ToolMetadata
from services.llm.base import BaseLLMProvider
from config import defaults, loader


def test_tool_response_contract():
    r = ToolResponse(tool_name="test_tool", status=ToolStatus.SUCCESS, data={"ok": True})
    assert r.succeeded()
    assert not r.failed()
    assert r.to_dict()["status"] == "success"


def test_tool_response_failure():
    r = ToolResponse(tool_name="test_tool", status=ToolStatus.FAILURE, error="boom")
    assert r.failed()
    assert r.error == "boom"


def test_tool_metadata():
    m = ToolMetadata(
        tool_name="get_prs",
        domain="engineering",
        task_type="read",
        description="Fetch open PRs for the current user",
    )
    assert m.context_budget == 2000        # default
    assert not m.requires_confirmation


def test_defaults_are_importable():
    assert defaults.DEFAULT_PROVIDER == "groq"
    assert "groq" in defaults.PROVIDER_CONFIGS
    assert "ollama" in defaults.FALLBACK_CHAIN


def test_base_provider_is_abstract():
    import inspect
    assert inspect.isabstract(BaseLLMProvider)
