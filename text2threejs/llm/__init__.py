"""LLM interface for the Text-to-Three.js pipeline.

Provider-agnostic. The LLM produces TextSceneSpec data, never raw executable
JavaScript. A deterministic mock provider is included so the application runs
without an API key; when an OpenAI API key is configured (via OPENAI_API_KEY
in the environment or a .env file), ``create_provider()`` returns the OpenAI
provider instead.
"""

from .base import LLMProvider, LLMResult, SceneGenerationError
from .mock import MockLLM
from .openai import OpenAIProvider


def create_provider() -> LLMProvider:
    """Return the best available LLM provider.

    Uses OpenAI when an API key is configured; otherwise falls back to the
    deterministic MockLLM so the application still runs offline.
    """
    from .config import get_openai_api_key

    if get_openai_api_key():
        return OpenAIProvider()
    return MockLLM()


__all__ = [
    "LLMProvider",
    "LLMResult",
    "SceneGenerationError",
    "MockLLM",
    "OpenAIProvider",
    "create_provider",
]