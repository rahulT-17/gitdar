"""
Config loader — reads ~/.gitdar-agent/config.toml and merges with defaults.
Everything in the app that needs a config value reads it through here.
Never access the config file directly anywhere else in the codebase.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import tomlkit

from src.config.defaults import CONFIG_FILE, DEFAULT_PROVIDER


def _config_path() -> Path:
    # expanduser() converts the ~ to the actual home directory path
    return Path(CONFIG_FILE).expanduser()


def get_config_path() -> Path:
    """Public accessor for the resolved config file path."""
    return _config_path()


def load() -> dict[str, Any]:
    """
    Load the full config from disk.
    Safe to call even before gitdar init has been run — returns an empty
    dict if the file doesn't exist yet, so nothing crashes.
    """
    path = _config_path()
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return dict(tomlkit.load(f))


def save(config: dict[str, Any]) -> None:
    """
    Write the config dict to disk as a TOML file.
    Creates the ~/.gitdar-agent/ directory if it doesn't exist yet.
    """
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        tomlkit.dump(config, f)


def get(key: str, default: Any = None) -> Any:
    """
    Read a single value using dot-notation.
    For example, get("llm.provider") reads config["llm"]["provider"].
    Returns default if the key doesn't exist at any level.
    """
    config = load()
    parts = key.split(".")
    val = config
    for part in parts:
        if not isinstance(val, dict):
            return default
        val = val.get(part, default)
    return val


def get_provider() -> str:
    """Returns the configured LLM provider, falling back to the default."""
    return get("llm.provider", DEFAULT_PROVIDER)


def get_github_token() -> Optional[str]:
    """
    Checks the config file first, then falls back to the GITHUB_TOKEN
    environment variable. This means the tool also works in CI environments
    where you'd set the token as an env var instead of running gitdar init.
    """
    return get("github.token") or os.environ.get("GITHUB_TOKEN")


def get_llm_api_key(provider: str) -> Optional[str]:
    """
    For cloud providers (groq, openai), returns their API key.
    Checks the config file first, then falls back to environment variables
    like GROQ_API_KEY or OPENAI_API_KEY.
    Local providers (lmstudio, ollama) don't need an API key so this
    returns None for them, which is fine.
    """
    env_map = {
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    from_config = get(f"llm.{provider}_api_key")
    if from_config:
        return from_config
    env_key = env_map.get(provider)
    return os.environ.get(env_key) if env_key else None
