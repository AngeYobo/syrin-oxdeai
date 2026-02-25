"""Provider registry: resolve provider name to Provider instance.

Moves provider resolution out of Agent so Agent depends on the Provider
abstraction only. New providers register here.
"""

from __future__ import annotations

from syrin.providers.base import Provider


def get_provider(provider_name: str) -> Provider:
    """Return the Provider instance for the given provider name.

    Use when you have a provider identifier (e.g. from ModelConfig.provider)
    but no Model instance. When using Model, prefer model.get_provider().

    Args:
        provider_name: openai, anthropic, ollama, litellm, etc.

    Returns:
        Provider instance for the given name.
    """
    name = (provider_name or "litellm").strip().lower()
    if name == "anthropic":
        from syrin.providers.anthropic import AnthropicProvider

        return AnthropicProvider()
    if name == "openai":
        from syrin.providers.openai import OpenAIProvider

        return OpenAIProvider()
    if name in ("ollama", "litellm"):
        from syrin.providers.litellm import LiteLLMProvider

        return LiteLLMProvider()
    from syrin.providers.litellm import LiteLLMProvider

    return LiteLLMProvider()
