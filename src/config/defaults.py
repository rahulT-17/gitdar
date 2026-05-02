"""
All default values live here.
Nothing else in the codebase hardcodes these values.
loader.py reads the user's config file and falls back to these.
"""

# Config file location
CONFIG_DIR = "~/.gitdar-agent"
CONFIG_FILE = "~/.gitdar-agent/config.toml"
DB_FILE = "~/.gitdar-agent/gitdar.db"

# Default LLM settings
DEFAULT_PROVIDER = "groq"
DEFAULT_MAX_TOKENS = 1000
DEFAULT_STANDUP_MODEL = "llama-3.3-70b-versatile"   # Groq default

# Provider base URLs
PROVIDER_CONFIGS: dict = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3",
        "api_key": "ollama",            # Ollama ignores this, required by openai client
    },
    "lmstudio": {
        "base_url": "http://localhost:1234/v1",
        "default_model": "local-model",
        "api_key": "lmstudio",
    },
}

# Provider fallback order when preferred provider is unavailable
FALLBACK_CHAIN = ["groq", "openai", "ollama"]

# GitHub API
GITHUB_API_BASE = "https://api.github.com"
GITHUB_CACHE_TTL_SECONDS = 300          # 5 minutes
GITHUB_SEARCH_RATE_LIMIT = 30          # requests per minute

# Standup lookback window
STANDUP_LOOKBACK_HOURS = 24

# Terminal output
MAX_TERMINAL_WIDTH = 80
