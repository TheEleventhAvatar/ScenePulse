"""Configuration for LLM providers.

Loads settings from environment variables, optionally supplemented by a
local ``.env`` file at the repository root (never committed). Supported
variables:

- ``OPENAI_API_KEY``  -- API key for the OpenAI provider.
- ``OPENAI_MODEL``    -- Model name (default: ``gpt-4o-mini``).
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"


def _load_env_file(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file. Existing env vars take precedence."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def get_setting(name: str, default: str | None = None) -> str | None:
    """Return a setting from the environment, falling back to the .env file."""
    value = os.environ.get(name)
    if value is not None and value.strip():
        return value.strip()
    return _load_env_file(_ENV_FILE).get(name, default)


def get_openai_api_key() -> str | None:
    """Return the configured OpenAI API key, or None if unset."""
    return get_setting("OPENAI_API_KEY")


def get_openai_model() -> str:
    """Return the configured OpenAI model name."""
    return get_setting("OPENAI_MODEL", DEFAULT_OPENAI_MODEL) or DEFAULT_OPENAI_MODEL